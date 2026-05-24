"""AcademicRepository — طبقة الوصول لبيانات الإعدادات المدرسية.

Covers: SchoolInfo, AcademicYears, Cycles, Classes, Subjects,
        AcademicPeriods, AssessmentTypes.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


class AcademicRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ── SchoolInfo ─────────────────────────────────────────

    def get_school_info(self) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()

    def save_school_info(
        self,
        republic: str,
        ia: str,
        ief: str,
        school_name: str,
        auth: str,
        address: str,
        phone: str,
        logo_path: str,
        director: str,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM SchoolInfo")
        cursor.execute(
            """
            INSERT INTO SchoolInfo
                (republic, ia, ief, school_name, auth_number,
                 address, phone, logo_path, director_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (republic, ia, ief, school_name, auth, address, phone, logo_path, director),
        )

    # ── AcademicYears ──────────────────────────────────────

    def list_years(self) -> list:
        """Return (id, year_label, is_active, start_date, end_date) for all years."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, year_label, is_active, start_date, end_date " "FROM AcademicYears ORDER BY id DESC")
        return cursor.fetchall()

    def get_year(self, year_id: int) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT year_label, start_date, end_date FROM AcademicYears WHERE id=%s", (year_id,))
        return cursor.fetchone()

    def get_year_is_active(self, year_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_active FROM AcademicYears WHERE id=%s", (year_id,))
        row = cursor.fetchone()
        return bool(row and row[0])

    def upsert_year(
        self,
        year_id: int | None,
        label: str,
        start_date_value: str | None = None,
        end_date_value: str | None = None,
    ) -> None:
        cursor = self.conn.cursor()
        if year_id:
            cursor.execute(
                "UPDATE AcademicYears SET year_label=%s, start_date=%s, end_date=%s WHERE id=%s",
                (label, start_date_value, end_date_value, year_id),
            )
        else:
            cursor.execute(
                "INSERT INTO AcademicYears (year_label, is_active, start_date, end_date) " "VALUES (%s, 0, %s, %s)",
                (label, start_date_value, end_date_value),
            )

    def activate_year(self, year_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("UPDATE AcademicYears SET is_active=0")
        cursor.execute("UPDATE AcademicYears SET is_active=1 WHERE id=%s", (year_id,))

    def delete_year(self, year_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM AcademicYears WHERE id=%s", (year_id,))

    # ── Cycles ─────────────────────────────────────────────

    def list_cycles(self) -> list:
        """Return (id, name_fr, name_ar) for all cycles."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name_fr, name_ar FROM Cycles")
        return cursor.fetchall()

    def get_cycle(self, cycle_id: int) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name_fr, name_ar FROM Cycles WHERE id=%s", (cycle_id,))
        return cursor.fetchone()

    def upsert_cycle(self, cycle_id: int | None, fr: str, ar: str) -> None:
        cursor = self.conn.cursor()
        if cycle_id:
            cursor.execute("UPDATE Cycles SET name_fr=%s, name_ar=%s WHERE id=%s", (fr, ar, cycle_id))
        else:
            cursor.execute("INSERT INTO Cycles (name_fr, name_ar) VALUES (%s, %s)", (fr, ar))

    def delete_cycle(self, cycle_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Cycles WHERE id=%s", (cycle_id,))

    # ── Classes ────────────────────────────────────────────

    def list_classes_with_cycle(self) -> list:
        """Return (id, cycle_name_fr, class_name_fr, class_name_ar) ordered by sort_order."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT CL.id, CY.name_fr, CL.class_name_fr, CL.class_name_ar"
            " FROM Classes CL JOIN Cycles CY ON CL.cycle_id=CY.id"
            " ORDER BY CL.sort_order"
        )
        return cursor.fetchall()

    def get_class(self, class_id: int) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT cycle_id, class_name_fr, class_name_ar, sort_order" " FROM Classes WHERE id=%s",
            (class_id,),
        )
        return cursor.fetchone()

    def upsert_class(self, class_id: int | None, cycle_id: int, fr: str, ar: str, order: int) -> None:
        cursor = self.conn.cursor()
        if class_id:
            cursor.execute(
                "UPDATE Classes SET cycle_id=%s, class_name_fr=%s," " class_name_ar=%s, sort_order=%s WHERE id=%s",
                (cycle_id, fr, ar, order, class_id),
            )
        else:
            cursor.execute(
                "INSERT INTO Classes (cycle_id, class_name_fr, class_name_ar, sort_order)" " VALUES (%s, %s, %s, %s)",
                (cycle_id, fr, ar, order),
            )

    def delete_class(self, class_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Classes WHERE id=%s", (class_id,))

    # ── Subjects ───────────────────────────────────────────

    def list_subjects_with_cycle(self) -> list:
        """Return (id, cycle_name_fr, subject_name_fr, subject_name_ar, lang, coeff)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT S.id, C.name_fr, S.subject_name_fr, S.subject_name_ar,"
            "       S.subject_lang, S.coefficient"
            " FROM Subjects S JOIN Cycles C ON S.cycle_id=C.id"
        )
        return cursor.fetchall()

    def get_subject(self, subject_id: int) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT cycle_id, subject_name_fr, subject_name_ar, coefficient, subject_lang" " FROM Subjects WHERE id=%s",
            (subject_id,),
        )
        return cursor.fetchone()

    def upsert_subject(
        self,
        subject_id: int | None,
        cycle_id: int,
        fr: str,
        ar: str,
        coef: float,
        lang: str,
    ) -> None:
        cursor = self.conn.cursor()
        if subject_id:
            cursor.execute(
                "UPDATE Subjects SET cycle_id=%s, subject_name_fr=%s,"
                " subject_name_ar=%s, coefficient=%s, subject_lang=%s WHERE id=%s",
                (cycle_id, fr, ar, coef, lang, subject_id),
            )
        else:
            cursor.execute(
                "INSERT INTO Subjects"
                " (cycle_id, subject_name_fr, subject_name_ar, coefficient, subject_lang)"
                " VALUES (%s, %s, %s, %s, %s)",
                (cycle_id, fr, ar, coef, lang),
            )

    def delete_subject(self, subject_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Subjects WHERE id=%s", (subject_id,))

    # ── AssessmentTypes / AcademicPeriods ──────────────────

    def list_evaluations(self) -> list:
        """Return (id, cycle_name, period_name, name_fr, name_ar, type_code, weight)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT A.id, C.name_fr, P.period_name_fr, A.name_fr, A.name_ar,"
            "       A.type_code, A.weight_percentage"
            " FROM AssessmentTypes A"
            " JOIN AcademicPeriods P ON A.period_id = P.id"
            " JOIN Cycles C ON P.cycle_id = C.id"
            " ORDER BY C.id, P.sort_order"
        )
        return cursor.fetchall()

    def delete_evaluation(self, eval_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM AssessmentTypes WHERE id=%s", (eval_id,))

    def list_periods_for_year_cycle(self, year_id: int, cycle_id: int) -> list:
        """Return (id, period_name_fr, period_name_ar, sort_order, start_date, end_date)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, period_name_fr, period_name_ar, sort_order, start_date, end_date "
            "FROM AcademicPeriods WHERE year_id=%s AND cycle_id=%s "
            "ORDER BY sort_order, id",
            (year_id, cycle_id),
        )
        return cursor.fetchall()

    def update_period_dates(self, period_id: int, start_date_value: str, end_date_value: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE AcademicPeriods SET start_date=%s, end_date=%s WHERE id=%s",
            (start_date_value, end_date_value, period_id),
        )

    def _split_date_range(self, start: date, end: date, count: int) -> list[tuple[str, str]]:
        """Split an inclusive date range into `count` contiguous ranges."""
        total_days = (end - start).days + 1
        base_days = total_days // count
        remainder = total_days % count

        ranges: list[tuple[str, str]] = []
        cursor = start
        for i in range(count):
            chunk_days = base_days + (1 if i < remainder else 0)
            chunk_end = cursor + timedelta(days=chunk_days - 1)
            ranges.append((cursor.isoformat(), chunk_end.isoformat()))
            cursor = chunk_end + timedelta(days=1)
        return ranges

    def _get_year_date_range(self, year_id: int) -> tuple[str | None, str | None]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT start_date, end_date FROM AcademicYears WHERE id=%s", (year_id,))
        row = cursor.fetchone()
        if not row:
            return None, None
        start_date_value = row[0].isoformat() if hasattr(row[0], "isoformat") and row[0] else row[0]
        end_date_value = row[1].isoformat() if hasattr(row[1], "isoformat") and row[1] else row[1]
        return start_date_value, end_date_value

    def generate_periods_and_assessments(
        self,
        year_id: int,
        cycle_id: int,
        is_elementary: bool,
        year_start_date: str | None = None,
        year_end_date: str | None = None,
    ) -> None:
        """Delete existing periods/assessments for (year, cycle) then regenerate."""
        cursor = self.conn.cursor()

        if not year_start_date or not year_end_date:
            year_start_date, year_end_date = self._get_year_date_range(year_id)

        if year_start_date and year_end_date:
            start_obj = date.fromisoformat(str(year_start_date))
            end_obj = date.fromisoformat(str(year_end_date))
            if end_obj < start_obj:
                raise ValueError("La date de fin de l'année doit être >= la date de début.")
            period_ranges = self._split_date_range(start_obj, end_obj, 3 if is_elementary else 2)
        else:
            period_ranges = []

        cursor.execute(
            "DELETE FROM AssessmentTypes WHERE period_id IN"
            " (SELECT id FROM AcademicPeriods WHERE year_id=%s AND cycle_id=%s)",
            (year_id, cycle_id),
        )
        cursor.execute(
            "DELETE FROM AcademicPeriods WHERE year_id=%s AND cycle_id=%s",
            (year_id, cycle_id),
        )

        if is_elementary:
            periods = [
                ("Trimestre 1", "الفصل الأول"),
                ("Trimestre 2", "الفصل الثاني"),
                ("Trimestre 3", "الفصل الثالث"),
            ]
            for idx, (p_fr, p_ar) in enumerate(periods):
                start_date_value = period_ranges[idx][0] if len(period_ranges) > idx else None
                end_date_value = period_ranges[idx][1] if len(period_ranges) > idx else None
                cursor.execute(
                    "INSERT INTO AcademicPeriods"
                    " (year_id, cycle_id, period_name_fr, period_name_ar, sort_order, start_date, end_date)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (year_id, cycle_id, p_fr, p_ar, idx + 1, start_date_value, end_date_value),
                )
                period_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO AssessmentTypes"
                    " (period_id, name_fr, name_ar, type_code, weight_percentage)"
                    " VALUES (%s, 'Composition', 'اختبار فصلي', 'COMPO', 1.0)",
                    (period_id,),
                )
        else:
            periods = [
                ("Semestre 1", "السداسي الأول"),
                ("Semestre 2", "السداسي الثاني"),
            ]
            for idx, (p_fr, p_ar) in enumerate(periods):
                start_date_value = period_ranges[idx][0] if len(period_ranges) > idx else None
                end_date_value = period_ranges[idx][1] if len(period_ranges) > idx else None
                cursor.execute(
                    "INSERT INTO AcademicPeriods"
                    " (year_id, cycle_id, period_name_fr, period_name_ar, sort_order, start_date, end_date)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (year_id, cycle_id, p_fr, p_ar, idx + 1, start_date_value, end_date_value),
                )
                period_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO AssessmentTypes"
                    " (period_id, name_fr, name_ar, type_code, weight_percentage)"
                    " VALUES (%s, 'Devoir 1', 'الواجب 1', 'DEV', 1.0)",
                    (period_id,),
                )
                cursor.execute(
                    "INSERT INTO AssessmentTypes"
                    " (period_id, name_fr, name_ar, type_code, weight_percentage)"
                    " VALUES (%s, 'Devoir 2', 'الواجب 2', 'DEV', 1.0)",
                    (period_id,),
                )
                cursor.execute(
                    "INSERT INTO AssessmentTypes"
                    " (period_id, name_fr, name_ar, type_code, weight_percentage)"
                    " VALUES (%s, 'Composition', 'الاختبار', 'COMPO', 2.0)",
                    (period_id,),
                )
