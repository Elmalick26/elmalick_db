"""H2 — clean-install bootstrap (setup_database).

A plain `alembic upgrade head` cannot build a fresh database (early migrations
assume db_schema-created tables). setup_database does db_schema first, stamps the
baseline on a fresh DB, then upgrades head. These tests lock that sequence with
mocks (no real DB).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import setup_database


def _fake_db(version):
    """DatabaseManager whose alembic_version query returns `version` (or raises)."""
    db = MagicMock()
    cur = MagicMock()
    if isinstance(version, Exception):
        cur.fetchone.side_effect = version
    else:
        cur.fetchone.return_value = (version,) if version is not None else None
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    db.get_connection.return_value = conn
    return db


def test_fresh_db_stamps_baseline_then_upgrades():
    db = _fake_db(None)  # no alembic_version row
    with (
        patch.object(setup_database, "DatabaseManager", return_value=db),
        patch.object(setup_database, "Config"),
        patch.object(setup_database.command, "stamp") as stamp,
        patch.object(setup_database.command, "upgrade") as upgrade,
    ):
        setup_database.setup_database()
    db.initialize_database.assert_called_once()  # tables created first
    stamp.assert_called_once()
    assert stamp.call_args[0][1] == "004"  # baseline
    upgrade.assert_called_once()
    assert upgrade.call_args[0][1] == "head"


def test_existing_db_upgrades_without_stamp():
    db = _fake_db("008")  # already migrated to some revision
    with (
        patch.object(setup_database, "DatabaseManager", return_value=db),
        patch.object(setup_database, "Config"),
        patch.object(setup_database.command, "stamp") as stamp,
        patch.object(setup_database.command, "upgrade") as upgrade,
    ):
        setup_database.setup_database()
    stamp.assert_not_called()  # do not re-stamp an initialised DB
    upgrade.assert_called_once_with(upgrade.call_args[0][0], "head")


def test_missing_alembic_table_treated_as_fresh():
    db = _fake_db(Exception("no such table"))
    assert setup_database._current_alembic_version(db) is None
