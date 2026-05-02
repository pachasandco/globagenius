"""Tests for the public GET /api/destinations/{iata} endpoint.

Returns the article + photo + active deals for a destination. Used by
the Next.js page /destination/[iata]. Public — no auth.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_returns_404_when_no_article_exists():
    """No article in DB → 404, the Next.js page renders the
    not-found state."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.routes.db", db_mock):
        r = client.get("/api/destinations/XXX")
    assert r.status_code == 404


def test_returns_article_payload_when_present():
    """Article exists → 200 with the article fields + photo + deals."""
    from app.main import app
    client = TestClient(app)

    article_row = {
        "id": "a1", "iata": "BCN", "destination": "Barcelone (BCN)",
        "slug": "barcelone-3-jours-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [],
        "cover_photo": "https://images.unsplash.com/x",
        "photographer_name": "Jane",
        "photographer_url": "https://unsplash.com/@jane",
        "word_count": 2000,
    }

    def _table(name):
        t = MagicMock()
        if name == "articles":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[article_row])
        elif name == "qualified_items":
            # Return 0 active deals (deals are optional in the response)
            t.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        return t

    db_mock = MagicMock()
    db_mock.table.side_effect = _table

    with patch("app.api.routes.db", db_mock):
        r = client.get("/api/destinations/BCN")
    assert r.status_code == 200
    body = r.json()
    assert body["article"]["iata"] == "BCN"
    assert body["article"]["slug"] == "barcelone-3-jours-guide"
    assert body["photo"]["url"] == "https://images.unsplash.com/x"
    assert body["photo"]["photographer_name"] == "Jane"
    assert "deals" in body  # may be empty


def test_iata_is_uppercased_for_lookup():
    """A request to /api/destinations/bcn (lowercase) must find the BCN article."""
    from app.main import app
    client = TestClient(app)

    article_row = {
        "id": "a1", "iata": "BCN", "destination": "Barcelone (BCN)",
        "slug": "barcelone-3-jours-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [],
        "cover_photo": "", "photographer_name": "", "photographer_url": "",
        "word_count": 2000,
    }

    captured = {}
    def _table(name):
        t = MagicMock()
        if name == "articles":
            def _eq(col, val):
                captured["iata_query"] = val
                m = MagicMock()
                m.limit.return_value.execute.return_value = MagicMock(data=[article_row])
                return m
            t.select.return_value.eq.side_effect = _eq
        elif name == "qualified_items":
            t.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        return t

    db_mock = MagicMock()
    db_mock.table.side_effect = _table

    with patch("app.api.routes.db", db_mock):
        r = client.get("/api/destinations/bcn")
    assert r.status_code == 200
    assert captured["iata_query"] == "BCN"
