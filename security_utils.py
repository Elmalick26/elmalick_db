"""
أدوات الأمان والتشفير
Security & Cryptography Utilities
"""

import hashlib  # للتوافق مع تجزئة SHA256 القديمة فقط
import secrets

import bcrypt

# عدد جولات bcrypt — 12 توازن جيد بين الأمان والسرعة
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    تقوم بتشفير كلمة المرور باستخدام خوارزمية bcrypt المعقدة
    """
    # bcrypt requires bytes
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifies a password against a stored hash.
    Supports both bcrypt and legacy SHA256 hashes.
    يتحقق من صحة كلمة المرور (يدعم كل من bcrypt الحديث و SHA256 القديم)
    """
    if not stored_hash:
        return False

    if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
        # It's a bcrypt hash
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
        except ValueError:
            # Handle cases where the stored hash is malformed
            return False
    else:
        # Legacy SHA256 check
        legacy_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return legacy_hash == stored_hash


def needs_rehash(stored_hash: str) -> bool:
    """
    Checks if the stored hash uses a legacy format (SHA256) and needs to be upgraded.
    يفحص ما إذا كانت كلمة المرور تحتاج إلى إعادة تشفير بالنظام الجديد
    """
    if not stored_hash:
        return True
    # If it doesn't look like a bcrypt hash, it needs rehash
    return not (stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'))


def validate_password(password: str, min_length: int = 8) -> tuple[bool, str]:
    """
    Basic password policy: minimum length, at least one letter and one digit.
    Returns (is_valid, message).
    يتحقق من قوة كلمة المرور (الحد الأدنى، وجود حروف وأرقام)
    """
    if len(password) < min_length:
        return (
            False,
            f"Mot de passe trop court (min {min_length} caractères).\nكلمة المرور قصيرة جداً (الأدنى {min_length} رموز).",
        )

    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)

    if not (has_letter and has_digit):
        return (
            False,
            "Le mot de passe doit contenir au moins une lettre et un chiffre.\nيجب أن تحتوي كلمة المرور على حرف ورقم واحد على الأقل.",
        )

    return True, ""


def generate_parent_pin(length: int = 4) -> str:
    """
    توليد رمز PIN عشوائي لولي الأمر (مؤمن تشفيرياً).
    Generate a cryptographically secure numeric PIN for parent portal access.
    """
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


def hash_pin(pin: str) -> str:
    """
    تشفير رمز PIN باستخدام bcrypt.
    Hash a numeric PIN using bcrypt (reuses existing hash_password logic).
    """
    return hash_password(pin)


def verify_pin(plain_pin: str, stored_hash: str) -> bool:
    """
    التحقق من صحة رمز PIN مقابل تجزئته المخزَّنة.
    Verify a PIN against its bcrypt hash.
    """
    return verify_password(plain_pin, stored_hash)


# ─── Fernet symmetric encryption (SMTP password at rest) ──────────────────────


def _get_fernet_key() -> bytes:
    """Retrieve or auto-generate a Fernet key stored in config.ini [SECURITY] fernet_key."""
    try:
        from config_manager import ConfigManager

        cfg = ConfigManager()
        key = (cfg.get("SECURITY", "fernet_key", fallback="") or "").strip()
        if not key:
            from cryptography.fernet import Fernet

            key = Fernet.generate_key().decode()
            cfg.set("SECURITY", "fernet_key", key)
        return key.encode()
    except Exception:
        # Fallback: derive a fixed key from a constant (should not happen in practice)
        import base64

        return base64.urlsafe_b64encode(b"ElMalickGest_FallbackKey_32bytes")


def encrypt_value(plain_text: str) -> str:
    """Encrypt a string using Fernet symmetric encryption.
    Returns the ciphertext as a UTF-8 string. Returns '' for empty input.
    """
    if not plain_text:
        return ""
    try:
        from cryptography.fernet import Fernet

        return Fernet(_get_fernet_key()).encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return plain_text  # fallback: store as-is if encryption fails


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet-encrypted token back to plain text.
    Returns '' for empty input. Returns the original token if decryption fails
    (handles legacy unencrypted values gracefully).
    """
    if not token:
        return ""
    try:
        from cryptography.fernet import Fernet, InvalidToken

        return Fernet(_get_fernet_key()).decrypt(token.encode("utf-8")).decode("utf-8")
    except (Exception,):  # InvalidToken or key mismatch → treat as plain text legacy value
        return token
