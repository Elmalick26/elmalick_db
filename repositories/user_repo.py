"""UserRepository — طبقة الوصول إلى بيانات المستخدمين وسجل المراجعة."""

from __future__ import annotations

from typing import Any


class UserRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ── Users ─────────────────────────────────────────────

    def count_users(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users")
        row = cursor.fetchone()
        return row[0] if row else 0

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str,
        staff_id=None,
        status: str = "Actif",
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO Users (staff_id, username, email, password_hash, role, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (staff_id, username, email, password_hash, role, status),
        )

    def list_users(self) -> list[tuple]:
        """Return (id, staff_id, staff_name, username, email, role) ordered by id DESC."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.staff_id,
                   COALESCE(s.first_name || ' ' || s.last_name, '---') AS staff_name,
                   u.username, u.email, u.role
            FROM Users u
            LEFT JOIN Staff s ON u.staff_id = s.id
            ORDER BY u.id DESC
            """
        )
        return cursor.fetchall()

    def update_password(self, user_id: int, password_hash: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE Users SET password_hash=%s WHERE id=%s",
            (password_hash, user_id),
        )

    def delete_user(self, user_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Users WHERE id=%s", (user_id,))

    # ── Staff lookups (read-only) ──────────────────────────

    def list_active_staff(self) -> list[tuple]:
        """Return (id, first_name, last_name) for active staff, ordered by last_name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, first_name, last_name FROM Staff WHERE status='Actif' ORDER BY last_name")
        return cursor.fetchall()

    def get_staff_email(self, staff_id: int) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT email FROM Staff WHERE id=%s", (staff_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else ""

    # ── AuditLogs ──────────────────────────────────────────

    def list_audit_logs(
        self,
        search: str = "",
        date_start=None,
        date_end=None,
        limit: int = 300,
    ) -> list[tuple]:
        """Return (timestamp, actor, action, target) newest-first."""
        pattern = f"%{search}%"
        query = (
            "SELECT timestamp, actor, action, target FROM AuditLogs "
            "WHERE (actor ILIKE %s OR action ILIKE %s OR target ILIKE %s)"
        )
        params: list = [pattern, pattern, pattern]
        if date_start and date_end:
            query += " AND timestamp >= %s AND timestamp <= %s"
            params.extend([date_start, date_end])
        query += " ORDER BY id DESC LIMIT %s"
        params.append(limit)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
