"""Performance indexes — pg_trgm text search + critical composite indexes.

Addresses T9.3 (text search strategy) and T10.1 (index application).

Changes:
  1. pg_trgm extension — enables fast ILIKE / % searches with GIN indexes
  2. GIN indexes on Students text columns (fixes 4-column ILIKE Seq Scan)
  3. Composite index on StudentClassNumbers(student_id, year_id, class_id)
  4. Composite index on Grades(student_id, year_id)
  5. Composite index on StudentAttendance(student_id, year_id)
  6. Composite index on StudentDues(student_id, year_id)

All operations are idempotent (DO $$ IF NOT EXISTS pattern).

Revision ID: 007
Revises: 006
Create Date: 2026-05-25
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helper — idempotent CREATE INDEX
# ---------------------------------------------------------------------------


def _create_index_if_not_exists(index_name: str, ddl: str) -> None:
    """Execute DDL only when the index does not already exist."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}'
            ) THEN
                {ddl};
            END IF;
        END$$;
        """
    )


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ── 1. pg_trgm extension ──────────────────────────────────────────────
    # Required for gin_trgm_ops operator class used by GIN indexes below.
    # ILIKE queries on text columns become index-scans instead of Seq Scans.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── 2. GIN indexes for Students text search (T9.3) ────────────────────
    # Fixes C1: list_students ILIKE on 4 columns — was a full Seq Scan.
    _create_index_if_not_exists(
        "idx_students_fn_fr_trgm",
        "CREATE INDEX idx_students_fn_fr_trgm " "ON Students USING GIN (first_name_fr gin_trgm_ops)",
    )
    _create_index_if_not_exists(
        "idx_students_ln_fr_trgm",
        "CREATE INDEX idx_students_ln_fr_trgm " "ON Students USING GIN (last_name_fr gin_trgm_ops)",
    )
    _create_index_if_not_exists(
        "idx_students_fn_ar_trgm",
        "CREATE INDEX idx_students_fn_ar_trgm " "ON Students USING GIN (first_name_ar gin_trgm_ops)",
    )
    _create_index_if_not_exists(
        "idx_students_ln_ar_trgm",
        "CREATE INDEX idx_students_ln_ar_trgm " "ON Students USING GIN (last_name_ar gin_trgm_ops)",
    )

    # ── 3. StudentClassNumbers composite index (C3) ───────────────────────
    # Used in every student list / grade / attendance query via LEFT JOIN.
    _create_index_if_not_exists(
        "idx_scn_student_year_class",
        "CREATE INDEX idx_scn_student_year_class " "ON StudentClassNumbers (student_id, year_id, class_id)",
    )

    # ── 4. Grades composite index (C4) ────────────────────────────────────
    _create_index_if_not_exists(
        "idx_grades_student_year",
        "CREATE INDEX idx_grades_student_year " "ON Grades (student_id, year_id)",
    )

    # ── 5. StudentAttendance composite index (C5) ─────────────────────────
    _create_index_if_not_exists(
        "idx_attendance_student_year",
        "CREATE INDEX idx_attendance_student_year " "ON StudentAttendance (student_id, year_id)",
    )

    # ── 6. StudentDues composite index (C6) ───────────────────────────────
    _create_index_if_not_exists(
        "idx_dues_student_year",
        "CREATE INDEX idx_dues_student_year " "ON StudentDues (student_id, year_id)",
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # Drop GIN indexes first (also dropped if extension CASCADE, but explicit is safer)
    op.execute("DROP INDEX IF EXISTS idx_students_fn_fr_trgm")
    op.execute("DROP INDEX IF EXISTS idx_students_ln_fr_trgm")
    op.execute("DROP INDEX IF EXISTS idx_students_fn_ar_trgm")
    op.execute("DROP INDEX IF EXISTS idx_students_ln_ar_trgm")

    # Drop composite indexes
    op.execute("DROP INDEX IF EXISTS idx_scn_student_year_class")
    op.execute("DROP INDEX IF EXISTS idx_grades_student_year")
    op.execute("DROP INDEX IF EXISTS idx_attendance_student_year")
    op.execute("DROP INDEX IF EXISTS idx_dues_student_year")

    # Remove pg_trgm extension (CASCADE drops any dependent objects)
    op.execute("DROP EXTENSION IF EXISTS pg_trgm CASCADE")
