"""Tests for small repositories — UserRepository, GlobalSearchRepository."""

from unittest.mock import MagicMock, call

import pytest

from repositories.user_repo import UserRepository
from repositories.global_search_repo import GlobalSearchRepository


# ─── helpers ────────────────────────────────────────────────────────────────

def _conn():
    """Return a mock psycopg2-like connection with a cursor."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    # Support context-manager style: `with conn.cursor() as cur`
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    return conn, cur


# ─── UserRepository ─────────────────────────────────────────────────────────

class TestUserRepository:
    def test_count_users_returns_int(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (5,)
        repo = UserRepository(conn)
        assert repo.count_users() == 5

    def test_count_users_empty_table(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = UserRepository(conn)
        assert repo.count_users() == 0

    def test_create_user_executes_insert(self):
        conn, cur = _conn()
        repo = UserRepository(conn)
        repo.create_user("alice", "alice@example.com", "hashed", "Admin")
        assert cur.execute.called
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO Users" in sql

    def test_list_users_returns_rows(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, None, "---", "admin", "admin@ex.com", "Admin")]
        repo = UserRepository(conn)
        rows = repo.list_users()
        assert len(rows) == 1
        assert rows[0][3] == "admin"

    def test_update_password_executes_update(self):
        conn, cur = _conn()
        repo = UserRepository(conn)
        repo.update_password(1, "newhash")
        sql = cur.execute.call_args[0][0]
        assert "UPDATE Users" in sql

    def test_delete_user_executes_delete(self):
        conn, cur = _conn()
        repo = UserRepository(conn)
        repo.delete_user(42)
        sql = cur.execute.call_args[0][0]
        assert "DELETE FROM Users" in sql

    def test_list_active_staff_returns_rows(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Ali", "Ben")]
        repo = UserRepository(conn)
        rows = repo.list_active_staff()
        assert rows[0][0] == 1

    def test_get_staff_email_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("ali@school.com",)
        repo = UserRepository(conn)
        assert repo.get_staff_email(1) == "ali@school.com"

    def test_get_staff_email_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = UserRepository(conn)
        assert repo.get_staff_email(99) == ""

    def test_list_audit_logs_no_dates(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("2026-01-01", "admin", "LOGIN", "system")]
        repo = UserRepository(conn)
        rows = repo.list_audit_logs(search="admin")
        assert len(rows) == 1

    def test_list_audit_logs_with_dates(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = UserRepository(conn)
        rows = repo.list_audit_logs(date_start="2026-01-01", date_end="2026-12-31")
        # verify date params were passed
        params = cur.execute.call_args[0][1]
        assert "2026-01-01" in params


# ─── GlobalSearchRepository ─────────────────────────────────────────────────

class TestGlobalSearchRepository:
    def _conn_with_results(self):
        """Mock connection where cursor context-manager fetchall returns preset data."""
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = lambda s: cur
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return conn, cur

    def test_search_all_returns_list(self):
        conn, cur = self._conn_with_results()
        # Four queries: students, staff, payments, auditlogs — each fetchall returns []
        cur.fetchall.return_value = []
        repo = GlobalSearchRepository(conn)
        results = repo.search_all("%ali%")
        assert isinstance(results, list)
        assert results == []

    def test_search_all_students(self):
        conn, cur = self._conn_with_results()
        # First call (students) returns one row, rest return []
        cur.fetchall.side_effect = [
            [(1, "Ali Ben", "علي بن")],  # students
            [],                           # staff
            [],                           # payments
            [],                           # auditlogs
        ]
        repo = GlobalSearchRepository(conn)
        results = repo.search_all("%ali%")
        assert len(results) == 1
        assert results[0][0] == "Élève"
        assert results[0][3] == "student_management"

    def test_search_all_audit_logs(self):
        conn, cur = self._conn_with_results()
        cur.fetchall.side_effect = [
            [],  # students
            [],  # staff
            [],  # payments
            [(10, "admin", "LOGIN → system", "2026-01-01 10:00")],
        ]
        repo = GlobalSearchRepository(conn)
        results = repo.search_all("%admin%")
        assert results[0][0] == "Audit"
        assert results[0][4] == 10
