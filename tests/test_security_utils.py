"""Tests for security_utils.py — hash_password, verify_password, needs_rehash."""

import hashlib

import pytest

from security_utils import hash_password, needs_rehash, verify_password


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$")

    def test_different_salts_each_call(self):
        h1 = hash_password("abc")
        h2 = hash_password("abc")
        assert h1 != h2

    def test_non_empty_result(self):
        assert len(hash_password("test")) > 20


class TestVerifyPassword:
    def test_bcrypt_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_bcrypt_wrong_password(self):
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_legacy_sha256_correct(self):
        raw = "legacypass"
        sha_hash = hashlib.sha256(raw.encode()).hexdigest()
        assert verify_password(raw, sha_hash) is True

    def test_legacy_sha256_wrong(self):
        sha_hash = hashlib.sha256(b"legacypass").hexdigest()
        assert verify_password("otherpass", sha_hash) is False

    def test_empty_stored_hash_returns_false(self):
        assert verify_password("anything", "") is False

    def test_none_stored_hash_returns_false(self):
        assert verify_password("anything", None) is False


class TestNeedsRehash:
    def test_bcrypt_hash_no_rehash_needed(self):
        h = hash_password("test")
        assert needs_rehash(h) is False

    def test_sha256_needs_rehash(self):
        sha_hash = hashlib.sha256(b"test").hexdigest()
        assert needs_rehash(sha_hash) is True

    def test_empty_string_needs_rehash(self):
        assert needs_rehash("") is True

    def test_none_needs_rehash(self):
        assert needs_rehash(None) is True
