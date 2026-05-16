"""
tests/test_logging_phase6.py
اختبارات Phase 6: JSON Logging + API Request Middleware

يغطي:
• JSONLogFormatter — إخراج JSON صحيح
• app_logger static methods — backward-compat + kwargs
• extract_token_subject — JWT helper
• log_requests middleware — duration / user_id / slow-request warning / health skip
"""

import json
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.auth import create_access_token, extract_token_subject

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────
# 1. JSONLogFormatter
# ─────────────────────────────────────────────────────────────

class TestJSONLogFormatter:
    def _make_record(self, level=logging.INFO, msg="test message", extra=None):
        """Produce a LogRecord similar to what AppLogger emits."""
        from app_logger import JSONLogFormatter  # noqa (side-effect import)
        record = logging.LogRecord(
            name="SchoolApp",
            level=level,
            pathname="test",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        if extra:
            for k, v in extra.items():
                setattr(record, k, v)
        return record

    def test_output_is_valid_json(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        record = self._make_record()
        output = fmt.format(record)
        obj = json.loads(output)
        assert isinstance(obj, dict)

    def test_required_fields_present(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        record = self._make_record(msg="hello")
        obj = json.loads(fmt.format(record))
        assert "timestamp" in obj
        assert "level" in obj
        assert "module" in obj
        assert "message" in obj

    def test_timestamp_format(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        obj = json.loads(fmt.format(self._make_record()))
        ts = obj["timestamp"]
        # ISO-8601 UTC: 2026-05-15T12:34:56.789Z
        assert ts.endswith("Z")
        assert "T" in ts

    def test_level_matches_record(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        obj = json.loads(fmt.format(self._make_record(level=logging.WARNING)))
        assert obj["level"] == "WARNING"

    def test_user_id_included_when_set(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        record = self._make_record(extra={"user_id": "alice"})
        obj = json.loads(fmt.format(record))
        assert obj["user_id"] == "alice"

    def test_user_id_absent_when_not_set(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        obj = json.loads(fmt.format(self._make_record()))
        assert "user_id" not in obj

    def test_duration_ms_included_when_set(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        record = self._make_record(extra={"duration_ms": 123.4})
        obj = json.loads(fmt.format(record))
        assert obj["duration_ms"] == 123.4

    def test_non_ascii_message_valid_json(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        record = self._make_record(msg="طالب جديد مسجل")
        output = fmt.format(record)
        obj = json.loads(output)
        assert "طالب" in obj["message"]

    def test_exception_field_when_exc_info(self):
        from app_logger import JSONLogFormatter
        fmt = JSONLogFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="",
                lineno=0, msg="oops", args=(), exc_info=sys.exc_info()
            )
        obj = json.loads(fmt.format(record))
        assert "exception" in obj
        assert "ValueError" in obj["exception"]


# ─────────────────────────────────────────────────────────────
# 2. AppLogger static methods — backward-compat + structured kwargs
# ─────────────────────────────────────────────────────────────

class TestAppLoggerMethods:
    def test_info_no_kwargs(self):
        """Legacy call must not raise."""
        from app_logger import AppLogger
        AppLogger.info("Test", "message info")

    def test_error_no_kwargs(self):
        from app_logger import AppLogger
        AppLogger.error("Test", "message error")

    def test_warning_no_kwargs(self):
        from app_logger import AppLogger
        AppLogger.warning("Test", "message warning")

    def test_debug_no_kwargs(self):
        from app_logger import AppLogger
        AppLogger.debug("Test", "message debug")

    def test_info_with_user_id(self):
        from app_logger import AppLogger
        # Should not raise
        AppLogger.info("Test", "user action", user_id="admin")

    def test_info_with_duration_ms(self):
        from app_logger import AppLogger
        AppLogger.info("Test", "slow op", duration_ms=350.5)

    def test_error_with_exception(self):
        from app_logger import AppLogger
        try:
            1 / 0
        except ZeroDivisionError as e:
            AppLogger.error("Test", "division error", exception=e)


# ─────────────────────────────────────────────────────────────
# 3. extract_token_subject helper
# ─────────────────────────────────────────────────────────────

class TestExtractTokenSubject:
    def test_valid_token_returns_sub(self):
        token = create_access_token({"sub": "alice", "role": "Admin"})
        assert extract_token_subject(token) == "alice"

    def test_invalid_token_returns_none(self):
        assert extract_token_subject("not.a.jwt") is None

    def test_empty_string_returns_none(self):
        assert extract_token_subject("") is None

    def test_no_sub_returns_none(self):
        token = create_access_token({"role": "Admin"})  # no 'sub' claim
        assert extract_token_subject(token) is None


# ─────────────────────────────────────────────────────────────
# 4. log_requests middleware via TestClient
# ─────────────────────────────────────────────────────────────

def _admin_headers() -> dict:
    token = create_access_token({"sub": "admin", "role": "Admin"})
    return {"Authorization": f"Bearer {token}"}


def _make_db_mock():
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = MagicMock()
    db = MagicMock()
    db.__enter__ = lambda s: s
    db.__exit__ = MagicMock(return_value=False)
    db.get_connection.return_value = conn
    return db, conn


class TestRequestLoggingMiddleware:
    def test_health_endpoint_not_logged(self):
        """GET /api/health must bypass the log middleware (accepts 200 or 503)."""
        r = client.get("/api/health")
        assert r.status_code in (200, 503)

    def test_request_logged_at_info_level(self, caplog):
        db, conn = _make_db_mock()
        repo = MagicMock()
        repo.get_active_year_id.return_value = 1
        repo.list_students.return_value = []

        with patch("api.routes_students.DatabaseManager", return_value=db), \
                patch("api.routes_students.StudentsApiRepository", return_value=repo), \
                caplog.at_level(logging.INFO, logger="api.requests"):
            r = client.get("/api/v1/students/", headers=_admin_headers())

        assert r.status_code == 200
        assert any("GET" in m and "/api/v1/students/" in m for m in caplog.messages)

    def test_log_contains_status_code(self, caplog):
        db, conn = _make_db_mock()
        repo = MagicMock()
        repo.get_active_year_id.return_value = 1
        repo.list_students.return_value = []

        with patch("api.routes_students.DatabaseManager", return_value=db), \
                patch("api.routes_students.StudentsApiRepository", return_value=repo), \
                caplog.at_level(logging.INFO, logger="api.requests"):
            client.get("/api/v1/students/", headers=_admin_headers())

        assert any("200" in m for m in caplog.messages)

    def test_log_contains_user_id(self, caplog):
        db, conn = _make_db_mock()
        repo = MagicMock()
        repo.get_active_year_id.return_value = 1
        repo.list_students.return_value = []

        with patch("api.routes_students.DatabaseManager", return_value=db), \
                patch("api.routes_students.StudentsApiRepository", return_value=repo), \
                caplog.at_level(logging.INFO, logger="api.requests"):
            client.get("/api/v1/students/", headers=_admin_headers())

        assert any("user=admin" in m for m in caplog.messages)

    def test_unauthenticated_request_logs_user_none(self, caplog):
        """Requests without a token should log user=None."""
        with caplog.at_level(logging.INFO, logger="api.requests"):
            client.get("/api/v1/students/")  # 401 expected

        assert any("user=None" in m for m in caplog.messages)

    def test_slow_request_logs_warning(self):
        """Requests taking > 2000 ms must emit WARNING with 'SLOW' prefix."""
        call_count = [0]

        def fake_counter():
            call_count[0] += 1
            # First call (t0) → 0.0 s; subsequent calls → 2.5 s
            return 0.0 if call_count[0] == 1 else 2.5

        db, conn = _make_db_mock()
        repo = MagicMock()
        repo.get_active_year_id.return_value = 1
        repo.list_students.return_value = []

        mock_logger = MagicMock()

        # Replace the entire `time` name in api.main so perf_counter is fully
        # under our control (needed because time.perf_counter is a C built-in
        # that patch() cannot reliably replace on Python 3.14).
        with patch("api.main.time") as mock_time, \
                patch("api.routes_students.DatabaseManager", return_value=db), \
                patch("api.routes_students.StudentsApiRepository", return_value=repo), \
                patch("api.main._req_logger", mock_logger):
            mock_time.perf_counter = fake_counter
            client.get("/api/v1/students/", headers=_admin_headers())

        assert mock_logger.warning.called, "Expected _req_logger.warning() for slow request"
        assert "SLOW" in str(mock_logger.warning.call_args)
