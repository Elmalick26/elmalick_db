"""Repository for AdminDocuments — school documents, student data, photos."""

from __future__ import annotations

from typing import Any


class AdminDocumentsRepository:
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

    def get_active_year_label(self) -> str | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_label FROM AcademicYears WHERE is_active=1")
        row = cursor.fetchone()
        return row[0] if row else None

    # --- Classes ---

    def list_classes(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes")
        return cursor.fetchall()

    # --- Students ---

    def list_active_students_in_class(self, class_id: int, year_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    def list_student_ids_in_class(self, class_id: int, year_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
            """,
            (class_id, year_id),
        )
        return [r[0] for r in cursor.fetchall()]

    def get_student_photo_path(self, student_id: int) -> str | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT photo_path FROM Students WHERE id=%s", (student_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def update_student_photo_path(self, student_id: int, path: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE Students SET photo_path=%s WHERE id=%s", (path, student_id))

    def get_student_full_data(self, student_id: int, year_id: int) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr, S.birth_date, S.birth_place,
                   C.class_name_fr, S.parent_name, S.photo_path, S.address, S.parent_phone, S.registration_date,
                   SCN.class_number, S.student_code
            FROM Students S
            LEFT JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id=%s
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE S.id=%s
            """,
            (year_id, student_id),
        )
        return cursor.fetchone()

    def get_student_dues(self, student_id: int, year_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT fee_type, fee_description, net_amount, due_date, is_paid
            FROM StudentDues
            WHERE student_id=%s AND year_id=%s
            ORDER BY due_date ASC, id ASC
            """,
            (student_id, year_id),
        )
        return cursor.fetchall()

    # --- School info ---

    def get_school_info(self) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()
