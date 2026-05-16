"""Staff repository — staff data access for El Malick Gest."""

from __future__ import annotations

from typing import Any


class StaffRepository:
    """Data access for Staff table operations."""

    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def list_staff(self, search: str = "") -> list[tuple]:
        """Return active staff rows filtered by search string.

        Columns:
          (id, full_name, role, specialty, phone, contract_type,
           salary_base, hourly_rate, photo_path, status)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id,
                   first_name || ' ' || last_name,
                   role, specialty, phone,
                   contract_type, salary_base, hourly_rate, photo_path, status
            FROM Staff
            WHERE (last_name ILIKE %s OR first_name ILIKE %s OR role ILIKE %s)
              AND COALESCE(status, 'Actif') != 'Archived'
            ORDER BY id DESC
            """,
            (f"%{search}%", f"%{search}%", f"%{search}%"),
        )
        return cursor.fetchall()

    def get_staff_details(self, staff_id: int) -> tuple | None:
        """Return a single staff record for form population.

        Columns:
          (first_name, last_name, role, specialty, phone, email, address,
           hire_date, contract_type, salary_base, hourly_rate, photo_path, status)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT first_name, last_name, role, specialty, phone,
                   email, address, hire_date, contract_type,
                   salary_base, hourly_rate, photo_path, status
            FROM Staff WHERE id = %s
            """,
            (staff_id,),
        )
        return cursor.fetchone()

    def get_photo_path(self, staff_id: int) -> str | None:
        """Return the current photo_path for an existing staff member."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT photo_path FROM Staff WHERE id = %s", (staff_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def add_staff(self, data: dict) -> None:
        """Insert a new staff record.

        Expected keys:
          first_name, last_name, role, specialty, phone, hire_date,
          contract_type, salary_base, hourly_rate, photo_path,
          email, address, status
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO Staff (
                first_name, last_name, role, specialty, phone, hire_date,
                contract_type, salary_base, hourly_rate, photo_path,
                email, address, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["first_name"],
                data["last_name"],
                data["role"],
                data["specialty"],
                data["phone"],
                data["hire_date"],
                data["contract_type"],
                data["salary_base"],
                data["hourly_rate"],
                data.get("photo_path", ""),
                data.get("email", ""),
                data.get("address", ""),
                data.get("status", "Actif"),
            ),
        )

    def update_staff(self, staff_id: int, data: dict) -> None:
        """Update an existing staff record."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE Staff SET
                first_name=%s, last_name=%s, role=%s, specialty=%s, phone=%s,
                hire_date=%s, contract_type=%s, salary_base=%s, hourly_rate=%s,
                photo_path=%s, email=%s, address=%s, status=%s
            WHERE id = %s
            """,
            (
                data["first_name"],
                data["last_name"],
                data["role"],
                data["specialty"],
                data["phone"],
                data["hire_date"],
                data["contract_type"],
                data["salary_base"],
                data["hourly_rate"],
                data.get("photo_path", ""),
                data.get("email", ""),
                data.get("address", ""),
                data.get("status", "Actif"),
                staff_id,
            ),
        )

    def archive_staff(self, staff_id: int) -> None:
        """Soft-delete: set status to 'Archived' to preserve history."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE Staff SET status='Archived' WHERE id=%s", (staff_id,))

    # ──────────────────────────────────────────────
    # Subjects
    # ──────────────────────────────────────────────

    def list_subjects(self) -> list[tuple]:
        """Return (id, subject_name_fr) for all subjects."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, subject_name_fr FROM Subjects ORDER BY subject_name_fr")
        return cursor.fetchall()

    # ──────────────────────────────────────────────
    # Timetable
    # ──────────────────────────────────────────────

    def list_timetable(self) -> list[tuple]:
        """Return all timetable rows ordered by day and time.

        Columns: (id, teacher_full_name, class_name_fr, subject_name_fr, day_of_week, time_range)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT T.id,
                   S.last_name || ' ' || S.first_name,
                   C.class_name_fr,
                   Sub.subject_name_fr,
                   T.day_of_week,
                   T.start_time || ' - ' || T.end_time
            FROM Timetable T
            JOIN Staff S ON T.teacher_id = S.id
            JOIN Classes C ON T.class_id = C.id
            JOIN Subjects Sub ON T.subject_id = Sub.id
            ORDER BY
                CASE T.day_of_week
                    WHEN 'Lundi' THEN 1 WHEN 'Mardi' THEN 2 WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4 WHEN 'Vendredi' THEN 5 WHEN 'Samedi' THEN 6 WHEN 'Dimanche' THEN 7
                END,
                T.start_time
            """
        )
        return cursor.fetchall()

    def get_timetable_for_class(self, class_id: int) -> list[tuple]:
        """Return timetable rows for a specific class ordered by day and time.

        Columns: (day_of_week, start_time, end_time, subject_name_fr, teacher_full_name)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT T.day_of_week, T.start_time, T.end_time,
                   Sub.subject_name_fr,
                   S.last_name || ' ' || S.first_name
            FROM Timetable T
            JOIN Staff S ON T.teacher_id = S.id
            JOIN Subjects Sub ON T.subject_id = Sub.id
            WHERE T.class_id = %s
            ORDER BY
                CASE T.day_of_week
                    WHEN 'Lundi' THEN 1 WHEN 'Mardi' THEN 2 WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4 WHEN 'Vendredi' THEN 5 WHEN 'Samedi' THEN 6 WHEN 'Dimanche' THEN 7
                END,
                T.start_time
            """,
            (class_id,),
        )
        return cursor.fetchall()

    def delete_timetable_entry(self, entry_id: int) -> None:
        """Delete a timetable row by id."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Timetable WHERE id = %s", (entry_id,))

    def list_staff_for_report(self) -> list[tuple]:
        """Return all staff rows for the staff list PDF report.

        Columns: (id, full_name, role, specialty, phone, email, address,
                  hire_date, contract_type, salary_base, hourly_rate, status)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, first_name || ' ' || last_name, role, specialty, phone, email,
                   address, hire_date, contract_type, salary_base, hourly_rate, status
            FROM Staff
            ORDER BY status='Actif' DESC, id DESC
            """
        )
        return cursor.fetchall()

    def list_classes(self) -> list[tuple]:
        """Return (id, class_name_fr) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    # ── StaffAttendance ────────────────────────────────────

    def list_active_staff_fullname(self) -> list[tuple]:
        """Return (id, full_name) for all active staff members."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id,
                   TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
            FROM Staff
            WHERE status='Actif'
            """
        )
        return cursor.fetchall()

    def list_active_staff_by_role(self, role_filter: str | None = None) -> list[tuple]:
        """Return (id, full_name, role) for active staff, optionally filtered by role."""
        cursor = self.conn.cursor()
        if role_filter:
            cursor.execute(
                """
                SELECT id,
                       TRIM(COALESCE(last_name, '') || ' ' || COALESCE(first_name, '')),
                       COALESCE(role, '')
                FROM Staff
                WHERE status = 'Actif' AND role = %s
                """,
                (role_filter,),
            )
        else:
            cursor.execute(
                """
                SELECT id,
                       TRIM(COALESCE(last_name, '') || ' ' || COALESCE(first_name, '')),
                       COALESCE(role, '')
                FROM Staff
                WHERE status = 'Actif'
                """
            )
        return cursor.fetchall()

    def get_staff_attendance_for_date(self, staff_id: int, attendance_date: str) -> tuple | None:
        """Return (status, check_in_time, check_out_time, note) for one staff/date."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT status, check_in_time, check_out_time, note
            FROM StaffAttendance
            WHERE staff_id = %s AND attendance_date = %s
            """,
            (staff_id, attendance_date),
        )
        return cursor.fetchone()

    def upsert_staff_attendance(
        self,
        staff_id: int,
        attendance_date: str,
        check_in: str,
        check_out: str,
        status: str,
        note: str,
    ) -> None:
        """Delete existing record then insert new one (upsert pattern)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM StaffAttendance WHERE staff_id = %s AND attendance_date = %s",
            (staff_id, attendance_date),
        )
        cursor.execute(
            """
            INSERT INTO StaffAttendance
                (staff_id, attendance_date, check_in_time, check_out_time, status, note)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (staff_id, attendance_date, check_in, check_out, status, note),
        )

    def get_attendance_report(self, start_date: str, end_date: str, staff_id: int | None = None) -> list[tuple]:
        """Return attendance rows for the report table."""
        cursor = self.conn.cursor()
        if staff_id:
            cursor.execute(
                """
                SELECT attendance_date, status, check_in_time, check_out_time, note
                FROM StaffAttendance
                WHERE staff_id = %s
                  AND attendance_date >= %s AND attendance_date < %s
                ORDER BY attendance_date
                """,
                (staff_id, start_date, end_date),
            )
        else:
            cursor.execute(
                """
                SELECT S.first_name || ' ' || S.last_name,
                       A.attendance_date, A.status,
                       A.check_in_time, A.check_out_time, A.note
                FROM StaffAttendance A
                JOIN Staff S ON A.staff_id = S.id
                WHERE A.attendance_date >= %s AND A.attendance_date < %s
                ORDER BY A.attendance_date DESC, S.last_name
                """,
                (start_date, end_date),
            )
        return cursor.fetchall()

    def get_attendance_report_for_display(
        self, start_date: str, end_date: str, staff_id: int | None = None
    ) -> list[tuple]:
        """Return attendance rows for the table display widget."""
        cursor = self.conn.cursor()
        query = """
            SELECT S.first_name || ' ' || S.last_name AS staff_name,
                   A.attendance_date, A.status,
                   A.check_in_time, A.check_out_time, A.note
            FROM StaffAttendance A
            JOIN Staff S ON A.staff_id = S.id
            WHERE A.attendance_date >= %s AND A.attendance_date < %s
        """
        params: list = [start_date, end_date]
        if staff_id:
            query += " AND A.staff_id = %s"
            params.append(staff_id)
        query += " ORDER BY A.attendance_date DESC, S.last_name"
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_school_info(self) -> tuple | None:
        """Return the single SchoolInfo row."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()

    # ── StaffLeaves ────────────────────────────────────────

    def insert_leave(
        self,
        staff_id: int,
        leave_type: str,
        start_date: str,
        end_date: str,
        days_count: int,
        reason: str,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO StaffLeaves
                (staff_id, leave_type, start_date, end_date, days_count, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (staff_id, leave_type, start_date, end_date, days_count, reason),
        )

    def list_leaves(self) -> list[tuple]:
        """Return all leaves joined with staff name, ordered by start_date DESC."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT L.id,
                   TRIM(COALESCE(S.first_name, '') || ' ' || COALESCE(S.last_name, '')),
                   L.leave_type, L.start_date, L.end_date, L.days_count, L.status
            FROM StaffLeaves L
            JOIN Staff S ON L.staff_id = S.id
            ORDER BY L.start_date DESC
            """
        )
        return cursor.fetchall()

    def update_leave_status(self, leave_id: int, new_status: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE StaffLeaves SET status=%s WHERE id=%s", (new_status, leave_id))

    def get_leaves_summary_report(self, date_from: str, date_to: str) -> list[tuple]:
        """Summary: one row per staff with approved/pending/rejected day counts."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TRIM(COALESCE(S.first_name, '') || ' ' || COALESCE(S.last_name, '')),
                   COUNT(L.id),
                   COALESCE(SUM(CASE WHEN L.status='Approuv\u00e9' THEN L.days_count ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN L.status='En Attente' THEN L.days_count ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN L.status='Rejet\u00e9' THEN L.days_count ELSE 0 END), 0)
            FROM Staff S
            LEFT JOIN StaffLeaves L
                   ON L.staff_id = S.id
                  AND CAST(L.start_date AS DATE) <= CAST(%s AS DATE)
                  AND CAST(L.end_date AS DATE) >= CAST(%s AS DATE)
            WHERE S.status='Actif'
            GROUP BY S.id, S.first_name, S.last_name
            ORDER BY 3 DESC, 1
            """,
            (date_to, date_from),
        )
        return cursor.fetchall()

    def get_leaves_detail_report(self, date_from: str, date_to: str) -> list[tuple]:
        """Detail: one row per leave request within the date range."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TRIM(COALESCE(S.first_name, '') || ' ' || COALESCE(S.last_name, '')),
                   L.leave_type, L.start_date, L.end_date,
                   L.days_count, L.status, COALESCE(L.reason, '')
            FROM StaffLeaves L
            JOIN Staff S ON S.id = L.staff_id
            WHERE CAST(L.start_date AS DATE) <= CAST(%s AS DATE)
              AND CAST(L.end_date AS DATE) >= CAST(%s AS DATE)
            ORDER BY L.start_date DESC, 1
            """,
            (date_to, date_from),
        )
        return cursor.fetchall()

    def get_leave_request_by_id(self, leave_id: int) -> tuple | None:
        """Return full leave request row for PDF export."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT L.id,
                   TRIM(COALESCE(S.first_name, '') || ' ' || COALESCE(S.last_name, '')),
                   L.leave_type, L.start_date, L.end_date,
                   L.days_count, L.status, COALESCE(L.reason, '')
            FROM StaffLeaves L
            JOIN Staff S ON S.id = L.staff_id
            WHERE L.id = %s
            """,
            (leave_id,),
        )
        return cursor.fetchone()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    def get_active_staff_count(self) -> int:
        """Return the number of active staff members."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Staff WHERE status = 'Actif'")
        row = cursor.fetchone()
        return row[0] if row else 0

    def list_pending_leaves(self, limit: int = 20) -> list[tuple]:
        """Return (full_name, leave_type) for staff with pending leave requests."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ST.first_name || ' ' || ST.last_name, SL.leave_type
            FROM StaffLeaves SL
            JOIN Staff ST ON SL.staff_id = ST.id
            WHERE SL.status = 'En Attente'
            ORDER BY SL.start_date DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()

    # ── Timetable conflict helpers ─────────────────────────

    def get_teacher_timetable_for_day(self, teacher_id: int, day: str) -> list[tuple]:
        """Return (class_name_fr, start_time, end_time) for a teacher on a given day."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT C.class_name_fr, T.start_time, T.end_time
            FROM Timetable T
            JOIN Classes C ON T.class_id = C.id
            WHERE T.teacher_id = %s AND T.day_of_week = %s
            """,
            (teacher_id, day),
        )
        return cursor.fetchall()

    def get_class_timetable_for_day(self, class_id: int, day: str) -> list[tuple]:
        """Return (prof_name, subject_name_fr, start_time, end_time) for a class on a given day."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.last_name || ' ' || S.first_name, Sub.subject_name_fr, T.start_time, T.end_time
            FROM Timetable T
            JOIN Staff S ON T.teacher_id = S.id
            JOIN Subjects Sub ON T.subject_id = Sub.id
            WHERE T.class_id = %s AND T.day_of_week = %s
            """,
            (class_id, day),
        )
        return cursor.fetchall()

    def insert_timetable_entry(
        self,
        teacher_id: int,
        class_id: int,
        sub_id: int,
        day: str,
        start: str,
        end: str,
    ) -> None:
        """Insert a new timetable entry."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO Timetable (teacher_id, class_id, subject_id, day_of_week, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (teacher_id, class_id, sub_id, day, start, end),
        )
