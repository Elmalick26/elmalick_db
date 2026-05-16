"""Tests for services/migration_service.py using MagicMock cursors.

The MigrationService uses %s (psycopg2 / PostgreSQL) placeholders so we cannot
use a raw sqlite3 connection.  Instead we mock the connection/cursor and verify
the business logic (branching, call counts, etc.) without a real database.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock

import pytest

from services.migration_service import MigrationService

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_conn(fetchone_sequence=None):
    """Build a mock connection whose cursor().fetchone() returns items from
    *fetchone_sequence* in order (default: always returns (0,) then None)."""
    cursor = MagicMock()
    if fetchone_sequence is not None:
        cursor.fetchone.side_effect = list(fetchone_sequence)
    else:
        cursor.fetchone.return_value = (0,)
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def _row(student_id, decision, current_class_id, next_class_id=None):
    return {
        "student_id": student_id,
        "decision": decision,
        "current_class_id": current_class_id,
        "next_class_id": next_class_id,
    }


@pytest.fixture
def svc():
    return MigrationService()


# ──────────────────────────────────────────────
# execute_migration
# ──────────────────────────────────────────────


class TestExecuteMigration:
    def test_admis_with_next_class_inserts_class_number(self, svc):
        """Admis + next_class_id → SELECT MAX then INSERT StudentClassNumbers."""
        conn, cursor = _make_conn(fetchone_sequence=[(0,), None])
        rows = [_row(1, "Admis", current_class_id=10, next_class_id=20)]

        count = svc.execute_migration(conn, rows, target_year_id=2024)

        assert count == 1
        sql_calls = [str(c.args[0]) for c in cursor.execute.call_args_list]
        assert any("INSERT INTO StudentClassNumbers" in s for s in sql_calls)

    def test_admis_with_existing_scn_row_does_update(self, svc):
        """When a StudentClassNumbers row already exists for the target year → UPDATE."""
        conn, cursor = _make_conn(fetchone_sequence=[(3,), (42,)])
        rows = [_row(1, "Admis", current_class_id=10, next_class_id=20)]

        svc.execute_migration(conn, rows, target_year_id=2024)

        sql_calls = [str(c.args[0]) for c in cursor.execute.call_args_list]
        assert any("UPDATE StudentClassNumbers" in s for s in sql_calls)

    def test_redouble_uses_current_class_id(self, svc):
        """Redouble → destination_class_id == current_class_id (10 in this case)."""
        conn, cursor = _make_conn(fetchone_sequence=[(0,), None])
        rows = [_row(1, "Redouble", current_class_id=10)]

        svc.execute_migration(conn, rows, target_year_id=2024)

        all_params = [c.args[1] for c in cursor.execute.call_args_list if len(c.args) > 1]
        flat = [p for params in all_params for p in params]
        assert 10 in flat

    def test_exclu_sets_status_exclu(self, svc):
        """Exclu → UPDATE Students SET status='Exclu'."""
        conn, cursor = _make_conn()
        rows = [_row(1, "Exclu", current_class_id=10)]

        svc.execute_migration(conn, rows, target_year_id=2024)

        sql_calls = [str(c.args[0]) for c in cursor.execute.call_args_list]
        assert any("Exclu" in s and "Students" in s for s in sql_calls)

    def test_admis_no_next_class_sets_diplome(self, svc):
        """Admis + next_class_id=None → UPDATE Students SET status='Diplômé'."""
        conn, cursor = _make_conn()
        rows = [_row(1, "Admis", current_class_id=10, next_class_id=None)]

        svc.execute_migration(conn, rows, target_year_id=2024)

        sql_calls = [str(c.args[0]) for c in cursor.execute.call_args_list]
        assert any("Diplôm" in s for s in sql_calls)

    def test_multiple_students_returns_correct_count(self, svc):
        """Returns processed count equal to number of input rows."""
        # Admis needs 2 fetchone; Exclu needs none
        conn, cursor = _make_conn(fetchone_sequence=[(0,), None, (0,), None])
        rows = [
            _row(1, "Admis", current_class_id=10, next_class_id=20),
            _row(2, "Exclu", current_class_id=10),
        ]

        count = svc.execute_migration(conn, rows, target_year_id=2024)
        assert count == 2

    def test_admis_active_year_update(self, svc):
        """change_active_year=True → UPDATE AcademicYears is called."""
        conn, cursor = _make_conn(fetchone_sequence=[(0,), None])
        rows = [_row(1, "Admis", current_class_id=10, next_class_id=20)]

        svc.execute_migration(conn, rows, target_year_id=2024, change_active_year=True)

        sql_calls = [str(c.args[0]) for c in cursor.execute.call_args_list]
        assert any("AcademicYears" in s for s in sql_calls)

    def test_admis_next_number_increments_from_existing_max(self, svc):
        """Mutation guard: Or→And in (max_number_result[0] or 0) + 1.
        When max_number = 5, next class_number must be 6 (not 1 as the And
        mutation would produce via `5 and 0 + 1`)."""
        conn, cursor = _make_conn(fetchone_sequence=[(5,), None])
        rows = [_row(1, "Admis", current_class_id=10, next_class_id=20)]

        svc.execute_migration(conn, rows, target_year_id=2024)

        all_params = [c.args[1] for c in cursor.execute.call_args_list if len(c.args) > 1]
        flat = [p for params in all_params for p in params]
        assert 6 in flat, "next class_number should be max+1 = 6"
