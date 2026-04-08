"""Shared Anthropic client singleton. Avoids recreating client on every call."""

from anthropic import Anthropic
from app.config import settings

_client: Anthropic | None = None


def get_client() -> Anthropic | None:
    global _client
    if not settings.ANTHROPIC_API_KEY:
        return None
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client
