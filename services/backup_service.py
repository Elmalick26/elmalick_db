"""Backup service for El Malick Gest.

Thin service wrapper around AutoBackupSystem that provides a clean interface
for backup/restore operations with typed return values.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from auto_backup import AutoBackupSystem
from app_logger import AppLogger


class BackupService:
    """Service façade over AutoBackupSystem for backup and restore operations."""

    def __init__(self, backup_dir: str | None = None):
        self._system = AutoBackupSystem(backup_dir=backup_dir)

    # ── Create ───────────────────────────────────────────────────────

    def create_backup(self) -> str | None:
        """
        Create a PostgreSQL dump.
        Returns the path of the created backup file, or None on failure.
        """
        path = self._system.create_backup()
        if path:
            AppLogger.info("BackupService", f"Backup created: {path}")
        else:
            AppLogger.error("BackupService", "Backup creation failed")
        return path

    # ── Restore ──────────────────────────────────────────────────────

    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore from a .sql or .backup file.
        Returns True on success.
        """
        ok = self._system.restore_backup(backup_path)
        if ok:
            AppLogger.info("BackupService", f"Restore succeeded: {backup_path}")
        else:
            AppLogger.error("BackupService", f"Restore failed: {backup_path}")
        return ok

    # ── List ─────────────────────────────────────────────────────────

    def list_backups(self) -> list[dict]:
        """
        Return sorted list (newest first) of backup files in the backup dir.
        Each dict: {path, name, size_mb, created_at (datetime)}.
        """
        backup_dir = self._system.backup_dir
        results: list[dict] = []
        for pattern in ("*.sql", "*.backup"):
            for f in backup_dir.glob(pattern):
                try:
                    stat = f.stat()
                    results.append(
                        {
                            "path": str(f),
                            "name": f.name,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "created_at": datetime.fromtimestamp(stat.st_mtime),
                        }
                    )
                except Exception:
                    continue
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results

    # ── Cleanup ──────────────────────────────────────────────────────

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """
        Remove auto-backup files older than keep_days days.
        Returns the number of files deleted.
        """
        from datetime import timedelta

        backup_dir = self._system.backup_dir
        cutoff = datetime.now() - timedelta(days=keep_days)
        deleted = 0
        for pattern in ("backup_auto_*.sql", "backup_auto_*.backup"):
            for f in backup_dir.glob(pattern):
                try:
                    if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                        deleted += 1
                        AppLogger.info("BackupService", f"Deleted old backup: {f.name}")
                except Exception as e:
                    AppLogger.warning("BackupService", f"Could not delete {f.name}: {e}")
        return deleted

    # ── Status ───────────────────────────────────────────────────────

    def get_latest_backup(self) -> dict | None:
        """Return info dict for the most recent backup, or None if no backups exist."""
        backups = self.list_backups()
        return backups[0] if backups else None

    def get_backup_summary(self) -> dict:
        """
        Return a summary dict:
            count       — total number of backup files
            total_mb    — combined size in MB
            latest_at   — datetime of most recent backup (or None)
            latest_name — filename of most recent backup (or None)
        """
        backups = self.list_backups()
        if not backups:
            return {"count": 0, "total_mb": 0.0, "latest_at": None, "latest_name": None}
        return {
            "count": len(backups),
            "total_mb": round(sum(b["size_mb"] for b in backups), 2),
            "latest_at": backups[0]["created_at"],
            "latest_name": backups[0]["name"],
        }
