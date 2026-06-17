"""Payment performance indexes (moved out of finance_payments runtime DDL).

These indexes were previously created lazily by finance_payments.init_db() at
UI startup. Schema/DDL belongs in migrations, so they are defined here and the
runtime DDL is removed. All idempotent (CREATE INDEX IF NOT EXISTS).

Revision ID: 010
Revises: 009
Create Date: 2026-06-17
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_student ON Payments(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON Payments(transaction_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_date ON Payments(student_id, transaction_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_dues_paid ON StudentDues(is_paid)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_student_dues_paid")
    op.execute("DROP INDEX IF EXISTS idx_payments_student_date")
    op.execute("DROP INDEX IF EXISTS idx_payments_date")
    op.execute("DROP INDEX IF EXISTS idx_payments_student")
