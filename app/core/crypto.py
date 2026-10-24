"""Password hashing and verification."""
import base64
import hashlib
import hmac
import secrets

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 180_000)
    return base64.b64encode(salt).decode() + ':' + base64.b64encode(hashed).decode()

def password_ok(password, stored):
    try:
        salt, expected = stored.split(':')
        actual = password_hash(password, base64.b64decode(salt)).split(':')[1]
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

