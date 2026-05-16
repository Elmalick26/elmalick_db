"""
repositories/attendance_repo.py — Student attendance data access layer

Methods cover:
  • Class & period lookups
  • Period resolution for a given date
  • Loading student list for daily entry (with existing attendance pre-filled)
  • Upserting a single attendance record
  • Report data retrieval (dynamic filters)
  • Alert query (high-absence students)
"""

from __future__ import annotations

from typing import Any


class AttendanceRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ─────────────────────────────────────────────────────────────
    # Lookup helpers
    # ─────────────────────────────────────────────────────────────

    def list_classes(self) -> list[tuple]:
        """Return (id, class_name_fr) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    def get_periods_for_class(self, class_id: int, year_id: int) -> list[tuple]:
        """Return (id, period_name_fr) ordered by sort_order for a class/year."""
        if not class_id or year_id == -1:
            return []
        cursor = self.conn.cursor()
        cursor.execute("SELECT cycle_id FROM Classes WHERE id = %s", (class_id,))
        cycle_row = cursor.fetchone()
        if not cycle_row:
            return []
        cursor.execute(
            """
            SELECT id, period_name_fr
            FROM AcademicPeriods
            WHERE year_id = %s AND cycle_id = %s
            ORDER BY sort_order, id
            """,
            (year_id, cycle_row[0]),
        )
        return cursor.fetchall()

    def resolve_period_id_for_class_date(self, class_id: int, date_str: str, year_id: int) -> int | None:
        """Return the period_id whose date range covers date_str for the given class/year."""
        if not class_id or not date_str or year_id == -1:
            return None
        cursor = self.conn.cursor()
        cursor.execute("SELECT cycle_id FROM Classes WHERE id = %s", (class_id,))
        cycle_row = cursor.fetchone()
        if not cycle_row:
            return None
        cursor.execute(
            """
            SELECT id
            FROM AcademicPeriods
            WHERE year_id = %s AND cycle_id = %s
              AND CAST(%s AS DATE) BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
            ORDER BY sort_order, id
            LIMIT 1
            """,
            (year_id, cycle_row[0], date_str),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ─────────────────────────────────────────────────────────────
    # Daily entry
    # ─────────────────────────────────────────────────────────────

    def load_students_for_attendance(
        self,
        class_id: int,
        date_sel: str,
        year_id: int,
        period_id: int | None = None,
    ) -> list[tuple]:
        """Return (student_id, full_name, status, justifie, reason, notes)
        for all active students in the class, with any existing attendance pre-filled.
        """
        cursor = self.conn.cursor()
        if period_id:
            cursor.execute(
                """
                SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr,
                       A.status, A.justifie, A.reason, A.notes
                FROM Students S
                JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = %s
                LEFT JOIN StudentAttendance A ON S.id = A.student_id
                                              AND A.date = %s
                                              AND A.year_id = %s
                                              AND A.period_id = %s
                WHERE SCN.class_id = %s AND S.status = 'Active'
                ORDER BY S.first_name_fr
                """,
                (year_id, date_sel, year_id, period_id, class_id),
            )
        else:
            cursor.execute(
                """
                SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr,
                       A.status, A.justifie, A.reason, A.notes
                FROM Students S
                JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = %s
                LEFT JOIN StudentAttendance A ON S.id = A.student_id
                                              AND A.date = %s
                                              AND A.year_id = %s
                WHERE SCN.class_id = %s AND S.status = 'Active'
                ORDER BY S.first_name_fr
                """,
                (year_id, date_sel, year_id, class_id),
            )
        return cursor.fetchall()

    def upsert_attendance(
        self,
        student_id: int,
        date_sel: str,
        status: str,
        is_justified: int,
        reason: str,
        notes: str,
        year_id: int,
        period_id: int | None,
    ) -> None:
        """Insert or update a single attendance record."""
        cursor = self.conn.cursor()
        if period_id:
            cursor.execute(
                "SELECT id FROM StudentAttendance WHERE student_id = %s AND date = %s AND year_id = %s AND COALESCE(period_id, 0) = %s",
                (student_id, date_sel, year_id, period_id),
            )
        else:
            cursor.execute(
                "SELECT id FROM StudentAttendance WHERE student_id = %s AND date = %s AND year_id = %s AND (period_id IS NULL OR period_id = 0)",
                (student_id, date_sel, year_id),
            )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE StudentAttendance
                SET status = %s, justifie = %s, reason = %s, notes = %s, year_id = %s, period_id = %s
                WHERE id = %s
                """,
                (status, is_justified, reason, notes, year_id, period_id, existing[0]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO StudentAttendance (student_id, date, status, justifie, reason, notes, year_id, period_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (student_id, date_sel, status, is_justified, reason, notes, year_id, period_id),
            )

    # ─────────────────────────────────────────────────────────────
    # Report
    # ─────────────────────────────────────────────────────────────

    def load_students_for_report_combo(self, class_id: int, year_id: int) -> list[tuple]:
        """Return (id, full_name_fr) for active students in a class/year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id = %s AND SCN.year_id = %s AND S.status = 'Active'
            ORDER BY S.first_name_fr
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    def fetch_report_data(
        self,
        year_id: int,
        date_from: str,
        date_to: str,
        class_id: int | None = None,
        student_id: int | None = None,
        period_id: int | None = None,
    ) -> list[tuple]:
        """Return attendance rows matching the given filters.

        Columns: (date, student_full_name, class_name_fr, status, justifie, reason)
        """
        cursor = self.conn.cursor()
        query = """
            SELECT A.date, S.first_name_fr || ' ' || S.last_name_fr, C.class_name_fr,
                   A.status, A.justifie, A.reason
            FROM StudentAttendance A
            JOIN Students S ON A.student_id = S.id
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = A.year_id
            JOIN Classes C ON SCN.class_id = C.id
            WHERE A.date BETWEEN %s AND %s
        """
        params: list = [date_from, date_to]
        if year_id != -1:
            query += " AND A.year_id = %s"
            params.append(year_id)
        if period_id:
            query += " AND COALESCE(A.period_id, 0) = %s"
            params.append(period_id)
        if class_id:
            query += " AND SCN.class_id = %s"
            params.append(class_id)
        if student_id:
            query += " AND A.student_id = %s"
            params.append(student_id)
        query += " ORDER BY A.date DESC, C.sort_order, S.first_name_fr"
        cursor.execute(query, params)
        return cursor.fetchall()

    # ─────────────────────────────────────────────────────────────
    # Alert query (used by main dashboard)
    # ─────────────────────────────────────────────────────────────

    def get_high_absence_students(self, year_id: int, threshold_pct: float = 20.0) -> list[tuple]:
        """Return (full_name, absence_rate) for students exceeding the absence threshold."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.first_name_fr || ' ' || S.last_name_fr,
                   ROUND(COUNT(*) FILTER (WHERE SA.status = 'Absent') * 100.0 / NULLIF(COUNT(*), 0), 0) AS absence_rate
            FROM Students S
            JOIN StudentAttendance SA ON S.id = SA.student_id
            WHERE SA.year_id = %s AND S.status = 'Active'
            GROUP BY S.id, S.first_name_fr, S.last_name_fr
            HAVING COUNT(*) FILTER (WHERE SA.status = 'Absent') * 100.0 / NULLIF(COUNT(*), 0) > %s
            ORDER BY absence_rate DESC
            LIMIT 20
            """,
            (year_id, threshold_pct),
        )
        return cursor.fetchall()
