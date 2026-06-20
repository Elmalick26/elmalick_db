"""Phase 2 — pedagogical grade-calculation rules (authoritative spec).

These tests exercise the REAL bulletin computation
(bulletin_generation.GradeCalculator.get_student_averages) with a fully mocked
repository — no database is touched. They assert the CORRECT values per the
school's official rules:

Collège / Lycée (2 semesters, /20):
    moy_devoirs   = (Devoir1 + Devoir2) / 2
    moy_matière   = (moy_devoirs + Composition) / 2          # NOT (d + 2*c)/3
    moy_générale  = Σ(moy_matière × coef) / Σ(coef)

Primaire (3 trimesters, /10):
    moy_matière   = Composition only (NO devoirs)
    moy_générale  = Σ(composition × coef) / Σ(coef)

A failing test here is a real finding: the production formula deviates from the
spec.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

import bulletin_generation
from bulletin_generation import GradeCalculator
from services.grade_service import GradeService


# ══════════════════════════════════════════════════════════════════
# Canonical subject_average — single source of truth (bulletin + promotion)
# ══════════════════════════════════════════════════════════════════
class TestCanonicalSubjectAverage:
    svc = GradeService()

    def test_college_devoirs_and_compo(self):
        assert self.svc.subject_average([12, 14], 10, is_primary=False) == pytest.approx(11.5)

    def test_college_compo_not_doubled(self):
        assert self.svc.subject_average([10, 10], 16, is_primary=False) == pytest.approx(13.0)

    def test_college_only_composition(self):
        assert self.svc.subject_average([], 10, is_primary=False) == pytest.approx(10.0)

    def test_college_only_devoirs(self):
        assert self.svc.subject_average([12, 14], None, is_primary=False) == pytest.approx(13.0)

    def test_college_empty_is_zero(self):
        assert self.svc.subject_average([], None, is_primary=False) == 0.0

    def test_primary_composition_only(self):
        # devoirs ignored entirely in primary
        assert self.svc.subject_average([1, 2], 7, is_primary=True) == pytest.approx(7.0)

    def test_is_devoir_classification(self):
        assert GradeService.is_devoir_assessment("DEV1", "Devoir 1") is True
        assert GradeService.is_devoir_assessment("X", "Devoir 2") is True
        assert GradeService.is_devoir_assessment("COMPO", "Composition") is False
        assert GradeService.is_devoir_assessment(None, None) is False


def _run_averages(cycle_name, subjects, assessments, grades, *, class_id=1, period_id=1):
    """Drive GradeCalculator.get_student_averages with a mocked repository.

    subjects:   list of (sub_id, name_fr, name_ar, coef)
    assessments:list of (assess_id, name, code, weight)
    grades:     dict {(student_id, sub_id, assess_id): score}  (one student, id=1)
    Returns the single student's result dict.
    """
    repo = MagicMock()
    repo.get_cycle_name_for_class.return_value = cycle_name
    repo.get_period_year_id.return_value = 1
    repo.list_students_in_class_ordered.return_value = [(1, "Awa", "Diop", "عوا", "جوب", 1)]
    repo.get_subjects_for_class.return_value = subjects
    repo.get_assessments_for_period.return_value = assessments
    repo.get_grades_map_for_students.return_value = grades

    with (
        patch.object(bulletin_generation, "DatabaseManager", MagicMock()),
        patch.object(bulletin_generation, "BulletinRepository", return_value=repo),
    ):
        results = GradeCalculator().get_student_averages(class_id, period_id, include_conduct=False)
    assert len(results) == 1
    return results[0]


# Standard assessment sets
_COLLEGE_ASSESS = [
    (10, "Devoir 1", "DEV1", 1.0),
    (11, "Devoir 2", "DEV2", 1.0),
    (12, "Composition", "COMPO", 1.0),
]
_PRIMARY_ASSESS = [(20, "Composition", "COMPO", 1.0)]


# ══════════════════════════════════════════════════════════════════
# Collège / Lycée — subject average = (moy_devoirs + composition) / 2
# ══════════════════════════════════════════════════════════════════
class TestCollegeSubjectAverage:
    def test_canonical_example_11_5(self):
        """D1=12, D2=14, Compo=10 → moy_devoirs=13 → moy_matière=(13+10)/2 = 11.5."""
        res = _run_averages(
            "Collège",
            subjects=[(1, "Maths", "", 1.0)],
            assessments=_COLLEGE_ASSESS,
            grades={(1, 1, 10): 12.0, (1, 1, 11): 14.0, (1, 1, 12): 10.0},
        )
        assert res["subjects"][0]["avg"] == pytest.approx(11.5)
        assert res["general_average"] == pytest.approx(11.5)

    def test_missing_devoir_counts_as_zero(self):
        """D1=12, D2 missing, Compo=10 → devoirs=[12,0]→6 → (6+10)/2 = 8.0.

        School policy: an un-entered grade counts as 0 (same in bulletin & promotion).
        """
        res = _run_averages(
            "Collège",
            subjects=[(1, "Maths", "", 1.0)],
            assessments=_COLLEGE_ASSESS,
            grades={(1, 1, 10): 12.0, (1, 1, 12): 10.0},  # assessment 11 (Devoir 2) absent
        )
        assert res["subjects"][0]["avg"] == pytest.approx(8.0)

    def test_compo_not_double_weighted(self):
        """D1=D2=10, Compo=16 → (10+16)/2 = 13.0  (the (d+2c)/3 bug gives 14.0)."""
        res = _run_averages(
            "Collège",
            subjects=[(1, "Maths", "", 1.0)],
            assessments=_COLLEGE_ASSESS,
            grades={(1, 1, 10): 10.0, (1, 1, 11): 10.0, (1, 1, 12): 16.0},
        )
        assert res["subjects"][0]["avg"] == pytest.approx(13.0)

    def test_general_average_with_coefficients(self):
        """Two subjects, different coefs.

        Maths : D1=12,D2=14,C=10 → 11.5, coef 4
        Fr    : D1=8, D2=10,C=12 → moy_dev=9 → (9+12)/2 = 10.5, coef 2
        général = (11.5*4 + 10.5*2) / 6 = (46 + 21)/6 = 11.1667
        """
        res = _run_averages(
            "Collège",
            subjects=[(1, "Maths", "", 4.0), (2, "Français", "", 2.0)],
            assessments=_COLLEGE_ASSESS,
            grades={
                (1, 1, 10): 12.0,
                (1, 1, 11): 14.0,
                (1, 1, 12): 10.0,
                (1, 2, 10): 8.0,
                (1, 2, 11): 10.0,
                (1, 2, 12): 12.0,
            },
        )
        assert res["subjects"][0]["avg"] == pytest.approx(11.5)
        assert res["subjects"][1]["avg"] == pytest.approx(10.5)
        assert res["general_average"] == pytest.approx((11.5 * 4 + 10.5 * 2) / 6)


# ══════════════════════════════════════════════════════════════════
# Primaire — composition only, no devoirs, /10
# ══════════════════════════════════════════════════════════════════
class TestPrimaryAverage:
    def test_general_average_7_4(self):
        """Maths C=7 coef6, Français C=8 coef4 → (7*6 + 8*4)/10 = 7.4."""
        res = _run_averages(
            "Élémentaire",
            subjects=[(1, "Maths", "", 6.0), (2, "Français", "", 4.0)],
            assessments=_PRIMARY_ASSESS,
            grades={(1, 1, 20): 7.0, (1, 2, 20): 8.0},
        )
        assert res["subjects"][0]["avg"] == pytest.approx(7.0)
        assert res["subjects"][1]["avg"] == pytest.approx(8.0)
        assert res["general_average"] == pytest.approx(7.4)

    def test_primary_ignores_devoirs(self):
        """If a primary period also carries devoir rows, they must NOT affect the
        subject average — primary counts the composition only."""
        res = _run_averages(
            "Élémentaire",
            subjects=[(1, "Maths", "", 6.0)],
            assessments=[
                (20, "Composition", "COMPO", 1.0),
                (21, "Devoir 1", "DEV1", 1.0),  # should be ignored in primary
            ],
            grades={(1, 1, 20): 7.0, (1, 1, 21): 1.0},  # devoir=1 must not drag it down
        )
        assert res["subjects"][0]["avg"] == pytest.approx(7.0)


# ══════════════════════════════════════════════════════════════════
# Cycle separation — primary vs collège must not be mixed
# ══════════════════════════════════════════════════════════════════
class TestCycleSeparation:
    def test_collège_uses_20_scale_context(self):
        res = _run_averages(
            "Collège",
            subjects=[(1, "Maths", "", 1.0)],
            assessments=_COLLEGE_ASSESS,
            grades={(1, 1, 10): 20.0, (1, 1, 11): 20.0, (1, 1, 12): 20.0},
        )
        assert res["is_primary"] is False
        assert res["max_score"] == 20.0

    def test_primary_uses_10_scale_context(self):
        res = _run_averages(
            "Élémentaire",
            subjects=[(1, "Maths", "", 6.0)],
            assessments=_PRIMARY_ASSESS,
            grades={(1, 1, 20): 9.0},
        )
        assert res["is_primary"] is True
        assert res["max_score"] == 10.0
