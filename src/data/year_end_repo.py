"""Repository for YearEndMigration — promotion calculation and year transition."""

from __future__ import annotations

from typing import Any


class YearEndRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # --- Academic years ---

    def list_academic_years(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, year_label, is_active FROM AcademicYears ORDER BY id ASC")
        return cursor.fetchall()

    # --- Classes ---

    def list_classes_with_order(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr, cycle_id, sort_order FROM Classes ORDER BY sort_order")
        return cursor.fetchall()

    def list_classes_basic(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr, cycle_id FROM Classes")
        return cursor.fetchall()

    def list_classes_for_combo(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY sort_order")
        return cursor.fetchall()

    # --- Periods ---

    def list_period_ids(self, year_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicPeriods WHERE year_id=%s", (year_id,))
        return [row[0] for row in cursor.fetchall()]

    # --- Students ---

    def list_active_students_in_class(self, year_id: int, class_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr, S.last_name_fr, SCN.class_id
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE S.status='Active' AND SCN.class_id=%s AND SCN.year_id=%s
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    def list_all_active_students(self, year_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr, S.last_name_fr, SCN.class_id
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE S.status='Active' AND SCN.year_id=%s
            """,
            (year_id,),
        )
        return cursor.fetchall()

    # --- Subjects & grades ---

    def list_subjects_with_coefficient(self, cycle_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, coefficient FROM Subjects WHERE cycle_id=%s", (cycle_id,))
        return cursor.fetchall()

    def get_period_assessment_types(self, period_id: int) -> list:
        """Return [(id, type_code, name_fr)] for all assessments defined in a period."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, type_code, name_fr FROM AssessmentTypes WHERE period_id=%s",
            (period_id,),
        )
        return cursor.fetchall()

    def get_grades_for_students_year(self, student_ids: list, year_id: int) -> dict:
        """Bulk-fetch a year's grades for many students in one query.

        Returns {(student_id, subject_id, period_id): {assessment_id: score}}.
        Combined with get_period_assessment_types, the promotion path computes the
        canonical subject average with missing assessments counted as 0 — exactly
        as the bulletin does (so the decision matches the report card). This single
        query replaces the per-(student, subject, period) fetch that turned the
        whole-class migration into an N×P×S query storm.
        """
        index: dict = {}
        if not student_ids:
            return index
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT G.student_id, G.subject_id, A.period_id, G.assessment_id, G.score
            FROM Grades G JOIN AssessmentTypes A ON G.assessment_id = A.id
            WHERE G.year_id=%s AND G.student_id = ANY(%s)
            """,
            (year_id, list(student_ids)),
        )
        for sid, subject_id, period_id, assessment_id, score in cursor.fetchall():
            index.setdefault((sid, subject_id, period_id), {})[assessment_id] = score
        return index

    def get_fallback_average(self, student_id: int, year_id: int) -> float:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT AVG(score) FROM Grades WHERE student_id=%s AND year_id=%s",
            (student_id, year_id),
        )
        res = cursor.fetchone()
        return float(res[0]) if res and res[0] is not None else 0.0

    # --- Cycles ---

    def get_cycle_name(self, cycle_id: int) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name_fr FROM Cycles WHERE id=%s", (cycle_id,))
        row = cursor.fetchone()
        return row[0] if row else ""
