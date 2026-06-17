"""Phase 5.2 / 5.4 / 6.3 — Parent portal columns + multi-school support.

Covers schema additions introduced in db_schema.py that were NOT present
in revisions 001-004:

  • Students.student_code    — unique identifier for parent portal
  • Students.parent_pin_hash — bcrypt PIN (replaces plain parent_pin)
  • Schools table            — school registry for multi-school support
  • school_id on Students, Staff, Classes, AcademicYears
  • Performance indexes for school_id

Revision ID: 005
Revises: 004
Create Date: 2026-05-25
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Students: student_code ──────────────────────────────────────────────
    op.execute(
        """
        ALTER TABLE Students
        ADD COLUMN IF NOT EXISTS student_code TEXT DEFAULT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_code
        ON Students(student_code)
        WHERE student_code IS NOT NULL
        """
    )

    # ── Students: parent_pin_hash ───────────────────────────────────────────
    op.execute(
        """
        ALTER TABLE Students
        ADD COLUMN IF NOT EXISTS parent_pin_hash TEXT DEFAULT NULL
        """
    )

    # ── Schools table ───────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS Schools (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        INSERT INTO Schools (id, name, code, is_active)
        VALUES (1, 'École Principale', 'MAIN', 1)
        ON CONFLICT (id) DO NOTHING
        """
    )

    # ── school_id on multi-entity tables ───────────────────────────────────
    for table in ("Students", "Staff", "Classes", "AcademicYears"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS school_id INTEGER DEFAULT 1")
        op.execute(f"UPDATE {table} SET school_id = 1 WHERE school_id IS NULL")

    # ── FK constraints school_id → Schools(id) ─────────────────────────────
    # صياغة conditional لتجنّب التكرار على بيئات موجودة
    for table, conname in (
        ("Students", "fk_students_school"),
        ("Staff", "fk_staff_school"),
        ("Classes", "fk_classes_school"),
        ("AcademicYears", "fk_academic_years_school"),
    ):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = '{conname}'
                ) THEN
                    ALTER TABLE {table}
                    ADD CONSTRAINT {conname}
                    FOREIGN KEY (school_id) REFERENCES Schools(id) ON DELETE RESTRICT;
                END IF;
            END$$;
            """
        )

    # ── Performance indexes ─────────────────────────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS idx_students_school ON Students(school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_staff_school    ON Staff(school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_classes_school  ON Classes(school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_years_school    ON AcademicYears(school_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_students_parent_pin
        ON Students(parent_pin)
        WHERE parent_pin IS NOT NULL
        """
    )


def downgrade() -> None:
    # إزالة الفهارس أولاً
    op.execute("DROP INDEX IF EXISTS idx_students_parent_pin")
    op.execute("DROP INDEX IF EXISTS idx_years_school")
    op.execute("DROP INDEX IF EXISTS idx_classes_school")
    op.execute("DROP INDEX IF EXISTS idx_staff_school")
    op.execute("DROP INDEX IF EXISTS idx_students_school")
    op.execute("DROP INDEX IF EXISTS idx_students_student_code")

    # إزالة FK constraints
    for table, conname in (
        ("AcademicYears", "fk_academic_years_school"),
        ("Classes", "fk_classes_school"),
        ("Staff", "fk_staff_school"),
        ("Students", "fk_students_school"),
    ):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {conname}")

    # إزالة school_id
    for table in ("AcademicYears", "Classes", "Staff", "Students"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS school_id")

    # إزالة Schools table
    op.execute("DROP TABLE IF EXISTS Schools")

    # إزالة أعمدة الطالب
    op.execute("ALTER TABLE Students DROP COLUMN IF EXISTS parent_pin_hash")
    op.execute("ALTER TABLE Students DROP COLUMN IF EXISTS student_code")
