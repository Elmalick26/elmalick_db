"""Tests for security_utils.py — hash_password, verify_password, needs_rehash."""

import hashlib

import pytest

from security_utils import (
    decrypt_value,
    encrypt_value,
    generate_parent_pin,
    hash_password,
    hash_pin,
    needs_rehash,
    validate_password,
    verify_password,
    verify_pin,
)


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

    def test_malformed_bcrypt_hash_returns_false(self):
        assert verify_password("anything", "$2b$12$malformedXXXXXXXXXXXXX") is False


class TestNeedsRehash:
    def test_bcrypt_hash_no_rehash_needed(self):
        h = hash_password("test")
        assert needs_rehash(h) is False

    def test_sha256_needs_rehash(self):
        sha_hash = hashlib.sha256(b"test").hexdigest()
        assert needs_rehash(sha_hash) is True

    def test_empty_string_needs_rehash(self):
        assert needs_rehash("") is True


class TestValidatePassword:
    def test_valid_password(self):
        ok, msg = validate_password("Secret123")
        assert ok is True
        assert msg == ""

    def test_too_short(self):
        ok, msg = validate_password("Ab1", min_length=8)
        assert ok is False
        assert "8" in msg

    def test_no_digit(self):
        ok, msg = validate_password("OnlyLetters")
        assert ok is False

    def test_no_letter(self):
        ok, msg = validate_password("12345678")
        assert ok is False

    def test_custom_min_length_passes(self):
        ok, _ = validate_password("Abc1", min_length=4)
        assert ok is True


class TestGenerateParentPin:
    def test_default_length(self):
        pin = generate_parent_pin()
        assert len(pin) == 4

    def test_all_digits(self):
        pin = generate_parent_pin(6)
        assert pin.isdigit()
        assert len(pin) == 6

    def test_different_each_call(self):
        pins = {generate_parent_pin() for _ in range(20)}
        assert len(pins) > 1  # extremely unlikely to be all identical


class TestPinHashVerify:
    def test_round_trip(self):
        h = hash_pin("1234")
        assert verify_pin("1234", h) is True

    def test_wrong_pin(self):
        h = hash_pin("1234")
        assert verify_pin("5678", h) is False


class TestEncryptDecryptValue:
    def test_empty_string_returns_empty(self):
        assert encrypt_value("") == ""
        assert decrypt_value("") == ""

    def test_round_trip(self):
        plain = "my_smtp_password_123"
        cipher = encrypt_value(plain)
        assert cipher != plain
        assert decrypt_value(cipher) == plain

    def test_decrypt_legacy_plain_text(self):
        # Unencrypted legacy value must pass through unchanged
        assert decrypt_value("plain_text_value") == "plain_text_value"

    def test_none_needs_rehash(self):
        assert needs_rehash(None) is True
