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
            "SELECT id, CONCAT(first_name, ' ', last_name) FROM Staff " "WHERE status != 'Archived' ORDER BY last_name"
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
                CONCAT(ST.first_name, ' ', ST.last_name) AS teacher_name
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
                   COALESCE(CONCAT(ST.first_name, ' ', ST.last_name), '—') AS teacher,
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

    # ── Teacher view ────────────────────────────────────────────

    def list_slots_for_teacher(self, teacher_id: int) -> list:
        """Return all slots assigned to a teacher, across all classes."""
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
                CONCAT(ST.first_name, ' ', ST.last_name) AS teacher_name,
                C.class_name_fr
            FROM Timetable T
            JOIN Subjects SB ON T.subject_id = SB.id
            LEFT JOIN Staff ST ON T.teacher_id = ST.id
            JOIN Classes C ON T.class_id = C.id
            WHERE T.teacher_id = %s
            ORDER BY
                CASE T.day_of_week
                    WHEN 'Lundi' THEN 1 WHEN 'Mardi' THEN 2 WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4 WHEN 'Vendredi' THEN 5 WHEN 'Samedi' THEN 6
                END,
                T.start_time
            """,
            (teacher_id,),
        )
        return cursor.fetchall()

    def list_slots_for_teacher_print(self, teacher_id: int) -> list:
        """Return (day, start, end, subject, class_name, room) for a teacher PDF."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT T.day_of_week, T.start_time, T.end_time,
                   SB.subject_name_fr,
                   C.class_name_fr,
                   COALESCE(T.room, '—') AS room
            FROM Timetable T
            JOIN Subjects SB ON T.subject_id = SB.id
            JOIN Classes C ON T.class_id = C.id
            WHERE T.teacher_id = %s
            ORDER BY
                CASE T.day_of_week
                    WHEN 'Lundi' THEN 1 WHEN 'Mardi' THEN 2 WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4 WHEN 'Vendredi' THEN 5 WHEN 'Samedi' THEN 6
                END,
                T.start_time
            """,
            (teacher_id,),
        )
        return cursor.fetchall()

    # ── Conflict detection ──────────────────────────────────────

    def get_teacher_slots_for_day(self, teacher_id: int, day: str, exclude_slot_id: int | None = None) -> list:
        """Return (class_name, start_time, end_time) for a teacher on a given day.

        Used to detect scheduling conflicts before inserting or updating a slot.
        Pass *exclude_slot_id* when editing an existing slot so the current row is
        not compared against itself.
        """
        cursor = self.conn.cursor()
        sql = """
            SELECT C.class_name_fr, T.start_time, T.end_time
            FROM Timetable T
            JOIN Classes C ON T.class_id = C.id
            WHERE T.teacher_id = %s AND T.day_of_week = %s
        """
        params: list = [teacher_id, day]
        if exclude_slot_id is not None:
            sql += " AND T.id != %s"
            params.append(exclude_slot_id)
        cursor.execute(sql, params)
        return cursor.fetchall()

    def get_class_slots_for_day(self, class_id: int, day: str, exclude_slot_id: int | None = None) -> list:
        """Return (teacher_name, subject_name, start_time, end_time) for a class on a given day.

        Used to detect class scheduling conflicts.
        """
        cursor = self.conn.cursor()
        sql = """
            SELECT COALESCE(CONCAT(ST.first_name, ' ', ST.last_name), '—'),
                   SB.subject_name_fr, T.start_time, T.end_time
            FROM Timetable T
            JOIN Subjects SB ON T.subject_id = SB.id
            LEFT JOIN Staff ST ON T.teacher_id = ST.id
            WHERE T.class_id = %s AND T.day_of_week = %s
        """
        params: list = [class_id, day]
        if exclude_slot_id is not None:
            sql += " AND T.id != %s"
            params.append(exclude_slot_id)
        cursor.execute(sql, params)
        return cursor.fetchall()
