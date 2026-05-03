"""Tests for unsplash.fetch_destination_photo.

The helper hits the Unsplash search API to find a representative photo
for a destination. Returns a dict with the URL we'll embed and the
photographer attribution (legally required by Unsplash terms).
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _ok_response(items: list[dict]):
    """Build a fake httpx response with the Unsplash search payload."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"results": items}
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def test_returns_first_landscape_photo_when_results_present():
    """Happy path: API returns 3 photos, helper picks the first one and
    extracts URL + photographer name + profile URL."""
    from app.notifications.unsplash import fetch_destination_photo

    fake_payload = [
        {
            "id": "abc123",
            "urls": {"regular": "https://images.unsplash.com/photo-abc?w=1200"},
            "user": {
                "name": "Jane Doe",
                "links": {"html": "https://unsplash.com/@janedoe"},
            },
        },
        {
            "id": "def456",
            "urls": {"regular": "https://images.unsplash.com/photo-def?w=1200"},
            "user": {"name": "John Smith", "links": {"html": "https://unsplash.com/@john"}},
        },
    ]
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _ok_response(fake_payload)

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        result = fetch_destination_photo("BCN", query_hint="Barcelona Spain")

    assert result is not None
    assert result["url"] == "https://images.unsplash.com/photo-abc?w=1200"
    assert result["photo_id"] == "abc123"
    assert result["photographer_name"] == "Jane Doe"
    assert result["photographer_url"] == "https://unsplash.com/@janedoe"


def test_returns_none_when_unsplash_returns_no_results():
    """Empty result set → None (no fallback to a default photo, the
    article page handles the missing-photo case in the UI)."""
    from app.notifications.unsplash import fetch_destination_photo

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _ok_response([])

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        result = fetch_destination_photo("XXX", query_hint="Nonexistent")

    assert result is None


def test_returns_none_when_unsplash_api_raises():
    """A network/API error must not crash the caller — return None."""
    from app.notifications.unsplash import fetch_destination_photo

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.side_effect = httpx.HTTPError("boom")

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        result = fetch_destination_photo("BCN", query_hint="Barcelona")

    assert result is None


def test_returns_none_when_access_key_missing():
    """No API key configured → no call, return None silently."""
    from app.notifications.unsplash import fetch_destination_photo

    with patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", ""):
        result = fetch_destination_photo("BCN", query_hint="Barcelona")

    assert result is None


def test_passes_query_hint_to_unsplash_search():
    """Verify the query string we send to Unsplash includes the hint
    (city name) — this is what makes results relevant."""
    from app.notifications.unsplash import fetch_destination_photo

    captured = {}
    def _capture_get(url, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params or {}
        captured["headers"] = headers or {}
        return _ok_response([{
            "id": "x",
            "urls": {"regular": "https://example.com/x"},
            "user": {"name": "A", "links": {"html": "https://unsplash.com/@a"}},
        }])

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.side_effect = _capture_get

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        fetch_destination_photo("BCN", query_hint="Barcelona Spain travel")

    assert "Barcelona Spain travel" in captured["params"].get("query", "")
    # Authorization header carries the access key, prefixed with Client-ID
    auth = captured["headers"].get("Authorization", "")
    assert "Client-ID" in auth and "test_key" in auth
    # Filter on landscape orientation for cover photos
    assert captured["params"].get("orientation") == "landscape"
