"""Tests for services/grade_service.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from services.grade_service import GradeService


@pytest.fixture
def svc():
    return GradeService()


# ──────────────────────────────────────────────
# calculate_period_average
# ──────────────────────────────────────────────


class TestCalculatePeriodAverage:
    def test_basic(self, svc):
        # (score, coefficient)
        result = svc.calculate_period_average([(10.0, 2.0), (15.0, 1.0)])
        assert abs(result - (10 * 2 + 15 * 1) / 3) < 1e-6

    def test_all_same_coeff(self, svc):
        result = svc.calculate_period_average([(12.0, 1.0), (14.0, 1.0)])
        assert abs(result - 13.0) < 1e-6

    def test_none_score_skipped(self, svc):
        result = svc.calculate_period_average([(None, 2.0), (10.0, 1.0)])
        assert abs(result - 10.0) < 1e-6

    def test_empty_list_returns_zero(self, svc):
        assert svc.calculate_period_average([]) == 0.0

    def test_all_none_returns_zero(self, svc):
        assert svc.calculate_period_average([(None, 1.0), (None, 2.0)]) == 0.0

    def test_zero_coefficient_returns_zero(self, svc):
        assert svc.calculate_period_average([(10.0, 0.0)]) == 0.0


# ──────────────────────────────────────────────
# calculate_annual_average
# ──────────────────────────────────────────────


class TestCalculateAnnualAverage:
    def test_basic(self, svc):
        result = svc.calculate_annual_average([10.0, 14.0, 12.0])
        assert abs(result - 12.0) < 1e-6

    def test_single_value(self, svc):
        assert abs(svc.calculate_annual_average([15.0]) - 15.0) < 1e-6

    def test_empty_uses_fallback(self, svc):
        assert svc.calculate_annual_average([], fallback_average=8.0) == 8.0

    def test_none_in_list_skipped(self, svc):
        result = svc.calculate_annual_average([None, 10.0, 14.0])
        assert abs(result - 12.0) < 1e-6


# ──────────────────────────────────────────────
# get_promotion_threshold
# ──────────────────────────────────────────────


class TestGetPromotionThreshold:
    def test_elementary_cycle(self, svc):
        # "elem" must appear in the lowercased cycle name (ASCII, no accent)
        assert svc.get_promotion_threshold("Elementaire") == 5.0

    def test_primary_cycle(self, svc):
        assert svc.get_promotion_threshold("Primary") == 5.0

    def test_ibtida_cycle(self, svc):
        assert svc.get_promotion_threshold("Ibtidaï") == 5.0

    def test_other_cycle(self, svc):
        assert svc.get_promotion_threshold("Moyen") == 10.0

    def test_none_cycle(self, svc):
        assert svc.get_promotion_threshold(None) == 10.0

    def test_empty_cycle(self, svc):
        assert svc.get_promotion_threshold("") == 10.0


# ──────────────────────────────────────────────
# get_promotion_decision
# ──────────────────────────────────────────────


class TestGetPromotionDecision:
    def test_pass_moyen(self, svc):
        assert svc.get_promotion_decision(10.0, "Moyen") == "Admis"

    def test_fail_moyen(self, svc):
        assert svc.get_promotion_decision(9.99, "Moyen") == "Redouble"

    def test_exact_threshold_passes(self, svc):
        assert svc.get_promotion_decision(10.0, "Moyen") == "Admis"

    def test_pass_elementary(self, svc):
        # Use ASCII cycle name so "elem" is matched
        assert svc.get_promotion_decision(5.0, "Elementaire") == "Admis"

    def test_fail_elementary(self, svc):
        assert svc.get_promotion_decision(4.99, "Élémentaire") == "Redouble"


# ──────────────────────────────────────────────
# get_next_class
# ──────────────────────────────────────────────


class TestGetNextClass:
    @pytest.fixture
    def class_map(self):
        return {
            1: {"name": "6e", "order": 1, "cycle": 10},
            2: {"name": "5e", "order": 2, "cycle": 10},
            3: {"name": "4e", "order": 3, "cycle": 10},
        }

    def test_promotion_moves_to_next_class(self, svc, class_map):
        class_id, name = svc.get_next_class(class_map, 1, 10, "Admis")
        assert class_id == 2
        assert name == "5e"

    def test_redouble_stays_in_same_class(self, svc, class_map):
        class_id, name = svc.get_next_class(class_map, 1, 10, "Redouble")
        assert class_id == 1
        assert "Redouble" in name

    def test_promotion_at_end_of_cycle_returns_none(self, svc, class_map):
        class_id, name = svc.get_next_class(class_map, 3, 10, "Admis")
        assert class_id is None
        assert "Diplômé" in name or "Cycle" in name

    def test_unknown_class_id_finds_first_class(self, svc, class_map):
        # Unknown class_id → order defaults to 0 → finds the class with order=1 in the cycle
        class_id, name = svc.get_next_class(class_map, 99, 10, "Admis")
        assert class_id == 1
        assert name == "6e"

    def test_no_class_at_exact_next_order_returns_end_of_cycle(self, svc):
        # Mutation guard: Eq→GtE would pick a class with order >= current+1 (e.g. order+2)
        # instead of requiring the EXACT next sequential class.
        class_map = {
            1: {"name": "6e", "order": 1, "cycle": 10},
            3: {"name": "4e", "order": 3, "cycle": 10},  # order 2 is missing
        }
        class_id, name = svc.get_next_class(class_map, 1, 10, "Admis")
        assert class_id is None  # no exact order=2 exists → end of cycle
