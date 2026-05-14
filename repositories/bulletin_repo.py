"""BulletinRepository — طبقة الوصول لبيانات الكشوف والنتائج.

Covers: Classes list, AcademicPeriods, active students, period lookup,
        SchoolInfo, AcademicYears labels — all used by BulletinGenerationWindow.

Note: GradeCalculator uses cursor-passing internally for performance;
      this repo covers only the standalone UI-level queries.
"""
from __future__ import annotations


class BulletinRepository:
    def __init__(self, conn):
        self.conn = conn

    # ── AcademicYears ──────────────────────────────────────

    def get_active_year_id(self) -> int:
        """Return the active year id, or the last year id, or -1."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("SELECT id FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else -1

    def get_year_label(self, year_id: int) -> str | None:
        """Return year_label for a given year_id, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_label FROM AcademicYears WHERE id=%s", (year_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_last_year_label(self) -> str | None:
        """Return year_label of the most recent year, or None."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_label FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Classes ────────────────────────────────────────────

    def list_classes(self) -> list:
        """Return (id, class_name_fr, class_name_ar) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr, class_name_ar FROM Classes")
        return cursor.fetchall()

    def get_class_names(self, class_id: int) -> tuple | None:
        """Return (class_name_fr, class_name_ar) for a given class_id."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT class_name_fr, class_name_ar FROM Classes WHERE id=%s", (class_id,)
        )
        return cursor.fetchone()

    def get_cycle_id_for_class(self, class_id: int) -> int | None:
        """Return cycle_id for a given class_id."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT cycle_id FROM Classes WHERE id=%s", (class_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    # ── AcademicPeriods ────────────────────────────────────

    def list_periods_for_year(self, year_id: int) -> list:
        """Return (id, period_name_fr, period_name_ar) for a given year."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods "
            "WHERE year_id=%s ORDER BY sort_order",
            (year_id,),
        )
        return cursor.fetchall()

    def list_all_periods(self) -> list:
        """Return (id, period_name_fr, period_name_ar) for all periods."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr, period_name_ar FROM AcademicPeriods ORDER BY sort_order"
        )
        return cursor.fetchall()

    def get_period_id_by_name(
        self, period_name: str, cycle_id: int, year_id: int | None = None
    ) -> int | None:
        """Lookup period id by name + cycle; optionally filter by year first."""
        cursor = self.conn.cursor()
        if year_id is not None and year_id != -1:
            cursor.execute(
                "SELECT id FROM AcademicPeriods "
                "WHERE period_name_fr=%s AND cycle_id=%s AND year_id=%s "
                "ORDER BY sort_order LIMIT 1",
                (period_name, cycle_id, year_id),
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        cursor.execute(
            "SELECT id FROM AcademicPeriods "
            "WHERE period_name_fr=%s AND cycle_id=%s ORDER BY id DESC LIMIT 1",
            (period_name, cycle_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ── Students ───────────────────────────────────────────

    def list_active_students_in_class(self, class_id: int, year_id: int) -> list:
        """Return (id, first_name_fr, last_name_fr, first_name_ar, last_name_ar)
        for active students enrolled in class_id for year_id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, S.first_name_fr, S.last_name_fr,
                   S.first_name_ar, S.last_name_ar
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id=%s AND SCN.year_id=%s AND S.status='Active'
            ORDER BY S.last_name_fr, S.first_name_fr
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    # ── SchoolInfo ─────────────────────────────────────────

    def get_school_info(self) -> tuple | None:
        """Return the single SchoolInfo row."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()
