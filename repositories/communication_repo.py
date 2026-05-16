"""Repository for CommunicationUI — email settings, recipients, notification logs."""

from __future__ import annotations

from typing import Any


class CommunicationRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # --- Academic year ---

    def get_active_year_id(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT id FROM AcademicYears ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
        return row[0] if row else -1

    # --- Classes ---

    def list_classes(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, COALESCE(class_name_fr, '-') FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    # --- Email settings ---

    def get_email_settings(self) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM EmailSettings LIMIT 1")
        return cursor.fetchone()

    def upsert_email_settings(self, smtp_server: str, smtp_port: str, email_address: str, email_password: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM EmailSettings")
        cursor.execute(
            "INSERT INTO EmailSettings (smtp_server, smtp_port, email_address, email_password) VALUES (%s,%s,%s,%s)",
            (smtp_server, smtp_port, email_address, email_password),
        )

    # --- Recipients ---

    def get_recipients_parents_of_class(self, class_id: int, year_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id,
                   COALESCE(S.parent_name, '[Parent]') AS parent_name,
                   COALESCE(S.parent_email, '') AS parent_email
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    def get_recipients_all_staff(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id,
                   TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')) AS full_name,
                   COALESCE(email, '') AS email
            FROM Staff
            WHERE COALESCE(status, '')='Actif'
            """
        )
        return cursor.fetchall()

    def get_recipients_teachers(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id,
                   TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')) AS full_name,
                   COALESCE(email, '') AS email
            FROM Staff
            WHERE COALESCE(status, '')='Actif' AND COALESCE(role, '') ILIKE '%Prof%'
            """
        )
        return cursor.fetchall()

    # --- Notification logs ---

    def insert_notification_log(
        self, recipient_contact: str, subject: str, status: str, error_msg: str, sent_at: str
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO NotificationLogs (recipient_contact, subject, status, error_msg, sent_at) VALUES (%s,%s,%s,%s,%s)",
            (recipient_contact, subject, status, error_msg, sent_at),
        )

    def list_notification_logs(self, limit: int = 50) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT sent_at, recipient_contact, subject, status FROM NotificationLogs ORDER BY id DESC LIMIT %s",
            (limit,),
        )
        return cursor.fetchall()

    def get_notification_log_summary(self, date_from: str, date_to_full: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT status, COUNT(*)
            FROM NotificationLogs
            WHERE sent_at BETWEEN %s AND %s
            GROUP BY status
            ORDER BY COUNT(*) DESC
            """,
            (date_from, date_to_full),
        )
        return cursor.fetchall()

    def get_notification_log_detail(self, date_from: str, date_to_full: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT sent_at, recipient_contact, subject, status, error_msg
            FROM NotificationLogs
            WHERE sent_at BETWEEN %s AND %s
            ORDER BY id DESC
            """,
            (date_from, date_to_full),
        )
        return cursor.fetchall()
