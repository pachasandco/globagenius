"""Tests for ensure_article_for_destination orchestration helper.

The function is called synchronously from the dispatch loop just before
sending a Telegram alert. It checks if an article exists for the IATA;
if not, it generates one (Claude) + fetches a photo (Unsplash) + inserts
into the articles table.

Returns True if an article exists in DB after the call, False otherwise
— so the caller can decide whether to include the "📖 Le guide" link
in the Telegram alert.
"""
from unittest.mock import MagicMock, patch

import pytest


def _build_db_mock(*, existing_article: bool = False, insert_succeeds: bool = True):
    """A db.table() router that responds to the queries
    ensure_article_for_destination makes."""
    db = MagicMock()
    # Memoize per-name so that production code AND test introspection
    # observe the SAME underlying mock for a given table name.
    _tables: dict = {}

    def _table(name):
        if name in _tables:
            return _tables[name]
        t = MagicMock()
        if name == "articles":
            # check-existence query
            select_chain = (
                t.select.return_value
                .eq.return_value
                .limit.return_value
            )
            select_chain.execute.return_value = MagicMock(
                data=[{"id": "x"}] if existing_article else []
            )
            # insert
            ins_chain = t.insert.return_value
            ins_chain.execute.return_value = MagicMock(
                data=[{"id": "newid"}] if insert_succeeds else None
            )
        _tables[name] = t
        return t

    db.table.side_effect = _table
    return db


def test_returns_true_immediately_when_article_already_exists():
    """No generation if the IATA is already in DB. Saves Anthropic budget."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=True)
    gen_mock = MagicMock()
    photo_mock = MagicMock()

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is True
    gen_mock.assert_not_called()
    photo_mock.assert_not_called()


def test_generates_and_inserts_when_no_existing_article():
    """Happy path: generate guide + fetch photo + insert row."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False, insert_succeeds=True)
    fake_article = {
        "iata": "BCN", "destination": "Barcelone (BCN)",
        "slug": "barcelone-3-jours-guide", "title": "T",
        "h1": "H1", "meta_description": "M", "lead": "L",
        "nut_graf": "N", "top_picks": [], "itinerary": [],
        "infos_pratiques": {}, "faq": [], "sources": [],
        "tags": [], "photo_query": "Barcelona Spain",
        "generated_at": "2026-05-02T12:00:00+00:00",
        "word_count": 2000,
    }
    fake_photo = {
        "url": "https://images.unsplash.com/photo-x",
        "photo_id": "x",
        "photographer_name": "Jane",
        "photographer_url": "https://unsplash.com/@jane",
    }
    gen_mock = MagicMock(return_value=fake_article)
    photo_mock = MagicMock(return_value=fake_photo)

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is True
    gen_mock.assert_called_once_with("BCN")
    photo_mock.assert_called_once_with("BCN", query_hint="Barcelona Spain")
    # The insert payload must include the photo URL merged in
    insert_payload = db_mock.table("articles").insert.call_args.args[0]
    assert insert_payload["iata"] == "BCN"
    assert insert_payload["cover_photo"] == "https://images.unsplash.com/photo-x"
    assert insert_payload["photographer_name"] == "Jane"


def test_returns_false_when_generation_fails():
    """Anthropic returns None → no DB insert, return False so caller
    falls back to alert-without-guide-link behaviour."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False)
    gen_mock = MagicMock(return_value=None)

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is False
    db_mock.table("articles").insert.assert_not_called()


def test_skips_insert_when_unsplash_returns_no_photo():
    """A guide without a cover photo looks broken on every listing
    page — better to skip insertion entirely than to ship an
    unillustrated guide. Replaces the previous behaviour that inserted
    with cover_photo='' anyway."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False, insert_succeeds=True)
    fake_article = {
        "iata": "XXX", "destination": "Nowhere (XXX)",
        "slug": "nowhere-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [], "photo_query": "Nowhere",
        "generated_at": "2026-05-02T12:00:00+00:00", "word_count": 1500,
    }
    gen_mock = MagicMock(return_value=fake_article)
    # All fallback queries return None → nothing to insert.
    photo_mock = MagicMock(return_value=None)

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("XXX")

    assert result is False
    db_mock.table("articles").insert.assert_not_called()


def test_uses_fallback_query_when_first_unsplash_search_fails():
    """The writer tries city-only + country fallbacks before giving up,
    so 'Londres Stansted' or 'Milan Bergame' (which Unsplash has zero
    results for) still find a photo via 'Londres' / 'Milan'."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False, insert_succeeds=True)
    fake_article = {
        "iata": "STN", "destination": "Londres Stansted", "country": "Royaume-Uni",
        "slug": "londres-stansted-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [], "photo_query": "Londres Stansted",
        "generated_at": "2026-05-02T12:00:00+00:00", "word_count": 1500,
    }
    gen_mock = MagicMock(return_value=fake_article)
    # First query ('Londres Stansted') misses, second ('Londres') finds.
    photo_mock = MagicMock(side_effect=[
        None,
        {
            "url": "https://example.com/photo.jpg",
            "photo_id": "abc",
            "photographer_name": "Test Photographer",
            "photographer_url": "https://example.com/p",
        },
    ])

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("STN")

    assert result is True
    insert_payload = db_mock.table("articles").insert.call_args.args[0]
    assert insert_payload["cover_photo"] == "https://example.com/photo.jpg"
    # Fallback query was used — photographer attribution preserved.
    assert insert_payload["photographer_name"] == "Test Photographer"


def test_returns_false_when_db_unavailable():
    """db is None (e.g. Supabase not configured in dev) → no-op, False."""
    from app.notifications import destination_articles

    with patch.object(destination_articles, "db", None):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is False
