"""
repositories/timetable_repo.py — Timetable data access layer

Methods cover:
  • Filter dropdowns (classes, subjects, staff)
  • Grid loading (slots for a class)
  • CRUD (insert, update, delete)
  • Print export
"""

from __future__ import annotations

from typing import Any


class TimetableRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ── Dropdowns ──────────────────────────────────────────────

    def list_classes(self) -> list:
        """Return (id, class_name_fr) ordered by name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    def list_subjects(self) -> list:
        """Return (id, subject_name_fr) ordered by name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, subject_name_fr FROM Subjects ORDER BY subject_name_fr")
        return cursor.fetchall()

    def list_active_staff(self) -> list:
        """Return (id, full_name_fr) for non-archived staff, ordered by last name."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, CONCAT(first_name_fr, ' ', last_name_fr) FROM Staff "
            "WHERE status != 'Archived' ORDER BY last_name_fr"
        )
        return cursor.fetchall()

    # ── Grid ────────────────────────────────────────────────────

    def list_slots_for_class(self, class_id: int) -> list:
        """Return timetable rows for a class, joined with subject/teacher names."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                T.id,
                T.day_of_week,
                T.start_time,
                T.end_time,
                T.subject_id,
                T.teacher_id,
                T.room,
                SB.subject_name_fr,
                CONCAT(ST.first_name_fr, ' ', ST.last_name_fr) AS teacher_name
            FROM Timetable T
            JOIN Subjects SB ON T.subject_id = SB.id
            LEFT JOIN Staff ST ON T.teacher_id = ST.id
            WHERE T.class_id = %s
            ORDER BY T.day_of_week, T.start_time
            """,
            (class_id,),
        )
        return cursor.fetchall()

    def list_slots_for_print(self, class_id: int) -> list:
        """Return (day_of_week, start_time, end_time, subject_name_fr, teacher, room)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT T.day_of_week, T.start_time, T.end_time,
                   SB.subject_name_fr,
                   COALESCE(CONCAT(ST.first_name_fr, ' ', ST.last_name_fr), '—') AS teacher,
                   COALESCE(T.room, '—') AS room
            FROM Timetable T
            JOIN Subjects SB ON T.subject_id = SB.id
            LEFT JOIN Staff ST ON T.teacher_id = ST.id
            WHERE T.class_id = %s
            ORDER BY T.day_of_week, T.start_time
            """,
            (class_id,),
        )
        return cursor.fetchall()

    # ── CRUD ────────────────────────────────────────────────────

    def insert_slot(
        self,
        class_id: int,
        day_of_week: str,
        start_time: Any,
        end_time: Any,
        subject_id: int,
        teacher_id: int | None,
        room: str | None,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO Timetable
                (class_id, day_of_week, start_time, end_time,
                 subject_id, teacher_id, room)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (class_id, day_of_week, start_time, end_time, subject_id, teacher_id, room or None),
        )

    def update_slot(
        self,
        slot_id: int,
        day_of_week: str,
        start_time: Any,
        end_time: Any,
        subject_id: int,
        teacher_id: int | None,
        room: str | None,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE Timetable SET
                day_of_week = %s,
                start_time  = %s,
                end_time    = %s,
                subject_id  = %s,
                teacher_id  = %s,
                room        = %s
            WHERE id = %s
            """,
            (day_of_week, start_time, end_time, subject_id, teacher_id, room or None, slot_id),
        )

    def delete_slot(self, slot_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Timetable WHERE id = %s", (slot_id,))
