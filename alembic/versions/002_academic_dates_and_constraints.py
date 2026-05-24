"""Add academic date columns and integrity constraints.

Revision ID: 002
Revises: 001
Create Date: 2026-05-24

Safe migration for existing databases:
- Adds AcademicYears.start_date/end_date when missing.
- Adds AcademicPeriods.start_date/end_date when missing.
- Adds check constraints to guarantee start_date <= end_date.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns if they do not exist
    op.execute(
        """
        ALTER TABLE AcademicYears
        ADD COLUMN IF NOT EXISTS start_date DATE
        """
    )
    op.execute(
        """
        ALTER TABLE AcademicYears
        ADD COLUMN IF NOT EXISTS end_date DATE
        """
    )
    op.execute(
        """
        ALTER TABLE AcademicPeriods
        ADD COLUMN IF NOT EXISTS start_date DATE
        """
    )
    op.execute(
        """
        ALTER TABLE AcademicPeriods
        ADD COLUMN IF NOT EXISTS end_date DATE
        """
    )

    # Add constraints if they do not exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_academic_year_dates'
            ) THEN
                ALTER TABLE AcademicYears
                ADD CONSTRAINT ck_academic_year_dates
                CHECK (start_date IS NULL OR end_date IS NULL OR start_date <= end_date);
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_academic_period_dates'
            ) THEN
                ALTER TABLE AcademicPeriods
                ADD CONSTRAINT ck_academic_period_dates
                CHECK (start_date IS NULL OR end_date IS NULL OR start_date <= end_date);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Drop constraints first
    op.execute("ALTER TABLE AcademicPeriods DROP CONSTRAINT IF EXISTS ck_academic_period_dates")
    op.execute("ALTER TABLE AcademicYears DROP CONSTRAINT IF EXISTS ck_academic_year_dates")

    # Keep columns for compatibility/history safety. If you want full rollback,
    # uncomment the following lines in a controlled environment:
    # op.execute("ALTER TABLE AcademicPeriods DROP COLUMN IF EXISTS end_date")
    # op.execute("ALTER TABLE AcademicPeriods DROP COLUMN IF EXISTS start_date")
    # op.execute("ALTER TABLE AcademicYears DROP COLUMN IF EXISTS end_date")
    # op.execute("ALTER TABLE AcademicYears DROP COLUMN IF EXISTS start_date")
