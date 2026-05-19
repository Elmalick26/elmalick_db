"""
repositories/students_api_repo.py — Students API data access layer

Methods cover:
  • Academic year lookup
  • Student listing (with search + pagination)
  • Student detail by id
  • Grades, attendance, dues per student
"""

from __future__ import annotations

from typing import Any, Optional


class StudentsApiRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ── Academic year ──────────────────────────────────────────

    def get_active_year_id(self) -> Optional[int]:
        """Return the active academic year id, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Students list ──────────────────────────────────────────

    def list_students(
        self,
        year_id: Optional[int],
        q: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list:
        """Return list of student dicts, filtered by optional search string."""
        cursor = self.conn.cursor()
        if q:
            pat = f"%{q}%"
            cursor.execute(
                """
                SELECT S.id, S.first_name_fr, S.last_name_fr,
                       S.first_name_ar, S.last_name_ar,
                       S.gender, S.birth_date, S.status,
                       C.class_name_fr AS class_name
                FROM Students S
                LEFT JOIN StudentClassNumbers SCN
                       ON S.id = SCN.student_id AND SCN.year_id = %s
                LEFT JOIN Classes C ON SCN.class_id = C.id
                WHERE S.status != 'Archived'
                  AND (S.first_name_fr ILIKE %s OR S.last_name_fr ILIKE %s
                       OR S.first_name_ar ILIKE %s OR S.last_name_ar ILIKE %s)
                ORDER BY S.last_name_fr, S.first_name_fr
                LIMIT %s OFFSET %s
                """,
                (year_id, pat, pat, pat, pat, limit, offset),
            )
        else:
            cursor.execute(
                """
                SELECT S.id, S.first_name_fr, S.last_name_fr,
                       S.first_name_ar, S.last_name_ar,
                       S.gender, S.birth_date, S.status,
                       C.class_name_fr AS class_name
                FROM Students S
                LEFT JOIN StudentClassNumbers SCN
                       ON S.id = SCN.student_id AND SCN.year_id = %s
                LEFT JOIN Classes C ON SCN.class_id = C.id
                WHERE S.status != 'Archived'
                ORDER BY S.last_name_fr, S.first_name_fr
                LIMIT %s OFFSET %s
                """,
                (year_id, limit, offset),
            )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def count_students(self) -> int:
        """Return total count of non-archived students."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Students WHERE status != 'Archived'")
        return cursor.fetchone()[0]

    # ── Student detail ─────────────────────────────────────────

    def get_student_by_id(self, student_id: int) -> dict | None:
        """Return full student row as dict, or None if not found."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Students WHERE id = %s", (student_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    # ── Grades / Attendance / Dues ─────────────────────────────

    def get_grades(self, student_id: int, year_id: Optional[int]) -> list:
        """Return list of grade dicts for the student in the given year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT G.score,
                   SB.subject_name_fr AS subject,
                   SB.coefficient,
                   AP.period_name_fr AS period,
                   AT.name_fr AS exam_type,
                   CASE WHEN LOWER(CY.name_fr) ~* '(elem|prim|ibtida)'
                        THEN 10.0 ELSE 20.0 END AS max_score
            FROM Grades G
            JOIN Subjects SB ON G.subject_id = SB.id
            JOIN AssessmentTypes AT ON G.assessment_id = AT.id
            JOIN AcademicPeriods AP ON AT.period_id = AP.id
            JOIN StudentClassNumbers SCN
                 ON G.student_id = SCN.student_id AND SCN.year_id = G.year_id
            JOIN Classes CL ON SCN.class_id = CL.id
            JOIN Cycles CY ON CL.cycle_id = CY.id
            WHERE G.student_id = %s AND G.year_id = %s
            ORDER BY AP.sort_order, SB.subject_name_fr
            """,
            (student_id, year_id),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_attendance(self, student_id: int, year_id: Optional[int]) -> list:
        """Return list of attendance dicts (last 90 records for given year)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT date, status, reason
            FROM StudentAttendance
            WHERE student_id = %s AND year_id = %s
            ORDER BY date DESC
            LIMIT 90
            """,
            (student_id, year_id),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_dues(self, student_id: int, year_id: Optional[int]) -> list:
        """Return list of fee/dues dicts for the student in the given year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, label, amount, due_date, is_paid
            FROM StudentDues
            WHERE student_id = %s AND year_id = %s
            ORDER BY due_date
            """,
            (student_id, year_id),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]
