"""
tests/test_repositories.py
اختبارات Repository Pattern باستخدام Mock لاتصال قاعدة البيانات.
"""

import pytest
from unittest.mock import MagicMock
from repositories.student_repo import StudentRepository
from repositories.finance_repo import FinanceRepository
from repositories.staff_repo import StaffRepository


def make_cursor(rows=None):
    """Helper: ينشئ cursor مزيف."""
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = rows[0] if rows else None
    return cur


def make_conn(cursor=None):
    conn = MagicMock()
    conn.cursor.return_value = cursor or MagicMock()
    return conn


# ─────────────────────────────────────────────────────────────
# StudentRepository
# ─────────────────────────────────────────────────────────────
class TestStudentRepository:

    def test_get_student_for_edit_found(self):
        row = ("Ahmed", "Ba", "أحمد", "با", "2010-01-01", "Dakar", "M",
               "", "Parent", "123", "p@ex.com", "", "2026-01-01", "Active", None, 3)
        cur = make_cursor([row])
        conn = make_conn(cur)

        repo = StudentRepository(conn)
        result = repo.get_student_for_edit(active_year_id=1, student_id=1)

        assert result is not None
        assert result[0] == "Ahmed"

    def test_get_student_for_edit_not_found(self):
        cur = make_cursor([])
        cur.fetchone.return_value = None
        conn = make_conn(cur)

        repo = StudentRepository(conn)
        assert repo.get_student_for_edit(1, 9999) is None

    def test_list_students_no_filter(self):
        rows = [
            (1, "Moussa", "Diop", "موسى", "جوب", "M", "CI2", "Papa", "77x", "2026-01-01", 101),
        ]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        repo = StudentRepository(conn)
        result = repo.list_students(year_id=1)

        assert result == rows
        cur.execute.assert_called_once()

    def test_list_students_with_search(self):
        cur = make_cursor([])
        conn = make_conn(cur)

        repo = StudentRepository(conn)
        repo.list_students(year_id=1, search="Moussa")

        # الاستعلام يجب أن يحتوي على ILIKE
        call_args = cur.execute.call_args[0]
        assert "ILIKE" in call_args[0]

    def test_list_students_with_class_filter(self):
        cur = make_cursor([])
        conn = make_conn(cur)
        StudentRepository(conn).list_students(year_id=1, class_id=5)
        sql = cur.execute.call_args[0][0]
        assert "class_id" in sql.lower() or "SCN.class_id" in sql

    def test_add_student_returns_id(self):
        cur = make_cursor()
        cur.fetchone.return_value = (42,)
        conn = make_conn(cur)

        data = {
            "first_name_fr": "Ali", "last_name_fr": "Sow",
            "first_name_ar": "علي", "last_name_ar": "صو",
            "birth_date": "2010-06-15", "birth_place": "Dakar",
            "gender": "M", "address": "", "parent_name": "Ibra",
            "parent_phone": "77123", "parent_email": "", "parent_address": "",
            "registration_date": "2026-09-01", "status": "Active", "photo_path": None,
        }
        new_id = StudentRepository(conn).add_student(data)
        assert new_id == 42

    def test_delete_student_executes_two_queries(self):
        cur = MagicMock()
        conn = make_conn(cur)

        StudentRepository(conn).delete_student(7)
        assert cur.execute.call_count == 2


# ─────────────────────────────────────────────────────────────
# FinanceRepository
# ─────────────────────────────────────────────────────────────
class TestFinanceRepository:

    def test_list_classes(self):
        rows = [(1, "CI1"), (2, "CI2")]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        result = FinanceRepository(conn).list_classes()
        assert len(result) == 2
        assert result[0][1] == "CI1"

    def test_list_students_by_class(self):
        rows = [(5, "Ahmed Ba"), (6, "Fatou Ndiaye")]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        result = FinanceRepository(conn).list_students_by_class(class_id=2, year_id=1)
        assert len(result) == 2

    def test_list_dues_for_student(self):
        rows = [(10, "Frais mensuel", 5000, 0, "2026-02-01", 0.0)]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        result = FinanceRepository(conn).list_dues_for_student(student_id=1, year_id=1)
        assert len(result) == 1
        assert result[0][1] == "Frais mensuel"

    def test_list_late_payers(self):
        rows = [("Moussa Diop", "CI2", "Frais janv.", 5000)]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        result = FinanceRepository(conn).list_late_payers(year_id=1, as_of_date="2026-03-01")
        assert len(result) == 1

    def test_list_payment_history(self):
        rows = [(1, "2026-01-15", "Frais scolaires", 10000.0, 5000.0)]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        result = FinanceRepository(conn).list_payment_history(student_id=1)
        assert len(result) == 1


# ─────────────────────────────────────────────────────────────
# StaffRepository
# ─────────────────────────────────────────────────────────────
class TestStaffRepository:

    def test_list_staff_no_filter(self):
        rows = [(1, "Moussa Diallo", "Professeur", "Maths", "77x",
                 "CDI", 150000, 0, None, "Actif")]
        cur = make_cursor(rows)
        conn = make_conn(cur)

        result = StaffRepository(conn).list_staff()
        assert len(result) == 1
        assert result[0][2] == "Professeur"

    def test_list_staff_with_search(self):
        cur = make_cursor([])
        conn = make_conn(cur)
        StaffRepository(conn).list_staff(search="Diallo")
        sql = cur.execute.call_args[0][0]
        assert "ILIKE" in sql

    def test_get_staff_details_found(self):
        row = ("Aissatou", "Ndiaye", "Secretaire", "Admin", "76x",
               "a@ex.com", "Dakar", "2020-01-01", "CDI", 80000, 0, None, "Actif")
        cur = make_cursor([row])
        conn = make_conn(cur)

        result = StaffRepository(conn).get_staff_details(3)
        assert result is not None
        assert result[2] == "Secretaire"

    def test_get_staff_details_not_found(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        conn = make_conn(cur)

        assert StaffRepository(conn).get_staff_details(9999) is None

    def test_get_photo_path_found(self):
        cur = MagicMock()
        cur.fetchone.return_value = ("/path/to/photo.jpg",)
        conn = make_conn(cur)

        result = StaffRepository(conn).get_photo_path(5)
        assert result == "/path/to/photo.jpg"

    def test_get_photo_path_not_found(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        conn = make_conn(cur)

        assert StaffRepository(conn).get_photo_path(999) is None

    def test_archive_staff_calls_update(self):
        cur = MagicMock()
        conn = make_conn(cur)

        StaffRepository(conn).archive_staff(10)
        sql = cur.execute.call_args[0][0]
        assert "Archived" in sql
        assert "id=%s" in sql or "id = %s" in sql



