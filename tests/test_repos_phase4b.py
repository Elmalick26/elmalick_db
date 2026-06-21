"""
tests/test_repos_phase4b.py
Phase 4b repository coverage — LoginRepository, AttendanceRepository,
GradesRepository, StaffRepository (missing methods).
"""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, call

# ── ensure project root is on sys.path ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.attendance_repo import AttendanceRepository
from repositories.grades_repo import GradesRepository
from repositories.login_repo import LoginRepository
from repositories.staff_repo import StaffRepository

# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════


def _ctx_cursor(rows=None, fetchone_val=None):
    """Build a mock connection whose cursor() works as context manager."""
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = fetchone_val
    conn = MagicMock()
    # context manager protocol for `with conn.cursor() as cur:`
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


def _plain_cursor(rows=None, fetchone_val=None):
    """Build a mock connection whose cursor() returns a plain mock (no ctx)."""
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = fetchone_val
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def _multi_cursor(*side_effects):
    """cursor().fetchone() returns successive values from side_effects."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.side_effect = list(side_effects)
    cur.fetchall.return_value = []
    return conn, cur


# ════════════════════════════════════════════════════════════════════════════
# LoginRepository
# ════════════════════════════════════════════════════════════════════════════


class TestLoginRepository:
    def test_count_users_returns_int(self):
        conn, cur = _ctx_cursor(fetchone_val=(7,))
        repo = LoginRepository(conn)
        assert repo.count_users() == 7

    def test_count_users_empty_returns_zero(self):
        conn, cur = _ctx_cursor(fetchone_val=None)
        repo = LoginRepository(conn)
        assert repo.count_users() == 0

    def test_insert_default_admin_executes(self):
        conn, cur = _ctx_cursor()
        repo = LoginRepository(conn)
        repo.insert_default_admin("hashed_pw")
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        assert "INSERT INTO Users" in args[0]
        assert "admin" in args[1]

    def test_get_user_for_login_found(self):
        row = (1, "Admin", "hash", "Actif")
        conn, cur = _ctx_cursor(fetchone_val=row)
        repo = LoginRepository(conn)
        result = repo.get_user_for_login("admin")
        assert result == row

    def test_get_user_for_login_not_found(self):
        conn, cur = _ctx_cursor(fetchone_val=None)
        repo = LoginRepository(conn)
        assert repo.get_user_for_login("ghost") is None

    def test_update_password_hash_executes(self):
        conn, cur = _ctx_cursor()
        repo = LoginRepository(conn)
        repo.update_password_hash(1, "new_hash")
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        assert "UPDATE Users" in args[0]
        assert ("new_hash", 1) == args[1]

    def test_update_admin_credentials_executes(self):
        conn, cur = _ctx_cursor()
        repo = LoginRepository(conn)
        repo.update_admin_credentials("new_hash", "superadmin")
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        assert "UPDATE Users" in args[0]


# ════════════════════════════════════════════════════════════════════════════
# AttendanceRepository
# ════════════════════════════════════════════════════════════════════════════


class TestAttendanceRepoLookups:
    def test_list_classes_returns_rows(self):
        rows = [(1, "6A"), (2, "5B")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        assert repo.list_classes() == rows

    def test_get_periods_empty_if_no_class_id(self):
        conn, cur = _plain_cursor()
        repo = AttendanceRepository(conn)
        assert repo.get_periods_for_class(None, 1) == []

    def test_get_periods_empty_if_year_minus1(self):
        conn, cur = _plain_cursor()
        repo = AttendanceRepository(conn)
        assert repo.get_periods_for_class(1, -1) == []

    def test_get_periods_no_cycle_returns_empty(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = AttendanceRepository(conn)
        assert repo.get_periods_for_class(5, 1) == []

    def test_get_periods_with_cycle(self):
        periods = [(10, "T1"), (11, "T2")]
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = (3,)
        cur.fetchall.return_value = periods
        repo = AttendanceRepository(conn)
        result = repo.get_periods_for_class(5, 1)
        assert result == periods

    def test_resolve_period_empty_inputs(self):
        conn, cur = _plain_cursor()
        repo = AttendanceRepository(conn)
        assert repo.resolve_period_id_for_class_date(None, "2025-01-01", 1) is None
        assert repo.resolve_period_id_for_class_date(1, "", 1) is None
        assert repo.resolve_period_id_for_class_date(1, "2025-01-01", -1) is None

    def test_resolve_period_no_cycle(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = AttendanceRepository(conn)
        assert repo.resolve_period_id_for_class_date(1, "2025-01-01", 1) is None

    def test_resolve_period_found(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.side_effect = [(2,), (99,)]
        repo = AttendanceRepository(conn)
        result = repo.resolve_period_id_for_class_date(1, "2025-01-15", 1)
        assert result == 99

    def test_resolve_period_not_found(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.side_effect = [(2,), None]
        repo = AttendanceRepository(conn)
        assert repo.resolve_period_id_for_class_date(1, "2025-01-15", 1) is None

    def test_resolve_timetable_slot_found(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = (77,)
        repo = AttendanceRepository(conn)
        result = repo.resolve_timetable_slot_for_class_datetime(1, "2025-01-13", "09:15")
        assert result == 77

    def test_list_timetable_slots_for_class_date(self):
        rows = [(12, "08:00", "09:00", "Math")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.list_timetable_slots_for_class_date(1, "2025-01-13")
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "FROM Timetable" in sql
        assert "Subjects" in sql


class TestAttendanceRepoDailyEntry:
    def test_load_students_with_period(self):
        rows = [(1, "Ali Ben", "Present", 0, "", "")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.load_students_for_attendance(1, "2025-01-15", 1, period_id=10)
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "period_id" in sql

    def test_load_students_without_period(self):
        rows = [(1, "Ali Ben", "Present", 0, "", "")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.load_students_for_attendance(1, "2025-01-15", 1, period_id=None)
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "period_id" not in sql.split("AND")[1] if "AND" in sql else True

    def test_load_students_with_slot(self):
        rows = [(1, "Ali Ben", "Present", 0, "", "")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.load_students_for_attendance(1, "2025-01-15", 1, timetable_slot_id=12)
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "timetable_slot_id" in sql

    def test_upsert_attendance_update_path(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = (42,)  # existing record
        repo = AttendanceRepository(conn)
        repo.upsert_attendance(1, "2025-01-15", "Absent", 0, "", "", 1, 10)
        calls = [c[0][0] for c in cur.execute.call_args_list]
        assert any("UPDATE" in s for s in calls)

    def test_upsert_attendance_insert_path(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None  # no existing record
        repo = AttendanceRepository(conn)
        repo.upsert_attendance(1, "2025-01-15", "Absent", 0, "", "", 1, None)
        calls = [c[0][0] for c in cur.execute.call_args_list]
        assert any("INSERT" in s for s in calls)

    def test_upsert_attendance_with_period_select(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        repo = AttendanceRepository(conn)
        repo.upsert_attendance(2, "2025-02-01", "Present", 1, "Médical", "OK", 1, 5)
        first_sql = cur.execute.call_args_list[0][0][0]
        assert "COALESCE(period_id" in first_sql

    def test_upsert_attendance_no_period_select(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        repo = AttendanceRepository(conn)
        repo.upsert_attendance(2, "2025-02-01", "Present", 1, "", "", 1, None)
        first_sql = cur.execute.call_args_list[0][0][0]
        assert "period_id IS NULL" in first_sql

    def test_upsert_attendance_slot_select(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        repo = AttendanceRepository(conn)
        repo.upsert_attendance(2, "2025-02-01", "Present", 1, "", "", 1, None, 12)
        first_sql = cur.execute.call_args_list[0][0][0]
        assert "timetable_slot_id = %s" in first_sql


class TestAttendanceRepoReport:
    def test_load_students_for_report_combo(self):
        rows = [(1, "Ali Ben")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.load_students_for_report_combo(1, 1)
        assert result == rows

    def test_list_subjects_for_report_all(self):
        rows = [(1, "Math"), (2, "Arabe")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.list_subjects_for_report()
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "FROM Subjects" in sql

    def test_list_slots_for_report_with_subject_filter(self):
        rows = [(12, "Lundi", "08:00", "09:00", "Math")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.list_slots_for_report(1, 5)
        assert result == rows
        sql = cur.execute.call_args[0][0]
        params = cur.execute.call_args[0][1]
        assert "T.subject_id = %s" in sql
        assert 5 in params

    def test_fetch_report_no_filters(self):
        rows = [("2025-01-01", "Ali Ben", "6A", "Present", 0, "", "08:00", "09:00", "Math")]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.fetch_report_data(1, "2025-01-01", "2025-01-31")
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "BETWEEN" in sql
        assert "LEFT JOIN Timetable" in sql

    def test_fetch_report_year_minus1_skips_year_filter(self):
        conn, cur = _plain_cursor(rows=[])
        repo = AttendanceRepository(conn)
        repo.fetch_report_data(-1, "2025-01-01", "2025-01-31")
        params = cur.execute.call_args[0][1]
        # year_id=-1 → no year_id appended to params list (only date_from + date_to)
        assert -1 not in params

    def test_fetch_report_with_all_filters(self):
        conn, cur = _plain_cursor(rows=[])
        repo = AttendanceRepository(conn)
        repo.fetch_report_data(
            1, "2025-01-01", "2025-01-31", class_id=2, student_id=5, period_id=3, subject_id=4, timetable_slot_id=9
        )
        sql = cur.execute.call_args[0][0]
        params = cur.execute.call_args[0][1]
        assert "class_id" in sql or "SCN.class_id" in sql
        assert "student_id" in sql or "A.student_id" in sql
        assert "T.subject_id = %s" in sql
        assert "A.timetable_slot_id = %s" in sql
        assert 5 in params
        assert 4 in params
        assert 9 in params

    def test_get_high_absence_students(self):
        rows = [("Ali Ben", 35.0)]
        conn, cur = _plain_cursor(rows=rows)
        repo = AttendanceRepository(conn)
        result = repo.get_high_absence_students(1, threshold_pct=20.0)
        assert result == rows
        params = cur.execute.call_args[0][1]
        assert 1 in params
        assert 20.0 in params


# ════════════════════════════════════════════════════════════════════════════
# GradesRepository
# ════════════════════════════════════════════════════════════════════════════


class TestGradesRepoLookups:
    def test_list_classes(self):
        rows = [(1, "6A")]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        assert repo.list_classes() == rows

    def test_list_periods_for_year(self):
        rows = [(1, "T1")]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        assert repo.list_periods_for_year(1) == rows

    def test_list_periods_for_class_year_with_cycle(self):
        periods = [(1, "T1"), (2, "T2")]
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = (3,)
        cur.fetchall.return_value = periods
        repo = GradesRepository(conn)
        result = repo.list_periods_for_class_year(1, 1)
        assert result == periods

    def test_list_periods_for_class_year_no_cycle_fallback(self):
        periods = [(1, "T1")]
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        cur.fetchall.return_value = periods
        repo = GradesRepository(conn)
        result = repo.list_periods_for_class_year(99, 1)
        assert result == periods

    def test_list_assessments_for_period(self):
        rows = [(1, "DS1")]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        assert repo.list_assessments_for_period(1) == rows

    def test_get_cycle_name_found(self):
        conn, cur = _plain_cursor(fetchone_val=("Primaire",))
        repo = GradesRepository(conn)
        assert repo.get_cycle_name_for_class(1) == "Primaire"

    def test_get_cycle_name_not_found(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = GradesRepository(conn)
        assert repo.get_cycle_name_for_class(99) is None

    def test_get_max_score_primary(self):
        # Rows are (name_fr, is_primary); flag=None exercises the name fallback.
        conn, cur = _plain_cursor(fetchone_val=("Primaire", None))
        repo = GradesRepository(conn)
        assert repo.get_max_score_for_class(1) == 10.0

    def test_get_max_score_secondary(self):
        conn, cur = _plain_cursor(fetchone_val=("Collège", None))
        repo = GradesRepository(conn)
        assert repo.get_max_score_for_class(1) == 20.0

    def test_get_max_score_explicit_flag_wins(self):
        # Non-primary-looking name flagged primary → /10 via the explicit flag.
        conn, cur = _plain_cursor(fetchone_val=("Cycle X", True))
        repo = GradesRepository(conn)
        assert repo.get_max_score_for_class(1) == 10.0

    def test_get_class_subjects_from_timetable(self):
        rows = [(1, "Maths", "رياضيات", 4)]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        result = repo.get_class_subjects(1)
        assert result == rows

    def test_get_class_subjects_fallback_no_timetable(self):
        subjects = [(2, "Sciences", "علوم", 3)]
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        # First fetchall (timetable) returns empty, then fetchone for cycle, then fetchall for subjects
        cur.fetchall.side_effect = [[], subjects]
        cur.fetchone.return_value = (5,)
        repo = GradesRepository(conn)
        result = repo.get_class_subjects(1)
        assert result == subjects

    def test_get_class_subjects_fallback_no_cycle(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchall.return_value = []
        cur.fetchone.return_value = None
        repo = GradesRepository(conn)
        result = repo.get_class_subjects(1)
        assert result == []


class TestGradesRepoGradingSheet:
    def test_load_grading_sheet(self):
        rows = [(1, "Ali Ben", "علي", 15.0, "Bien")]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        result = repo.load_grading_sheet(1, 1, 1, 1)
        assert result == rows

    def test_upsert_grade_is_atomic_insert_on_conflict(self):
        # Single atomic statement: INSERT ... ON CONFLICT DO UPDATE (migration 009).
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        repo = GradesRepository(conn)
        repo.upsert_grade(1, 1, 1, 1, 15.0, "Bien", "2025-01-15")
        # Exactly one statement, no prior SELECT-then-branch.
        assert cur.execute.call_count == 1
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO Grades" in sql
        assert "ON CONFLICT" in sql and "DO UPDATE" in sql

    def test_upsert_grade_passes_all_values(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        repo = GradesRepository(conn)
        repo.upsert_grade(7, 3, 2, 5, 12.0, "note", "2025-01-15")
        params = cur.execute.call_args[0][1]
        assert params == (7, 3, 2, 12.0, "note", "2025-01-15", 5)


class TestGradesRepoSearch:
    def test_search_grades_no_filters(self):
        rows = [("2025-01-01", "6A", "Ali", "Maths", "DS1", 15.0, "")]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        result = repo.search_grades(1)
        assert result == rows

    def test_search_grades_with_class_filter(self):
        conn, cur = _plain_cursor(rows=[])
        repo = GradesRepository(conn)
        repo.search_grades(1, class_id=2)
        sql = cur.execute.call_args[0][0]
        assert "class_id" in sql or "SCN.class_id" in sql

    def test_search_grades_with_period_filter(self):
        conn, cur = _plain_cursor(rows=[])
        repo = GradesRepository(conn)
        repo.search_grades(1, period_id=3)
        sql = cur.execute.call_args[0][0]
        assert "period_id" in sql

    def test_search_grades_with_name_filter(self):
        conn, cur = _plain_cursor(rows=[])
        repo = GradesRepository(conn)
        repo.search_grades(1, student_name="Ali")
        sql = cur.execute.call_args[0][0]
        assert "ILIKE" in sql

    def test_get_low_average_students(self):
        rows = [("Ali", 6.5)]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        result = repo.get_low_average_students(1, threshold=8.0)
        assert result == rows


class TestGradesRepoLabels:
    def test_get_class_label_found(self):
        conn, cur = _plain_cursor(fetchone_val=("6ème A",))
        repo = GradesRepository(conn)
        assert repo.get_class_label(1) == "6ème A"

    def test_get_class_label_not_found(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = GradesRepository(conn)
        assert repo.get_class_label(99) == "Classe"

    def test_get_subject_label_found(self):
        conn, cur = _plain_cursor(fetchone_val=("Mathématiques",))
        repo = GradesRepository(conn)
        assert repo.get_subject_label(1) == "Mathématiques"

    def test_get_subject_label_not_found(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = GradesRepository(conn)
        assert repo.get_subject_label(99) == "Matière"

    def test_get_assessment_label_found(self):
        conn, cur = _plain_cursor(fetchone_val=("DS1",))
        repo = GradesRepository(conn)
        assert repo.get_assessment_label(1) == "DS1"

    def test_get_assessment_label_not_found(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = GradesRepository(conn)
        assert repo.get_assessment_label(99) == "Évaluation"

    def test_get_students_for_class_year(self):
        rows = [(1, "Ali Ben", "علي بن")]
        conn, cur = _plain_cursor(rows=rows)
        repo = GradesRepository(conn)
        result = repo.get_students_for_class_year(1, 1)
        assert result == rows


# ════════════════════════════════════════════════════════════════════════════
# StaffRepository
# ════════════════════════════════════════════════════════════════════════════


class TestStaffRepoBasic:
    def test_list_staff_returns_rows(self):
        rows = [(1, "Ali Ben", "Prof", "Maths", "0700000", "CDI", 3000, 50, "", "Actif")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.list_staff()
        assert result == rows

    def test_list_staff_with_search(self):
        conn, cur = _plain_cursor(rows=[])
        repo = StaffRepository(conn)
        repo.list_staff(search="Ali")
        params = cur.execute.call_args[0][1]
        assert "%Ali%" in params

    def test_get_staff_details(self):
        row = ("Ali", "Ben", "Prof", "Maths", "0700000", "ali@mail", "", "2020-01-01", "CDI", 3000, 50, "", "Actif")
        conn, cur = _plain_cursor(fetchone_val=row)
        repo = StaffRepository(conn)
        assert repo.get_staff_details(1) == row

    def test_get_photo_path_found(self):
        conn, cur = _plain_cursor(fetchone_val=("photos/ali.jpg",))
        repo = StaffRepository(conn)
        assert repo.get_photo_path(1) == "photos/ali.jpg"

    def test_get_photo_path_not_found(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = StaffRepository(conn)
        assert repo.get_photo_path(99) is None

    def test_add_staff_executes_insert(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        data = {
            "first_name": "Ali",
            "last_name": "Ben",
            "role": "Prof",
            "specialty": "Maths",
            "phone": "0700",
            "hire_date": "2020-01-01",
            "contract_type": "CDI",
            "salary_base": 3000,
            "hourly_rate": 50,
        }
        repo.add_staff(data)
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO Staff" in sql

    def test_update_staff_executes_update(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        data = {
            "first_name": "Ali",
            "last_name": "Ben",
            "role": "Prof",
            "specialty": "Maths",
            "phone": "0700",
            "hire_date": "2020-01-01",
            "contract_type": "CDI",
            "salary_base": 3000,
            "hourly_rate": 50,
        }
        repo.update_staff(1, data)
        sql = cur.execute.call_args[0][0]
        assert "UPDATE Staff" in sql

    def test_archive_staff(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        repo.archive_staff(5)
        sql = cur.execute.call_args[0][0]
        assert "Archived" in sql
        assert cur.execute.call_args[0][1] == (5,)


class TestStaffRepoSubjectsAndTimetable:
    def test_list_subjects(self):
        rows = [(1, "Maths")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        assert repo.list_subjects() == rows

    def test_list_timetable(self):
        rows = [(1, "Ben Ali", "6A", "Maths", "Lundi", "08:00 - 09:00")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        assert repo.list_timetable() == rows

    def test_get_timetable_for_class(self):
        rows = [("Lundi", "08:00", "09:00", "Maths", "Ben Ali")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        assert repo.get_timetable_for_class(1) == rows

    def test_delete_timetable_entry(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        repo.delete_timetable_entry(7)
        sql = cur.execute.call_args[0][0]
        assert "DELETE FROM Timetable" in sql

    def test_list_staff_for_report(self):
        rows = [(1, "Ali Ben", "Prof", "Maths", "070", "ali@m", "", "2020-01-01", "CDI", 3000, 50, "Actif")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        assert repo.list_staff_for_report() == rows

    def test_insert_timetable_entry(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        repo.insert_timetable_entry(1, 2, 3, "Lundi", "08:00", "09:00")
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO Timetable" in sql


class TestStaffRepoAttendance:
    def test_list_active_staff_fullname(self):
        rows = [(1, "Ali Ben")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        assert repo.list_active_staff_fullname() == rows

    def test_list_active_staff_by_role_all(self):
        rows = [(1, "Ali Ben", "Prof")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.list_active_staff_by_role()
        assert result == rows
        sql = cur.execute.call_args[0][0]
        assert "role =" not in sql

    def test_list_active_staff_by_role_filtered(self):
        conn, cur = _plain_cursor(rows=[])
        repo = StaffRepository(conn)
        repo.list_active_staff_by_role(role_filter="Prof")
        sql = cur.execute.call_args[0][0]
        assert "role = %s" in sql

    def test_get_staff_attendance_for_date(self):
        row = ("Présent", "08:00", "17:00", "")
        conn, cur = _plain_cursor(fetchone_val=row)
        repo = StaffRepository(conn)
        assert repo.get_staff_attendance_for_date(1, "2025-01-15") == row

    def test_upsert_staff_attendance(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        repo.upsert_staff_attendance(1, "2025-01-15", "08:00", "17:00", "Présent", "")
        calls = [c[0][0] for c in cur.execute.call_args_list]
        assert any("DELETE" in s for s in calls)
        assert any("INSERT" in s for s in calls)

    def test_get_attendance_report_with_staff(self):
        rows = [("2025-01-15", "Présent", "08:00", "17:00", "")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.get_attendance_report("2025-01-01", "2025-02-01", staff_id=1)
        assert result == rows

    def test_get_attendance_report_all_staff(self):
        conn, cur = _plain_cursor(rows=[])
        repo = StaffRepository(conn)
        repo.get_attendance_report("2025-01-01", "2025-02-01", staff_id=None)
        sql = cur.execute.call_args[0][0]
        assert "JOIN Staff" in sql

    def test_get_attendance_report_for_display_with_filter(self):
        conn, cur = _plain_cursor(rows=[])
        repo = StaffRepository(conn)
        repo.get_attendance_report_for_display("2025-01-01", "2025-02-01", staff_id=2)
        sql, params = cur.execute.call_args[0]
        assert "staff_id" in sql
        assert 2 in params

    def test_get_attendance_report_for_display_no_filter(self):
        conn, cur = _plain_cursor(rows=[])
        repo = StaffRepository(conn)
        repo.get_attendance_report_for_display("2025-01-01", "2025-02-01")
        sql = cur.execute.call_args[0][0]
        assert "JOIN Staff" in sql

    def test_get_school_info(self):
        row = (1, "École Primaire", "Dakar", "SN")
        conn, cur = _plain_cursor(fetchone_val=row)
        repo = StaffRepository(conn)
        assert repo.get_school_info() == row


class TestStaffRepoLeaves:
    def test_insert_leave(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        repo.insert_leave(1, "Congé", "2025-01-01", "2025-01-07", 5, "Vacances")
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO StaffLeaves" in sql

    def test_list_leaves(self):
        rows = [(1, "Ali Ben", "Congé", "2025-01-01", "2025-01-07", 5, "En Attente")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        assert repo.list_leaves() == rows

    def test_update_leave_status(self):
        conn, cur = _plain_cursor()
        repo = StaffRepository(conn)
        repo.update_leave_status(3, "Approuvé")
        sql, params = cur.execute.call_args[0]
        assert "UPDATE StaffLeaves" in sql
        assert params == ("Approuvé", 3)

    def test_get_leaves_summary_report(self):
        rows = [("Ali Ben", 2, 10, 0, 0)]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.get_leaves_summary_report("2025-01-01", "2025-01-31")
        assert result == rows

    def test_get_leaves_detail_report(self):
        rows = [("Ali Ben", "Congé", "2025-01-01", "2025-01-07", 5, "Approuvé", "")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.get_leaves_detail_report("2025-01-01", "2025-01-31")
        assert result == rows

    def test_get_leave_request_by_id(self):
        row = (1, "Ali Ben", "Congé", "2025-01-01", "2025-01-07", 5, "En Attente", "Vacances")
        conn, cur = _plain_cursor(fetchone_val=row)
        repo = StaffRepository(conn)
        assert repo.get_leave_request_by_id(1) == row

    def test_list_pending_leaves(self):
        rows = [("Ali Ben", "Congé")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.list_pending_leaves(limit=5)
        assert result == rows


class TestStaffRepoExtra:
    def test_get_active_staff_count(self):
        conn, cur = _plain_cursor(fetchone_val=(12,))
        repo = StaffRepository(conn)
        assert repo.get_active_staff_count() == 12

    def test_get_active_staff_count_none(self):
        conn, cur = _plain_cursor(fetchone_val=None)
        repo = StaffRepository(conn)
        assert repo.get_active_staff_count() == 0

    def test_get_teacher_timetable_for_day(self):
        rows = [("6A", "08:00", "09:00")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.get_teacher_timetable_for_day(1, "Lundi")
        assert result == rows

    def test_get_class_timetable_for_day(self):
        rows = [("Ben Ali", "Maths", "08:00", "09:00")]
        conn, cur = _plain_cursor(rows=rows)
        repo = StaffRepository(conn)
        result = repo.get_class_timetable_for_day(1, "Lundi")
        assert result == rows
