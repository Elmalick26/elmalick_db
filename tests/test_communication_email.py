"""Tests for communication_ui EmailWorker retry logic.

Tests focus on _send_with_retry and _build_message (pure-ish logic).
QThread.start() is never called — we test the methods directly on an
instance created with a minimal smtp_config mock.
"""

import os
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Fixture: minimal EmailWorker instance (no QApplication needed for methods)
# ---------------------------------------------------------------------------


def _make_worker(subject="Test", body="Bonjour {NOM}", attachment=None):
    """Return an EmailWorker configured with fake SMTP settings."""
    from communication_ui import EmailWorker

    smtp_config = {
        'host': 'smtp.example.com',
        'port': '587',
        'email': 'sender@example.com',
        'password': 'secret',
    }
    recipients = [(1, "Alice", "alice@example.com")]
    worker = EmailWorker.__new__(EmailWorker)  # bypass QThread.__init__
    worker.smtp_config = smtp_config
    worker.recipients = recipients
    worker.subject = subject
    worker.body = body
    worker.attachment = attachment
    worker._sent = 0
    worker._failed = 0
    return worker


# ---------------------------------------------------------------------------
# _build_message
# ---------------------------------------------------------------------------


class TestBuildMessage:

    def test_from_and_to_headers_set(self):
        worker = _make_worker()
        msg = worker._build_message("Alice", "alice@example.com")
        assert msg['From'] == 'sender@example.com'
        assert msg['To'] == 'alice@example.com'

    def test_subject_header_set(self):
        worker = _make_worker(subject="Résultats scolaires")
        msg = worker._build_message("Bob", "bob@example.com")
        assert msg['Subject'] == "Résultats scolaires"

    def test_nom_placeholder_replaced(self):
        worker = _make_worker(body="Bonjour {NOM}, voici vos résultats.")
        msg = worker._build_message("Alice", "alice@example.com")
        # get_payload(decode=True) returns bytes; decode to str
        payload = msg.get_payload(0).get_payload(decode=True).decode("utf-8", errors="replace")
        assert "Alice" in payload
        assert "{NOM}" not in payload

    def test_no_attachment_when_path_none(self):
        worker = _make_worker(attachment=None)
        msg = worker._build_message("Alice", "alice@example.com")
        assert len(msg.get_payload()) == 1  # only text part

    def test_attachment_added_when_file_exists(self, tmp_path):
        att = tmp_path / "report.pdf"
        att.write_bytes(b"%PDF-1.4 fake")
        worker = _make_worker(attachment=str(att))
        msg = worker._build_message("Alice", "alice@example.com")
        assert len(msg.get_payload()) == 2  # text + attachment

    def test_attachment_skipped_when_file_missing(self):
        worker = _make_worker(attachment="/nonexistent/path/file.pdf")
        msg = worker._build_message("Alice", "alice@example.com")
        assert len(msg.get_payload()) == 1  # only text part


# ---------------------------------------------------------------------------
# _send_with_retry
# ---------------------------------------------------------------------------


class TestSendWithRetry:

    def test_success_on_first_attempt(self):
        worker = _make_worker()
        server = MagicMock()
        with patch.object(worker, '_build_message', return_value=MagicMock()):
            ok, err = worker._send_with_retry(server, "Alice", "alice@example.com")
        assert ok is True
        assert err == ""
        assert server.send_message.call_count == 1

    def test_success_on_second_attempt(self):
        worker = _make_worker()
        server = MagicMock()
        server.send_message.side_effect = [Exception("Timeout"), None]

        with patch.object(worker, '_build_message', return_value=MagicMock()):
            with patch("time.sleep"):  # don't actually sleep
                ok, err = worker._send_with_retry(server, "Alice", "alice@example.com")

        assert ok is True
        assert server.send_message.call_count == 2

    def test_all_attempts_fail_returns_false(self):
        worker = _make_worker()
        server = MagicMock()
        server.send_message.side_effect = Exception("Connection refused")

        with patch.object(worker, '_build_message', return_value=MagicMock()):
            with patch("time.sleep"):
                ok, err = worker._send_with_retry(server, "Alice", "alice@example.com")

        assert ok is False
        assert "Échec après 3 tentatives" in err
        assert server.send_message.call_count == 3

    def test_error_message_contains_last_exception(self):
        worker = _make_worker()
        server = MagicMock()
        server.send_message.side_effect = [
            Exception("first error"),
            Exception("second error"),
            Exception("final error"),
        ]

        with patch.object(worker, '_build_message', return_value=MagicMock()):
            with patch("time.sleep"):
                ok, err = worker._send_with_retry(server, "Alice", "alice@example.com")

        assert "final error" in err

    def test_no_sleep_after_last_attempt(self):
        """No delay should be added after the final failed attempt."""
        from communication_ui import _EMAIL_MAX_RETRIES

        worker = _make_worker()
        server = MagicMock()
        server.send_message.side_effect = Exception("error")

        sleep_calls = []

        def fake_sleep(t):
            sleep_calls.append(t)

        with patch.object(worker, '_build_message', return_value=MagicMock()):
            with patch("time.sleep", side_effect=fake_sleep):
                ok, err = worker._send_with_retry(server, "Alice", "alice@example.com")

        assert ok is False
        # Sleep should be called MAX_RETRIES - 1 times (not after the last attempt)
        assert len(sleep_calls) == _EMAIL_MAX_RETRIES - 1

    def test_sleep_uses_exponential_backoff(self):
        """Delays should be 0.5*attempt — 0.5s then 1.0s for 3 max retries."""
        worker = _make_worker()
        server = MagicMock()
        server.send_message.side_effect = Exception("error")

        sleep_calls = []

        def fake_sleep(t):
            sleep_calls.append(t)

        with patch.object(worker, '_build_message', return_value=MagicMock()):
            with patch("time.sleep", side_effect=fake_sleep):
                worker._send_with_retry(server, "Alice", "alice@example.com")

        assert sleep_calls == [0.5, 1.0]  # 0.5*1, 0.5*2

    def test_max_retries_constant_is_three(self):
        from communication_ui import _EMAIL_MAX_RETRIES

        assert _EMAIL_MAX_RETRIES == 3


# ---------------------------------------------------------------------------
# Integration: retry count matches _EMAIL_MAX_RETRIES
# ---------------------------------------------------------------------------


class TestRetryCountRespected:

    @pytest.mark.parametrize("max_retries", [1, 2, 3])
    def test_attempts_equal_to_max_retries(self, max_retries):
        """Regardless of the constant value, attempts == max_retries."""
        import communication_ui as cu

        original = cu._EMAIL_MAX_RETRIES
        cu._EMAIL_MAX_RETRIES = max_retries
        try:
            worker = _make_worker()
            server = MagicMock()
            server.send_message.side_effect = Exception("error")

            with patch.object(worker, '_build_message', return_value=MagicMock()):
                with patch("time.sleep"):
                    ok, err = worker._send_with_retry(server, "Alice", "alice@example.com")

            assert server.send_message.call_count == max_retries
        finally:
            cu._EMAIL_MAX_RETRIES = original
