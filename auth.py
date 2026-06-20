"""
auth.py — Authentication and input validation for the Pharmacy Management System.

Password hashing uses PBKDF2-HMAC-SHA256 (Python stdlib hashlib) with a
random 16-byte salt per password.  No third-party crypto library is required.

Admin credentials are read from environment variables so they are never
hard-coded in source.  Set PHARMACY_ADMIN_USER and PHARMACY_ADMIN_PASS in a
.env file (load with python-dotenv) or in your system environment.

Round-2: Optional[str] type hint for Python 3.7+ compatibility.
"""

import hashlib
import hmac
import os
import re
import logging
from typing import Optional, Tuple, List

from database import customer_get_password_hash

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Admin credentials — read from environment, fall back to insecure defaults
# ---------------------------------------------------------------------------

ADMIN_USERNAME: str = os.environ.get("PHARMACY_ADMIN_USER", "admin")
ADMIN_PASSWORD: str = os.environ.get("PHARMACY_ADMIN_PASS", "admin")

if ADMIN_USERNAME == "admin" and ADMIN_PASSWORD == "admin":
    logger.warning(
        "Admin credentials are using insecure defaults. "
        "Set PHARMACY_ADMIN_USER and PHARMACY_ADMIN_PASS environment variables."
    )

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

_ITERATIONS = 260_000   # OWASP 2023 recommended minimum for PBKDF2-SHA256


def hash_password(password: str) -> str:
    """
    Hash *password* and return a storable string:
        <salt_hex>:<dk_hex>
    Each call produces a different salt, so equal passwords yield different hashes.
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Return True if *password* matches *stored_hash* produced by hash_password().
    Never raises — returns False for any malformed or mismatched input.
    """
    try:
        salt_hex, dk_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
        return dk.hex() == dk_hex
    except Exception as exc:
        logger.error("verify_password error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

def authenticate_customer(email: str, password: str) -> bool:
    """
    Return True if *email* exists and *password* matches its stored hash.
    Never raises IndexError or similar — returns False for unknown users.
    """
    if not email or not password:
        return False
    stored_hash: Optional[str] = customer_get_password_hash(email)
    if stored_hash is None:
        return False        # user not found
    return verify_password(password, stored_hash)


def authenticate_admin(username: str, password: str) -> bool:
    """Return True if the supplied credentials match the configured admin account."""
    if not username or not password:
        return False
    # Use hmac.compare_digest to prevent timing attacks
    user_ok = hmac.compare_digest(username.encode(), ADMIN_USERNAME.encode())
    pass_ok = hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode())
    return user_ok and pass_ok


# ---------------------------------------------------------------------------
# Input validators
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
_PHONE_RE = re.compile(r'^\+?[\d\s\-]{7,15}$')


def validate_email(email: str) -> bool:
    """Return True if *email* looks like a valid e-mail address."""
    return bool(_EMAIL_RE.match(email.strip()))


def validate_phone(phone: str) -> bool:
    """Return True if *phone* looks like a valid phone number (7-15 digits)."""
    return bool(_PHONE_RE.match(phone.strip()))


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength.
    Returns (is_strong, list of error messages).
    """
    errors = []
    if len(password) < 6:
        errors.append("Password must be at least 6 characters long.")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit.")
    return len(errors) == 0, errors
