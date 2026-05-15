"""
tests/test_attendance_service.py
تغطية كاملة لـ AttendanceService (خدمة الحضور).
"""

import pytest
from datetime import date
from services.attendance_service import AttendanceService


@pytest.fixture
def svc():
    return AttendanceService()


# ─────────────────────────────────────────────────────────────
# calculate_stats
# ─────────────────────────────────────────────────────────────
class TestCalculateStats:

    def test_empty_records(self, svc):
        stats = svc.calculate_stats([])
        assert stats["total"] == 0
        assert stats["absence_rate_pct"] == 0.0

    def test_all_present(self, svc):
        records = [{"status": "Present"}] * 5
        stats = svc.calculate_stats(records)
        assert stats["total"] == 5
        assert stats["present"] == 5
        assert stats["absent"] == 0
        assert stats["absence_rate_pct"] == 0.0

    def test_mixed_statuses(self, svc):
        records = [
            {"status": "Present"},
            {"status": "Absent"},
            {"status": "Late"},
            {"status": "Justifié"},
            {"status": "Absent"},
        ]
        stats = svc.calculate_stats(records)
        assert stats["total"] == 5
        assert stats["present"] == 1
        assert stats["absent"] == 2
        assert stats["late"] == 1
        assert stats["justified"] == 1
        assert stats["absence_rate_pct"] == 40.0

    def test_absence_rate_rounding(self, svc):
        records = [{"status": "Absent"}] + [{"status": "Present"}] * 2
        stats = svc.calculate_stats(records)
        assert stats["absence_rate_pct"] == round(100 / 3, 2)


# ─────────────────────────────────────────────────────────────
# get_attendance_status
# ─────────────────────────────────────────────────────────────
class TestGetAttendanceStatus:

    def test_normal(self, svc):
        assert svc.get_attendance_status(5.0) == "Normal"

    def test_attention_lower_bound(self, svc):
        assert svc.get_attendance_status(10.0) == "Attention"

    def test_attention_upper(self, svc):
        assert svc.get_attendance_status(19.9) == "Attention"

    def test_avertissement(self, svc):
        assert svc.get_attendance_status(20.0) == "Avertissement"

    def test_avertissement_mid(self, svc):
        assert svc.get_attendance_status(25.0) == "Avertissement"

    def test_critique(self, svc):
        assert svc.get_attendance_status(30.0) == "Critique"

    def test_critique_high(self, svc):
        assert svc.get_attendance_status(100.0) == "Critique"


# ─────────────────────────────────────────────────────────────
# is_at_risk
# ─────────────────────────────────────────────────────────────
class TestIsAtRisk:

    def test_not_at_risk_below_threshold(self, svc):
        assert svc.is_at_risk(19.9) is False

    def test_at_risk_at_threshold(self, svc):
        assert svc.is_at_risk(20.0) is True

    def test_at_risk_above_threshold(self, svc):
        assert svc.is_at_risk(35.0) is True


# ─────────────────────────────────────────────────────────────
# count_consecutive_absences
# ─────────────────────────────────────────────────────────────
class TestCountConsecutiveAbsences:

    def test_no_absences(self, svc):
        records = [{"status": "Present"}, {"status": "Present"}]
        assert svc.count_consecutive_absences(records) == 0

    def test_trailing_absences(self, svc):
        records = [
            {"status": "Present"},
            {"status": "Absent"},
            {"status": "Absent"},
            {"status": "Absent"},
        ]
        assert svc.count_consecutive_absences(records) == 3

    def test_streak_broken_by_present(self, svc):
        records = [
            {"status": "Absent"},
            {"status": "Present"},
            {"status": "Absent"},
        ]
        assert svc.count_consecutive_absences(records) == 1

    def test_empty_records(self, svc):
        assert svc.count_consecutive_absences([]) == 0


