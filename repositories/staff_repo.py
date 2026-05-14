"""Staff repository — staff data access for El Malick Gest."""

from __future__ import annotations


class StaffRepository:
    """Data access for Staff table operations."""

    def __init__(self, conn):
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
                data["first_name"], data["last_name"], data["role"],
                data["specialty"], data["phone"], data["hire_date"],
                data["contract_type"], data["salary_base"], data["hourly_rate"],
                data.get("photo_path", ""), data.get("email", ""),
                data.get("address", ""), data.get("status", "Actif"),
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
                data["first_name"], data["last_name"], data["role"],
                data["specialty"], data["phone"], data["hire_date"],
                data["contract_type"], data["salary_base"], data["hourly_rate"],
                data.get("photo_path", ""), data.get("email", ""),
                data.get("address", ""), data.get("status", "Actif"),
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
