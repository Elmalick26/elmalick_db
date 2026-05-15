"""Write the backward-compat shim for database_setup.py."""

shim = '''\
"""
database_setup.py -- Backward-compatibility shim.

All application code that does:
    from database_setup import DatabaseManager
    from database_setup import log_audit
continues to work unchanged.

Implementation lives in:
  - db_manager.py  (connection pool + context manager, ~130 lines)
  - db_schema.py   (DDL schema / migrations, ~900 lines)
"""

from db_manager import DatabaseManager  # noqa: F401
import logging

logger = logging.getLogger("DatabaseManager")


def log_audit(conn, actor: str, action: str, target: str) -> None:
    """Log an operation to AuditLogs. Call inside an open connection."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO AuditLogs (actor, action, target) VALUES (%s, %s, %s)",
            (str(actor)[:100], str(action)[:100], str(target)[:200]),
        )
    except Exception as e:
        import logging as _logging
        _logging.getLogger("DatabaseManager").warning(f"Audit log failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager()
    db.initialize_database()
'''

with open("database_setup.py", "w", encoding="utf-8") as f:
    f.write(shim)

print(f"database_setup.py rewritten: {len(shim.splitlines())} lines")
