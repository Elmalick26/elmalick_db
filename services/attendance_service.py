"""Attendance business rules for El Malick Gest — Phase 6."""

from __future__ import annotations
from datetime import date


class AttendanceService:
    """Pure business rules for attendance analysis and statistics."""

    # ── Constants ─────────────────────────────────────────────────────
    ALERT_THRESHOLD_PCT = 20.0  # % غياب يُطلق تنبيهاً
    MAX_ABSENCES_FOR_WARNING = 3  # أيام غياب متتالية قبل التحذير

    # ── Core Stats ────────────────────────────────────────────────────
    def calculate_stats(self, records: list[dict]) -> dict:
        """
        records: list of dicts with 'status' key (Present/Absent/Late/Justifié).
        Returns: dict with total, present, absent, late, justified, absence_rate_pct.
        """
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
                "justified": 0,
                "absence_rate_pct": 0.0,
            }

        present = sum(1 for r in records if r.get("status") == "Present")
        absent = sum(1 for r in records if r.get("status") == "Absent")
        late = sum(1 for r in records if r.get("status") == "Late")
        justified = sum(1 for r in records if r.get("status") == "Justifié")

        absence_rate = (absent / total) * 100

        return {
            "total": total,
            "present": present,
            "absent": absent,
            "late": late,
            "justified": justified,
            "absence_rate_pct": round(absence_rate, 2),
        }

    def get_attendance_status(self, absence_rate_pct: float) -> str:
        """Return status label based on absence rate."""
        if absence_rate_pct >= 30:
            return "Critique"
        if absence_rate_pct >= 20:
            return "Avertissement"
        if absence_rate_pct >= 10:
            return "Attention"
        return "Normal"

    def is_at_risk(self, absence_rate_pct: float) -> bool:
        return absence_rate_pct >= self.ALERT_THRESHOLD_PCT

    # ── Consecutive Absences ──────────────────────────────────────────
    def count_consecutive_absences(self, records: list[dict]) -> int:
        """
        records: list of dicts sorted by date ASC with 'date' and 'status' keys.
        Returns: current streak of consecutive absences (from the end of the list).
        """
        streak = 0
        for record in reversed(records):
            if record.get("status") == "Absent":
                streak += 1
            else:
                break
        return streak

    def get_absence_periods(self, records: list[dict]) -> list[dict]:
        """
        Returns list of absence periods: {start, end, days}.
        Records must be sorted by date.
        """
        periods: list[dict] = []
        current_start: date | None = None
        current_count = 0

        for record in records:
            rec_date = record.get("date")
            if isinstance(rec_date, str):
                try:
                    rec_date = date.fromisoformat(rec_date)
                except ValueError:
                    continue

            if record.get("status") == "Absent":
                if current_start is None:
                    current_start = rec_date
                current_count += 1
            else:
                if current_start is not None:
                    periods.append(
                        {
                            "start": current_start,
                            "end": rec_date,
                            "days": current_count,
                        }
                    )
                    current_start = None
                    current_count = 0

        # Close any open period
        if current_start is not None:
            periods.append(
                {
                    "start": current_start,
                    "end": current_start,
                    "days": current_count,
                }
            )

        return periods

    # ── Class Attendance Rate ─────────────────────────────────────────
    def calculate_class_daily_rate(self, student_records: list[dict]) -> float:
        """
        student_records: list of dicts with 'status' (for one day, all students in class).
        Returns: present percentage for that day.
        """
        if not student_records:
            return 0.0
        present = sum(1 for r in student_records if r.get("status") == "Present")
        return round((present / len(student_records)) * 100, 2)

    # ── Period Summary ────────────────────────────────────────────────
    def summarize_by_month(self, records: list[dict]) -> dict[str, dict]:
        """
        Returns dict keyed by 'YYYY-MM' with stats per month.
        """
        monthly: dict[str, list] = {}
        for record in records:
            rec_date = record.get("date", "")
            if isinstance(rec_date, date):
                key = rec_date.strftime("%Y-%m")
            elif isinstance(rec_date, str) and len(rec_date) >= 7:
                key = rec_date[:7]
            else:
                continue
            monthly.setdefault(key, []).append(record)

        return {month: self.calculate_stats(recs) for month, recs in sorted(monthly.items())}

    # ── Alert Messages ────────────────────────────────────────────────
    def get_alert_message(self, student_name: str, stats: dict) -> str | None:
        """Returns alert message if student is at risk, else None."""
        rate = stats.get("absence_rate_pct", 0.0)
        absent = stats.get("absent", 0)
        if rate >= 30:
            return f"🔴 {student_name} — Taux d'absence critique: {rate:.1f}% ({absent} jours)"
        if rate >= 20:
            return f"🟠 {student_name} — Taux d'absence élevé: {rate:.1f}% ({absent} jours)"
        return None
