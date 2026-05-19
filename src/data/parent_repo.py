"""
repositories/parent_repo.py — Parent portal data access layer

Methods cover:
  • Academic year lookup
  • Student lookup by code (for PIN login)
  • PIN update / reset
  • Student profile, grades, attendance, dues
  • Student active check
"""

from __future__ import annotations

from typing import Any


class ParentRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ── Academic year ──────────────────────────────────────────

    def get_active_year_id(self) -> int | None:
        """Return the active academic year id, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Student lookup / PIN ───────────────────────────────────

    def get_student_for_parent_login(self, student_code: str) -> tuple | None:
        """Return (id, first_name_fr, last_name_fr, parent_name, parent_phone,
        pin_hash, pin_plain, student_code) or None."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, first_name_fr, last_name_fr,
                   parent_name, parent_phone,
                   COALESCE(parent_pin_hash, '') AS pin_hash,
                   COALESCE(parent_pin, '')      AS pin_plain,
                   student_code
            FROM Students
            WHERE student_code = %s AND status != 'Archived'
            LIMIT 1
            """,
            (student_code,),
        )
        return cursor.fetchone()

    def update_student_pin(self, student_id: int, new_hash: str) -> None:
        """Set bcrypt pin_hash and clear plain pin."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE Students SET parent_pin_hash = %s, parent_pin = NULL WHERE id = %s",
            (new_hash, student_id),
        )

    def reset_student_pin(self, student_id: int) -> None:
        """Clear both pin columns so the parent can redefine at next login."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE Students SET parent_pin_hash = NULL, parent_pin = NULL WHERE id = %s",
            (student_id,),
        )

    def check_student_active(self, student_id: int) -> bool:
        """Return True if the student exists and is not archived."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM Students WHERE id = %s AND status != 'Archived'",
            (student_id,),
        )
        return cursor.fetchone() is not None

    # ── Profile / data ─────────────────────────────────────────

    def get_student_info(self, student_id: int, year_id: int) -> dict | None:
        """Return student profile dict (with class/year) or None."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.first_name_fr, S.last_name_fr,
                   S.first_name_ar, S.last_name_ar,
                   S.birth_date, S.gender,
                   S.parent_name, S.parent_phone, S.parent_email,
                   C.class_name_fr AS class_name,
                   AY.year_label AS academic_year
            FROM Students S
            LEFT JOIN StudentClassNumbers SCN
                   ON S.id = SCN.student_id AND SCN.year_id = %s
            LEFT JOIN AcademicYears AY ON SCN.year_id = AY.id AND AY.is_active = 1
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE S.id = %s
            """,
            (year_id, student_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    def get_student_grades(self, student_id: int, year_id: int) -> list:
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

    def get_student_attendance(self, student_id: int) -> list:
        """Return list of attendance dicts (last 60 records for active year)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT SA.date, SA.status, SA.reason
            FROM StudentAttendance SA
            JOIN AcademicYears AY ON SA.year_id = AY.id AND AY.is_active = 1
            WHERE SA.student_id = %s
            ORDER BY SA.date DESC
            LIMIT 60
            """,
            (student_id,),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]

    def get_student_dues(self, student_id: int) -> list:
        """Return list of fee/dues dicts for the student in the active year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT SD.fee_description AS label,
                   SD.net_amount AS amount,
                   SD.due_date,
                   SD.is_paid
            FROM StudentDues SD
            JOIN AcademicYears AY ON SD.year_id = AY.id AND AY.is_active = 1
            WHERE SD.student_id = %s
            ORDER BY SD.due_date
            """,
            (student_id,),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]
