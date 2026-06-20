"""One-shot database setup / bootstrap for El Malick Gest.

Brings a database to a complete, fully-constrained state. Safe to re-run.

Why this exists: the schema is created by db_schema.initialize_schema() while the
integrity constraints (CHECK on amounts, grade range, missing FKs, unique grade
key, performance indexes) live in Alembic migrations 006-010. A plain
``alembic upgrade head`` cannot build a clean database from scratch because the
early migrations assume tables that db_schema creates. This script does it in the
correct order:

    1. db_schema.initialize_schema()            -> all tables (idempotent)
    2. on a fresh DB: ``alembic stamp 004``     -> baseline whose tables/columns
       db_schema already provides
    3. ``alembic upgrade head``                 -> applies the idempotent
       constraint/index migrations (005-010)

Usage (after setting config.ini [DATABASE]):
    python setup_database.py
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from app_logger import AppLogger
from database_setup import DatabaseManager

# Migrations 001-004 create tables/columns that db_schema also creates; 005-010
# only add columns (idempotent) and constraints/indexes (idempotent). Stamping at
# 004 then upgrading lets every constraint migration run exactly once.
_DB_SCHEMA_BASELINE = "004"


def _current_alembic_version(db: DatabaseManager) -> str | None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None  # alembic_version table absent → fresh database


def setup_database() -> None:
    """Create the schema and bring Alembic to head. Idempotent."""
    db = DatabaseManager()
    db.initialize_database()  # tables via db_schema (CREATE TABLE IF NOT EXISTS)

    cfg = Config("alembic.ini")
    if _current_alembic_version(db) is None:
        # Fresh DB: db_schema already built the 001-004 tables — mark that baseline
        # so the constraint migrations (005-010) apply cleanly on top.
        command.stamp(cfg, _DB_SCHEMA_BASELINE)
    command.upgrade(cfg, "head")
    AppLogger.info("Setup", "Database setup complete — schema + migrations at head.")


if __name__ == "__main__":
    setup_database()
    print("Database setup complete (schema created, migrations at head).")
