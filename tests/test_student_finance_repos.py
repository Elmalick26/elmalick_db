"""Tests for StudentRepository and FinanceRepository."""

from unittest.mock import MagicMock, call

import pytest

from repositories.finance_repo import FinanceRepository
from repositories.student_repo import StudentRepository

# ─── helpers ────────────────────────────────────────────────────────────────


def _conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


_STUDENT_DATA = {
    "first_name_fr": "Ahmed",
    "last_name_fr": "Ba",
    "first_name_ar": "أحمد",
    "last_name_ar": "با",
    "birth_date": "2010-05-01",
    "birth_place": "Dakar",
    "gender": "M",
    "address": "Rue 12",
    "parent_name": "Mamadou Ba",
    "parent_phone": "771234567",
    "parent_email": "m@ex.com",
    "parent_address": "Rue 13",
    "registration_date": "2026-09-01",
    "status": "Active",
    "photo_path": None,
}


# ─── StudentRepository ───────────────────────────────────────────────────────


class TestStudentRepository:
    def test_get_student_for_edit(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (
            "Ahmed",
            "Ba",
            "أحمد",
            "با",
            "2010-05-01",
            "Dakar",
            "M",
            "Rue 12",
            "Parent",
            "771234567",
            None,
            None,
            "2026-09-01",
            "Active",
            None,
            1,
        )
        repo = StudentRepository(conn)
        row = repo.get_student_for_edit(1, 10)
        assert row[0] == "Ahmed"
        assert "SELECT" in cur.execute.call_args[0][0]

    def test_list_students_no_filters(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [
            (1, "Ahmed", "Ba", "أحمد", "با", "M", "CE1", "Parent", "77", "2026-09-01", 5, "EMG-001")
        ]
        repo = StudentRepository(conn)
        rows = repo.list_students(year_id=1)
        assert len(rows) == 1
        assert rows[0][1] == "Ahmed"

    def test_list_students_with_class_filter(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students(year_id=1, class_id=2)
        sql = cur.execute.call_args[0][0]
        assert "SCN.class_id = %s" in sql

    def test_list_students_with_cycle_filter(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students(year_id=1, cycle_id=3)
        sql = cur.execute.call_args[0][0]
        assert "C.cycle_id = %s" in sql

    def test_list_students_with_search(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students(year_id=1, search="Ahmed")
        sql = cur.execute.call_args[0][0]
        assert "ILIKE" in sql

    def test_list_students_with_date_range(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students(year_id=1, date_from="2026-01-01", date_to="2026-12-31")
        sql = cur.execute.call_args[0][0]
        assert "BETWEEN" in sql

    def test_list_students_detailed(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = StudentRepository(conn)
        repo.list_students_detailed(year_id=1, class_id=2)
        sql = cur.execute.call_args[0][0]
        assert "Students S" in sql

    def test_add_student_returns_id(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (55,)
        repo = StudentRepository(conn)
        new_id = repo.add_student(_STUDENT_DATA)
        assert new_id == 55
        # Two calls: INSERT then UPDATE student_code — check the first call
        first_call_sql = cur.execute.call_args_list[0][0][0]
        assert "INSERT INTO Students" in first_call_sql
        # Verify student_code generation was also called
        last_call_sql = cur.execute.call_args_list[-1][0][0]
        assert "student_code" in last_call_sql

    def test_update_student_no_photo(self):
        conn, cur = _conn()
        repo = StudentRepository(conn)
        data = dict(_STUDENT_DATA)  # photo_path=None
        repo.update_student(student_id=1, data=data)
        sql = cur.execute.call_args[0][0]
        assert "UPDATE Students" in sql
        assert "photo_path" not in sql

    def test_update_student_with_photo(self):
        conn, cur = _conn()
        repo = StudentRepository(conn)
        data = dict(_STUDENT_DATA, photo_path="/photos/ahmed.jpg")
        repo.update_student(student_id=1, data=data)
        sql = cur.execute.call_args[0][0]
        assert "photo_path=%s" in sql

    def test_delete_student(self):
        conn, cur = _conn()
        repo = StudentRepository(conn)
        repo.delete_student(student_id=1)
        calls = [str(c) for c in cur.execute.call_args_list]
        assert any("StudentClassNumbers" in c for c in calls)
        assert any("DELETE FROM Students" in c for c in calls)

    def test_get_active_year_id_active_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (3,)
        repo = StudentRepository(conn)
        assert repo.get_active_year_id() == 3

    def test_get_active_year_id_fallback(self):
        conn, cur = _conn()
        # First call returns None (no is_active=1), second returns latest
        cur.fetchone.side_effect = [None, (2,)]
        repo = StudentRepository(conn)
        assert repo.get_active_year_id() == 2

    def test_get_active_year_id_no_years(self):
        conn, cur = _conn()
        cur.fetchone.side_effect = [None, None]
        repo = StudentRepository(conn)
        assert repo.get_active_year_id() == -1

    def test_list_cycles(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Primaire"), (2, "Collège")]
        repo = StudentRepository(conn)
        rows = repo.list_cycles()
        assert len(rows) == 2

    def test_list_classes_all(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1"), (2, "CM1")]
        repo = StudentRepository(conn)
        rows = repo.list_classes()
        assert len(rows) == 2

    def test_list_classes_by_cycle(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1")]
        repo = StudentRepository(conn)
        rows = repo.list_classes(cycle_id=1)
        sql = cur.execute.call_args[0][0]
        assert "cycle_id = %s" in sql

    def test_get_next_class_number(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (9,)
        repo = StudentRepository(conn)
        assert repo.get_next_class_number(class_id=1, year_id=1) == 10

    def test_get_next_class_number_empty(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (None,)
        repo = StudentRepository(conn)
        assert repo.get_next_class_number(1, 1) == 1

    def test_get_class_assignment_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (2, 7)
        repo = StudentRepository(conn)
        result = repo.get_class_assignment(student_id=1, year_id=1)
        assert result == (2, 7)

    def test_get_class_assignment_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = StudentRepository(conn)
        assert repo.get_class_assignment(1, 1) is None

    def test_set_class_assignment_update(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (2, 7)  # existing assignment
        repo = StudentRepository(conn)
        repo.set_class_assignment(student_id=1, class_id=3, year_id=1, number=8)
        last_sql = cur.execute.call_args_list[-1][0][0]
        assert "UPDATE StudentClassNumbers" in last_sql

    def test_set_class_assignment_insert(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None  # no existing assignment
        repo = StudentRepository(conn)
        repo.set_class_assignment(student_id=1, class_id=3, year_id=1, number=1)
        last_sql = cur.execute.call_args_list[-1][0][0]
        assert "INSERT INTO StudentClassNumbers" in last_sql

    def test_count_active_students(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (42,)
        repo = StudentRepository(conn)
        assert repo.count_active_students(year_id=1) == 42

    def test_count_classes(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (8,)
        repo = StudentRepository(conn)
        assert repo.count_classes() == 8

    def test_get_students_by_cycle(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Primaire", 120), ("Collège", 45)]
        repo = StudentRepository(conn)
        rows = repo.get_students_by_cycle(year_id=1)
        assert rows[0][1] == 120


# ─── FinanceRepository ───────────────────────────────────────────────────────


class TestFinanceRepository:
    def test_list_classes(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1"), (2, "CM1")]
        repo = FinanceRepository(conn)
        rows = repo.list_classes()
        assert len(rows) == 2

    def test_list_students_by_class(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Ahmed Ba"), (2, "Fatou Diop")]
        repo = FinanceRepository(conn)
        rows = repo.list_students_by_class(class_id=1, year_id=1)
        assert rows[0][1] == "Ahmed Ba"
        sql = cur.execute.call_args[0][0]
        assert "SCN.class_id = %s" in sql

    def test_list_dues_for_student(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Inscription", 50000, 0, "2026-09-30", 0)]
        repo = FinanceRepository(conn)
        rows = repo.list_dues_for_student(student_id=1, year_id=1)
        assert len(rows) == 1
        assert rows[0][1] == "Inscription"

    def test_list_late_payers(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Ahmed Ba", "CE1", "Inscription", 50000)]
        repo = FinanceRepository(conn)
        rows = repo.list_late_payers(year_id=1, as_of_date="2026-12-31")
        assert len(rows) == 1
