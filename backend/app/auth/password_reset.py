"""V7: password reset helpers.

Pure functions for token lifecycle. The DB read/write happens in routes.py
to keep this module easy to unit-test without mocking Supabase.
"""

import secrets
from datetime import datetime, timezone

# Tokens live 1 hour. Long enough for a user to find the email in their
# inbox and click; short enough to limit damage if the email leaks.
PASSWORD_RESET_TTL_HOURS = 1

# 24 raw bytes → ~32 URL-safe chars after base64 encoding.
_TOKEN_BYTES = 24


def generate_reset_token() -> str:
    """Return a fresh URL-safe token suitable for a password-reset link."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def is_token_valid(row: dict | None) -> bool:
    """True iff the row exists, is not consumed, and has not expired.

    Designed to be called with the dict returned by a Supabase row read
    (snake_case fields). Returns False on missing fields, malformed
    timestamps, or any unexpected shape — better to refuse a reset than
    to risk authorising one we can't verify.
    """
    if not row:
        return False
    if row.get("used_at"):
        return False
    expires_at_raw = row.get("expires_at")
    if not isinstance(expires_at_raw, str):
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    return expires_at > datetime.now(timezone.utc)
