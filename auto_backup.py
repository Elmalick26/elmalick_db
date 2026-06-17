"""
نظام النسخ الاحتياطي التلقائي - PostgreSQL
Auto Backup System (pg_dump / pg_restore)
"""

import os
import shutil
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

import schedule

import db_path as db_paths_module
from app_logger import AppLogger
from config_manager import ConfigManager
from db_path import find_pg_tool


class AutoBackupSystem:
    """نظام النسخ الاحتياطي التلقائي - PostgreSQL"""

    def __init__(self, db_path=None, backup_dir=None):
        # db_path unused with PostgreSQL (kept for backward compatibility)
        self.backup_dir = Path(backup_dir) if backup_dir else Path(db_paths_module.get_backup_dir())
        self._config = ConfigManager()

        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            AppLogger.error("AutoBackup", f"فشل في إنشاء مجلد النسخ الاحتياطي: {e}", e)

        # FIX 4: Use threading.Event instead of a bare bool flag.
        # event.wait(60) blocks up to 60s but wakes immediately on event.set(),
        # so stop_auto_backup() now halts the thread instantly instead of
        # waiting up to 60 seconds for the sleep to expire.
        self._stop_event = threading.Event()

        # FIX 1: Use a per-instance schedule.Scheduler() instead of the global
        # module-level scheduler.  The global schedule.clear() call in
        # stop_auto_backup() would otherwise cancel ALL scheduled jobs across
        # the entire application, including jobs from other instances.
        self._scheduler = schedule.Scheduler()

        self.backup_thread: Thread | None = None

    # ── internal helpers ────────────────────────────────────────────────────

    def _log(self, level: str, message: str, exception: Exception | None = None) -> None:
        """Route log messages through AppLogger.

        FIX 3: Added `exception` parameter so callers inside except-blocks can
        forward the live exception object.  AppLogger.error() then captures the
        full stack trace via exception.__traceback__ instead of silently dropping it.
        """
        if level == "info":
            AppLogger.info("AutoBackup", message)
        elif level == "warning":
            AppLogger.warning("AutoBackup", message)
        elif level == "error":
            AppLogger.error("AutoBackup", message, exception)

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set() and self.backup_thread is not None and self.backup_thread.is_alive()

    # ── core backup / restore ────────────────────────────────────────────────

    def create_backup(self) -> str | None:
        """
        إنشاء نسخة احتياطية من قاعدة PostgreSQL باستخدام pg_dump.
        الملفات بصيغة SQL نقية (.sql) مع عبارات DROP للاستعادة الآمنة.
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"backup_auto_{timestamp}.sql"

            db_host = self._config.db_host
            db_port = str(self._config.db_port)
            db_name = self._config.db_name
            db_user = self._config.db_user
            db_password = self._config.db_password

            env = os.environ.copy()
            env["PGPASSWORD"] = db_password

            # FIX 5: Validate find_pg_tool() before using it.
            # If it returns None (pg_dump not installed / not in PATH), subprocess.run
            # raises a confusing TypeError instead of a clear "tool not found" message.
            pg_dump = find_pg_tool("pg_dump")
            if not pg_dump:
                self._log("error", "أداة pg_dump غير موجودة في PATH — تأكد من تثبيت أدوات PostgreSQL")
                return None

            # FIX 2: Added --clean so the SQL file contains DROP TABLE IF EXISTS
            # before each CREATE TABLE.  Without this, restoring onto a non-empty
            # database fails with "relation already exists" errors because psql has
            # no --clean flag of its own (unlike pg_restore).
            dump_command = [
                pg_dump,
                "-h",
                db_host,
                "-p",
                db_port,
                "-U",
                db_user,
                "--clean",
                "--if-exists",
                "-f",
                str(backup_file),
                db_name,
            ]

            result = subprocess.run(dump_command, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                self._log("error", f"pg_dump فشل: {result.stderr.strip()}")
                return None

            self._log("info", f"تم إنشاء نسخة احتياطية بنجاح: {backup_file.name}")
            self.cleanup_old_backups(keep_days=30)
            return str(backup_file)

        except FileNotFoundError as e:
            self._log("error", f"أداة pg_dump غير موجودة: {e}", e)
            return None
        except Exception as e:
            self._log("error", f"فشل إنشاء النسخة الاحتياطية: {e}", e)
            return None

    def cleanup_old_backups(self, keep_days: int = 30) -> None:
        """حذف النسخ الاحتياطية التلقائية القديمة"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            for pattern in ("backup_auto_*.backup", "backup_auto_*.sql"):
                for backup_file in self.backup_dir.glob(pattern):
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        self._log("info", f"تم حذف نسخة قديمة: {backup_file.name}")
        except Exception as e:
            self._log("warning", f"خطأ في تنظيف النسخ القديمة: {e}", e)

    def _is_custom_backup_file(self, backup_path: Path) -> bool:
        """Detect PostgreSQL custom-format dump by file signature (PGDMP)."""
        try:
            with open(backup_path, "rb") as f:
                return f.read(5) == b"PGDMP"
        except Exception:
            return False

    def restore_backup(self, backup_file: str) -> bool:
        """
        استعادة قاعدة PostgreSQL من نسخة احتياطية.
        .backup → pg_restore
        .sql    → psql  (SQL dump must include --clean, see create_backup)
        """
        try:
            backup_path = Path(backup_file)

            if not backup_path.exists():
                self._log("error", f"النسخة الاحتياطية غير موجودة: {backup_file}")
                return False

            db_host = self._config.db_host
            db_port = str(self._config.db_port)
            db_name = self._config.db_name
            db_user = self._config.db_user
            db_password = self._config.db_password

            env = os.environ.copy()
            env["PGPASSWORD"] = db_password

            if self._is_custom_backup_file(backup_path):
                # FIX 5: Validate tool before use
                tool = find_pg_tool("pg_restore")
                if not tool:
                    self._log("error", "أداة pg_restore غير موجودة في PATH")
                    return False
                restore_command = [
                    tool,
                    "-h",
                    db_host,
                    "-p",
                    db_port,
                    "-U",
                    db_user,
                    "-d",
                    db_name,
                    "--clean",
                    "--if-exists",
                    "-1",
                    str(backup_path),
                ]
            else:
                # FIX 5: Validate tool before use
                tool = find_pg_tool("psql")
                if not tool:
                    self._log("error", "أداة psql غير موجودة في PATH")
                    return False
                restore_command = [
                    tool,
                    "-h",
                    db_host,
                    "-p",
                    db_port,
                    "-U",
                    db_user,
                    "-d",
                    db_name,
                    # Atomic restore: wrap the whole dump in one transaction and abort
                    # on the first error, so a partial failure rolls back instead of
                    # leaving the database half-restored. ON_ERROR_STOP also makes psql
                    # return a non-zero exit code on SQL errors (otherwise it exits 0).
                    "--single-transaction",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-f",
                    str(backup_path),
                ]

            result = subprocess.run(restore_command, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                self._log("error", f"فشلت الاستعادة: {result.stderr.strip()}")
                return False

            self._log("info", f"تم استعادة النسخة الاحتياطية بنجاح: {backup_path.name}")
            return True

        except FileNotFoundError as e:
            self._log("error", "أداة pg_restore/psql غير موجودة في PATH — تأكد من تثبيت أدوات PostgreSQL", e)
            return False
        except Exception as e:
            self._log("error", f"فشلت الاستعادة: {e}", e)
            return False

    # ── listing / stats ──────────────────────────────────────────────────────

    def list_backups(self) -> list[dict]:
        """عرض قائمة النسخ الاحتياطية (PostgreSQL)"""
        backups = []

        if not self.backup_dir.exists():
            return backups

        all_files = list(self.backup_dir.glob("backup_*.backup")) + list(self.backup_dir.glob("backup_*.sql"))
        for backup_file in sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                # FIX 6: Cache stat() result — previously called 3 times per file
                # (once in sorted(), once for mtime, once for size).  Now called once.
                stat = backup_file.stat()
                file_time = datetime.fromtimestamp(stat.st_mtime)
                file_size_mb = stat.st_size / (1024 * 1024)
                backups.append(
                    {
                        'file': str(backup_file),
                        'filename': backup_file.name,
                        'name': backup_file.name,
                        'date': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'size': f"{file_size_mb:.2f} MB",
                        'size_mb': file_size_mb,
                    }
                )
            except Exception:
                continue

        return backups

    def get_backup_stats(self) -> dict:
        """إحصائيات النسخ الاحتياطية"""
        backups = self.list_backups()
        # FIX 7: list_backups() already computed size_mb for every entry —
        # no need to re-call .stat() here (previous code did an extra stat
        # per file for no reason).
        total_mb = sum(b['size_mb'] for b in backups)

        return {
            'total_backups': len(backups),
            'total_size_mb': total_mb,
            'oldest_backup': backups[-1]['date'] if backups else 'لا توجد',
            'newest_backup': backups[0]['date'] if backups else 'لا توجد',
        }

    # ── scheduler / thread ───────────────────────────────────────────────────

    def schedule_auto_backup(self, interval_hours: int = 24) -> None:
        """جدولة النسخ الاحتياطي التلقائي"""
        # FIX 1: Use per-instance scheduler to avoid corrupting global schedule state
        self._scheduler.every(interval_hours).hours.do(self.create_backup)
        self._log("info", f"تم جدولة النسخ الاحتياطي التلقائي كل {interval_hours} ساعة")

    def start_auto_backup(self, interval_hours: int = 24) -> None:
        """بدء النسخ الاحتياطي التلقائي في خيط منفصل (Background Thread)"""
        if self.is_running:
            self._log("warning", "نظام النسخ الاحتياطي التلقائي يعمل بالفعل")
            return

        self._stop_event.clear()
        self.schedule_auto_backup(interval_hours)

        def run_scheduler() -> None:
            while not self._stop_event.is_set():
                self._scheduler.run_pending()
                # FIX 4: event.wait() blocks up to 60s but wakes immediately
                # when _stop_event.set() is called, enabling instant shutdown
                self._stop_event.wait(60)

        self.backup_thread = Thread(target=run_scheduler, daemon=True)
        self.backup_thread.start()

        self._log("info", "تم بدء خدمة النسخ الاحتياطي التلقائي في الخلفية")

    def stop_auto_backup(self) -> None:
        """إيقاف النسخ الاحتياطي التلقائي"""
        # FIX 4: set() wakes the sleeping thread immediately via event.wait()
        self._stop_event.set()
        # FIX 1: clear only this instance's scheduler, not the global one
        self._scheduler.clear()
        self._log("info", "تم إيقاف خدمة النسخ الاحتياطي التلقائي")

    def backup_on_startup(self) -> str | None:
        """إنشاء نسخة احتياطية فورية عند بدء البرنامج"""
        # FIX 8: Removed unused `compress=True` parameter from create_backup().
        # The parameter was declared but never referenced inside the method —
        # all backups were always plain .sql regardless of the value passed.
        self._log("info", "بدء إنشاء نسخة احتياطية أولية عند تشغيل النظام...")
        return self.create_backup()


if __name__ == "__main__":
    backup_system = AutoBackupSystem()
    print("=== نظام النسخ الاحتياطي التلقائي ===\n")

    backup_file = backup_system.create_backup()

    print("\n=== قائمة النسخ الاحتياطية ===")
    backups = backup_system.list_backups()
    for i, backup in enumerate(backups[:5], 1):
        print(f"{i}. {backup['name']} - {backup['date']} - {backup['size']}")

    print("\n=== الإحصائيات ===")
    stats = backup_system.get_backup_stats()
    print(f"عدد النسخ: {stats['total_backups']}")
    print(f"الحجم الكلي: {stats['total_size_mb']:.2f} MB")
    print(f"أحدث نسخة: {stats['newest_backup']}")
    print(f"أقدم نسخة: {stats['oldest_backup']}")

    print("\n✅ نظام النسخ الاحتياطي يعمل بشكل صحيح")
