"""Add missing FK constraint: StudentDiscipline.period_id → AcademicPeriods.

Changes:
  1. Add FK on StudentDiscipline.period_id referencing AcademicPeriods(id)
     with ON DELETE SET NULL (existing rows with no matching period remain intact).

All operations are idempotent (check pg_constraint before adding).

Revision ID: 008
Revises: 007
Create Date: 2026-06-06
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add period_id FK on StudentDiscipline only if not already present
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY'
                  AND table_name = 'studentdiscipline'
                  AND constraint_name = 'fk_studentdiscipline_period'
            ) THEN
                -- Ensure period_id column exists (schema-version guard)
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'studentdiscipline'
                      AND column_name = 'period_id'
                ) THEN
                    ALTER TABLE StudentDiscipline
                        ADD CONSTRAINT fk_studentdiscipline_period
                        FOREIGN KEY (period_id)
                        REFERENCES AcademicPeriods(id)
                        ON DELETE SET NULL;
                END IF;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_studentdiscipline_period'
            ) THEN
                ALTER TABLE StudentDiscipline
                    DROP CONSTRAINT fk_studentdiscipline_period;
            END IF;
        END $$;
        """
    )
