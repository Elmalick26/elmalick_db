"""Financial data integrity — CHECK constraints on amount columns.

Adds CHECK (amount >= 0) to all monetary columns in:
  • Payments        — total_due, discount, amount_paid, remaining_balance
  • StudentDues     — original_amount, discount_amount, net_amount
  • Expenses        — amount
  • MonthlyPaymentsStatus — amount_paid

Uses conditional DO $$ blocks to be idempotent on existing databases.

Revision ID: 006
Revises: 005
Create Date: 2026-05-25
"""

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helper — conditional ADD CONSTRAINT (idempotent)
# ---------------------------------------------------------------------------


def _add_check(table: str, constraint: str, expression: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{constraint}' AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table}
                ADD CONSTRAINT {constraint} CHECK ({expression});
            END IF;
        END$$;
        """
    )


def upgrade() -> None:
    # ── Payments ───────────────────────────────────────────────────────────
    _add_check("Payments", "chk_payments_total_due_gte_0", "total_due >= 0")
    _add_check("Payments", "chk_payments_discount_gte_0", "discount >= 0")
    _add_check("Payments", "chk_payments_amount_paid_gte_0", "amount_paid >= 0")
    _add_check("Payments", "chk_payments_remaining_gte_0", "remaining_balance >= 0")

    # ── StudentDues ────────────────────────────────────────────────────────
    _add_check("StudentDues", "chk_dues_original_gte_0", "original_amount >= 0")
    _add_check("StudentDues", "chk_dues_discount_gte_0", "discount_amount >= 0")
    _add_check("StudentDues", "chk_dues_net_gte_0", "net_amount >= 0")

    # ── Expenses ───────────────────────────────────────────────────────────
    _add_check("Expenses", "chk_expenses_amount_gte_0", "amount >= 0")

    # ── MonthlyPaymentsStatus ──────────────────────────────────────────────
    _add_check("MonthlyPaymentsStatus", "chk_monthly_amount_paid_gte_0", "amount_paid >= 0")


def downgrade() -> None:
    for table, constraint in (
        ("MonthlyPaymentsStatus", "chk_monthly_amount_paid_gte_0"),
        ("Expenses", "chk_expenses_amount_gte_0"),
        ("StudentDues", "chk_dues_net_gte_0"),
        ("StudentDues", "chk_dues_discount_gte_0"),
        ("StudentDues", "chk_dues_original_gte_0"),
        ("Payments", "chk_payments_remaining_gte_0"),
        ("Payments", "chk_payments_amount_paid_gte_0"),
        ("Payments", "chk_payments_discount_gte_0"),
        ("Payments", "chk_payments_total_due_gte_0"),
    ):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}")
