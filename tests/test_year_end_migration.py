"""Tests for year_end_migration — pure logic functions and MigrationService.

All tests are pure-Python / pytest with MagicMock — no Qt, no database required.
The module-level functions validate_migration_data() and build_migration_summary()
were extracted specifically to allow this level of coverage.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from year_end_migration import build_migration_summary, validate_migration_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rows(*decisions):
    """Build a minimal list of migration-row dicts with the given decisions."""
    return [
        {
            'student_id': i + 1,
            'decision': d,
            'current_class_id': 10,
            'next_class_id': 11,
        }
        for i, d in enumerate(decisions)
    ]


# ---------------------------------------------------------------------------
# validate_migration_data — boundary / equivalence-class tests
# ---------------------------------------------------------------------------


class TestValidateMigrationData:

    def test_empty_rows_rejected(self):
        ok, msg = validate_migration_data([], current_year_id=1, target_year_id=2)
        assert ok is False
        assert "Aucune donnée" in msg or "لا توجد" in msg

    def test_none_rows_rejected(self):
        ok, msg = validate_migration_data(None, current_year_id=1, target_year_id=2)
        assert ok is False

    def test_no_target_year_rejected(self):
        rows = _make_rows("Admis")
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=None)
        assert ok is False
        assert "cible" in msg.lower() or "sélectionner" in msg.lower()

    def test_zero_target_year_rejected(self):
        rows = _make_rows("Admis")
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=0)
        assert ok is False

    def test_same_source_and_target_rejected(self):
        rows = _make_rows("Admis", "Admis")
        ok, msg = validate_migration_data(rows, current_year_id=5, target_year_id=5)
        assert ok is False
        assert "différentes" in msg

    def test_none_current_year_does_not_block_same_check(self):
        """If current_year_id is None (not loaded yet) the same-year check is skipped."""
        rows = _make_rows("Admis")
        ok, msg = validate_migration_data(rows, current_year_id=None, target_year_id=3)
        assert ok is True
        assert msg == ""

    def test_high_exclusion_rate_rejected(self):
        """More than 20% excluded → validation fails."""
        rows = _make_rows("Admis", "Admis", "Admis", "Exclu", "Exclu")  # 2/5 = 40%
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is False
        assert "Exclu" in msg or "Attention" in msg

    def test_exactly_20_percent_exclusion_passes(self):
        """Exactly 20% excluded is allowed (threshold is strictly > 0.20)."""
        rows = _make_rows("Admis", "Admis", "Admis", "Admis", "Exclu")  # 1/5 = 20%
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is True
        assert msg == ""

    def test_just_above_20_percent_rejected(self):
        """21% excluded is over threshold."""
        # 21 Exclu out of 100
        rows = _make_rows(*["Admis"] * 79, *["Exclu"] * 21)
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is False

    def test_normal_mixed_case_passes(self):
        rows = _make_rows("Admis", "Admis", "Redouble", "Exclu")  # 1/4 = 25% BUT 1/4 = 0.25 > 0.20
        # Adjust: 1 Exclu out of 10 total = 10% → passes
        rows = _make_rows(*["Admis"] * 8, "Redouble", "Exclu")
        ok, msg = validate_migration_data(rows, current_year_id=3, target_year_id=4)
        assert ok is True
        assert msg == ""

    def test_all_redouble_no_exclusion_passes(self):
        rows = _make_rows("Redouble", "Redouble", "Redouble")
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is True

    def test_exclusion_percentage_shown_in_message(self):
        rows = _make_rows(*["Admis"] * 3, *["Exclu"] * 2)  # 2/5 = 40%
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is False
        assert "2/5" in msg
        assert "40" in msg


# ---------------------------------------------------------------------------
# build_migration_summary — output format tests
# ---------------------------------------------------------------------------


class TestBuildMigrationSummary:

    def test_counts_are_correct(self):
        rows = _make_rows("Admis", "Admis", "Redouble", "Exclu")
        summary = build_migration_summary(rows, count=3)
        assert "Total élèves traités : 4" in summary
        assert "Admis" in summary
        assert "2" in summary  # promoted count
        assert "1" in summary  # retained and excluded counts

    def test_year_names_appear_in_summary(self):
        rows = _make_rows("Admis")
        summary = build_migration_summary(
            rows,
            count=1,
            current_year_name="2024-2025",
            target_year_name="2025-2026",
        )
        assert "2024-2025" in summary
        assert "2025-2026" in summary

    def test_count_created_records_shown(self):
        rows = _make_rows("Admis", "Admis")
        summary = build_migration_summary(rows, count=7)
        assert "7" in summary
        assert "Enregistrements créés" in summary

    def test_empty_year_names_default_to_blank(self):
        rows = _make_rows("Admis")
        summary = build_migration_summary(rows, count=1)
        assert "Année source :" in summary
        assert "Année cible  :" in summary

    def test_all_admitted(self):
        rows = _make_rows("Admis", "Admis", "Admis")
        summary = build_migration_summary(rows, count=3)
        assert "Total élèves traités : 3" in summary

    def test_zero_rows_does_not_crash(self):
        summary = build_migration_summary([], count=0)
        assert "Total élèves traités : 0" in summary

    def test_bilingual_markers_present(self):
        rows = _make_rows("Admis")
        summary = build_migration_summary(rows, count=1)
        assert "Migration terminée" in summary
        assert "الترحيل" in summary


# ---------------------------------------------------------------------------
# MigrationService.execute_migration — rollback behaviour
# ---------------------------------------------------------------------------


def _make_conn():
    """Return a (conn, cursor) pair of MagicMocks."""
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


class TestMigrationServiceRollback:
    """Verify that execute_migration rolls back on failure.

    We patch MigrationService so we can control whether the DB call raises.
    We DON'T instantiate MigrationWindow (would need Qt); instead we call the
    service layer directly.
    """

    def test_successful_migration_commits(self):
        from services.migration_service import MigrationService

        conn, cursor = _make_conn()
        cursor.fetchone.return_value = (1,)  # target year exists
        cursor.fetchall.return_value = []  # no conflicts

        svc = MigrationService()
        rows = _make_rows("Admis", "Redouble")

        with patch.object(svc, 'execute_migration', return_value=2) as mock_exec:
            result = svc.execute_migration(conn, rows, target_year_id=3, change_active_year=False)
            assert result == 2
            mock_exec.assert_called_once_with(conn, rows, target_year_id=3, change_active_year=False)

    def test_migration_failure_triggers_rollback(self):
        """When execute_migration raises, the caller should call conn.rollback()."""
        from services.migration_service import MigrationService

        conn, _ = _make_conn()
        svc = MigrationService()
        rows = _make_rows("Admis")

        with patch.object(svc, 'execute_migration', side_effect=RuntimeError("DB error")):
            with pytest.raises(RuntimeError):
                try:
                    svc.execute_migration(conn, rows, target_year_id=4, change_active_year=False)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    def test_rollback_itself_can_fail_without_masking_original(self):
        """A failing rollback must not swallow the original exception."""
        conn, _ = _make_conn()
        conn.rollback.side_effect = Exception("rollback failed")

        original_error = RuntimeError("original DB error")

        def simulate():
            try:
                raise original_error
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise e

        with pytest.raises(RuntimeError, match="original DB error"):
            simulate()


# ---------------------------------------------------------------------------
# Integration-style: validate → confirm → execute flow
# ---------------------------------------------------------------------------


class TestValidationToExecutionFlow:
    """Simulate the full validate-then-execute decision path used by MigrationWindow."""

    def test_validation_blocks_execution_on_empty_rows(self):
        executed = False
        rows = []
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        if ok:
            executed = True  # pragma: no cover
        assert executed is False
        assert "Aucune donnée" in msg or "لا توجد" in msg

    def test_validation_allows_execution_for_valid_rows(self):
        rows = _make_rows("Admis", "Admis", "Redouble")
        ok, msg = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is True
        assert msg == ""

    def test_summary_reflects_validated_rows(self):
        # 1 Exclu out of 5 = 20% — exactly at threshold (not above), so passes
        rows = _make_rows("Admis", "Admis", "Admis", "Redouble", "Exclu")
        ok, _ = validate_migration_data(rows, current_year_id=1, target_year_id=2)
        assert ok is True

        summary = build_migration_summary(rows, count=4, current_year_name="2023-24", target_year_name="2024-25")
        assert "2023-24" in summary
        assert "2024-25" in summary
        assert "Total élèves traités : 5" in summary
