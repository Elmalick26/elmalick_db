"""
Alembic environment configuration for El Malick Gest.
Reads database connection from ConfigManager (config.ini / keyring).
Migrations use raw SQL via op.execute() — no SQLAlchemy ORM models needed.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── اجعل جذر المشروع متاحاً في sys.path ──────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import ConfigManager  # noqa: E402

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# ── Logging setup ─────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── لا يوجد metadata في هذا المشروع (raw SQL فقط) ───────────────────────────
target_metadata = None


def get_url() -> str:
    """بناء DSN من ConfigManager — يقرأ كلمة المرور من keyring تلقائياً."""
    cfg = ConfigManager()
    user = cfg.db_user
    password = cfg.db_password or ""
    host = cfg.db_host
    port = cfg.db_port
    dbname = cfg.db_name
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def run_migrations_offline() -> None:
    """
    وضع Offline: لا يتطلب اتصالاً حقيقياً.
    مفيد لتوليد SQL scripts للمراجعة دون تطبيق.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    وضع Online: يتصل بقاعدة البيانات ويطبق migrations مباشرة.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
