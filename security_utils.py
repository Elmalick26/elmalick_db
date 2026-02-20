import bcrypt
import hashlib

def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
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
    """
    if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'):
        # It's a bcrypt hash
        return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
    else:
        # Legacy SHA256 check
        legacy_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return legacy_hash == stored_hash

def needs_rehash(stored_hash: str) -> bool:
    """
    Checks if the stored hash uses a legacy format (SHA256) and needs to be upgraded.
    """
    # If it doesn't look like a bcrypt hash, it needs rehash
    return not (stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$') or stored_hash.startswith('$2y$'))

def validate_password(password: str, min_length: int = 8) -> tuple[bool, str]:
    """
    Basic password policy: minimum length, at least one letter and one digit.
    Returns (is_valid, message).
    """
    if len(password) < min_length:
        return False, f"Mot de passe trop court (min {min_length} caracteres)."
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if not (has_letter and has_digit):
        return False, "Le mot de passe doit contenir au moins une lettre et un chiffre."
    return True, ""
