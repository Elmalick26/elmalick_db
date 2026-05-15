"""BulletinRepository — طبقة الوصول لبيانات الكشوف والنتائج.

Covers: Classes list, AcademicPeriods, active students, period lookup,
        SchoolInfo, AcademicYears labels — all used by BulletinGenerationWindow.

Note: GradeCalculator uses cursor-passing internally for performance;
      this repo covers only the standalone UI-level queries.
"""
from __future__ import annotations


class BulletinRepository:
    def __init__(self, conn):
        self.conn = conn

    # ── AcademicYears ──────────────────────────────────────

    def get_active_year_id(self) -> int:
        """Return the active year id, or the last year id, or -1."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("SELECT id FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else -1

    def get_year_label(self, year_id: int) -> str | None:
        """Return year_label for a given year_id, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_label FROM AcademicYears WHERE id=%s", (year_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_last_year_label(self) -> str | None:
        """Return year_label of the most recent year, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_label FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Classes ────────────────────────────────────────────

    def list_classes(self) -> list:
        """Return (id, class_name_fr, class_name_ar) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr, class_name_ar FROM Classes")
        return cursor.fetchall()

    def get_class_names(self, class_id: int) -> tuple | None:
        """Return (class_name_fr, class_name_ar) for a given class_id."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT class_name_fr, class_name_ar FROM Classes WHERE id=%s", (class_id,)
        )
        return cursor.fetchone()

    def get_cycle_id_for_class(self, class_id: int) -> int | None:
        """Return cycle_id for a given class_id."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT cycle_id FROM Classes WHERE id=%s", (class_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    # ── AcademicPeriods ────────────────────────────────────

    def list_periods_for_year(self, year_id: int) -> list:
        """Return (id, period_name_fr, period_name_ar) for a given year."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods "
            "WHERE year_id=%s ORDER BY sort_order",
            (year_id,),
        )
        return cursor.fetchall()

    def list_all_periods(self) -> list:
        """Return (id, period_name_fr, period_name_ar) for all periods."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods ORDER BY sort_order"
        )
        return cursor.fetchall()

    def get_period_id_by_name(
        self, period_name: str, cycle_id: int, year_id: int | None = None
    ) -> int | None:
        """Lookup period id by name + cycle; optionally filter by year first."""
        cursor = self.conn.cursor()
        if year_id is not None and year_id != -1:
            cursor.execute(
                "SELECT id FROM AcademicPeriods "
                "WHERE period_name_fr=%s AND cycle_id=%s AND year_id=%s "
                "ORDER BY sort_order LIMIT 1",
                (period_name, cycle_id, year_id),
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        cursor.execute(
            "SELECT id FROM AcademicPeriods "
            "WHERE period_name_fr=%s AND cycle_id=%s ORDER BY id DESC LIMIT 1",
            (period_name, cycle_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Students ───────────────────────────────────────────

    def list_active_students_in_class(self, class_id: int, year_id: int) -> list:
        """Return (id, first_name_fr, last_name_fr, first_name_ar, last_name_ar)
        for active students enrolled in class_id for year_id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr, S.last_name_fr,
                   S.first_name_ar, S.last_name_ar
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
            ORDER BY S.last_name_fr, S.first_name_fr
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    # ── SchoolInfo ─────────────────────────────────────────

    def get_school_info(self) -> tuple | None:
        """Return the single SchoolInfo row."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()

    # ── GradeCalculator helpers ─────────────────────────────

    def get_cycle_name_for_class(self, class_id: int):
        """Return cycle name (name_fr) for a class, or None."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT CY.name_fr FROM Classes CL
               JOIN Cycles CY ON CL.cycle_id = CY.id
               WHERE CL.id = %s""",
            (class_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_subjects_for_class(self, class_id: int) -> list:
        """Return subjects from Timetable; fall back to Subjects by cycle."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT DISTINCT S.id, S.subject_name_fr, S.subject_name_ar, S.coefficient
               FROM Timetable T JOIN Subjects S ON T.subject_id = S.id
               WHERE T.class_id = %s ORDER BY S.id""",
            (class_id,),
        )
        subjects = cursor.fetchall()
        if subjects:
            return subjects
        cursor.execute("SELECT cycle_id FROM Classes WHERE id=%s", (class_id,))
        res = cursor.fetchone()
        if not res:
            return []
        cycle_id = res[0]
        cursor.execute(
            "SELECT id, subject_name_fr, subject_name_ar, coefficient FROM Subjects WHERE cycle_id=%s ORDER BY id",
            (cycle_id,),
        )
        return cursor.fetchall()

    def get_period_year_id(self, period_id: int):
        """Return year_id for an AcademicPeriod, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_id FROM AcademicPeriods WHERE id=%s", (period_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_grade_score(self, student_id, subject_id, assessment_id, year_id) -> float:
        """Return the latest grade score for a student/subject/assessment."""
        cursor = self.conn.cursor()
        if year_id:
            cursor.execute(
                """SELECT score FROM Grades
                   WHERE student_id=%s AND subject_id=%s AND assessment_id=%s
                     AND (year_id=%s OR year_id IS NULL)
                   ORDER BY CASE WHEN year_id=%s THEN 0 ELSE 1 END, id DESC LIMIT 1""",
                (student_id, subject_id, assessment_id, year_id, year_id),
            )
        else:
            cursor.execute(
                "SELECT score FROM Grades WHERE student_id=%s AND subject_id=%s AND assessment_id=%s ORDER BY id DESC LIMIT 1",
                (student_id, subject_id, assessment_id),
            )
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_table_columns(self, table_name: str) -> set:
        """Return column names for a table via information_schema."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_schema = current_schema() AND lower(table_name) = lower(%s)""",
                (table_name,),
            )
            return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()

    def get_attendance_count(self, student_id, status: str, year_id, period_id=None) -> int:
        """Return count of attendance records matching the given filters."""
        attendance_cols = self.get_table_columns("StudentAttendance")
        has_period_col = "period_id" in attendance_cols
        cursor = self.conn.cursor()
        if period_id and has_period_col:
            cursor.execute(
                "SELECT COUNT(*) FROM StudentAttendance WHERE student_id=%s AND status=%s AND period_id=%s",
                (student_id, status, period_id),
            )
            return int(cursor.fetchone()[0] or 0)
        if year_id:
            cursor.execute(
                "SELECT COUNT(*) FROM StudentAttendance WHERE student_id=%s AND status=%s AND year_id=%s",
                (student_id, status, year_id),
            )
            return int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE student_id=%s AND status=%s",
            (student_id, status),
        )
        return int(cursor.fetchone()[0] or 0)

    def get_discipline_data_raw(self, student_id, year_id, period_id=None) -> tuple:
        """Return (total_deducted: float, records: list) for discipline data."""
        discipline_cols = self.get_table_columns("StudentDiscipline")
        points_col = "points_deducted" if "points_deducted" in discipline_cols else "0"
        sanction_col = (
            "sanction"
            if "sanction" in discipline_cols
            else ("action_taken" if "action_taken" in discipline_cols else "''")
        )
        observation_col = (
            "observation"
            if "observation" in discipline_cols
            else ("description" if "description" in discipline_cols else "''")
        )
        has_period_col = "period_id" in discipline_cols
        cursor = self.conn.cursor()

        if period_id and has_period_col:
            cursor.execute(
                f"SELECT COALESCE(SUM({points_col}), 0) FROM StudentDiscipline WHERE student_id=%s AND period_id=%s",
                (student_id, period_id),
            )
            total_deducted = float(cursor.fetchone()[0] or 0)
            cursor.execute(
                f"SELECT incident_type, {sanction_col}, {points_col}, {observation_col}"
                f" FROM StudentDiscipline WHERE student_id=%s AND period_id=%s"
                f" ORDER BY incident_date DESC LIMIT 5",
                (student_id, period_id),
            )
            return total_deducted, cursor.fetchall()

        if year_id:
            cursor.execute(
                "SELECT COUNT(*) FROM StudentDiscipline WHERE student_id=%s AND year_id=%s",
                (student_id, year_id),
            )
            has_year_data = cursor.fetchone()[0] > 0
        else:
            has_year_data = False

        if has_year_data:
            cursor.execute(
                f"SELECT COALESCE(SUM({points_col}), 0) FROM StudentDiscipline WHERE student_id=%s AND year_id=%s",
                (student_id, year_id),
            )
            total_deducted = float(cursor.fetchone()[0] or 0)
            cursor.execute(
                f"SELECT incident_type, {sanction_col}, {points_col}, {observation_col}"
                f" FROM StudentDiscipline WHERE student_id=%s AND year_id=%s"
                f" ORDER BY incident_date DESC LIMIT 5",
                (student_id, year_id),
            )
        else:
            cursor.execute(
                f"SELECT COALESCE(SUM({points_col}), 0) FROM StudentDiscipline WHERE student_id=%s",
                (student_id,),
            )
            total_deducted = float(cursor.fetchone()[0] or 0)
            cursor.execute(
                f"SELECT incident_type, {sanction_col}, {points_col}, {observation_col}"
                f" FROM StudentDiscipline WHERE student_id=%s"
                f" ORDER BY incident_date DESC LIMIT 5",
                (student_id,),
            )
        return total_deducted, cursor.fetchall()

    def list_students_in_class_ordered(self, class_id: int, year_id: int) -> list:
        """Return (id, first_name_fr, last_name_fr, first_name_ar, last_name_ar, class_number)
        ordered by class_number then name."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT S.id, S.first_name_fr, S.last_name_fr, S.first_name_ar, S.last_name_ar,
                      COALESCE(SCN.class_number, 0)
               FROM Students S
               JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
               WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
               ORDER BY COALESCE(SCN.class_number, 9999), S.last_name_fr, S.first_name_fr""",
            (class_id, year_id),
        )
        return cursor.fetchall()

    def get_assessments_for_period(self, period_id: int) -> list:
        """Return (id, name_fr, type_code, weight_percentage) for a period."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, name_fr, type_code, weight_percentage FROM AssessmentTypes WHERE period_id=%s",
            (period_id,),
        )
        return cursor.fetchall()

    def get_student_details(self, student_id: int):
        """Return (first_name_fr, last_name_fr, first_name_ar, last_name_ar, birth_date, birth_place, parent_name)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT first_name_fr, last_name_fr, first_name_ar, last_name_ar, birth_date, birth_place, parent_name FROM Students WHERE id=%s",
            (student_id,),
        )
        return cursor.fetchone()

    def get_class_size(self, class_id: int, year_id: int) -> int:
        """Return count of students enrolled in class for year."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM StudentClassNumbers WHERE class_id=%s AND year_id=%s",
            (class_id, year_id),
        )
        return int(cursor.fetchone()[0] or 0)

    def get_period_meta(self, period_id: int):
        """Return (year_id, cycle_id) for a period, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_id, cycle_id FROM AcademicPeriods WHERE id=%s", (period_id,))
        return cursor.fetchone()

    def list_periods_for_year_and_cycle(self, year_id: int, cycle_id: int) -> list:
        """Return (id, period_name_fr, period_name_ar) for year+cycle ordered by sort_order."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods WHERE year_id=%s AND cycle_id=%s ORDER BY sort_order",
            (year_id, cycle_id),
        )
        return cursor.fetchall()

    def list_student_ids_in_class(self, class_id: int, year_id: int) -> list:
        """Return list of active student ids in class for year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT S.id FROM Students S
               JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
               WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'""",
            (class_id, year_id),
        )
        return [r[0] for r in cursor.fetchall()]
