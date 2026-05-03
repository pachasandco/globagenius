"""Unsplash search helper for destination cover photos.

Hits the Unsplash search API and returns the first landscape result
along with photographer attribution (mandatory per Unsplash API terms:
https://help.unsplash.com/en/articles/2511315-guideline-attribution).

We don't use a CDN cache here — Unsplash URLs are themselves served
from a fast CDN, and we store the URL once in DB per destination so
each user-facing page makes zero Unsplash calls.
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"


def fetch_destination_photo(
    iata: str,
    query_hint: str,
    timeout: float = 8.0,
) -> Optional[dict]:
    """Return a dict with `url`, `photo_id`, `photographer_name`,
    `photographer_url` for the first landscape match, or None on any
    failure (no key, no result, network error).

    `query_hint` should be a search-friendly string like "Barcelona Spain"
    — Unsplash search ranks by relevance, so the more context the better.
    """
    if not settings.UNSPLASH_ACCESS_KEY:
        logger.info("UNSPLASH_ACCESS_KEY not set, skipping photo fetch for %s", iata)
        return None

    headers = {"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}
    params = {
        "query": query_hint,
        "per_page": 5,
        "orientation": "landscape",
        "content_filter": "high",  # safe-search
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(UNSPLASH_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Unsplash search failed for %s: %s", iata, e)
        return None

    results = data.get("results") or []
    if not results:
        logger.info("Unsplash returned no results for %s (query=%s)", iata, query_hint)
        return None

    first = results[0]
    return {
        "url": first.get("urls", {}).get("regular", ""),
        "photo_id": first.get("id", ""),
        "photographer_name": first.get("user", {}).get("name", ""),
        "photographer_url": first.get("user", {}).get("links", {}).get("html", ""),
    }
