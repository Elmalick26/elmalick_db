"""Tests for services/finance_service.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date

import pytest

from services.finance_service import FinanceService


@pytest.fixture
def svc():
    return FinanceService()


# ──────────────────────────────────────────────
# calculate_debt
# ──────────────────────────────────────────────


class TestCalculateDebt:
    def test_no_payment(self, svc):
        assert svc.calculate_debt(10_000, 0) == 10_000.0

    def test_partial_payment(self, svc):
        assert svc.calculate_debt(10_000, 3_000) == 7_000.0

    def test_fully_paid(self, svc):
        assert svc.calculate_debt(10_000, 10_000) == 0.0

    def test_overpaid_never_negative(self, svc):
        assert svc.calculate_debt(10_000, 12_000) == 0.0

    def test_zero_due(self, svc):
        assert svc.calculate_debt(0, 0) == 0.0


# ──────────────────────────────────────────────
# calculate_total_debt
# ──────────────────────────────────────────────


class TestCalculateTotalDebt:
    def test_multiple_dues(self, svc):
        dues = [
            {"net_amount": 10_000, "total_paid": 5_000},
            {"net_amount": 8_000, "total_paid": 8_000},
            {"net_amount": 6_000, "total_paid": 0},
        ]
        assert svc.calculate_total_debt(dues) == 11_000.0

    def test_all_paid(self, svc):
        dues = [{"net_amount": 5_000, "total_paid": 5_000}]
        assert svc.calculate_total_debt(dues) == 0.0

    def test_empty_list(self, svc):
        assert svc.calculate_total_debt([]) == 0.0


# ──────────────────────────────────────────────
# get_payment_status
# ──────────────────────────────────────────────


class TestGetPaymentStatus:
    def test_fully_paid(self, svc):
        assert svc.get_payment_status(10_000, 10_000) == "Payé"

    def test_partial(self, svc):
        assert svc.get_payment_status(10_000, 3_000) == "Partiel"

    def test_overdue(self, svc):
        past = date(2024, 1, 1)
        today = date(2026, 5, 15)
        assert svc.get_payment_status(10_000, 0, past, today) == "En Retard"

    def test_upcoming(self, svc):
        future = date(2030, 1, 1)
        today = date(2026, 5, 15)
        assert svc.get_payment_status(10_000, 0, future, today) == "À Venir"

    def test_no_due_date_returns_upcoming(self, svc):
        assert svc.get_payment_status(10_000, 0, None) == "À Venir"

    def test_exact_due_date_today_is_upcoming(self, svc):
        # due_date == today → not strictly less than today → "À Venir"
        today = date(2026, 5, 15)
        assert svc.get_payment_status(10_000, 0, today, today) == "À Venir"


# ──────────────────────────────────────────────
# is_overdue
# ──────────────────────────────────────────────


class TestIsOverdue:
    def test_overdue_unpaid(self, svc):
        assert svc.is_overdue(10_000, 0, date(2024, 1, 1), date(2026, 5, 15)) is True

    def test_overdue_but_paid(self, svc):
        assert svc.is_overdue(10_000, 10_000, date(2024, 1, 1), date(2026, 5, 15)) is False

    def test_future_due_not_overdue(self, svc):
        assert svc.is_overdue(10_000, 0, date(2030, 1, 1), date(2026, 5, 15)) is False


# ──────────────────────────────────────────────
# calculate_collection_rate
# ──────────────────────────────────────────────


class TestCalculateCollectionRate:
    def test_full_collection(self, svc):
        assert svc.calculate_collection_rate(10_000, 10_000) == 100.0

    def test_half_collection(self, svc):
        assert svc.calculate_collection_rate(10_000, 5_000) == 50.0

    def test_no_collection(self, svc):
        assert svc.calculate_collection_rate(10_000, 0) == 0.0

    def test_zero_due_returns_100(self, svc):
        assert svc.calculate_collection_rate(0, 0) == 100.0

    def test_capped_at_100(self, svc):
        assert svc.calculate_collection_rate(10_000, 15_000) == 100.0


# ──────────────────────────────────────────────
# get_collection_status
# ──────────────────────────────────────────────


class TestGetCollectionStatus:
    def test_excellent(self, svc):
        assert svc.get_collection_status(95) == "Excellent"

    def test_bon(self, svc):
        assert svc.get_collection_status(75) == "Bon"

    def test_moyen(self, svc):
        assert svc.get_collection_status(55) == "Moyen"

    def test_insuffisant(self, svc):
        assert svc.get_collection_status(30) == "Insuffisant"

    def test_exact_90_is_excellent(self, svc):
        assert svc.get_collection_status(90) == "Excellent"


# ──────────────────────────────────────────────
# summarize_dues
# ──────────────────────────────────────────────


class TestSummarizeDues:
    def test_mixed_dues(self, svc):
        today = date(2026, 5, 15)
        dues = [
            {"net_amount": 10_000, "total_paid": 10_000, "due_date": date(2026, 1, 1)},  # Payé
            {"net_amount": 8_000, "total_paid": 3_000, "due_date": date(2026, 1, 1)},  # Partiel
            {"net_amount": 6_000, "total_paid": 0, "due_date": date(2024, 1, 1)},  # En Retard
            {"net_amount": 4_000, "total_paid": 0, "due_date": date(2030, 1, 1)},  # À Venir
        ]
        summary = svc.summarize_dues(dues)
        assert summary["total_due"] == 28_000.0
        assert summary["total_paid"] == 13_000.0
        assert summary["total_debt"] == 15_000.0
        assert summary["paid_count"] == 1
        assert summary["partial_count"] == 1
        assert summary["overdue_count"] == 1

    def test_empty_dues(self, svc):
        summary = svc.summarize_dues([])
        assert summary["total_due"] == 0.0
        assert summary["collection_rate"] == 100.0

    def test_all_paid(self, svc):
        dues = [{"net_amount": 5_000, "total_paid": 5_000, "due_date": None}] * 3
        summary = svc.summarize_dues(dues)
        assert summary["total_debt"] == 0.0
        assert summary["collection_rate"] == 100.0
        assert summary["paid_count"] == 3


# ──────────────────────────────────────────────
# format_amount
# ──────────────────────────────────────────────


class TestFormatAmount:
    def test_basic(self, svc):
        assert svc.format_amount(10_000) == "10,000 FCFA"

    def test_custom_currency(self, svc):
        assert "EUR" in svc.format_amount(1_500, "EUR")

    def test_zero(self, svc):
        assert svc.format_amount(0) == "0 FCFA"

    def test_invalid_input(self, svc):
        assert svc.format_amount("bad") == "0 FCFA"


# ──────────────────────────────────────────────
# validate_payment_amount
# ──────────────────────────────────────────────


class TestValidatePaymentAmount:
    def test_valid_amount(self, svc):
        assert svc.validate_payment_amount(5_000, 10_000) == []

    def test_zero_amount(self, svc):
        errors = svc.validate_payment_amount(0, 10_000)
        assert len(errors) > 0

    def test_negative_amount(self, svc):
        errors = svc.validate_payment_amount(-100, 10_000)
        assert len(errors) > 0

    def test_exceeds_debt(self, svc):
        errors = svc.validate_payment_amount(15_000, 10_000)
        assert len(errors) > 0

    def test_exceeds_debt_allowed(self, svc):
        # allow_overpay=True should not raise
        errors = svc.validate_payment_amount(15_000, 10_000, allow_overpay=True)
        assert errors == []

    def test_non_numeric_input(self, svc):
        errors = svc.validate_payment_amount("abc", 10_000)
        assert len(errors) > 0

    def test_exact_debt_is_valid(self, svc):
        assert svc.validate_payment_amount(10_000, 10_000) == []

    def test_amount_at_rounding_tolerance_boundary_is_valid(self, svc):
        # Mutation guard: Gt→GtE would reject amount == remaining_debt * 1.005.
        # The original `>` means equality is within tolerance and must NOT produce an error.
        remaining_debt = 10_000
        amount_at_boundary = remaining_debt * 1.005  # exactly 10 050.0
        errors = svc.validate_payment_amount(amount_at_boundary, remaining_debt)
        assert errors == []
