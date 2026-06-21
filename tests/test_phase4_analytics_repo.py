"""Phase 4 — AnalyticsRepository tests.

Covers analytics_repo.py (23% → ~100%).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.data.analytics_repo import AnalyticsRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    repo = AnalyticsRepository(conn)
    return repo, cursor


# ===========================================================================
# Year context
# ===========================================================================


class TestAnalyticsGetActiveYearContext:
    def test_active_year_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (3, "2024-2025")
        year_id, label = repo.get_active_year_context()
        assert year_id == 3
        assert label == "2024-2025"

    def test_no_active_year_fallback_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, (2, "2023-2024")]
        year_id, label = repo.get_active_year_context()
        assert year_id == 2
        assert label == "2023-2024"

    def test_no_years_at_all(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, None]
        year_id, label = repo.get_active_year_context()
        assert year_id is None
        assert label == "N/A"


# ===========================================================================
# Schema introspection
# ===========================================================================


class TestAnalyticsGetStudentColumns:
    def test_returns_lowercase_set(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("Id",), ("FirstName_Fr",), ("Status",)]
        result = repo.get_student_columns()
        assert result == {"id", "firstname_fr", "status"}

    def test_empty(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        assert repo.get_student_columns() == set()


# ===========================================================================
# Class helpers
# ===========================================================================


class TestAnalyticsGetClassMaxScore:
    # Rows are (name_fr, is_primary); flag=None exercises the name-fallback path.
    def test_elementary_cycle(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("elementaire", None)  # lowercase, no accent
        assert repo.get_class_max_score(1) == 10

    def test_primary_cycle(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("Primaire", None)
        assert repo.get_class_max_score(2) == 10

    def test_secondary_cycle(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("Secondaire", None)
        assert repo.get_class_max_score(3) == 20

    def test_class_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_class_max_score(99) == 20

    def test_cycle_name_none(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None, None)
        assert repo.get_class_max_score(1) == 20

    def test_explicit_flag_overrides_name(self):
        # A non-primary-looking name flagged primary still scores /10.
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("Cycle X", True)
        assert repo.get_class_max_score(1) == 10


# ===========================================================================
# Attendance
# ===========================================================================


class TestAnalyticsGetAttendanceSummaryByClass:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("CE1", 25, 20, 4, 1, 25)]
        result = repo.get_attendance_summary_by_class(year_id=1)
        assert result == [("CE1", 25, 20, 4, 1, 25)]

    def test_empty(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        assert repo.get_attendance_summary_by_class(year_id=1) == []


# ===========================================================================
# Grades
# ===========================================================================


class TestAnalyticsGetGradesSummaryByClass:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("CE2", 20, 100, 8.0, 14.5, 20.0)]
        result = repo.get_grades_summary_by_class(year_id=1)
        assert result == [("CE2", 20, 100, 8.0, 14.5, 20.0)]


class TestAnalyticsGetGradesForClass:
    def test_returns_scores(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(15.5,), (12.0,), (18.0,)]
        result = repo.get_grades_for_class(class_id=1, year_id=1)
        assert result == [15.5, 12.0, 18.0]

    def test_empty(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        assert repo.get_grades_for_class(class_id=1, year_id=1) == []


# ===========================================================================
# Financial period filter (static method)
# ===========================================================================


class TestAnalyticsBuildPeriodFilter:
    def test_default_period(self):
        f, params = AnalyticsRepository._build_period_filter("Tout", "transaction_date")
        assert "IS NOT NULL" in f
        assert params == []

    def test_6_months(self):
        f, params = AnalyticsRepository._build_period_filter("6 derniers mois", "transaction_date")
        assert "5 months" in f
        assert params == []

    def test_12_months(self):
        f, params = AnalyticsRepository._build_period_filter("12 derniers mois", "transaction_date")
        assert "11 months" in f
        assert params == []

    def test_current_year(self):
        f, params = AnalyticsRepository._build_period_filter("Année en cours", "transaction_date")
        assert "YYYY" in f
        assert len(params) == 1
        assert len(params[0]) == 4  # year string like "2026"


# ===========================================================================
# Monthly financial totals
# ===========================================================================


class TestAnalyticsGetMonthlyIncomeTotals:
    def test_with_default_period(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-01", 10, 5000.0)]
        result = repo.get_monthly_income_totals("Tout")
        assert result == [("2026-01", 10, 5000.0)]

    def test_with_6_months(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        result = repo.get_monthly_income_totals("6 derniers mois")
        assert result == []

    def test_with_current_year(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-01", 5, 2500.0)]
        result = repo.get_monthly_income_totals("Année en cours")
        assert len(result) == 1


class TestAnalyticsGetMonthlyExpenseTotals:
    def test_with_12_months(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2025-06", 3, 1200.0)]
        result = repo.get_monthly_expense_totals("12 derniers mois")
        assert result == [("2025-06", 3, 1200.0)]

    def test_with_current_year(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        result = repo.get_monthly_expense_totals("Année en cours")
        assert result == []


# ===========================================================================
# Total aggregates
# ===========================================================================


class TestAnalyticsGetTotalIncomeByPeriod:
    def test_returns_float(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (12500.0,)
        result = repo.get_total_income_by_period("Tout")
        assert result == 12500.0

    def test_returns_zero_when_null(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None,)
        result = repo.get_total_income_by_period("6 derniers mois")
        assert result == 0.0

    def test_with_current_year(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (3000.0,)
        result = repo.get_total_income_by_period("Année en cours")
        assert result == 3000.0


class TestAnalyticsGetTotalExpenseByPeriod:
    def test_returns_float(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (5000.0,)
        result = repo.get_total_expense_by_period("Tout")
        assert result == 5000.0

    def test_returns_zero_when_null(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None,)
        result = repo.get_total_expense_by_period("12 derniers mois")
        assert result == 0.0


# ===========================================================================
# Comprehensive stats
# ===========================================================================


class TestAnalyticsGetComprehensiveStats:
    def test_with_year_id(self):
        repo, cursor = _make_repo()
        # 5 fetchone calls: active_students, total_classes, presents, absents, lates
        cursor.fetchone.side_effect = [(10,), (5,), (100,), (20,), (3,)]
        result = repo.get_comprehensive_stats(year_id=1)
        assert result["active_students"] == 10
        assert result["total_classes"] == 5
        assert result["presents"] == 100
        assert result["absents"] == 20
        assert result["lates"] == 3

    def test_without_year_id(self):
        repo, cursor = _make_repo()
        # 4 fetchone calls (no active_students query when year_id=0)
        cursor.fetchone.side_effect = [(5,), (80,), (15,), (2,)]
        result = repo.get_comprehensive_stats(year_id=0)
        assert result["active_students"] == 0
        assert result["total_classes"] == 5

    def test_null_values_coerce_to_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [(None,), (None,), (None,), (None,), (None,)]
        result = repo.get_comprehensive_stats(year_id=1)
        assert result["active_students"] == 0
        assert result["total_classes"] == 0


# ===========================================================================
# Dashboard filter queries
# ===========================================================================


class TestAnalyticsGetClassesForYear:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "CE1"), (2, "CE2")]
        result = repo.get_classes_for_year(year_id=1)
        assert result == [(1, "CE1"), (2, "CE2")]


class TestAnalyticsGetGradesBySubject:
    def test_without_class_filter(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("Math", 14.5, 4, 20.0)]
        result = repo.get_grades_by_subject(year_id=1)
        assert result == [("Math", 14.5, 4, 20.0)]
        # Verify class_id param was NOT appended (only year_id in params)
        call_args = cursor.execute.call_args
        assert call_args[0][1] == [1]  # only year_id

    def test_with_class_filter(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("Français", 12.0, 3, 20.0)]
        result = repo.get_grades_by_subject(year_id=1, class_id=2)
        assert len(result) == 1
        # Verify class_id was added to SQL
        call_args = cursor.execute.call_args
        assert "SCN.class_id" in call_args[0][0]

    def test_empty(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        assert repo.get_grades_by_subject(year_id=1) == []


class TestAnalyticsGetMonthlyAttendanceRate:
    def test_without_class_filter(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-01", 500, 480)]
        result = repo.get_monthly_attendance_rate(year_id=1)
        assert result == [("2026-01", 500, 480)]

    def test_with_class_filter(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-02", 100, 95)]
        result = repo.get_monthly_attendance_rate(year_id=1, class_id=3)
        assert len(result) == 1
        call_args = cursor.execute.call_args
        assert "SCN.class_id" in call_args[0][0]


class TestAnalyticsGetFinanceSummary:
    def test_without_class_filter(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [(50000.0,), (45000.0,)]
        total_paid, total_due = repo.get_finance_summary(year_id=1)
        assert total_due == 50000.0
        assert total_paid == 45000.0

    def test_with_class_filter(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [(20000.0,), (18000.0,)]
        total_paid, total_due = repo.get_finance_summary(year_id=1, class_id=2)
        assert total_due == 20000.0
        assert total_paid == 18000.0

    def test_null_values_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [(None,), (None,)]
        total_paid, total_due = repo.get_finance_summary(year_id=1)
        assert total_due == 0.0
        assert total_paid == 0.0
