"""Explicit cycle type — is_primary flag on Cycles.

Why: the entire grading scale (/10 vs /20), the subject-average formula
(composition-only vs devoirs+composition) and the promotion threshold are
selected from the cycle. Until now that choice was inferred by string-matching
the cycle's free-text name (is_primary_cycle). A typo or an unexpected name
(e.g. "CP-CE1") silently mis-scales every calculation. This adds an explicit,
validated boolean so the type no longer depends on the label.

Changes:
  1. ADD COLUMN is_primary BOOLEAN on Cycles (nullable — NULL means "fall back to
     the name heuristic", for forward safety).
  2. Backfill existing rows from their current names, using the same patterns as
     services.grade_service.is_primary_cycle, so no existing cycle changes type.

Idempotent.

Revision ID: 011
Revises: 010
Create Date: 2026-06-21
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE Cycles ADD COLUMN IF NOT EXISTS is_primary BOOLEAN")
    # Backfill from current names (matches is_primary_cycle: elem/élém/prim/ibtida
    # in French, the 'بتدائ' stem in Arabic) so existing data keeps its type.
    op.execute(
        """
        UPDATE Cycles
        SET is_primary = (
            COALESCE(name_fr, '') ~* '(elem|élém|prim|ibtida)'
            OR COALESCE(name_ar, '') ~ 'بتدائ'
        )
        WHERE is_primary IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE Cycles DROP COLUMN IF EXISTS is_primary")
