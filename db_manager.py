"""
db_manager.py — DatabaseManager connection pool + context manager.

This is the extracted connection-management layer. The database schema
(DDL / migrations) lives in db_schema.py.

All existing code that does:
    from database_setup import DatabaseManager
still works because database_setup.py re-exports this class.
"""

import logging
import threading
import time as _time
from contextlib import contextmanager

import psycopg2  # noqa: F401
from psycopg2 import Error, OperationalError
from psycopg2 import pool as pg_pool

from config_manager import ConfigManager

logger = logging.getLogger("DatabaseManager")

# حدود مجمع الاتصالات — يمكن تعديلها من مكان واحد
_POOL_MIN_CONN: int = 2  # حد أدنى: عدد الاتصالات المفتوحة دائماً
_POOL_MAX_CONN: int = 10  # حد أقصى: عدد الاتصالات المتزامنة المسموح بها
_POOL_CONNECT_TIMEOUT: int = 10  # مهلة انتظار الاتصال بالثواني

# إعادة المحاولة عند انقطاع الاتصال (OperationalError فقط)
_RETRY_MAX: int = 3  # عدد المحاولات القصوى
_RETRY_BASE_DELAY: float = 0.5  # تأخير أساسي بالثواني (يتضاعف: 0.5 → 1 → 2)


class DatabaseManager:
    """
    Centralized database manager:
    1. PostgreSQL connection pool (ThreadedConnectionPool, minconn=2, maxconn=10).
    2. Context manager for safe connection acquisition / release.
    3. Schema initialization via db_schema.initialize_schema().
    """

    # ── Pool — class-level singleton ─────────────────────────────────────────
    _pool: "pg_pool.ThreadedConnectionPool | None" = None
    _pool_lock: threading.Lock = threading.Lock()

    def __init__(self):
        self.config = ConfigManager()
        self._conn = None

    # ── Pool management ───────────────────────────────────────────────────────

    @classmethod
    def _get_pool(cls) -> "pg_pool.ThreadedConnectionPool":
        """Return the shared pool, creating it lazily (thread-safe double-check)."""
        if cls._pool is None:
            with cls._pool_lock:
                if cls._pool is None:
                    config = ConfigManager()
                    cls._pool = pg_pool.ThreadedConnectionPool(
                        _POOL_MIN_CONN,
                        _POOL_MAX_CONN,
                        host=config.db_host,
                        port=config.db_port,
                        dbname=config.db_name,
                        user=config.db_user,
                        password=config.db_password,
                        sslmode=config.db_ssl_mode,
                        connect_timeout=_POOL_CONNECT_TIMEOUT,
                    )
                    logger.info(
                        f"Connection pool initialized: minconn={_POOL_MIN_CONN}, maxconn={_POOL_MAX_CONN} "
                        f"({config.db_host}:{config.db_port}/{config.db_name})"
                    )
        return cls._pool

    @classmethod
    def close_pool(cls) -> None:
        """Close all pool connections. Call once at application shutdown."""
        with cls._pool_lock:
            if cls._pool is not None:
                cls._pool.closeall()
                cls._pool = None
                logger.info("Connection pool closed.")

    @classmethod
    def reset_pool(cls) -> None:
        """Force-recreate the pool (after config change or reconnect)."""
        with cls._pool_lock:
            if cls._pool is not None:
                try:
                    cls._pool.closeall()
                except Exception:
                    pass
                cls._pool = None
        logger.info("Connection pool reset. Will be recreated on next use.")

    # ── Context Manager (with DatabaseManager() as db:) ──────────────────────

    def __enter__(self):
        self._conn = self._get_pool().getconn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
            self._get_pool().putconn(self._conn)
            self._conn = None

    def get_connection(self):
        """
        إرجاع الاتصال النشط بطريقتين:
        - داخل ``with DatabaseManager() as db:``  → يرجع الاتصال مباشرة
          مثال: ``conn = db.get_connection(); cursor = conn.cursor()``
        - خارج أي context manager → يرجع context manager جديد
          مثال: ``with db.get_connection() as conn: cursor = conn.cursor()``
        """
        if self._conn:
            return self._conn
        return self._connection_context()

    @contextmanager
    def _connection_context(self):
        """Acquire a pooled connection, yield it, then return it to the pool.

        OperationalError (network drop, server restart) → up to _RETRY_MAX retries
        with exponential back-off. Other DB errors are re-raised immediately.
        """
        conn = self._get_pool().getconn()
        attempt = 0
        try:
            while True:
                try:
                    yield conn
                    conn.commit()
                    break
                except OperationalError as e:
                    attempt += 1
                    try:
                        conn.rollback()
                    except Error:
                        pass
                    if attempt >= _RETRY_MAX:
                        logger.error(f"[E-DB-002] OperationalError after {attempt} attempt(s): {e}")
                        raise
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"[E-DB-002] OperationalError (attempt {attempt}/{_RETRY_MAX})," f" retry in {delay:.1f}s: {e}"
                    )
                    _time.sleep(delay)
                except Error as e:
                    logger.error(f"[E-DB-001] Database Error: {e}")
                    try:
                        conn.rollback()
                    except Error:
                        pass
                    raise
        finally:
            self._get_pool().putconn(conn)

    # ── Schema initialization ─────────────────────────────────────────────────

    def initialize_database(self) -> None:
        """Create / migrate all database tables by delegating to db_schema."""
        from db_schema import initialize_schema

        initialize_schema(self)
        self._check_migration_drift()

    # ── Migration Drift Check (T3.2) ─────────────────────────────────────────

    #: Dernière révision Alembic connue — mettre à jour après chaque nouveau fichier de version
    _LATEST_ALEMBIC_REVISION: str = "009"

    def _check_migration_drift(self) -> None:
        """Compare la révision Alembic en base avec la dernière révision connue.

        • En production  : avertissement CRITIQUE si dérive détectée.
        • En développement : avertissement informatif uniquement.
        • Si alembic_version n'existe pas encore : message d'information.
        """
        import os
        import sys

        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
                row = cur.fetchone()
        except Exception:
            logger.info(
                "[Migration] Table alembic_version absente — "
                "les migrations Alembic n'ont pas encore été appliquées. "
                "Exécutez : alembic upgrade head"
            )
            return

        db_revision: str = row[0].strip() if row else "(vide)"
        latest: str = self._LATEST_ALEMBIC_REVISION

        if db_revision == latest:
            logger.info(f"[Migration] ✅ Schema à jour (révision {db_revision})")
            return

        is_production = os.environ.get("ELMALICK_ENV", "development").lower() == "production" or getattr(
            sys, "frozen", False
        )

        msg = (
            f"[Migration] ⚠️  DÉRIVE DÉTECTÉE — "
            f"DB={db_revision} / attendu={latest}. "
            "Exécutez 'alembic upgrade head' avant de déployer."
        )
        if is_production:
            logger.critical(msg)
        else:
            logger.warning(msg)
