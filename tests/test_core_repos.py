"""Tests for InventoryRepository, ImportWizardRepository, YearEndRepository,
AttendanceRepository, GradesRepository — all using mocked connections."""

from unittest.mock import MagicMock, call

import pytest

from repositories.inventory_repo import InventoryRepository
from repositories.import_wizard_repo import ImportWizardRepository
from repositories.year_end_repo import YearEndRepository
from repositories.attendance_repo import AttendanceRepository
from repositories.grades_repo import GradesRepository


# ─── helpers ────────────────────────────────────────────────────────────────

def _conn():
    """Mock psycopg2-style connection + plain cursor."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def _ctx_conn():
    """Mock connection whose cursor is used as a context manager."""
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


# ─── InventoryRepository ────────────────────────────────────────────────────

class TestInventoryRepository:
    def test_list_all_items(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Tableau", "Fourniture", 5, 2, 1500.0, "Bureau")]
        repo = InventoryRepository(conn)
        rows = repo.list_all_items()
        assert len(rows) == 1
        assert "SELECT * FROM InventoryItems" in cur.execute.call_args[0][0]

    def test_get_item_quantity_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (10,)
        repo = InventoryRepository(conn)
        assert repo.get_item_quantity(1) == 10

    def test_get_item_quantity_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = InventoryRepository(conn)
        assert repo.get_item_quantity(999) == 0

    def test_get_item_quantity_none_value(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (None,)
        repo = InventoryRepository(conn)
        assert repo.get_item_quantity(1) == 0

    def test_update_item_quantity(self):
        conn, cur = _conn()
        repo = InventoryRepository(conn)
        repo.update_item_quantity(1, 20)
        sql = cur.execute.call_args[0][0]
        assert "UPDATE InventoryItems" in sql

    def test_insert_item_returns_id(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (42,)
        repo = InventoryRepository(conn)
        new_id = repo.insert_item("Tableau", "لوح", "Fourniture", 5, 1, 1500.0, "Classe 1")
        assert new_id == 42
        assert "INSERT INTO InventoryItems" in cur.execute.call_args[0][0]

    def test_insert_movement_log(self):
        conn, cur = _conn()
        repo = InventoryRepository(conn)
        repo.insert_movement_log(1, "IN", 5, "2026-01-10", "Achat")
        assert "INSERT INTO InventoryLog" in cur.execute.call_args[0][0]

    def test_list_movement_history(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("2026-01-10", "IN", "Tableau", 5, "Achat")]
        repo = InventoryRepository(conn)
        rows = repo.list_movement_history(limit=10)
        assert len(rows) == 1

    def test_get_stock_value_by_category(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Fourniture", 3, 15, 22500.0)]
        repo = InventoryRepository(conn)
        rows = repo.get_stock_value_by_category()
        assert rows[0][0] == "Fourniture"

    def test_get_low_stock_items(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Craie", "Fourniture", 1, 5, "Salle 2")]
        repo = InventoryRepository(conn)
        rows = repo.get_low_stock_items()
        assert rows[0][0] == "Craie"

    def test_get_movements_by_period(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Craie", 20, 15, 5)]
        repo = InventoryRepository(conn)
        rows = repo.get_movements_by_period("2026-01-01", "2026-12-31 23:59:59")
        assert rows[0][0] == "Craie"


# ─── ImportWizardRepository ─────────────────────────────────────────────────

class TestImportWizardRepository:
    def test_get_next_class_number(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = (5,)
        repo = ImportWizardRepository(conn)
        n = repo.get_next_class_number(class_id=1, year_id=2)
        assert n == 5

    def test_get_next_class_number_empty(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = None
        repo = ImportWizardRepository(conn)
        n = repo.get_next_class_number(class_id=1, year_id=2)
        assert n == 1

    def test_insert_student_returns_id(self):
        conn, cur = _ctx_conn()
        cur.fetchone.return_value = (77,)
        repo = ImportWizardRepository(conn)
        data = {
            "first_name_fr": "Ahmed", "last_name_fr": "Ba",
            "first_name_ar": "أحمد", "last_name_ar": "با",
            "birth_date": "2010-01-01", "birth_place": "Dakar",
            "gender": "M", "address": "Rue 10",
            "parent_name": "Mamadou Ba", "parent_phone": "771234567",
            "parent_email": "m@ex.com", "parent_address": "Rue 11",
        }
        sid = repo.insert_student(data)
        assert sid == 77

    def test_insert_student_class_number(self):
        conn, cur = _ctx_conn()
        repo = ImportWizardRepository(conn)
        repo.insert_student_class_number(1, 2, 3, 10)
        assert "INSERT INTO StudentClassNumbers" in cur.execute.call_args[0][0]

    def test_list_academic_years(self):
        conn, cur = _ctx_conn()
        cur.fetchall.return_value = [(1, "2025-2026")]
        repo = ImportWizardRepository(conn)
        years = repo.list_academic_years()
        assert years[0][1] == "2025-2026"

    def test_list_classes(self):
        conn, cur = _ctx_conn()
        cur.fetchall.return_value = [(1, "Cours 1"), (2, "Cours 2")]
        repo = ImportWizardRepository(conn)
        classes = repo.list_classes()
        assert len(classes) == 2


# ─── YearEndRepository ──────────────────────────────────────────────────────

class TestYearEndRepository:
    def test_list_academic_years(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "2024-2025", False), (2, "2025-2026", True)]
        repo = YearEndRepository(conn)
        years = repo.list_academic_years()
        assert len(years) == 2

    def test_list_classes_with_order(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1", 2, 1)]
        repo = YearEndRepository(conn)
        rows = repo.list_classes_with_order()
        assert rows[0][1] == "CE1"

    def test_list_classes_basic(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1", 2)]
        repo = YearEndRepository(conn)
        rows = repo.list_classes_basic()
        assert rows[0][0] == 1

    def test_list_classes_for_combo(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1"), (2, "CE2")]
        repo = YearEndRepository(conn)
        rows = repo.list_classes_for_combo()
        assert len(rows) == 2

    def test_list_period_ids(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1,), (2,), (3,)]
        repo = YearEndRepository(conn)
        ids = repo.list_period_ids(year_id=1)
        assert ids == [1, 2, 3]

    def test_list_active_students_in_class(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(10, "Ahmed", "Ba", 1)]
        repo = YearEndRepository(conn)
        rows = repo.list_active_students_in_class(year_id=1, class_id=1)
        assert rows[0][1] == "Ahmed"

    def test_list_all_active_students(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(10, "Ahmed", "Ba", 1), (11, "Fatou", "Diop", 2)]
        repo = YearEndRepository(conn)
        rows = repo.list_all_active_students(year_id=1)
        assert len(rows) == 2

    def test_list_subjects_with_coefficient(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, 3), (2, 2)]
        repo = YearEndRepository(conn)
        rows = repo.list_subjects_with_coefficient(cycle_id=1)
        assert rows[0] == (1, 3)

    def test_get_grade_average_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (13.5,)
        repo = YearEndRepository(conn)
        avg = repo.get_grade_average(student_id=1, subject_id=1, period_id=1, year_id=1)
        assert avg == 13.5

    def test_get_grade_average_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (None,)
        repo = YearEndRepository(conn)
        avg = repo.get_grade_average(1, 1, 1, 1)
        assert avg is None

    def test_get_fallback_average(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (11.0,)
        repo = YearEndRepository(conn)
        avg = repo.get_fallback_average(student_id=1, year_id=1)
        assert avg == 11.0

    def test_get_fallback_average_no_grades(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (None,)
        repo = YearEndRepository(conn)
        assert repo.get_fallback_average(1, 1) == 0.0

    def test_get_cycle_name_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("Primaire",)
        repo = YearEndRepository(conn)
        assert repo.get_cycle_name(cycle_id=1) == "Primaire"

    def test_get_cycle_name_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = YearEndRepository(conn)
        assert repo.get_cycle_name(cycle_id=99) == ""


# ─── AttendanceRepository ───────────────────────────────────────────────────

class TestAttendanceRepository:
    def test_list_classes(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1"), (2, "CE2")]
        repo = AttendanceRepository(conn)
        rows = repo.list_classes()
        assert len(rows) == 2
        assert "SELECT id, class_name_fr FROM Classes" in cur.execute.call_args[0][0]

    def test_get_periods_for_class_no_cycle(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None  # no cycle found
        repo = AttendanceRepository(conn)
        rows = repo.get_periods_for_class(class_id=1, year_id=1)
        assert rows == []

    def test_get_periods_for_class_invalid_args(self):
        conn, cur = _conn()
        repo = AttendanceRepository(conn)
        rows = repo.get_periods_for_class(class_id=0, year_id=-1)
        assert rows == []

    def test_get_periods_for_class_with_cycle(self):
        conn, cur = _conn()
        # First fetchone → cycle row, second fetchall → periods
        cur.fetchone.return_value = (2,)
        cur.fetchall.return_value = [(1, "Trimestre 1"), (2, "Trimestre 2")]
        repo = AttendanceRepository(conn)
        rows = repo.get_periods_for_class(class_id=1, year_id=1)
        assert len(rows) == 2

    def test_resolve_period_id_invalid_args(self):
        conn, cur = _conn()
        repo = AttendanceRepository(conn)
        assert repo.resolve_period_id_for_class_date(0, "2026-01-01", 1) is None
        assert repo.resolve_period_id_for_class_date(1, "", 1) is None
        assert repo.resolve_period_id_for_class_date(1, "2026-01-01", -1) is None

    def test_resolve_period_id_no_cycle(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AttendanceRepository(conn)
        result = repo.resolve_period_id_for_class_date(1, "2026-01-01", 1)
        assert result is None

    def test_resolve_period_id_found(self):
        conn, cur = _conn()
        # First call: cycle, second call: period
        cur.fetchone.side_effect = [(2,), (5,)]
        repo = AttendanceRepository(conn)
        pid = repo.resolve_period_id_for_class_date(1, "2026-01-15", 1)
        assert pid == 5

    def test_resolve_period_id_not_found(self):
        conn, cur = _conn()
        cur.fetchone.side_effect = [(2,), None]
        repo = AttendanceRepository(conn)
        result = repo.resolve_period_id_for_class_date(1, "2026-07-01", 1)
        assert result is None


# ─── GradesRepository ───────────────────────────────────────────────────────

class TestGradesRepository:
    def test_list_classes(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CE1"), (2, "CM1")]
        repo = GradesRepository(conn)
        rows = repo.list_classes()
        assert len(rows) == 2
        assert "SELECT id, class_name_fr FROM Classes" in cur.execute.call_args[0][0]

    def test_list_periods_for_year(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Trimestre 1"), (2, "Trimestre 2")]
        repo = GradesRepository(conn)
        rows = repo.list_periods_for_year(year_id=1)
        assert len(rows) == 2

    def test_list_periods_for_class_year_with_cycle(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (3,)  # cycle_id
        cur.fetchall.return_value = [(1, "T1"), (2, "T2"), (3, "T3")]
        repo = GradesRepository(conn)
        rows = repo.list_periods_for_class_year(class_id=1, year_id=1)
        assert len(rows) == 3

    def test_list_periods_for_class_year_no_cycle(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        cur.fetchall.return_value = [(1, "T1")]
        repo = GradesRepository(conn)
        rows = repo.list_periods_for_class_year(class_id=1, year_id=1)
        assert len(rows) == 1

    def test_list_assessments_for_period(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Devoir 1"), (2, "Composition")]
        repo = GradesRepository(conn)
        rows = repo.list_assessments_for_period(period_id=1)
        assert len(rows) == 2

    def test_get_cycle_name_for_class_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("Primaire",)
        repo = GradesRepository(conn)
        assert repo.get_cycle_name_for_class(1) == "Primaire"

    def test_get_cycle_name_for_class_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = GradesRepository(conn)
        assert repo.get_cycle_name_for_class(99) is None
