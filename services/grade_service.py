"""Grade and promotion business rules for El Malick Gest."""

from __future__ import annotations

import unicodedata

_PRIMARY_KEYS = ("elem", "prim", "ibtida")


def is_primary_cycle(cycle_name: str | None) -> bool:
    """Return True for a primary cycle (élémentaire / primaire / ابتدائي).

    Accent- and case-insensitive: 'Élémentaire' normalises to 'elementaire' so it
    matches 'elem'. Without this, the accented 'é' makes a plain substring check
    miss the cycle and fall back to the collège scale/formula.
    """
    if not cycle_name:
        return False
    stripped = unicodedata.normalize("NFKD", str(cycle_name))
    stripped = "".join(c for c in stripped if not unicodedata.combining(c)).lower()
    if any(k in stripped for k in _PRIMARY_KEYS):
        return True
    # Arabic form — match on the stem after the (variably-hamza'd) alef so
    # ابتدائي / إبتدائي / أبتدائي all qualify.
    return "بتدائ" in str(cycle_name)


def resolve_is_primary(is_primary_flag: bool | None, cycle_name: str | None) -> bool:
    """Authoritative primary/secondary decision for the grading scale.

    Prefer the explicit ``Cycles.is_primary`` flag (set from a fixed dropdown, so
    it cannot be mistyped). Fall back to the name heuristic only when the flag is
    NULL — i.e. legacy rows created before the column existed. This keeps the
    grading scale from depending on a free-text label.
    """
    if is_primary_flag is not None:
        return bool(is_primary_flag)
    return is_primary_cycle(cycle_name)


class GradeService:
    """Pure business rules for grade averages, promotion decisions, and next class selection."""

    @staticmethod
    def is_devoir_assessment(type_code: str | None, name: str | None) -> bool:
        """True if an assessment is a devoir (vs a composition)."""
        return "DEV" in str(type_code or "").upper() or "DEVOIR" in str(name or "").upper()

    def subject_average(self, devoir_scores: list[float], composition: float | None, is_primary: bool) -> float:
        """Canonical per-subject average — the single source of truth for both the
        bulletin and the year-end promotion decision.

        Primary (/10): composition only — devoirs are ignored.
        Collège/Lycée (/20): (mean(devoirs) + composition) / 2 when both exist;
            otherwise whichever part is available.
        """
        compo = None if composition is None else float(composition)
        if is_primary:
            return compo if compo is not None else 0.0
        devs = [float(d) for d in devoir_scores if d is not None]
        if devs and compo is not None:
            return (sum(devs) / len(devs) + compo) / 2
        if compo is not None:
            return compo
        if devs:
            return sum(devs) / len(devs)
        return 0.0

    def calculate_period_average(self, weighted_scores: list[tuple[float, float]]) -> float:
        total_points = 0.0
        total_coefficient = 0.0
        for score, coefficient in weighted_scores:
            if score is None:
                continue
            total_points += float(score) * float(coefficient)
            total_coefficient += float(coefficient)
        if total_coefficient <= 0:
            return 0.0
        return total_points / total_coefficient

    def calculate_annual_average(self, period_averages: list[float], fallback_average: float = 0.0) -> float:
        valid_averages = [float(avg) for avg in period_averages if avg is not None]
        if valid_averages:
            return sum(valid_averages) / len(valid_averages)
        return float(fallback_average)

    def get_promotion_threshold(self, cycle_name: str | None = None, *, is_primary: bool | None = None) -> float:
        """Pass mark for the cycle. Prefer the explicit ``is_primary`` flag; fall
        back to the cycle name when it is not supplied (legacy callers)."""
        primary = is_primary if is_primary is not None else is_primary_cycle(cycle_name)
        return 5.0 if primary else 10.0

    def get_promotion_decision(
        self, annual_average: float, cycle_name: str | None = None, *, is_primary: bool | None = None
    ) -> str:
        threshold = self.get_promotion_threshold(cycle_name, is_primary=is_primary)
        return "Admis" if float(annual_average) >= threshold else "Redouble"

    def get_honor_mention(self, average: float) -> str:
        """Return honour mention label based on average out of 20."""
        avg = float(average)
        if avg >= 18:
            return "Excellent / ممتاز"
        elif avg >= 16:
            return "Très Bien / جيد جداً"
        elif avg >= 14:
            return "Bien / جيد"
        elif avg >= 12:
            return "Assez Bien / مقبول"
        elif avg >= 10:
            return "Passable / ضعيف"
        else:
            return "Insuffisant / راسب"

    def calculate_rank(self, students: list[dict], key_name: str = "average") -> list[dict]:
        """Assign competition ranks (standard "1224" style) by ``key_name`` descending.

        Students with an equal value share the same rank (ex aequo); the next
        distinct value takes the rank corresponding to its position, so a tie at
        rank 2 is followed by rank 4. Comparison uses a small epsilon so values
        that are mathematically equal but differ by floating-point noise still tie.

        Mutates each dict by setting ``["rank"]`` and returns ``students`` sorted
        descending by ``key_name``.
        """
        students.sort(key=lambda s: s[key_name], reverse=True)
        prev_value: float | None = None
        prev_rank = 0
        for position, student in enumerate(students, start=1):
            value = float(student[key_name])
            if prev_value is not None and abs(value - prev_value) < 1e-9:
                student["rank"] = prev_rank
            else:
                student["rank"] = position
                prev_rank = position
                prev_value = value
        return students

    def get_next_class(
        self, class_map: dict, current_class_id: int, cycle_id: int, decision: str
    ) -> tuple[int | None, str]:
        current_class = class_map.get(current_class_id, {})
        current_name = current_class.get("name", "?")

        if decision != "Admis":
            return current_class_id, f"{current_name} (Redouble)"

        current_order = current_class.get("order", 0)
        for class_id, class_data in class_map.items():
            if class_data.get("cycle") == cycle_id and class_data.get("order") == current_order + 1:
                return class_id, class_data.get("name", "?")

        return None, "Fin de Cycle / Diplômé (تخرج)"
