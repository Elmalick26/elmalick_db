"""AnalyticsRepository — طبقة الوصول لبيانات التقارير التحليلية."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class AnalyticsRepository:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    # ── Year context ───────────────────────────────────────────────────────────

    def get_active_year_context(self) -> tuple:
        """Return (year_id, year_label) for the current active academic year."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, year_label FROM AcademicYears WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        cursor.execute("SELECT id, year_label FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, "N/A"

    # ── Schema introspection ──────────────────────────────────────────────────

    def get_student_columns(self) -> set:
        """Return the set of column names (lowercase) for the Students table."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'students'")
        return {row[0].lower() for row in cursor.fetchall()}

    # ── Class helpers ─────────────────────────────────────────────────────────

    def get_class_max_score(self, class_id: int) -> int:
        """Return 10 for primary/elementary cycles, 20 otherwise."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(CY.name_fr, '')
            FROM Classes CL
            LEFT JOIN Cycles CY ON CL.cycle_id = CY.id
            WHERE CL.id = %s
            """,
            (class_id,),
        )
        row = cursor.fetchone()
        cycle_name = (row[0] or "").lower() if row else ""
        return 10 if ("elem" in cycle_name or "prim" in cycle_name) else 20

    # ── Attendance ────────────────────────────────────────────────────────────

    def get_attendance_summary_by_class(self, year_id) -> list:
        """(class_name_fr, students_count, presents, absents, lates, attendance_rows)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT C.class_name_fr,
                   COUNT(DISTINCT S.id) AS students_count,
                   SUM(CASE WHEN SA.status='Présent' THEN 1 ELSE 0 END) AS presents,
                   SUM(CASE WHEN SA.status='Absent'  THEN 1 ELSE 0 END) AS absents,
                   SUM(CASE WHEN SA.status='Retard'  THEN 1 ELSE 0 END) AS lates,
                   COUNT(SA.id) AS attendance_rows
            FROM Classes C
            LEFT JOIN StudentClassNumbers SCN ON SCN.class_id = C.id AND SCN.year_id = %s
            LEFT JOIN Students S ON S.id = SCN.student_id AND S.status='Active'
            LEFT JOIN StudentAttendance SA ON SA.student_id = S.id AND SA.year_id = %s
            GROUP BY C.id, C.class_name_fr
            ORDER BY C.sort_order, C.class_name_fr
            """,
            (year_id, year_id),
        )
        return cursor.fetchall()

    # ── Grades ────────────────────────────────────────────────────────────────

    def get_grades_summary_by_class(self, year_id) -> list:
        """(class_name_fr, students_count, grades_count, min, avg, max)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT C.class_name_fr,
                   COUNT(DISTINCT S.id) AS students_count,
                   COUNT(G.id) AS grades_count,
                   MIN(G.score) AS min_score,
                   AVG(G.score) AS avg_score,
                   MAX(G.score) AS max_score
            FROM Classes C
            LEFT JOIN StudentClassNumbers SCN ON SCN.class_id = C.id AND SCN.year_id = %s
            LEFT JOIN Students S ON S.id = SCN.student_id AND S.status='Active'
            LEFT JOIN Grades G ON G.student_id = S.id AND G.score IS NOT NULL AND G.year_id = %s
            GROUP BY C.id, C.class_name_fr
            ORDER BY C.sort_order, C.class_name_fr
            """,
            (year_id, year_id),
        )
        return cursor.fetchall()

    def get_grades_for_class(self, class_id: int, year_id) -> list:
        """Return [score, ...] for all students in a class for the given year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT g.score
            FROM Grades g
            JOIN Students s ON g.student_id = s.id
            JOIN StudentClassNumbers scn ON scn.student_id = s.id AND scn.year_id = %s
            WHERE scn.class_id = %s AND g.score IS NOT NULL AND g.year_id = %s
            """,
            (year_id, class_id, year_id),
        )
        return [row[0] for row in cursor.fetchall()]

    # ── Financial monthly totals ──────────────────────────────────────────────

    @staticmethod
    def _build_period_filter(period: str, date_col: str) -> tuple[str, list]:
        """Return (filter_sql, params) for the given period string."""
        f = f"{date_col} IS NOT NULL"
        params: list = []
        if period == "6 derniers mois":
            f += f" AND CAST({date_col} AS DATE) >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months'"
        elif period == "12 derniers mois":
            f += f" AND CAST({date_col} AS DATE) >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '11 months'"
        elif period == "Année en cours":
            f += f" AND TO_CHAR(CAST({date_col} AS TIMESTAMP), 'YYYY') = %s"
            params.append(datetime.now().strftime('%Y'))
        return f, params

    def get_monthly_income_totals(self, period: str) -> list:
        """(month_str, count, total) ordered by month."""
        f, params = self._build_period_filter(period, "transaction_date")
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT TO_CHAR(CAST(transaction_date AS TIMESTAMP), 'YYYY-MM') AS month,
                   COUNT(*) AS count,
                   SUM(amount_paid) AS total
            FROM Payments
            WHERE {f}
            GROUP BY month ORDER BY month
            """,
            params,
        )
        return cursor.fetchall()

    def get_monthly_expense_totals(self, period: str) -> list:
        """(month_str, count, total) ordered by month."""
        f, params = self._build_period_filter(period, "expense_date")
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT TO_CHAR(CAST(expense_date AS TIMESTAMP), 'YYYY-MM') AS month,
                   COUNT(*) AS count,
                   SUM(amount) AS total
            FROM Expenses
            WHERE {f}
            GROUP BY month ORDER BY month
            """,
            params,
        )
        return cursor.fetchall()

    def get_total_income_by_period(self, period: str) -> float:
        """Return aggregate income for the given period."""
        f, params = self._build_period_filter(period, "transaction_date")
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COALESCE(SUM(amount_paid), 0) FROM Payments WHERE {f}", params)
        return float(cursor.fetchone()[0] or 0)

    def get_total_expense_by_period(self, period: str) -> float:
        """Return aggregate expenses for the given period."""
        f, params = self._build_period_filter(period, "expense_date")
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COALESCE(SUM(amount), 0) FROM Expenses WHERE {f}", params)
        return float(cursor.fetchone()[0] or 0)

    # ── Comprehensive stats ───────────────────────────────────────────────────

    def get_comprehensive_stats(self, year_id) -> dict:
        """Return summary counts needed for the comprehensive PDF report."""
        cursor = self.conn.cursor()

        if year_id:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT S.id)
                FROM Students S
                JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
                WHERE S.status = 'Active' AND SCN.year_id = %s
                """,
                (year_id,),
            )
            active_students = int(cursor.fetchone()[0] or 0)
        else:
            active_students = 0

        cursor.execute("SELECT COUNT(*) FROM Classes")
        total_classes = int(cursor.fetchone()[0] or 0)

        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE status='Présent'" " AND (year_id=%s OR %s IS NULL)",
            (year_id, year_id),
        )
        presents = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE status='Absent'" " AND (year_id=%s OR %s IS NULL)",
            (year_id, year_id),
        )
        absents = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE status='Retard'" " AND (year_id=%s OR %s IS NULL)",
            (year_id, year_id),
        )
        lates = int(cursor.fetchone()[0] or 0)

        return {
            "active_students": active_students,
            "total_classes": total_classes,
            "presents": presents,
            "absents": absents,
            "lates": lates,
        }

    # ── Dashboard filter queries ──────────────────────────────────────────────

    def get_academic_years(self) -> list:
        """Return all academic years ordered by id DESC: list of (id, label, is_active)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, year_label, is_active FROM AcademicYears ORDER BY id DESC")
        return cursor.fetchall()

    def get_classes_for_year(self, year_id: int) -> list:
        """Return distinct classes that have students for the given year: list of (id, name_fr)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT C.id, C.class_name_fr
            FROM Classes C
            JOIN StudentClassNumbers SCN ON SCN.class_id = C.id AND SCN.year_id = %s
            ORDER BY C.class_name_fr
            """,
            (year_id,),
        )
        return cursor.fetchall()

    def get_grades_by_subject(self, year_id: int, class_id=None) -> list:
        """Return per-subject grade averages for a year, optionally filtered by class.

        Returns list of (subject_name_fr, avg_score, coefficient, max_score).
        """
        cursor = self.conn.cursor()
        sql = """
            SELECT SB.subject_name_fr,
                   AVG(G.score)       AS avg_score,
                   SB.coefficient,
                   MAX(CASE WHEN LOWER(CY.name_fr) SIMILAR TO '%%(elem|prim|ibtida)%%'
                            THEN 10.0 ELSE 20.0 END) AS max_score
            FROM Grades G
            JOIN Subjects SB    ON G.subject_id = SB.id
            JOIN AssessmentTypes AT ON G.assessment_id = AT.id
            JOIN StudentClassNumbers SCN ON G.student_id = SCN.student_id
                                       AND SCN.year_id   = G.year_id
            JOIN Classes CL     ON SCN.class_id = CL.id
            JOIN Cycles CY      ON CL.cycle_id  = CY.id
            WHERE G.year_id = %s
        """
        params = [year_id]
        if class_id:
            sql += " AND SCN.class_id = %s"
            params.append(class_id)
        sql += " GROUP BY SB.id, SB.subject_name_fr, SB.coefficient ORDER BY avg_score DESC"
        cursor.execute(sql, params)
        return cursor.fetchall()

    def get_monthly_attendance_rate(self, year_id: int, class_id=None) -> list:
        """Return monthly attendance data for a year, optionally filtered by class.

        Returns list of (month_str, total, present_count).
        """
        cursor = self.conn.cursor()
        sql = """
            SELECT TO_CHAR(SA.date, 'YYYY-MM') AS month,
                   COUNT(*)                                    AS total,
                   COUNT(*) FILTER (WHERE SA.status = 'Present') AS present
            FROM StudentAttendance SA
            JOIN StudentClassNumbers SCN ON SA.student_id = SCN.student_id
                                       AND SCN.year_id = SA.year_id
            WHERE SA.year_id = %s
        """
        params = [year_id]
        if class_id:
            sql += " AND SCN.class_id = %s"
            params.append(class_id)
        sql += " GROUP BY month ORDER BY month"
        cursor.execute(sql, params)
        return cursor.fetchall()

    def get_finance_summary(self, year_id: int, class_id=None) -> tuple:
        """Return (total_paid, total_due) for a year, optionally filtered by class."""
        cursor = self.conn.cursor()
        sql_due = """
            SELECT COALESCE(SUM(net_amount), 0)
            FROM StudentDues
            WHERE year_id = %s
        """
        params_due = [year_id]
        if class_id:
            sql_due += """
                AND student_id IN (
                    SELECT student_id FROM StudentClassNumbers
                    WHERE year_id = %s AND class_id = %s
                )
            """
            params_due.extend([year_id, class_id])
        cursor.execute(sql_due, params_due)
        total_due = float(cursor.fetchone()[0] or 0)

        sql_paid = """
            SELECT COALESCE(SUM(P.amount_paid), 0)
            FROM Payments P
            WHERE P.year_id = %s
        """
        params_paid = [year_id]
        if class_id:
            sql_paid += (
                " AND P.student_id IN (SELECT student_id FROM StudentClassNumbers WHERE year_id=%s AND class_id=%s)"
            )
            params_paid.extend([year_id, class_id])
        cursor.execute(sql_paid, params_paid)
        total_paid = float(cursor.fetchone()[0] or 0)

        return total_paid, total_due
