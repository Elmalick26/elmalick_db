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
