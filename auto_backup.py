"""
نظام النسخ الاحتياطي التلقائي - PostgreSQL
Auto Backup System (pg_dump / pg_restore)
"""

import subprocess
import shutil
import os
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

import db_path as db_paths_module
from db_path import find_pg_tool
from app_logger import AppLogger
from config_manager import ConfigManager


class AutoBackupSystem:
    """نظام النسخ الاحتياطي التلقائي - PostgreSQL"""

    def __init__(self, db_path=None, backup_dir=None):
        # db_path غير مستخدم مع PostgreSQL (محتفظ به للتوافق مع الكود القديم)
        self.backup_dir = Path(backup_dir) if backup_dir else Path(db_paths_module.get_backup_dir())
        self._config = ConfigManager()

        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            AppLogger.error("AutoBackup", f"فشل في إنشاء مجلد النسخ الاحتياطي: {e}")

        self.is_running = False
        self.backup_thread = None

    def _log(self, level, message):
        """تسجيل الرسائل عبر نظام AppLogger الموحد بدلاً من ملف منفصل"""
        if level == "info":
            AppLogger.info("AutoBackup", message)
        elif level == "warning":
            AppLogger.warning("AutoBackup", message)
        elif level == "error":
            AppLogger.error("AutoBackup", message)

    def create_backup(self, compress=True):
        """
        إنشاء نسخة احتياطية من قاعدة PostgreSQL باستخدام pg_dump.
        الملفات بصيغة SQL نقية (.sql) للتوافقية العالية.
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

            pg_dump = find_pg_tool("pg_dump")

            # استخدام صيغة SQL نقية (أكثر توافقاً من Custom format)
            dump_command = [
                pg_dump,
                "-h", db_host, "-p", db_port,
                "-U", db_user,
                "-f", str(backup_file),
                db_name
            ]

            result = subprocess.run(dump_command, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                self._log("error", f"pg_dump فشل: {result.stderr.strip()}")
                return None

            self._log("info", f"تم إنشاء نسخة احتياطية بنجاح: {backup_file.name}")
            self.cleanup_old_backups(keep_days=30)
            return str(backup_file)

        except FileNotFoundError as e:
            self._log("error", f"أداة pg_dump غير موجودة: {e}")
            return None
        except Exception as e:
            self._log("error", f"فشل إنشاء النسخة الاحتياطية: {str(e)}")
            return None

    def cleanup_old_backups(self, keep_days=30):
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
            self._log("warning", f"خطأ في تنظيف النسخ القديمة: {str(e)}")

    def _is_custom_backup_file(self, backup_path: Path) -> bool:
        """Detect PostgreSQL custom-format dump by file signature (PGDMP)."""
        try:
            with open(backup_path, "rb") as f:
                return f.read(5) == b"PGDMP"
        except Exception:
            return False

    def restore_backup(self, backup_file):
        """
        استعادة قاعدة PostgreSQL من نسخة احتياطية.
        .backup → pg_restore
        .sql    → psql
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
                restore_command = [
                    find_pg_tool("pg_restore"),
                    "-h", db_host, "-p", db_port,
                    "-U", db_user,
                    "-d", db_name,
                    "--clean", "--if-exists", "-1",
                    str(backup_path)
                ]
            else:
                restore_command = [
                    find_pg_tool("psql"),
                    "-h", db_host, "-p", db_port,
                    "-U", db_user,
                    "-d", db_name,
                    "-f", str(backup_path)
                ]

            result = subprocess.run(restore_command, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                self._log("error", f"فشلت الاستعادة: {result.stderr.strip()}")
                return False

            self._log("info", f"تم استعادة النسخة الاحتياطية بنجاح: {backup_path.name}")
            return True

        except FileNotFoundError:
            self._log("error", "أداة pg_restore/psql غير موجودة في PATH — تأكد من تثبيت أدوات PostgreSQL")
            return False
        except Exception as e:
            self._log("error", f"فشلت الاستعادة: {str(e)}")
            return False

    def list_backups(self):
        """عرض قائمة النسخ الاحتياطية (PostgreSQL)"""
        backups = []

        if not self.backup_dir.exists():
            return backups

        # يدعم كلاً من .backup و .sql
        all_files = list(self.backup_dir.glob("backup_*.backup")) + list(self.backup_dir.glob("backup_*.sql"))
        for backup_file in sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                file_size_mb = backup_file.stat().st_size / (1024 * 1024)
                backups.append({
                    'file': str(backup_file),
                    'filename': backup_file.name,
                    'name': backup_file.name,
                    'date': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': f"{file_size_mb:.2f} MB",
                    'size_mb': file_size_mb
                })
            except Exception:
                continue

        return backups

    def schedule_auto_backup(self, interval_hours=24):
        """جدولة النسخ الاحتياطي التلقائي"""
        schedule.every(interval_hours).hours.do(self.create_backup)
        self._log("info", f"تم جدولة النسخ الاحتياطي التلقائي كل {interval_hours} ساعة")

    def start_auto_backup(self, interval_hours=24):
        """بدء النسخ الاحتياطي التلقائي في خيط منفصل (Background Thread)"""
        if self.is_running:
            self._log("warning", "نظام النسخ الاحتياطي التلقائي يعمل بالفعل")
            return

        self.is_running = True
        self.schedule_auto_backup(interval_hours)

        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # تحقق كل دقيقة لتخفيف الحمل على المعالج

        self.backup_thread = Thread(target=run_scheduler, daemon=True)
        self.backup_thread.start()

        self._log("info", "تم بدء خدمة النسخ الاحتياطي التلقائي في الخلفية")

    def stop_auto_backup(self):
        """إيقاف النسخ الاحتياطي التلقائي"""
        self.is_running = False
        schedule.clear()
        self._log("info", "تم إيقاف خدمة النسخ الاحتياطي التلقائي")

    def backup_on_startup(self):
        """إنشاء نسخة احتياطية فورية عند بدء البرنامج (يُنصح بربطها بتشغيل النظام)"""
        self._log("info", "بدء إنشاء نسخة احتياطية أولية عند تشغيل النظام...")
        return self.create_backup(compress=True)

    def get_backup_stats(self):
        """إحصائيات النسخ الاحتياطية"""
        backups = self.list_backups()
        try:
            total_size = sum(Path(b['file']).stat().st_size for b in backups)
            total_mb = total_size / (1024 * 1024)
        except Exception:
            total_mb = 0.0

        return {
            'total_backups': len(backups),
            'total_size_mb': total_mb,
            'oldest_backup': backups[-1]['date'] if backups else 'لا توجد',
            'newest_backup': backups[0]['date'] if backups else 'لا توجد'
        }


# مثال على الاستخدام
if __name__ == "__main__":
    # تشغيل وهمي لاختبار النظام
    backup_system = AutoBackupSystem()
    print("=== نظام النسخ الاحتياطي التلقائي ===\n")

    # إنشاء نسخة احتياطية
    backup_file = backup_system.create_backup(compress=True)

    # عرض قائمة النسخ
    print("\n=== قائمة النسخ الاحتياطية ===")
    backups = backup_system.list_backups()
    for i, backup in enumerate(backups[:5], 1):
        print(f"{i}. {backup['name']} - {backup['date']} - {backup['size']}")

    # عرض الإحصائيات
    print("\n=== الإحصائيات ===")
    stats = backup_system.get_backup_stats()
    print(f"عدد النسخ: {stats['total_backups']}")
    print(f"الحجم الكلي: {stats['total_size_mb']:.2f} MB")
    print(f"أحدث نسخة: {stats['newest_backup']}")
    print(f"أقدم نسخة: {stats['oldest_backup']}")

    print("\n✅ نظام النسخ الاحتياطي يعمل بشكل صحيح")
