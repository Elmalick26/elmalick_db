"""Phase 4 — Integration tests (batch B).

Covers:
  • StudentsApiRepository  (src/data/students_api_repo.py)
  • ParentRepository       (src/data/parent_repo.py)
  • LoginRepository        (src/data/login_repo.py) — lockout methods
  • StudentRepository      (src/data/student_repo.py) — count_students,
                            list_students_detailed, list_students with filters
  • CommunicationRepository — get_notification_log_detail (extra method)
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from repositories.communication_repo import CommunicationRepository
from repositories.login_repo import LoginRepository
from repositories.parent_repo import ParentRepository
from repositories.student_repo import StudentRepository
from repositories.students_api_repo import StudentsApiRepository

# ─── helpers ────────────────────────────────────────────────────────────────


def _conn():
    """Plain cursor mock."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def _ctx_conn():
    """Mock connection whose cursor acts as a context manager (with conn.cursor() as cur:)."""
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


def _desc(*names):
    """Build a cursor.description mock with the given column names."""
    return [(n,) for n in names]


# ════════════════════════════════════════════════════════════════════════════
#  StudentsApiRepository
# ════════════════════════════════════════════════════════════════════════════


class TestStudentsApiRepository:
    def test_get_active_year_id_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (3,)
        repo = StudentsApiRepository(conn)
        assert repo.get_active_year_id() == 3

    def test_get_active_year_id_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = StudentsApiRepository(conn)
        assert repo.get_active_year_id() is None

    def test_list_students_no_query(self):
        conn, cur = _conn()
        cur.description = _desc(
            "id",
            "first_name_fr",
            "last_name_fr",
            "first_name_ar",
            "last_name_ar",
            "gender",
            "birth_date",
            "status",
            "class_name",
        )
        cur.fetchall.return_value = [(1, "Ahmed", "Diop", "أحمد", "ديوب", "M", "2010-01-01", "Active", "CI")]
        repo = StudentsApiRepository(conn)
        rows = repo.list_students(year_id=1)
        assert len(rows) == 1
        assert rows[0]["first_name_fr"] == "Ahmed"

    def test_list_students_with_query(self):
        conn, cur = _conn()
        cur.description = _desc(
            "id",
            "first_name_fr",
            "last_name_fr",
            "first_name_ar",
            "last_name_ar",
            "gender",
            "birth_date",
            "status",
            "class_name",
        )
        cur.fetchall.return_value = [(2, "Fatou", "Ba", "فاطو", "با", "F", "2011-05-01", "Active", "CP")]
        repo = StudentsApiRepository(conn)
        rows = repo.list_students(year_id=1, q="Fatou", limit=5, offset=0)
        assert rows[0]["last_name_fr"] == "Ba"
        sql = cur.execute.call_args[0][0]
        assert "ILIKE" in sql

    def test_list_students_empty(self):
        conn, cur = _conn()
        cur.description = _desc(
            "id",
            "first_name_fr",
            "last_name_fr",
            "first_name_ar",
            "last_name_ar",
            "gender",
            "birth_date",
            "status",
            "class_name",
        )
        cur.fetchall.return_value = []
        repo = StudentsApiRepository(conn)
        assert repo.list_students(year_id=1) == []

    def test_count_students(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (42,)
        repo = StudentsApiRepository(conn)
        assert repo.count_students() == 42

    def test_get_student_by_id_found(self):
        conn, cur = _conn()
        cur.description = _desc("id", "first_name_fr", "last_name_fr")
        cur.fetchone.return_value = (7, "Omar", "Fall")
        repo = StudentsApiRepository(conn)
        result = repo.get_student_by_id(7)
        assert result == {"id": 7, "first_name_fr": "Omar", "last_name_fr": "Fall"}

    def test_get_student_by_id_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = StudentsApiRepository(conn)
        assert repo.get_student_by_id(999) is None

    def test_get_grades(self):
        conn, cur = _conn()
        cur.description = _desc("score", "subject", "coefficient", "period", "exam_type", "max_score")
        cur.fetchall.return_value = [(15.0, "Maths", 2.0, "T1", "Composition", 20.0)]
        repo = StudentsApiRepository(conn)
        rows = repo.get_grades(1, 1)
        assert rows[0]["score"] == 15.0

    def test_get_grades_empty(self):
        conn, cur = _conn()
        cur.description = _desc("score", "subject", "coefficient", "period", "exam_type", "max_score")
        cur.fetchall.return_value = []
        repo = StudentsApiRepository(conn)
        assert repo.get_grades(1, 1) == []

    def test_get_attendance(self):
        conn, cur = _conn()
        cur.description = _desc("date", "status", "reason")
        cur.fetchall.return_value = [("2025-01-05", "P", None)]
        repo = StudentsApiRepository(conn)
        rows = repo.get_attendance(1, 1)
        assert rows[0]["status"] == "P"

    def test_get_dues(self):
        conn, cur = _conn()
        cur.description = _desc("id", "label", "amount", "due_date", "is_paid")
        cur.fetchall.return_value = [(1, "Inscription", 50000, "2024-10-01", 0)]
        repo = StudentsApiRepository(conn)
        rows = repo.get_dues(1, 1)
        assert rows[0]["label"] == "Inscription"
        assert rows[0]["is_paid"] == 0

    def test_get_dues_none_year(self):
        conn, cur = _conn()
        cur.description = _desc("id", "label", "amount", "due_date", "is_paid")
        cur.fetchall.return_value = []
        repo = StudentsApiRepository(conn)
        assert repo.get_dues(1, None) == []


# ════════════════════════════════════════════════════════════════════════════
#  ParentRepository
# ════════════════════════════════════════════════════════════════════════════


class TestParentRepository:
    def test_get_active_year_id_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (2,)
        repo = ParentRepository(conn)
        assert repo.get_active_year_id() == 2

    def test_get_active_year_id_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = ParentRepository(conn)
        assert repo.get_active_year_id() is None

    def test_get_student_for_parent_login_found(self):
        conn, cur = _conn()
        row = (5, "Ahmed", "Diop", "Parent A", "33000000", "$2b$...", None, "EMG-0001")
        cur.fetchone.return_value = row
        repo = ParentRepository(conn)
        result = repo.get_student_for_parent_login("EMG-0001")
        assert result == row

    def test_get_student_for_parent_login_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = ParentRepository(conn)
        assert repo.get_student_for_parent_login("INVALID") is None

    def test_update_student_pin(self):
        conn, cur = _conn()
        repo = ParentRepository(conn)
        repo.update_student_pin(5, "$2b$hash")
        sql = cur.execute.call_args[0][0]
        assert "UPDATE Students" in sql
        assert "parent_pin_hash" in sql

    def test_reset_student_pin(self):
        conn, cur = _conn()
        repo = ParentRepository(conn)
        repo.reset_student_pin(5)
        sql = cur.execute.call_args[0][0]
        assert "parent_pin_hash = NULL" in sql

    def test_check_student_active_true(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (5,)
        repo = ParentRepository(conn)
        assert repo.check_student_active(5) is True

    def test_check_student_active_false(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = ParentRepository(conn)
        assert repo.check_student_active(99) is False

    def test_get_student_info_found(self):
        conn, cur = _conn()
        cur.description = _desc(
            "first_name_fr",
            "last_name_fr",
            "first_name_ar",
            "last_name_ar",
            "birth_date",
            "gender",
            "parent_name",
            "parent_phone",
            "parent_email",
            "class_name",
            "academic_year",
        )
        cur.fetchone.return_value = (
            "Ahmed",
            "Diop",
            "أحمد",
            "ديوب",
            "2010-01-01",
            "M",
            "Papa A",
            "33000000",
            "papa@mail.com",
            "CI",
            "2024-2025",
        )
        repo = ParentRepository(conn)
        result = repo.get_student_info(5, 1)
        assert result is not None
        assert result["first_name_fr"] == "Ahmed"
        assert result["class_name"] == "CI"

    def test_get_student_info_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = ParentRepository(conn)
        assert repo.get_student_info(999, 1) is None

    def test_get_student_grades(self):
        conn, cur = _conn()
        cur.description = _desc("score", "subject", "coefficient", "period", "exam_type", "max_score")
        cur.fetchall.return_value = [(14.0, "Français", 3.0, "T1", "Compo", 20.0)]
        repo = ParentRepository(conn)
        rows = repo.get_student_grades(5, 1)
        assert len(rows) == 1
        assert rows[0]["subject"] == "Français"

    def test_get_student_grades_empty(self):
        conn, cur = _conn()
        cur.description = _desc("score", "subject", "coefficient", "period", "exam_type", "max_score")
        cur.fetchall.return_value = []
        repo = ParentRepository(conn)
        assert repo.get_student_grades(5, 1) == []

    def test_get_student_attendance(self):
        conn, cur = _conn()
        cur.description = _desc("date", "status", "reason")
        cur.fetchall.return_value = [("2025-01-06", "P", None), ("2025-01-07", "A", "Maladie")]
        repo = ParentRepository(conn)
        rows = repo.get_student_attendance(5)
        assert len(rows) == 2
        assert rows[1]["status"] == "A"

    def test_get_student_dues(self):
        conn, cur = _conn()
        cur.description = _desc("label", "amount", "due_date", "is_paid")
        cur.fetchall.return_value = [("Inscription", 50000, "2024-10-01", 1)]
        repo = ParentRepository(conn)
        rows = repo.get_student_dues(5)
        assert rows[0]["is_paid"] == 1


# ════════════════════════════════════════════════════════════════════════════
#  LoginRepository — lockout methods (lines 62-117)
# ════════════════════════════════════════════════════════════════════════════


class TestLoginRepositoryLockout:
    def test_get_lockout_status_found_locked(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = (5, True)
        repo = LoginRepository(conn)
        count, locked = repo.get_lockout_status("admin")
        assert count == 5
        assert locked is True

    def test_get_lockout_status_found_unlocked(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = (3, False)
        repo = LoginRepository(conn)
        count, locked = repo.get_lockout_status("admin")
        assert count == 3
        assert locked is False

    def test_get_lockout_status_not_found(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = None
        repo = LoginRepository(conn)
        count, locked = repo.get_lockout_status("unknown")
        assert count == 0
        assert locked is False

    def test_get_lockout_status_exception(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("DB error")
        repo = LoginRepository(conn)
        count, locked = repo.get_lockout_status("admin")
        assert count == 0
        assert locked is False

    def test_record_failed_attempt_below_threshold(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = (3,)  # count < 5
        repo = LoginRepository(conn)
        result = repo.record_failed_attempt("admin")
        assert result is False

    def test_record_failed_attempt_triggers_lockout(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = (5,)  # count >= 5 → lockout
        repo = LoginRepository(conn)
        result = repo.record_failed_attempt("admin")
        assert result is True
        # The second execute should set lockout_until
        sqls = [c[0][0] for c in cur.execute.call_args_list]
        assert any("lockout_until" in s for s in sqls)

    def test_record_failed_attempt_exception(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("DB error")
        repo = LoginRepository(conn)
        result = repo.record_failed_attempt("admin")
        assert result is False

    def test_clear_attempts(self):
        conn, cur = _ctx_conn()
        repo = LoginRepository(conn)
        repo.clear_attempts("admin")
        sql = cur.execute.call_args[0][0]
        assert "DELETE FROM LoginAttempts" in sql

    def test_clear_attempts_exception_does_not_raise(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("DB error")
        repo = LoginRepository(conn)
        repo.clear_attempts("admin")  # must not raise


# ════════════════════════════════════════════════════════════════════════════
#  StudentRepository — new/uncovered methods
# ════════════════════════════════════════════════════════════════════════════


class TestStudentRepositoryExtended:
    # ── count_students ────────────────────────────────────────────────────────

    def test_count_students_no_filters(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (10,)
        repo = StudentRepository(conn)
        assert repo.count_students(year_id=1) == 10

    def test_count_students_with_class_id(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (3,)
        repo = StudentRepository(conn)
        count = repo.count_students(year_id=1, class_id=2)
        sql = cur.execute.call_args[0][0]
        assert "SCN.class_id" in sql
        assert count == 3

    def test_count_students_with_cycle_id(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (7,)
        repo = StudentRepository(conn)
        count = repo.count_students(year_id=1, cycle_id=1)
        sql = cur.execute.call_args[0][0]
        assert "C.cycle_id" in sql
        assert count == 7

    def test_count_students_with_search(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (2,)
        repo = StudentRepository(conn)
        count = repo.count_students(year_id=1, search="Ahmed")
        sql = cur.execute.call_args[0][0]
        assert "ILIKE" in sql
        assert count == 2

    def test_count_students_with_date_range(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1,)
        repo = StudentRepository(conn)
        count = repo.count_students(year_id=1, date_from="2024-10-01", date_to="2024-12-31")
        sql = cur.execute.call_args[0][0]
        assert "BETWEEN" in sql
        assert count == 1

    def test_count_students_returns_zero_on_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = StudentRepository(conn)
        assert repo.count_students(year_id=1) == 0

    # ── list_students with limit/offset ──────────────────────────────────────

    def test_list_students_with_limit(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Ahmed", "Diop", "أحمد", "ديوب", "M", "CI", "", "", None, None, "EMG-0001")]
        repo = StudentRepository(conn)
        rows = repo.list_students(year_id=1, limit=10, offset=0)
        sql = cur.execute.call_args[0][0]
        assert "LIMIT" in sql
        assert len(rows) == 1

    def test_list_students_no_limit(self):
        """limit=None → no LIMIT clause in SQL."""
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students(year_id=1)  # default limit=None
        sql = cur.execute.call_args[0][0]
        assert "LIMIT" not in sql

    def test_list_students_with_offset(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students(year_id=1, limit=50, offset=50)
        params = cur.execute.call_args[0][1]
        assert 50 in params  # offset value in params

    # ── list_students_detailed ─────────────────────────────────────────────────

    def test_list_students_detailed_no_filters(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [
            (
                1,
                "Ahmed",
                "Diop",
                "أحمد",
                "ديوب",
                "2010-01-01",
                "Dakar",
                "M",
                "Dakar",
                "CI",
                "05",
                "EMG-0001",
                "Parent A",
                "33000000",
                "",
                "2024-10-01",
                "Active",
            )
        ]
        repo = StudentRepository(conn)
        rows = repo.list_students_detailed(year_id=1)
        assert len(rows) == 1
        assert rows[0][1] == "Ahmed"

    def test_list_students_detailed_with_class_id(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students_detailed(year_id=1, class_id=2)
        sql = cur.execute.call_args[0][0]
        assert "SCN.class_id" in sql

    def test_list_students_detailed_with_cycle_id(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students_detailed(year_id=1, cycle_id=1)
        sql = cur.execute.call_args[0][0]
        assert "C.cycle_id" in sql

    def test_list_students_detailed_with_search(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students_detailed(year_id=1, search="Diop")
        sql = cur.execute.call_args[0][0]
        assert "ILIKE" in sql

    def test_list_students_detailed_with_date_range(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students_detailed(year_id=1, date_from="2024-10-01", date_to="2024-12-31")
        sql = cur.execute.call_args[0][0]
        assert "BETWEEN" in sql


# ════════════════════════════════════════════════════════════════════════════
#  CommunicationRepository — extra method not yet covered
# ════════════════════════════════════════════════════════════════════════════


class TestCommunicationRepositoryExtra:
    def test_get_notification_log_detail(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [
            ("2025-01-01 10:00:00", "33000000", "Résultats T1", "sent", ""),
            ("2025-01-02 11:00:00", "77000000", "Convocation", "failed", "Timeout"),
        ]
        repo = CommunicationRepository(conn)
        rows = repo.get_notification_log_detail("2025-01-01", "2025-01-31 23:59:59")
        assert len(rows) == 2
        sql = cur.execute.call_args[0][0]
        assert "NotificationLogs" in sql
        assert "BETWEEN" in sql
