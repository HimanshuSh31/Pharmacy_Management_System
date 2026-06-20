"""
tests/test_auth.py — Unit tests for auth.py (hashing, validation, authentication).
"""

import pytest
from auth import (
    hash_password,
    verify_password,
    authenticate_customer,
    authenticate_admin,
    validate_email,
    validate_phone,
    validate_password_strength,
)
from database import customer_add_data


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_produces_storable_string(self):
        h = hash_password("mysecret")
        assert ":" in h, "hash must contain salt:dk separator"

    def test_verify_correct_password(self):
        h = hash_password("correcthorse")
        assert verify_password("correcthorse", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correcthorse")
        assert verify_password("batterystaple", h) is False

    def test_each_hash_is_unique(self):
        """Same password must produce different hashes (different salts)."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_malformed_hash_returns_false(self):
        assert verify_password("password", "notahashstring") is False

    def test_empty_hash_returns_false(self):
        assert verify_password("password", "") is False

    def test_empty_password_wrong_hash(self):
        h = hash_password("realpass")
        assert verify_password("", h) is False


# ---------------------------------------------------------------------------
# Email validator
# ---------------------------------------------------------------------------

class TestValidateEmail:
    @pytest.mark.parametrize("email", [
        "user@example.com",
        "user.name+tag@domain.co.uk",
        "first.last@subdomain.org",
    ])
    def test_valid_emails(self, email):
        assert validate_email(email) is True

    @pytest.mark.parametrize("email", [
        "notanemail",
        "missing@domain",
        "@domain.com",
        "spaces in@email.com",
        "",
    ])
    def test_invalid_emails(self, email):
        assert validate_email(email) is False


# ---------------------------------------------------------------------------
# Phone validator
# ---------------------------------------------------------------------------

class TestValidatePhone:
    @pytest.mark.parametrize("phone", [
        "1234567890",
        "+91 9876543210",
        "123-456-7890",
    ])
    def test_valid_phones(self, phone):
        assert validate_phone(phone) is True

    @pytest.mark.parametrize("phone", [
        "123",          # too short
        "abcdefghij",   # non-numeric
        "",
    ])
    def test_invalid_phones(self, phone):
        assert validate_phone(phone) is False


# ---------------------------------------------------------------------------
# Customer authentication (requires DB via conftest patch)
# ---------------------------------------------------------------------------

class TestAuthenticateCustomer:
    def test_empty_email_returns_false(self):
        assert authenticate_customer("", "password") is False

    def test_empty_password_returns_false(self):
        assert authenticate_customer("user@test.com", "") is False

    def test_nonexistent_user_returns_false(self):
        """Must not raise IndexError or crash — just return False."""
        assert authenticate_customer("ghost@test.com", "password") is False

    def test_valid_credentials(self):
        pw = "testpass123"
        customer_add_data("Test User", hash_password(pw), "auth@test.com", "NY", "1234567890")
        assert authenticate_customer("auth@test.com", pw) is True

    def test_wrong_password(self):
        customer_add_data(
            "Test User2", hash_password("correct"), "auth2@test.com", "NY", "1234567890"
        )
        assert authenticate_customer("auth2@test.com", "wrong") is False


# ---------------------------------------------------------------------------
# Password strength validator
# ---------------------------------------------------------------------------

class TestValidatePassword:
    def test_strong_password(self):
        is_strong, errors = validate_password_strength("Strong1")
        assert is_strong is True
        assert len(errors) == 0

    def test_too_short(self):
        is_strong, errors = validate_password_strength("St1")
        assert is_strong is False
        assert any("6 characters" in err for err in errors)

    def test_missing_uppercase(self):
        is_strong, errors = validate_password_strength("weakpassword1")
        assert is_strong is False
        assert any("uppercase letter" in err for err in errors)

    def test_missing_lowercase(self):
        is_strong, errors = validate_password_strength("WEAKPASSWORD1")
        assert is_strong is False
        assert any("lowercase letter" in err for err in errors)

    def test_missing_digit(self):
        is_strong, errors = validate_password_strength("WeakPassword")
        assert is_strong is False
        assert any("digit" in err for err in errors)


# ---------------------------------------------------------------------------
# Admin authentication
# ---------------------------------------------------------------------------

class TestAuthenticateAdmin:
    def test_empty_credentials(self):
        assert authenticate_admin("", "") is False

    def test_wrong_credentials(self):
        assert authenticate_admin("not_admin", "not_pass") is False

    def test_valid_credentials(self):
        # Uses default fallback from auth.py environment configuration if not custom set
        from auth import ADMIN_USERNAME, ADMIN_PASSWORD
        assert authenticate_admin(ADMIN_USERNAME, ADMIN_PASSWORD) is True

