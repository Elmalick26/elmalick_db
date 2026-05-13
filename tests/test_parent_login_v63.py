"""Regression tests for parent login v6.3 (student_code + bcrypt PIN)."""

import os
import sys
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api import routes_parent


class _ConnCtx:
    """Small context manager wrapper for fake DB connection."""

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_db_with_row(row):
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = row
    conn.cursor.return_value = cur

    db = MagicMock()
    db.get_connection.return_value = _ConnCtx(conn)
    return db, conn, cur


def _run_login(student_code, pin):
    req = routes_parent.ParentLoginRequest(student_code=student_code, pin=pin)
    return asyncio.run(routes_parent.parent_login(req))


def test_parent_login_not_found_returns_404():
    db, conn, cur = _make_db_with_row(None)

    with patch("api.routes_parent.DatabaseManager", return_value=db):
        with pytest.raises(HTTPException) as ex:
            _run_login("EMG-0099", "1234")

    assert ex.value.status_code == 404
    assert "Code élève" in ex.value.detail


def test_parent_login_hash_success_without_update():
    pin_hash = routes_parent._hash_pin("1234")
    row = (1, "Malick", "Diouf", "Parent", "7700", pin_hash, "", "EMG-0001")
    db, conn, cur = _make_db_with_row(row)

    with patch("api.routes_parent.DatabaseManager", return_value=db), \
         patch("api.routes_parent.create_access_token", return_value="tok_parent"):
        data = _run_login("emg-0001", "1234")

    assert data["access_token"] == "tok_parent"
    assert data["student_code"] == "EMG-0001"
    # Only the SELECT should execute; no UPDATE for already-hashed PIN.
    assert cur.execute.call_count == 1


def test_parent_login_hash_wrong_pin_returns_401():
    pin_hash = routes_parent._hash_pin("1234")
    row = (1, "Malick", "Diouf", "Parent", "7700", pin_hash, "", "EMG-0001")
    db, conn, cur = _make_db_with_row(row)

    with patch("api.routes_parent.DatabaseManager", return_value=db):
        with pytest.raises(HTTPException) as ex:
            _run_login("EMG-0001", "0000")

    assert ex.value.status_code == 401


def test_parent_login_migrates_plain_pin_to_hash():
    row = (2, "Babou", "Diop", "Parent", "7701", "", "9999", "EMG-0002")
    db, conn, cur = _make_db_with_row(row)

    with patch("api.routes_parent.DatabaseManager", return_value=db), \
         patch("api.routes_parent.create_access_token", return_value="tok_parent"):
        data = _run_login("EMG-0002", "9999")

    assert data["access_token"] == "tok_parent"
    assert cur.execute.call_count == 2  # SELECT + UPDATE
    sql = cur.execute.call_args_list[1][0][0]
    assert "UPDATE Students SET parent_pin_hash" in sql
    conn.commit.assert_called_once()


def test_parent_login_first_access_invalid_pin_returns_400():
    row = (3, "Loukhman", "Diouf", "Parent", "7702", "", "", "EMG-0003")
    db, conn, cur = _make_db_with_row(row)

    with patch("api.routes_parent.DatabaseManager", return_value=db):
        with pytest.raises(HTTPException) as ex:
            _run_login("EMG-0003", "12a")

    assert ex.value.status_code == 400


def test_parent_login_first_access_sets_hash_and_clears_plain():
    row = (3, "Loukhman", "Diouf", "Parent", "7702", "", "", "EMG-0003")
    db, conn, cur = _make_db_with_row(row)

    with patch("api.routes_parent.DatabaseManager", return_value=db), \
         patch("api.routes_parent.create_access_token", return_value="tok_parent"):
        data = _run_login("EMG-0003", "4567")

    assert data["student_code"] == "EMG-0003"
    assert cur.execute.call_count == 2
    _, params = cur.execute.call_args_list[1][0]
    assert params[0]  # hash value not empty
    assert params[1] == 3
    conn.commit.assert_called_once()
