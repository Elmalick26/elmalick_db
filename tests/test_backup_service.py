"""Tests for services/backup_service.py — uses mocking (no pg_dump required)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_fake_file(name: str, size: int = 1024, mtime_offset_days: int = 0):
    """Return a MagicMock that behaves like a Path file stat."""
    f = MagicMock(spec=Path)
    f.name = name
    f.__str__ = lambda self: f"/backups/{name}"
    stat = MagicMock()
    stat.st_size = size
    stat.st_mtime = (datetime.now() - timedelta(days=mtime_offset_days)).timestamp()
    f.stat.return_value = stat
    return f


@pytest.fixture
def svc():
    """BackupService with a fully mocked AutoBackupSystem."""
    with patch("services.backup_service.AutoBackupSystem"):
        from services.backup_service import BackupService

        service = BackupService.__new__(BackupService)
        mock_abs = MagicMock()
        mock_abs.backup_dir = MagicMock(spec=Path)
        service._system = mock_abs
        yield service, mock_abs


# ──────────────────────────────────────────────
# create_backup
# ──────────────────────────────────────────────


class TestCreateBackup:
    def test_success_returns_path(self, svc):
        service, mock_abs = svc
        mock_abs.create_backup.return_value = "/fake/backups/backup_auto_20260515.sql"
        result = service.create_backup()
        assert result == "/fake/backups/backup_auto_20260515.sql"

    def test_failure_returns_none(self, svc):
        service, mock_abs = svc
        mock_abs.create_backup.return_value = None
        result = service.create_backup()
        assert result is None

    def test_delegates_to_system(self, svc):
        service, mock_abs = svc
        mock_abs.create_backup.return_value = "/path/to/backup.sql"
        service.create_backup()
        mock_abs.create_backup.assert_called_once()


# ──────────────────────────────────────────────
# restore_backup
# ──────────────────────────────────────────────


class TestRestoreBackup:
    def test_success_returns_true(self, svc):
        service, mock_abs = svc
        mock_abs.restore_backup.return_value = True
        assert service.restore_backup("/path/to/backup.sql") is True

    def test_failure_returns_false(self, svc):
        service, mock_abs = svc
        mock_abs.restore_backup.return_value = False
        assert service.restore_backup("/path/to/missing.sql") is False

    def test_delegates_to_system(self, svc):
        service, mock_abs = svc
        mock_abs.restore_backup.return_value = True
        service.restore_backup("/my/backup.sql")
        mock_abs.restore_backup.assert_called_once_with("/my/backup.sql")


# ──────────────────────────────────────────────
# list_backups
# ──────────────────────────────────────────────


class TestListBackups:
    def test_returns_sorted_newest_first(self, svc):
        service, mock_abs = svc
        old = _make_fake_file("backup_auto_old.sql", mtime_offset_days=5)
        new = _make_fake_file("backup_auto_new.sql", mtime_offset_days=0)
        # glob returns old first, expect sorted newest first
        mock_abs.backup_dir.glob.side_effect = lambda p: [old, new] if "sql" in p else []
        results = service.list_backups()
        assert results[0]["name"] == "backup_auto_new.sql"
        assert results[1]["name"] == "backup_auto_old.sql"

    def test_empty_dir_returns_empty_list(self, svc):
        service, mock_abs = svc
        mock_abs.backup_dir.glob.return_value = []
        assert service.list_backups() == []

    def test_size_mb_calculation(self, svc):
        service, mock_abs = svc
        f = _make_fake_file("backup.sql", size=2 * 1024 * 1024)  # 2 MB
        mock_abs.backup_dir.glob.side_effect = lambda p: [f] if "sql" in p else []
        results = service.list_backups()
        assert results[0]["size_mb"] == 2.0

    def test_dict_has_expected_keys(self, svc):
        service, mock_abs = svc
        f = _make_fake_file("backup.sql")
        mock_abs.backup_dir.glob.side_effect = lambda p: [f] if "sql" in p else []
        result = service.list_backups()[0]
        assert {"path", "name", "size_mb", "created_at"} <= result.keys()


# ──────────────────────────────────────────────
# cleanup_old_backups
# ──────────────────────────────────────────────


class TestCleanupOldBackups:
    def test_deletes_old_files(self, svc):
        service, mock_abs = svc
        old = _make_fake_file("backup_auto_old.sql", mtime_offset_days=40)
        recent = _make_fake_file("backup_auto_recent.sql", mtime_offset_days=5)
        mock_abs.backup_dir.glob.side_effect = lambda p: [old, recent] if "sql" in p else []
        deleted = service.cleanup_old_backups(keep_days=30)
        old.unlink.assert_called_once()
        recent.unlink.assert_not_called()
        assert deleted == 1

    def test_no_old_files_returns_zero(self, svc):
        service, mock_abs = svc
        recent = _make_fake_file("backup_auto_recent.sql", mtime_offset_days=1)
        mock_abs.backup_dir.glob.side_effect = lambda p: [recent] if "sql" in p else []
        deleted = service.cleanup_old_backups(keep_days=30)
        assert deleted == 0

    def test_empty_dir_returns_zero(self, svc):
        service, mock_abs = svc
        mock_abs.backup_dir.glob.return_value = []
        assert service.cleanup_old_backups() == 0


# ──────────────────────────────────────────────
# get_latest_backup
# ──────────────────────────────────────────────


class TestGetLatestBackup:
    def test_returns_newest(self, svc):
        service, mock_abs = svc
        old = _make_fake_file("old.sql", mtime_offset_days=3)
        new = _make_fake_file("new.sql", mtime_offset_days=0)
        mock_abs.backup_dir.glob.side_effect = lambda p: [old, new] if "sql" in p else []
        result = service.get_latest_backup()
        assert result["name"] == "new.sql"

    def test_no_backups_returns_none(self, svc):
        service, mock_abs = svc
        mock_abs.backup_dir.glob.return_value = []
        assert service.get_latest_backup() is None


# ──────────────────────────────────────────────
# get_backup_summary
# ──────────────────────────────────────────────


class TestGetBackupSummary:
    def test_summary_with_files(self, svc):
        service, mock_abs = svc
        f1 = _make_fake_file("b1.sql", size=1 * 1024 * 1024, mtime_offset_days=0)
        f2 = _make_fake_file("b2.sql", size=2 * 1024 * 1024, mtime_offset_days=1)
        mock_abs.backup_dir.glob.side_effect = lambda p: [f1, f2] if "sql" in p else []
        summary = service.get_backup_summary()
        assert summary["count"] == 2
        assert summary["total_mb"] == 3.0
        assert summary["latest_name"] == "b1.sql"
        assert summary["latest_at"] is not None

    def test_empty_dir_summary(self, svc):
        service, mock_abs = svc
        mock_abs.backup_dir.glob.return_value = []
        summary = service.get_backup_summary()
        assert summary == {"count": 0, "total_mb": 0.0, "latest_at": None, "latest_name": None}


# ──────────────────────────────────────────────
# Mutation guards
# ──────────────────────────────────────────────


class TestMutationGuards:
    def test_default_backup_dir_is_none(self):
        """Mutation guard: None→True in default arg.
        BackupService() must pass backup_dir=None to AutoBackupSystem."""
        with patch("services.backup_service.AutoBackupSystem") as mock_abs_class:
            from services.backup_service import BackupService

            BackupService()
            mock_abs_class.assert_called_once_with(backup_dir=None)

    def test_failure_logs_error_not_info(self):
        """Mutation guard: if path:→if True — when path is None, error must be
        logged, NOT info."""
        with patch("services.backup_service.AutoBackupSystem"):
            from services.backup_service import BackupService

            service = BackupService.__new__(BackupService)
            mock_abs = MagicMock()
            mock_abs.create_backup.return_value = None
            service._system = mock_abs

            with patch("services.backup_service.AppLogger") as mock_logger:
                service.create_backup()
                mock_logger.error.assert_called_once()
                mock_logger.info.assert_not_called()
