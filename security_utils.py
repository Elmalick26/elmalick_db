"""
أدوات الأمان والتشفير
Security & Cryptography Utilities
"""

import bcrypt
import hashlib


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    تقوم بتشفير كلمة المرور باستخدام خوارزمية bcrypt المعقدة
    """
    # bcrypt requires bytes
    password_bytes = password.encode('utf-8')
    # gensalt generates a salt
    salt = bcrypt.gensalt()
    # hashpw returns bytes, decode to store as string
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
