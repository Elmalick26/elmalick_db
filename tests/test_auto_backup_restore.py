"""P3 — restore safety in auto_backup.AutoBackupSystem.restore_backup.

A plain .sql restore via psql must run atomically: --single-transaction so a
partial failure rolls back, and -v ON_ERROR_STOP=1 so psql aborts on the first
error and returns a non-zero exit code. The custom-format (.backup) path must
keep using pg_restore -1 (single transaction).

Built via __new__ + mocked subprocess to avoid touching a real database.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import auto_backup


def _system():
    obj = auto_backup.AutoBackupSystem.__new__(auto_backup.AutoBackupSystem)
    obj._config = SimpleNamespace(
        db_host="localhost",
        db_port=5432,
        db_name="testdb",
        db_user="postgres",
        db_password="secret",
    )
    obj._log = lambda *a, **k: None  # silence logging, avoid uninitialised deps
    return obj


def _run_restore(path: str, is_custom: bool):
    """Return the command list passed to subprocess.run for the given file."""
    system = _system()
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    with (
        patch.object(auto_backup, "find_pg_tool", side_effect=lambda name: f"/usr/bin/{name}"),
        patch.object(auto_backup.subprocess, "run", side_effect=fake_run),
        patch.object(auto_backup.Path, "exists", return_value=True),
        patch.object(auto_backup.AutoBackupSystem, "_is_custom_backup_file", return_value=is_custom),
    ):
        result = system.restore_backup(path)
    return result, captured


class TestSqlRestoreIsAtomic:
    def test_sql_restore_uses_single_transaction_and_on_error_stop(self):
        ok, captured = _run_restore("/backups/backup_auto_x.sql", is_custom=False)
        assert ok is True
        cmd = captured["cmd"]
        assert "psql" in cmd[0]
        assert "--single-transaction" in cmd
        # ON_ERROR_STOP must be passed as a psql -v variable
        assert "-v" in cmd and "ON_ERROR_STOP=1" in cmd

    def test_password_passed_via_env_not_cmdline(self):
        _, captured = _run_restore("/backups/backup_auto_x.sql", is_custom=False)
        assert captured["env"].get("PGPASSWORD") == "secret"
        assert "secret" not in captured["cmd"]


class TestCustomFormatRestoreStaysTransactional:
    def test_backup_restore_uses_pg_restore_single_transaction(self):
        ok, captured = _run_restore("/backups/backup_auto_x.backup", is_custom=True)
        assert ok is True
        cmd = captured["cmd"]
        assert "pg_restore" in cmd[0]
        assert "-1" in cmd  # single transaction for custom-format restore
