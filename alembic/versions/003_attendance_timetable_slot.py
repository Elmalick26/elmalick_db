"""Add slot-level attendance linkage.

Revision ID: 003
Revises: 002
Create Date: 2026-05-24

Adds an optional timetable slot reference to StudentAttendance so the same
student can be tracked across multiple lessons on the same day.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE StudentAttendance
        ADD COLUMN IF NOT EXISTS timetable_slot_id INTEGER
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_student_attendance_timetable_slot'
            ) THEN
                ALTER TABLE StudentAttendance
                ADD CONSTRAINT fk_student_attendance_timetable_slot
                FOREIGN KEY (timetable_slot_id) REFERENCES Timetable(id) ON DELETE SET NULL;
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attendance_year_slot
        ON StudentAttendance(year_id, timetable_slot_id)
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_attendance_student_date_slot
        ON StudentAttendance(student_id, date, year_id, timetable_slot_id)
        WHERE timetable_slot_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_attendance_student_date_slot")
    op.execute("DROP INDEX IF EXISTS idx_attendance_year_slot")
    op.execute("ALTER TABLE StudentAttendance DROP CONSTRAINT IF EXISTS fk_student_attendance_timetable_slot")
    # Keep timetable_slot_id for rollback safety/history compatibility.
