"""Add optional timetable slot linkage for discipline incidents.

Revision ID: 004
Revises: 003
Create Date: 2026-05-24
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE StudentDiscipline
        ADD COLUMN IF NOT EXISTS timetable_slot_id INTEGER
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_student_discipline_timetable_slot'
            ) THEN
                ALTER TABLE StudentDiscipline
                ADD CONSTRAINT fk_student_discipline_timetable_slot
                FOREIGN KEY (timetable_slot_id) REFERENCES Timetable(id) ON DELETE SET NULL;
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_discipline_year_slot
        ON StudentDiscipline(year_id, timetable_slot_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_discipline_year_slot")
    op.execute("ALTER TABLE StudentDiscipline DROP CONSTRAINT IF EXISTS fk_student_discipline_timetable_slot")
    # Keep timetable_slot_id column for rollback safety.
