"""Grade integrity — score range CHECK + uniqueness on Grades.

Changes:
  1. CHECK (score >= 0 AND score <= 20) on Grades — the Senegalese system grades
     out of 20 (primary /10 values stay within range). Rejects negative or
     out-of-range scores at the database level (defence in depth: the UI spinbox
     is not the only entry path — imports and the API write here too).
  2. UNIQUE (student_id, subject_id, assessment_id, year_id) on Grades — enables
     an atomic ON CONFLICT upsert and prevents duplicate grades.

All operations are idempotent (check pg_constraint before adding).

NOTE: the UNIQUE constraint will fail to apply if duplicate grades already exist.
Resolve them first, e.g. keep the highest id per key:
    DELETE FROM Grades g USING Grades d
    WHERE g.student_id=d.student_id AND g.subject_id=d.subject_id
      AND g.assessment_id=d.assessment_id AND g.year_id IS NOT DISTINCT FROM d.year_id
      AND g.id < d.id;

Revision ID: 009
Revises: 008
Create Date: 2026-06-17
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Score range CHECK (0..20)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_grades_score_range'
            ) THEN
                ALTER TABLE Grades
                    ADD CONSTRAINT chk_grades_score_range
                    CHECK (score >= 0 AND score <= 20);
            END IF;
        END $$;
        """
    )

    # 2. Uniqueness on (student_id, subject_id, assessment_id, year_id)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_grades_student_subject_assessment_year'
            ) THEN
                ALTER TABLE Grades
                    ADD CONSTRAINT uq_grades_student_subject_assessment_year
                    UNIQUE (student_id, subject_id, assessment_id, year_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint
                       WHERE conname = 'uq_grades_student_subject_assessment_year') THEN
                ALTER TABLE Grades DROP CONSTRAINT uq_grades_student_subject_assessment_year;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_grades_score_range') THEN
                ALTER TABLE Grades DROP CONSTRAINT chk_grades_score_range;
            END IF;
        END $$;
        """
    )
