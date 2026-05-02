"""Tests for the Aviasales URL builders.

build_aviasales_url is the round-trip builder (legacy).
build_aviasales_oneway_url is the V9 one-way variant — needed because
historic one-way rows in DB had source_url=null and the alert footer
rendered with no booking link.
"""
from app.notifications.aviasales import (
    build_aviasales_url,
    build_aviasales_oneway_url,
)


def test_oneway_url_format():
    """Slug is {ORIG}{DDMM}{DEST}1, no return-date segment."""
    url = build_aviasales_oneway_url("BVA", "PMI", "2026-05-29")
    assert url == "https://www.aviasales.com/search/BVA2905PMI1"


def test_oneway_url_with_marker():
    url = build_aviasales_oneway_url("CDG", "BKK", "2026-09-01", marker="649153")
    assert url == "https://www.aviasales.com/search/CDG0109BKK1?marker=649153"


def test_oneway_url_invalid_date_falls_back_to_query_string():
    """A malformed date must not crash the alert pipeline — fall back to
    the generic search URL with origin/destination as query params."""
    url = build_aviasales_oneway_url("CDG", "BKK", "not-a-date")
    assert url.startswith("https://www.aviasales.com/search?")
    assert "origin=CDG" in url
    assert "destination=BKK" in url


def test_oneway_url_marker_appended_to_fallback():
    url = build_aviasales_oneway_url("CDG", "BKK", "", marker="aff123")
    assert "marker=aff123" in url


def test_roundtrip_unchanged_after_oneway_addition():
    """Sanity: V9 didn't break the round-trip builder."""
    url = build_aviasales_url("CDG", "BCN", "2026-09-01", "2026-09-08")
    assert url == "https://www.aviasales.com/search/CDG0109BCN08091"
