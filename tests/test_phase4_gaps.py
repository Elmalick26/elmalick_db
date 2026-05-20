"""Phase 4 — Remaining small coverage gaps.

Covers:
- repositories/bulletin_repo.py (import shim, 2 lines)
- src/data/global_search_repo.py lines 58, 79-81 (staff + payments loops)
- src/data/staff_repo.py line 223-225 (list_classes)
- src/data/timetable_repo.py lines 71-86 (list_slots_for_print)
"""

from __future__ import annotations

from unittest.mock import MagicMock

# ── repositories/bulletin_repo shim ─────────────────────────────────────────
# Importing this covers the 2 missing lines in the shim module.
from repositories.bulletin_repo import BulletinRepository  # noqa: F401
from repositories.global_search_repo import GlobalSearchRepository
from src.data.staff_repo import StaffRepository
from src.data.timetable_repo import TimetableRepository

# ===========================================================================
# GlobalSearchRepository — staff and payments result loops
# ===========================================================================


def _global_search_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


class TestGlobalSearchStaffAndPaymentLoops:
    def test_staff_results_appended(self):
        conn, cur = _global_search_conn()
        cur.fetchall.side_effect = [
            [],  # students
            [(5, "Diop Ahmed", "Directeur")],  # staff — covers line 58
            [],  # payments
            [],  # auditlogs
        ]
        repo = GlobalSearchRepository(conn)
        results = repo.search_all("%diop%")
        assert len(results) == 1
        assert results[0][0] == "Personnel"
        assert results[0][4] == 5

    def test_payment_results_appended(self):
        conn, cur = _global_search_conn()
        cur.fetchall.side_effect = [
            [],  # students
            [],  # staff
            [(10, "Ali Ben", "2026-01-10", 5000.0)],  # payments — covers lines 79-81
            [],  # auditlogs
        ]
        repo = GlobalSearchRepository(conn)
        results = repo.search_all("%ali%")
        assert len(results) == 1
        assert results[0][0] == "Paiement"
        assert results[0][4] == 10
        assert "Reçu #10" in results[0][2]

    def test_payment_with_none_date(self):
        conn, cur = _global_search_conn()
        cur.fetchall.side_effect = [
            [],
            [],
            [(11, "Ben Ali", None, 3000.0)],  # tx_date is None → date_str = ""
            [],
        ]
        repo = GlobalSearchRepository(conn)
        results = repo.search_all("%ben%")
        assert results[0][2].startswith("Reçu #11")


# ===========================================================================
# StaffRepository — list_classes (lines 223-225)
# ===========================================================================


class TestStaffListClasses:
    def test_returns_list(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [(1, "CE1"), (2, "CE2")]
        repo = StaffRepository(conn)
        result = repo.list_classes()
        assert result == [(1, "CE1"), (2, "CE2")]

    def test_empty(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = StaffRepository(conn)
        assert repo.list_classes() == []


# ===========================================================================
# TimetableRepository — list_slots_for_print (lines 71-86)
# ===========================================================================


class TestTimetableListSlotsForPrint:
    def test_returns_list(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            (1, "08:00", "09:00", "Math", "Ahmed Diop", "A1"),
            (2, "09:00", "10:00", "Français", "—", "B2"),
        ]
        repo = TimetableRepository(conn)
        result = repo.list_slots_for_print(class_id=1)
        assert len(result) == 2
        assert result[0][3] == "Math"

    def test_empty(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        repo = TimetableRepository(conn)
        assert repo.list_slots_for_print(class_id=99) == []
