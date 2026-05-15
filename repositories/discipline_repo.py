"""DisciplineRepository — طبقة الوصول لبيانات الانضباط المدرسي.

Covers: StudentDiscipline CRUD, period resolution, class context,
        student lists, history with dynamic filters.
"""

from __future__ import annotations


class DisciplineRepository:
    def __init__(self, conn):
        self.conn = conn

    # ── AcademicYears ──────────────────────────────────────

    def get_active_year_id(self) -> int:
        """Return the active year id, or last year id, or -1."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("SELECT id FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else -1

    # ── Classes ────────────────────────────────────────────

    def list_classes(self) -> list:
        """Return (id, class_name_fr) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes")
        return cursor.fetchall()

    def get_cycle_name_for_class(self, class_id: int) -> str | None:
        """Return cycle name_fr (lowercase) for a given class_id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT CY.name_fr
            FROM Classes CL
            JOIN Cycles CY ON CL.cycle_id = CY.id
            WHERE CL.id = %s
            """,
            (class_id,),
        )
        row = cursor.fetchone()
        return row[0].lower() if row and row[0] else None

    def get_cycle_id_for_class(self, class_id: int) -> int | None:
        """Return cycle_id for a given class_id."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT cycle_id FROM Classes WHERE id=%s", (class_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Students ───────────────────────────────────────────

    def list_active_students_fullname(self, class_id: int, year_id: int) -> list:
        """Return (id, full_name_fr) for active students in class/year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id,
                   S.first_name_fr || ' ' || S.last_name_fr
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
            ORDER BY S.last_name_fr, S.first_name_fr
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    # ── AcademicPeriods ────────────────────────────────────

    def list_periods_for_class(self, class_id: int, year_id: int) -> list:
        """Return (id, period_name_fr) for a given class + year."""
        cycle_id = self.get_cycle_id_for_class(class_id)
        if not cycle_id:
            return []
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, period_name_fr
            FROM AcademicPeriods
            WHERE year_id=%s AND cycle_id=%s
            ORDER BY sort_order, id
            """,
            (year_id, cycle_id),
        )
        return cursor.fetchall()

    def resolve_period_id_for_class_date(self, class_id: int, date_str: str, year_id: int) -> int | None:
        """Return the period id whose date range contains date_str, or None."""
        cycle_id = self.get_cycle_id_for_class(class_id)
        if not cycle_id:
            return None
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM AcademicPeriods
            WHERE year_id=%s AND cycle_id=%s
              AND CAST(%s AS DATE)
                  BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
            ORDER BY sort_order, id
            LIMIT 1
            """,
            (year_id, cycle_id, date_str),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ── StudentDiscipline ──────────────────────────────────

    def insert_incident(
        self,
        student_id: int,
        date: str,
        incident_type: str,
        sanction: str,
        points: int,
        observation: str,
        year_id: int,
        period_id: int | None,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO StudentDiscipline
                (student_id, incident_date, incident_type, sanction,
                 points_deducted, observation, year_id, period_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (student_id, date, incident_type, sanction, points, observation, year_id, period_id),
        )

    def update_incident(
        self,
        incident_id: int,
        date: str,
        incident_type: str,
        sanction: str,
        points: int,
        observation: str,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE StudentDiscipline
            SET incident_date=%s, incident_type=%s, sanction=%s,
                points_deducted=%s, observation=%s
            WHERE id=%s
            """,
            (date, incident_type, sanction, points, observation, incident_id),
        )

    def delete_incident(self, incident_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM StudentDiscipline WHERE id=%s", (incident_id,))

    def get_incident_details(self, incident_id: int) -> dict | None:
        """Return a detail dict for the incident, or None."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT D.id,
                   S.first_name_fr || ' ' || S.last_name_fr,
                   C.class_name_fr,
                   SCN.class_id,
                   D.incident_date, D.incident_type, D.sanction,
                   D.points_deducted, D.observation
            FROM StudentDiscipline D
            JOIN Students S ON D.student_id = S.id
            LEFT JOIN StudentClassNumbers SCN
                   ON S.id = SCN.student_id AND SCN.year_id = D.year_id
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE D.id = %s
            """,
            (incident_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "student_name": row[1],
            "class_name": row[2] if row[2] else "-",
            "class_id": row[3],
            "date": row[4],
            "incident": row[5],
            "sanction": row[6],
            "points": row[7],
            "observation": row[8],
        }

    def get_recent_incidents(self, year_id: int, limit: int = 10) -> list:
        """Return the most recent discipline incidents for a year."""
        cursor = self.conn.cursor()
        if year_id != -1:
            cursor.execute(
                """
                SELECT S.first_name_fr, D.incident_date, D.incident_type,
                       D.points_deducted
                FROM StudentDiscipline D
                JOIN Students S ON D.student_id = S.id
                WHERE D.year_id = %s
                ORDER BY D.id DESC LIMIT %s
                """,
                (year_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT S.first_name_fr, D.incident_date, D.incident_type,
                       D.points_deducted
                FROM StudentDiscipline D
                JOIN Students S ON D.student_id = S.id
                ORDER BY D.id DESC LIMIT %s
                """,
                (limit,),
            )
        return cursor.fetchall()

    def get_history(
        self,
        year_id: int,
        class_id: int | None = None,
        period_id: int | None = None,
        search: str | None = None,
    ) -> list:
        """Return discipline history rows with optional filters.

        Columns: (id, student_name, class_name, incident_date,
                  incident_type, sanction, points_deducted, observation)
        """
        query = """
            SELECT D.id,
                   S.first_name_fr || ' ' || S.last_name_fr,
                   C.class_name_fr,
                   D.incident_date, D.incident_type, D.sanction,
                   D.points_deducted, D.observation
            FROM StudentDiscipline D
            JOIN Students S ON D.student_id = S.id
            LEFT JOIN StudentClassNumbers SCN
                   ON S.id = SCN.student_id AND SCN.year_id = D.year_id
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE 1=1
        """
        params: list = []
        if year_id != -1:
            query += " AND D.year_id = %s"
            params.append(year_id)
        if period_id:
            query += """
                AND (
                    D.period_id = %s
                    OR (
                        D.period_id IS NULL
                        AND CAST(D.incident_date AS DATE) BETWEEN
                            (SELECT CAST(start_date AS DATE)
                             FROM AcademicPeriods WHERE id = %s)
                            AND
                            (SELECT CAST(end_date AS DATE)
                             FROM AcademicPeriods WHERE id = %s)
                    )
                )
            """
            params.extend([period_id, period_id, period_id])
        if class_id:
            query += " AND SCN.class_id = %s"
            params.append(class_id)
        if search:
            query += " AND (S.first_name_fr ILIKE %s OR S.last_name_fr ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY D.incident_date DESC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    # ── SchoolInfo ─────────────────────────────────────────

    def get_school_info(self) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()
