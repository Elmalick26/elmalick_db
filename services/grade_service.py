"""Grade and promotion business rules for El Malick Gest."""

from __future__ import annotations


class GradeService:
    """Pure business rules for grade averages, promotion decisions, and next class selection."""

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

    def get_promotion_threshold(self, cycle_name: str | None) -> float:
        cycle_lower = (cycle_name or "").lower()
        if "elem" in cycle_lower or "prim" in cycle_lower or "ibtida" in cycle_lower:
            return 5.0
        return 10.0

    def get_promotion_decision(self, annual_average: float, cycle_name: str | None) -> str:
        threshold = self.get_promotion_threshold(cycle_name)
        return "Admis" if float(annual_average) >= threshold else "Redouble"

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
