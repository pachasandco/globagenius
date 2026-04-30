"""V7: tests for the password reset helpers.

Token strategy:
- 32+ URL-safe chars (secrets.token_urlsafe(24) → 32 chars).
- TTL: 1 hour from creation.
- Single-use: marked consumed once a successful reset uses it.
- DB-backed: lookup by primary key, status checks via columns.
"""
from datetime import datetime, timezone, timedelta

from app.auth.password_reset import (
    generate_reset_token,
    is_token_valid,
    PASSWORD_RESET_TTL_HOURS,
)


def test_generate_token_returns_url_safe_string():
    token = generate_reset_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    # No /, +, or = (URL-safe)
    assert all(c.isalnum() or c in "-_" for c in token)


def test_generate_token_is_unique():
    tokens = {generate_reset_token() for _ in range(20)}
    assert len(tokens) == 20  # extremely unlikely collision


def test_ttl_constant_is_one_hour():
    assert PASSWORD_RESET_TTL_HOURS == 1


def test_is_token_valid_accepts_fresh_unused_token():
    row = {
        "token": "abc",
        "user_id": "u1",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "used_at": None,
    }
    assert is_token_valid(row) is True


def test_is_token_valid_rejects_expired_token():
    row = {
        "token": "abc",
        "user_id": "u1",
        "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "used_at": None,
    }
    assert is_token_valid(row) is False


def test_is_token_valid_rejects_already_used_token():
    row = {
        "token": "abc",
        "user_id": "u1",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "used_at": datetime.now(timezone.utc).isoformat(),
    }
    assert is_token_valid(row) is False


def test_is_token_valid_rejects_none_row():
    assert is_token_valid(None) is False


def test_is_token_valid_rejects_malformed_expires_at():
    row = {
        "token": "abc",
        "user_id": "u1",
        "expires_at": "not-a-date",
        "used_at": None,
    }
    assert is_token_valid(row) is False
