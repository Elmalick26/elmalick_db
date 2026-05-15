"""Finance business rules for El Malick Gest.

Pure logic — no DB access, no UI imports.
All inputs are plain Python values (float, date, str).
"""

from __future__ import annotations

from datetime import date


class FinanceService:
    """Pure business rules for payments, dues, and collection rates."""

    # ── Payment status constants ─────────────────────────────────────
    STATUS_PAID = "Payé"
    STATUS_PARTIAL = "Partiel"
    STATUS_OVERDUE = "En Retard"
    STATUS_UPCOMING = "À Venir"

    # ── Debt ─────────────────────────────────────────────────────────

    def calculate_debt(self, due_amount: float, total_paid: float) -> float:
        """Remaining debt for a single due (never negative)."""
        return max(0.0, float(due_amount) - float(total_paid))

    def calculate_total_debt(self, dues: list[dict]) -> float:
        """
        Total unpaid debt across a list of dues.
        Each dict must have: 'net_amount' and 'total_paid'.
        """
        total = 0.0
        for d in dues:
            total += self.calculate_debt(d.get("net_amount", 0), d.get("total_paid", 0))
        return round(total, 2)

    # ── Payment status ───────────────────────────────────────────────

    def get_payment_status(
        self,
        due_amount: float,
        total_paid: float,
        due_date: date | None = None,
        as_of: date | None = None,
    ) -> str:
        """
        Return human-readable status for a single due.
        - "Payé"      → total_paid >= due_amount
        - "Partiel"   → 0 < total_paid < due_amount
        - "En Retard" → nothing paid and due_date has passed
        - "À Venir"   → nothing paid and due_date is in the future (or unknown)
        """
        due_amount = float(due_amount)
        total_paid = float(total_paid)
        debt = self.calculate_debt(due_amount, total_paid)

        if debt <= 0:
            return self.STATUS_PAID

        if total_paid > 0:
            return self.STATUS_PARTIAL

        today = as_of or date.today()
        if due_date and isinstance(due_date, date) and due_date < today:
            return self.STATUS_OVERDUE

        return self.STATUS_UPCOMING

    def is_overdue(
        self,
        due_amount: float,
        total_paid: float,
        due_date: date | None,
        as_of: date | None = None,
    ) -> bool:
        """True if the due is not fully paid and the due_date has passed."""
        return self.get_payment_status(due_amount, total_paid, due_date, as_of) == self.STATUS_OVERDUE

    # ── Collection rate ──────────────────────────────────────────────

    def calculate_collection_rate(self, total_due: float, total_collected: float) -> float:
        """
        Return collection rate as a percentage (0–100).
        Returns 100.0 if total_due is zero (nothing owed → fully collected).
        """
        total_due = float(total_due)
        total_collected = float(total_collected)
        if total_due <= 0:
            return 100.0
        rate = (total_collected / total_due) * 100.0
        return round(min(rate, 100.0), 2)

    def get_collection_status(self, rate: float) -> str:
        """Human label for a collection rate percentage."""
        if rate >= 90:
            return "Excellent"
        if rate >= 70:
            return "Bon"
        if rate >= 50:
            return "Moyen"
        return "Insuffisant"

    # ── Aggregates ───────────────────────────────────────────────────

    def summarize_dues(self, dues: list[dict]) -> dict:
        """
        Aggregate summary for a list of dues.
        Each dict: 'net_amount', 'total_paid', 'due_date' (date | None).

        Returns:
            total_due       — sum of net_amount
            total_paid      — sum of total_paid
            total_debt      — remaining unpaid amount
            collection_rate — percentage paid
            overdue_count   — number of overdue dues
            paid_count      — number of fully-paid dues
            partial_count   — number of partially-paid dues
        """
        today = date.today()
        total_due = 0.0
        total_paid = 0.0
        overdue_count = 0
        paid_count = 0
        partial_count = 0

        for d in dues:
            net = float(d.get("net_amount", 0))
            paid = float(d.get("total_paid", 0))
            dd = d.get("due_date")
            total_due += net
            total_paid += paid
            status = self.get_payment_status(net, paid, dd, today)
            if status == self.STATUS_PAID:
                paid_count += 1
            elif status == self.STATUS_PARTIAL:
                partial_count += 1
            elif status == self.STATUS_OVERDUE:
                overdue_count += 1

        total_debt = max(0.0, total_due - total_paid)
        collection_rate = self.calculate_collection_rate(total_due, total_paid)

        return {
            "total_due": round(total_due, 2),
            "total_paid": round(total_paid, 2),
            "total_debt": round(total_debt, 2),
            "collection_rate": collection_rate,
            "overdue_count": overdue_count,
            "paid_count": paid_count,
            "partial_count": partial_count,
        }

    # ── Receipt helpers ──────────────────────────────────────────────

    def format_amount(self, amount: float, currency: str = "FCFA") -> str:
        """Format a monetary amount with thousands separator."""
        try:
            return f"{float(amount):,.0f} {currency}"
        except (ValueError, TypeError):
            return f"0 {currency}"

    def calculate_change(self, amount_paid: float, amount_due: float) -> float:
        """Return change (overpayment). Negative means still owes."""
        return round(float(amount_paid) - float(amount_due), 2)

    # ── Validation ───────────────────────────────────────────────────

    def validate_payment_amount(
        self,
        amount: float,
        remaining_debt: float,
        allow_overpay: bool = False,
    ) -> list[str]:
        """
        Returns list of error strings (empty = valid).
        - amount must be > 0
        - amount must not exceed remaining_debt (unless allow_overpay=True)
        """
        errors: list[str] = []
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return ["المبلغ يجب أن يكون رقماً / Le montant doit être un nombre"]

        if amount <= 0:
            errors.append("المبلغ يجب أن يكون أكبر من صفر / Le montant doit être supérieur à zéro")

        if not allow_overpay and amount > float(remaining_debt) * 1.005:  # 0.5% rounding tolerance
            errors.append(
                f"المبلغ المدفوع ({amount:,.0f}) يتجاوز الدين المتبقي ({remaining_debt:,.0f}) "
                f"/ Montant ({amount:,.0f}) supérieur à la dette ({remaining_debt:,.0f})"
            )
        return errors
