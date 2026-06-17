"""S6 — SMTP password is encrypted at rest in CommunicationRepository.

upsert_email_settings must store a Fernet ciphertext (not plaintext), and
get_email_settings must transparently decrypt it. Legacy plaintext rows (written
before encryption existed) must still be readable.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import security_utils
from src.data.communication_repo import CommunicationRepository


def _repo():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return CommunicationRepository(conn), cur


class TestEmailPasswordEncryption:
    def test_upsert_stores_ciphertext_not_plaintext(self):
        repo, cur = _repo()
        repo.upsert_email_settings("smtp.gmail.com", "587", "a@b.com", "s3cret-pass")
        # The INSERT is the second execute call; its params hold the stored password.
        insert_params = cur.execute.call_args_list[1][0][1]
        stored = insert_params[3]
        assert stored != "s3cret-pass"  # not stored in clear
        assert security_utils.decrypt_value(stored) == "s3cret-pass"  # but recoverable

    def test_empty_password_stays_empty(self):
        repo, cur = _repo()
        repo.upsert_email_settings("smtp.gmail.com", "587", "a@b.com", "")
        assert cur.execute.call_args_list[1][0][1][3] == ""

    def test_get_decrypts_password_column(self):
        repo, cur = _repo()
        token = security_utils.encrypt_value("my-pass")
        cur.fetchone.return_value = (1, "smtp.gmail.com", "587", "a@b.com", token)
        cur.description = [("id",), ("smtp_server",), ("smtp_port",), ("email_address",), ("email_password",)]
        row = repo.get_email_settings()
        assert row[4] == "my-pass"  # decrypted in place
        assert row[1] == "smtp.gmail.com"  # other columns untouched

    def test_get_tolerates_legacy_plaintext(self):
        repo, cur = _repo()
        cur.fetchone.return_value = (1, "smtp.gmail.com", "587", "a@b.com", "legacy-plain")
        cur.description = [("id",), ("smtp_server",), ("smtp_port",), ("email_address",), ("email_password",)]
        row = repo.get_email_settings()
        assert row[4] == "legacy-plain"  # not a token → returned as-is

    def test_get_returns_none_when_empty(self):
        repo, cur = _repo()
        cur.fetchone.return_value = None
        assert repo.get_email_settings() is None
