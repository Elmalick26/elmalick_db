"""G2 — robust primary-cycle detection (services.grade_service.is_primary_cycle).

The previous substring check ("elem" in name) was accent-sensitive, so the
correctly-spelled French "Élémentaire" was NOT recognised as primary. This locks
the accent- and language-tolerant behaviour shared by the bulletin, grade
service and the data repositories.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from services.grade_service import GradeService, is_primary_cycle, resolve_is_primary


@pytest.mark.parametrize(
    "name",
    [
        "Élémentaire",  # accented French (the regression case)
        "élémentaire",
        "Elementaire",
        "elemantaire",  # the spelling currently in the DB
        "Primaire",
        "primaire",
        "ابتدائي",  # Arabic
        "إبتدائي",
        "CI - Élémentaire",
    ],
)
def test_primary_names_detected(name):
    assert is_primary_cycle(name) is True


@pytest.mark.parametrize("name", ["Collège", "collège", "Lycée", "Moyen", "Secondaire", "", None])
def test_non_primary_names(name):
    assert is_primary_cycle(name) is False


class TestThresholdUsesDetection:
    def test_primary_threshold_5_for_accented_name(self):
        # Regression: "Élémentaire" must resolve to the /10 primary threshold (5.0),
        # not the collège 10.0.
        assert GradeService().get_promotion_threshold("Élémentaire") == 5.0

    def test_college_threshold_10(self):
        assert GradeService().get_promotion_threshold("Collège") == 10.0

    def test_threshold_uses_explicit_flag(self):
        # An explicit is_primary flag overrides the name entirely.
        assert GradeService().get_promotion_threshold("Collège", is_primary=True) == 5.0
        assert GradeService().get_promotion_threshold("Primaire", is_primary=False) == 10.0


class TestResolveIsPrimary:
    """resolve_is_primary: explicit flag wins; name heuristic only as fallback."""

    def test_explicit_true_overrides_secondary_name(self):
        assert resolve_is_primary(True, "Collège") is True

    def test_explicit_false_overrides_primary_name(self):
        assert resolve_is_primary(False, "Élémentaire") is False

    def test_none_flag_falls_back_to_name(self):
        assert resolve_is_primary(None, "Élémentaire") is True
        assert resolve_is_primary(None, "Collège") is False

    def test_none_flag_and_no_name(self):
        assert resolve_is_primary(None, None) is False
