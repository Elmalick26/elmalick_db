"""AnalyticsRepository — طبقة الوصول لبيانات التقارير التحليلية."""
from __future__ import annotations


class AnalyticsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_active_year_context(self) -> tuple:
        """Return (year_id, year_label) for the current active academic year.
        Falls back to most-recent year; returns (None, 'N/A') if the table is empty.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, year_label FROM AcademicYears WHERE is_active=1 ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        cursor.execute(
            "SELECT id, year_label FROM AcademicYears ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, "N/A"

    def get_comprehensive_stats(self, year_id) -> dict:
        """Return summary counts needed for the comprehensive PDF report.

        Returns:
            dict with keys: active_students, total_classes, presents, absents, lates
        """
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
            "SELECT COUNT(*) FROM StudentAttendance WHERE status='Présent'"
            " AND (year_id=%s OR %s IS NULL)",
            (year_id, year_id),
        )
        presents = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE status='Absent'"
            " AND (year_id=%s OR %s IS NULL)",
            (year_id, year_id),
        )
        absents = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT COUNT(*) FROM StudentAttendance WHERE status='Retard'"
            " AND (year_id=%s OR %s IS NULL)",
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
