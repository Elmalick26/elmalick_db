"""Phase 4 — BulletinRepository tests.

Covers bulletin_repo.py (0% → ~100%) to push global coverage past 80 %.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.data.bulletin_repo import BulletinRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    repo = BulletinRepository(conn)
    return repo, cursor


# ===========================================================================
# AcademicYears
# ===========================================================================


class TestBulletinGetActiveYearId:
    def test_active_year_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (7,)
        assert repo.get_active_year_id() == 7

    def test_no_active_year_fallback_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, (3,)]
        assert repo.get_active_year_id() == 3

    def test_no_years_at_all(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, None]
        assert repo.get_active_year_id() == -1


class TestBulletinGetYearLabel:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("2024-2025",)
        assert repo.get_year_label(1) == "2024-2025"

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_year_label(99) is None


class TestBulletinGetLastYearLabel:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("2024-2025",)
        assert repo.get_last_year_label() == "2024-2025"

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_last_year_label() is None


# ===========================================================================
# Classes
# ===========================================================================


class TestBulletinListClasses:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "CE1", "الاول")]
        result = repo.list_classes()
        assert result == [(1, "CE1", "الاول")]


class TestBulletinGetClassNames:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("CE1", "الاول")
        assert repo.get_class_names(1) == ("CE1", "الاول")

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_class_names(99) is None


class TestBulletinGetCycleIdForClass:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (2,)
        assert repo.get_cycle_id_for_class(5) == 2

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_cycle_id_for_class(99) is None


# ===========================================================================
# AcademicPeriods
# ===========================================================================


class TestBulletinListPeriodsForYear:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Trimestre 1", "الثلاثي الأول")]
        assert repo.list_periods_for_year(1) == [(1, "Trimestre 1", "الثلاثي الأول")]


class TestBulletinListAllPeriods:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "T1", "ث1"), (2, "T2", "ث2")]
        assert len(repo.list_all_periods()) == 2


class TestBulletinGetPeriodIdByName:
    def test_with_year_id_found_first_query(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (10,)
        result = repo.get_period_id_by_name("Trimestre 1", cycle_id=1, year_id=5)
        assert result == 10

    def test_with_year_id_fallback_to_second_query(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, (7,)]
        result = repo.get_period_id_by_name("Trimestre 1", cycle_id=1, year_id=5)
        assert result == 7

    def test_year_id_minus_one_skips_first_query(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (4,)
        result = repo.get_period_id_by_name("Trimestre 2", cycle_id=1, year_id=-1)
        assert result == 4

    def test_no_year_id_direct_query(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (3,)
        result = repo.get_period_id_by_name("Trimestre 3", cycle_id=1)
        assert result == 3

    def test_not_found_anywhere(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, None]
        result = repo.get_period_id_by_name("Missing", cycle_id=1, year_id=5)
        assert result is None


# ===========================================================================
# Students
# ===========================================================================


class TestBulletinListActiveStudentsInClass:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Ali", "Ben", "علي", "بن")]
        result = repo.list_active_students_in_class(class_id=1, year_id=1)
        assert result == [(1, "Ali", "Ben", "علي", "بن")]


# ===========================================================================
# SchoolInfo
# ===========================================================================


class TestBulletinGetSchoolInfo:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (1, "École El Malick", "مدرسة")
        assert repo.get_school_info() == (1, "École El Malick", "مدرسة")

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_school_info() is None


# ===========================================================================
# GradeCalculator helpers
# ===========================================================================


class TestBulletinGetCycleNameForClass:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("Primaire",)
        assert repo.get_cycle_name_for_class(3) == "Primaire"

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_cycle_name_for_class(99) is None


class TestBulletinGetSubjectsForClass:
    def test_timetable_subjects_found(self):
        repo, cursor = _make_repo()
        subjects = [(1, "Math", "رياضيات", 4)]
        cursor.fetchall.return_value = subjects
        result = repo.get_subjects_for_class(1)
        assert result == subjects

    def test_fallback_to_cycle_subjects(self):
        repo, cursor = _make_repo()
        # First fetchall returns empty (no timetable subjects)
        cursor.fetchall.side_effect = [[], [(1, "Math", "رياضيات", 4)]]
        cursor.fetchone.return_value = (2,)  # cycle_id
        result = repo.get_subjects_for_class(1)
        assert result == [(1, "Math", "رياضيات", 4)]

    def test_fallback_class_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None  # class not found
        result = repo.get_subjects_for_class(99)
        assert result == []


class TestBulletinGetPeriodYearId:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (5,)
        assert repo.get_period_year_id(1) == 5

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_period_year_id(99) is None


class TestBulletinGetGradeScore:
    def test_with_year_id_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (18.5,)
        result = repo.get_grade_score(student_id=1, subject_id=2, assessment_id=3, year_id=4)
        assert result == 18.5

    def test_without_year_id_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (15.0,)
        result = repo.get_grade_score(student_id=1, subject_id=2, assessment_id=3, year_id=0)
        assert result == 15.0

    def test_not_found_returns_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        result = repo.get_grade_score(student_id=1, subject_id=2, assessment_id=3, year_id=4)
        assert result == 0


class TestBulletinGetTableColumns:
    def test_returns_column_names(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("id",), ("period_id",), ("year_id",)]
        result = repo.get_table_columns("StudentAttendance")
        assert result == {"id", "period_id", "year_id"}

    def test_exception_returns_empty_set(self):
        repo, cursor = _make_repo()
        cursor.execute.side_effect = Exception("DB error")
        result = repo.get_table_columns("NoTable")
        assert result == set()


class TestBulletinGetAttendanceCount:
    def test_with_period_id_and_period_col(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value={"period_id", "year_id"})
        cursor.fetchone.return_value = (5,)
        result = repo.get_attendance_count(student_id=1, status="Absent", year_id=2, period_id=3)
        assert result == 5

    def test_with_year_id_no_period_col(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value={"year_id"})
        cursor.fetchone.return_value = (3,)
        result = repo.get_attendance_count(student_id=1, status="Late", year_id=2)
        assert result == 3

    def test_fallback_no_year_no_period(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value={"year_id"})
        cursor.fetchone.return_value = (7,)
        result = repo.get_attendance_count(student_id=1, status="Absent", year_id=0)
        assert result == 7

    def test_returns_zero_when_none(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value={"year_id"})
        cursor.fetchone.return_value = (None,)
        result = repo.get_attendance_count(student_id=1, status="Absent", year_id=0)
        assert result == 0


class TestBulletinGetDisciplineDataRaw:
    def _make_cols(self, with_period=False, with_points=True, with_sanction=True, with_obs=True):
        cols = set()
        if with_period:
            cols.add("period_id")
        if with_points:
            cols.add("points_deducted")
        if with_sanction:
            cols.add("sanction")
        if with_obs:
            cols.add("observation")
        cols.add("year_id")
        return cols

    def test_with_period_id_and_period_col(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value=self._make_cols(with_period=True))
        cursor.fetchone.return_value = (2.0,)
        cursor.fetchall.return_value = [("retard", "avertissement", 1.0, "obs")]
        total, records = repo.get_discipline_data_raw(student_id=1, year_id=2, period_id=3)
        assert total == 2.0
        assert len(records) == 1

    def test_with_year_id_has_data(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value=self._make_cols(with_period=False))
        # fetchone calls: COUNT(*) > 0, SUM → total
        cursor.fetchone.side_effect = [(1,), (3.5,)]
        cursor.fetchall.return_value = [("violence", "exclusion", 2.0, "note")]
        total, records = repo.get_discipline_data_raw(student_id=1, year_id=2)
        assert total == 3.5
        assert len(records) == 1

    def test_with_year_id_no_data_fallback(self):
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value=self._make_cols(with_period=False))
        # COUNT(*) = 0 → fall back to all-student query
        cursor.fetchone.side_effect = [(0,), (1.0,)]
        cursor.fetchall.return_value = [("retard", "obs", 0.5, "")]
        total, records = repo.get_discipline_data_raw(student_id=1, year_id=2)
        assert total == 1.0

    def test_fallback_col_names(self):
        """Test with non-standard column names (action_taken, description)."""
        repo, cursor = _make_repo()
        cols = {"year_id", "action_taken", "description"}
        repo.get_table_columns = MagicMock(return_value=cols)
        cursor.fetchone.side_effect = [(0,), (0.0,)]
        cursor.fetchall.return_value = []
        total, records = repo.get_discipline_data_raw(student_id=1, year_id=0)
        assert total == 0.0

    def test_minimal_cols(self):
        """Test with no known optional columns."""
        repo, cursor = _make_repo()
        repo.get_table_columns = MagicMock(return_value={"year_id"})
        cursor.fetchone.side_effect = [(0,), (0.0,)]
        cursor.fetchall.return_value = []
        total, records = repo.get_discipline_data_raw(student_id=1, year_id=5)
        assert total == 0.0


# ===========================================================================
# Additional helpers
# ===========================================================================


class TestBulletinListStudentsInClassOrdered:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Ali", "Ben", "علي", "بن", 1)]
        result = repo.list_students_in_class_ordered(class_id=2, year_id=1)
        assert result == [(1, "Ali", "Ben", "علي", "بن", 1)]


class TestBulletinGetAssessmentsForPeriod:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Devoir 1", "DS", 30.0)]
        result = repo.get_assessments_for_period(period_id=1)
        assert result == [(1, "Devoir 1", "DS", 30.0)]


class TestBulletinGetStudentDetails:
    def test_found(self):
        repo, cursor = _make_repo()
        row = ("Ali", "Ben", "علي", "بن", "2010-01-01", "Dakar", "Parent")
        cursor.fetchone.return_value = row
        assert repo.get_student_details(1) == row

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_student_details(99) is None


class TestBulletinGetClassSize:
    def test_returns_int(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (25,)
        assert repo.get_class_size(class_id=1, year_id=1) == 25

    def test_returns_zero_when_none(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None,)
        assert repo.get_class_size(class_id=1, year_id=1) == 0


class TestBulletinGetPeriodMeta:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (2, 1)
        assert repo.get_period_meta(5) == (2, 1)

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_period_meta(99) is None


class TestBulletinListPeriodsForYearAndCycle:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "T1", "ث1"), (2, "T2", "ث2")]
        result = repo.list_periods_for_year_and_cycle(year_id=1, cycle_id=2)
        assert len(result) == 2


class TestBulletinListStudentIdsInClass:
    def test_returns_ids(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1,), (2,), (3,)]
        result = repo.list_student_ids_in_class(class_id=1, year_id=1)
        assert result == [1, 2, 3]

    def test_empty(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        result = repo.list_student_ids_in_class(class_id=1, year_id=1)
        assert result == []