# ─────────────────────────────────────────────────────────────
# get_absence_periods
# ─────────────────────────────────────────────────────────────
class TestGetAbsencePeriods:

    def test_no_absences_returns_empty(self, svc):
        records = [{"date": date(2026, 1, i), "status": "Present"} for i in range(1, 6)]
        assert svc.get_absence_periods(records) == []

    def test_single_period(self, svc):
        records = [
            {"date": date(2026, 1, 1), "status": "Absent"},
            {"date": date(2026, 1, 2), "status": "Absent"},
            {"date": date(2026, 1, 3), "status": "Present"},
        ]
        periods = svc.get_absence_periods(records)
        assert len(periods) == 1
        assert periods[0]["days"] == 2

    def test_period_at_end_of_list(self, svc):
        records = [
            {"date": date(2026, 1, 1), "status": "Present"},
            {"date": date(2026, 1, 2), "status": "Absent"},
            {"date": date(2026, 1, 3), "status": "Absent"},
        ]
        periods = svc.get_absence_periods(records)
        assert len(periods) == 1
        assert periods[0]["days"] == 2

    def test_string_dates(self, svc):
        records = [
            {"date": "2026-02-01", "status": "Absent"},
            {"date": "2026-02-02", "status": "Present"},
        ]
        periods = svc.get_absence_periods(records)
        assert len(periods) == 1

    def test_invalid_date_skipped(self, svc):
        records = [
            {"date": "INVALID", "status": "Absent"},
            {"date": date(2026, 1, 1), "status": "Present"},
        ]
        periods = svc.get_absence_periods(records)
        assert periods == []


# ─────────────────────────────────────────────────────────────
# calculate_class_daily_rate
# ─────────────────────────────────────────────────────────────
class TestCalculateClassDailyRate:

    def test_all_present(self, svc):
        records = [{"status": "Present"}] * 30
        assert svc.calculate_class_daily_rate(records) == 100.0

    def test_all_absent(self, svc):
        records = [{"status": "Absent"}] * 10
        assert svc.calculate_class_daily_rate(records) == 0.0

    def test_half_present(self, svc):
        records = [{"status": "Present"}] * 5 + [{"status": "Absent"}] * 5
        assert svc.calculate_class_daily_rate(records) == 50.0

    def test_empty_returns_zero(self, svc):
        assert svc.calculate_class_daily_rate([]) == 0.0


# ─────────────────────────────────────────────────────────────
# summarize_by_month
# ─────────────────────────────────────────────────────────────
class TestSummarizeByMonth:

    def test_groups_by_month(self, svc):
        records = [
            {"date": date(2026, 1, 5), "status": "Present"},
            {"date": date(2026, 1, 10), "status": "Absent"},
            {"date": date(2026, 2, 3), "status": "Present"},
        ]
        result = svc.summarize_by_month(records)
        assert "2026-01" in result
        assert "2026-02" in result
        assert result["2026-01"]["total"] == 2
        assert result["2026-02"]["total"] == 1

    def test_string_dates(self, svc):
        records = [
            {"date": "2026-03-15", "status": "Present"},
            {"date": "2026-03-20", "status": "Absent"},
        ]
        result = svc.summarize_by_month(records)
        assert "2026-03" in result

    def test_invalid_date_skipped(self, svc):
        records = [{"date": None, "status": "Present"}]
        result = svc.summarize_by_month(records)
        assert result == {}

    def test_sorted_months(self, svc):
        records = [
            {"date": date(2026, 3, 1), "status": "Present"},
            {"date": date(2026, 1, 1), "status": "Present"},
            {"date": date(2026, 2, 1), "status": "Present"},
        ]
        keys = list(svc.summarize_by_month(records).keys())
        assert keys == ["2026-01", "2026-02", "2026-03"]


# ─────────────────────────────────────────────────────────────
# get_alert_message
# ─────────────────────────────────────────────────────────────
class TestGetAlertMessage:

    def test_no_alert_for_normal(self, svc):
        stats = {"absence_rate_pct": 5.0, "absent": 1}
        assert svc.get_alert_message("Ahmed Ba", stats) is None

    def test_warning_at_20_percent(self, svc):
        stats = {"absence_rate_pct": 22.0, "absent": 5}
        msg = svc.get_alert_message("Ahmed Ba", stats)
        assert msg is not None
        assert "Ahmed Ba" in msg

    def test_critical_at_30_percent(self, svc):
        stats = {"absence_rate_pct": 35.0, "absent": 10}
        msg = svc.get_alert_message("Fatou Ndiaye", stats)
        assert msg is not None
        assert "Fatou Ndiaye" in msg
        assert "critique" in msg.lower() or "Critique" in msg
