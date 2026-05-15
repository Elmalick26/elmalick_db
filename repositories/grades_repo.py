"""
repositories/grades_repo.py — Grades data access layer

Methods cover:
  • Lookup dropdowns (classes, periods, assessments, subjects)
  • Grading sheet (load + upsert)
  • Grade search / report
  • Labels for PDF print
"""

from __future__ import annotations


class GradesRepository:
    def __init__(self, conn):
        self.conn = conn

    # ─────────────────────────────────────────────────────────────
    # Lookup helpers
    # ─────────────────────────────────────────────────────────────

    def list_classes(self) -> list[tuple]:
        """Return (id, class_name_fr) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    def list_periods_for_year(self, year_id: int) -> list[tuple]:
        """Return (id, period_name_fr) for every period in an academic year."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr FROM AcademicPeriods WHERE year_id = %s ORDER BY sort_order",
            (year_id,),
        )
        return cursor.fetchall()

    def list_periods_for_class_year(self, class_id: int, year_id: int) -> list[tuple]:
        """Return (id, period_name_fr) ordered by sort_order for a class/year.

        Looks up the cycle of the class first; if not found falls back to year-only.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT cycle_id FROM Classes WHERE id = %s", (class_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "SELECT id, period_name_fr FROM AcademicPeriods WHERE cycle_id = %s AND year_id = %s ORDER BY sort_order",
                (row[0], year_id),
            )
        else:
            cursor.execute(
                "SELECT id, period_name_fr FROM AcademicPeriods WHERE year_id = %s ORDER BY sort_order",
                (year_id,),
            )
        return cursor.fetchall()

    def list_assessments_for_period(self, period_id: int) -> list[tuple]:
        """Return (id, name_fr) for all assessment types in a period."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name_fr FROM AssessmentTypes WHERE period_id = %s", (period_id,))
        return cursor.fetchall()

    def get_cycle_name_for_class(self, class_id: int) -> str | None:
        """Return the cycle's name_fr for a class, or None."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT CY.name_fr FROM Classes CL JOIN Cycles CY ON CL.cycle_id = CY.id WHERE CL.id = %s",
            (class_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_max_score_for_class(self, class_id: int) -> float:
        """Return 10.0 for primary cycles, 20.0 for all others."""
        cname = (self.get_cycle_name_for_class(class_id) or "").lower()
        return 10.0 if any(k in cname for k in ("elem", "prim", "ibtida")) else 20.0

    def get_class_subjects(self, class_id: int) -> list[tuple]:
        """Return (id, name_fr, name_ar, coefficient) for a class.

        Tries Timetable first; falls back to Subjects filtered by cycle.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT S.id, S.subject_name_fr, S.subject_name_ar, S.coefficient
            FROM Timetable T
            JOIN Subjects S ON T.subject_id = S.id
            WHERE T.class_id = %s
            ORDER BY S.id
            """,
            (class_id,),
        )
        rows = cursor.fetchall()
        if rows:
            return rows
        cursor.execute("SELECT cycle_id FROM Classes WHERE id = %s", (class_id,))
        res = cursor.fetchone()
        if not res:
            return []
        cursor.execute(
            "SELECT id, subject_name_fr, subject_name_ar, coefficient FROM Subjects WHERE cycle_id = %s ORDER BY id",
            (res[0],),
        )
        return cursor.fetchall()

    # ─────────────────────────────────────────────────────────────
    # Grading sheet
    # ─────────────────────────────────────────────────────────────

    def load_grading_sheet(self, class_id: int, subject_id: int, assess_id: int, year_id: int) -> list[tuple]:
        """Return rows (student_id, full_name_fr, full_name_ar, score, observation)
        for every active student in the class, LEFT JOIN'ing existing grades.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id,
                   S.first_name_fr || ' ' || S.last_name_fr,
                   S.first_name_ar || ' ' || S.last_name_ar,
                   G.score, G.observation
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            LEFT JOIN Grades G ON S.id = G.student_id
                               AND G.subject_id = %s
                               AND G.assessment_id = %s
                               AND G.year_id = %s
            WHERE SCN.class_id = %s AND SCN.year_id = %s AND S.status = 'Active'
            ORDER BY S.last_name_fr
            """,
            (subject_id, assess_id, year_id, class_id, year_id),
        )
        return cursor.fetchall()

    def upsert_grade(
        self,
        student_id: int,
        subject_id: int,
        assess_id: int,
        year_id: int,
        score: float,
        observation: str,
        date_recorded: str,
    ) -> None:
        """Insert or update a single grade row."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM Grades WHERE student_id = %s AND subject_id = %s AND assessment_id = %s AND year_id = %s",
            (student_id, subject_id, assess_id, year_id),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE Grades SET score = %s, observation = %s, date_recorded = %s WHERE id = %s",
                (score, observation, date_recorded, existing[0]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO Grades (student_id, subject_id, assessment_id, score, observation, date_recorded, year_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (student_id, subject_id, assess_id, score, observation, date_recorded, year_id),
            )

    # ─────────────────────────────────────────────────────────────
    # Search / report view
    # ─────────────────────────────────────────────────────────────

    def search_grades(
        self,
        year_id: int,
        class_id: int | None = None,
        period_id: int | None = None,
        student_name: str | None = None,
        limit: int = 100,
    ) -> list[tuple]:
        """Return grade rows matching the filters.

        Columns: (date_recorded, class_name_fr, student_full_name,
                  subject_name_fr, assessment_name, score, observation)
        """
        cursor = self.conn.cursor()
        query = """
            SELECT G.date_recorded, C.class_name_fr,
                   S.first_name_fr || ' ' || S.last_name_fr,
                   Sub.subject_name_fr, A.name_fr, G.score, G.observation
            FROM Grades G
            JOIN Students S ON G.student_id = S.id
            LEFT JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = G.year_id
            LEFT JOIN Classes C ON SCN.class_id = C.id
            JOIN Subjects Sub ON G.subject_id = Sub.id
            JOIN AssessmentTypes A ON G.assessment_id = A.id
            WHERE G.year_id = %s
        """
        params: list = [year_id]
        if class_id:
            query += " AND SCN.class_id = %s"
            params.append(class_id)
        if period_id:
            query += " AND A.period_id = %s"
            params.append(period_id)
        if student_name:
            query += " AND (S.first_name_fr ILIKE %s OR S.last_name_fr ILIKE %s)"
            params.extend([f"%{student_name}%", f"%{student_name}%"])
        query += f" ORDER BY G.date_recorded DESC LIMIT {int(limit)}"
        cursor.execute(query, params)
        return cursor.fetchall()

    # ─────────────────────────────────────────────────────────────
    # Alert query (used by main dashboard)
    # ─────────────────────────────────────────────────────────────

    def get_low_average_students(self, year_id: int, threshold: float = 8.0) -> list[tuple]:
        """Return (full_name, normalized_avg) for students averaging below threshold/20."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.first_name_fr || ' ' || S.last_name_fr,
                   ROUND(
                       AVG(G.score * 20.0 /
                           CASE WHEN LOWER(CY.name_fr) SIMILAR TO '%%(elem|prim|ibtida)%%'
                                THEN 10.0 ELSE 20.0 END
                       ), 1
                   ) AS avg_normalized
            FROM Grades G
            JOIN Students S ON G.student_id = S.id
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = G.year_id
            JOIN Classes CL ON SCN.class_id = CL.id
            JOIN Cycles CY ON CL.cycle_id = CY.id
            WHERE G.year_id = %s AND G.score IS NOT NULL
            GROUP BY S.id, S.first_name_fr, S.last_name_fr
            HAVING ROUND(
                       AVG(G.score * 20.0 /
                           CASE WHEN LOWER(CY.name_fr) SIMILAR TO '%%(elem|prim|ibtida)%%'
                                THEN 10.0 ELSE 20.0 END
                       ), 1
                   ) < %s
            ORDER BY avg_normalized ASC
            LIMIT 20
            """,
            (year_id, threshold),
        )
        return cursor.fetchall()

    # ─────────────────────────────────────────────────────────────
    # Labels for PDF print
    # ─────────────────────────────────────────────────────────────

    def get_class_label(self, class_id: int) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT class_name_fr FROM Classes WHERE id = %s", (class_id,))
        row = cursor.fetchone()
        return row[0] if row else "Classe"

    def get_subject_label(self, subject_id: int) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT subject_name_fr FROM Subjects WHERE id = %s", (subject_id,))
        row = cursor.fetchone()
        return row[0] if row else "Matière"

    def get_assessment_label(self, assess_id: int) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name_fr FROM AssessmentTypes WHERE id = %s", (assess_id,))
        row = cursor.fetchone()
        return row[0] if row else "Évaluation"

    def get_students_for_class_year(self, class_id: int, year_id: int) -> list[tuple]:
        """Return (id, full_name_fr, full_name_ar) for active students in a class."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr,
                   S.first_name_ar || ' ' || S.last_name_ar
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id = %s AND SCN.year_id = %s AND S.status = 'Active'
            ORDER BY S.last_name_fr
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()
