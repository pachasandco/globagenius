"""Synchronous helper called from the alert dispatcher to lazily generate
a destination guide before the very first Telegram alert ever sent for
that destination.

Behaviour:
- If an article exists in DB for `iata` → no-op, returns True.
- Else → call destination_writer.generate_destination_guide(iata),
  fetch a cover photo via Unsplash, insert the row.
- Returns True iff an article exists in DB after the call.

Cost discipline: an article is generated AT MOST ONCE per destination,
ever. Subsequent alerts to the same destination don't pay any Anthropic
tokens.

A separate `is_legacy_format()` / `regenerate_in_background()` pair
handles the 2026-05 schema change (itinerary → neighborhoods): the
/api/destinations/{iata} endpoint detects articles still carrying the
old 3-day program and triggers a non-blocking regeneration so the next
visitor sees the new city-presentation format.

Failure modes don't crash the caller — they return False so the alert
dispatcher can decide to send the alert without the guide link.
"""
import logging
from typing import Optional

from app.agents.destination_writer import generate_destination_guide
from app.db import db
from app.notifications.unsplash import fetch_destination_photo

logger = logging.getLogger(__name__)


def _article_exists(iata: str) -> bool:
    """Return True iff the articles table has a row with this iata."""
    if not db:
        return False
    try:
        r = (
            db.table("articles")
            .select("id")
            .eq("iata", iata)
            .limit(1)
            .execute()
        )
        return bool(r.data)
    except Exception as e:
        logger.warning("Article existence check failed for %s: %s", iata, e)
        return False


def ensure_article_for_destination(iata: str) -> bool:
    """Make sure an article row exists for the destination. Generates one
    synchronously if needed (~30-60s blocking call). Safe to call before
    every Telegram dispatch — it returns immediately when the article is
    already in DB.

    Returns:
        True  — an article exists in DB after the call (already there or
                successfully generated).
        False — generation failed or DB unavailable. Caller should still
                send the alert, just without the "📖 guide" link.
    """
    if not db:
        logger.info("DB unavailable, cannot ensure article for %s", iata)
        return False

    if _article_exists(iata):
        return True

    logger.info("No article for %s yet, generating now (synchronous)", iata)
    article = generate_destination_guide(iata)
    if not article:
        logger.warning("Article generation returned None for %s", iata)
        return False

    # Fetch cover photo. We try a couple of progressively-broader queries
    # because Unsplash sometimes returns 0 results for niche airport
    # designators (e.g. "Londres Stansted", "Milan Bergame", "Alicante").
    # If everything fails, we skip insertion entirely — a guide without a
    # cover photo looks broken on the home page and the listing pages.
    destination_name = article.get("destination") or ""
    country_name = article.get("country") or ""
    # Strip airport descriptors so "Londres Stansted" / "Milan Bergame"
    # also try a search on the city alone, which Unsplash actually has
    # photos for.
    city_only = destination_name.split(" ")[0] if destination_name else ""
    queries = [
        article.get("photo_query") or destination_name or iata,
        destination_name,
        city_only if city_only != destination_name else "",
        f"{destination_name} {country_name}".strip() if country_name else "",
        f"{city_only} {country_name}".strip() if (city_only and country_name) else "",
        country_name,
        f"{city_only} skyline" if city_only else "",
    ]
    # Dedup while preserving order, drop empties.
    seen: set[str] = set()
    queries = [q for q in queries if q and not (q in seen or seen.add(q))]

    photo = None
    for q in queries:
        photo = fetch_destination_photo(iata, query_hint=q)
        if photo:
            if q != queries[0]:
                logger.info("Unsplash matched %s on fallback query %r", iata, q)
            break

    if not photo:
        logger.warning(
            "No Unsplash photo found for %s after %d query attempts — "
            "skipping article insert to avoid an unillustrated guide",
            iata, len(queries),
        )
        return False

    article["cover_photo"] = photo["url"]
    article["photo_id"] = photo["photo_id"]
    article["photographer_name"] = photo["photographer_name"]
    article["photographer_url"] = photo["photographer_url"]

    # Convert nested lists/dicts to JSON-friendly form. Supabase python
    # client serialises dict / list automatically into jsonb columns,
    # so no manual json.dumps needed.
    try:
        db.table("articles").insert(article).execute()
        logger.info("Article inserted for %s (slug=%s, words=%s)",
                    iata, article.get("slug"), article.get("word_count"))
        return True
    except Exception as e:
        logger.error("Article insert failed for %s: %s", iata, e)
        return False


# ── Legacy-format regeneration (2026-05 schema change) ────────────────────


def is_legacy_format(article: dict) -> bool:
    """An article is "legacy" when it carries the dropped 3-day
    itinerary and lacks the new neighborhoods block.

    We don't treat "has itinerary AND has neighborhoods" as legacy —
    that's an article mid-migration and the frontend should already
    render the neighborhoods. Same for "no itinerary AND no
    neighborhoods" (a generation that bailed early, not our concern).
    """
    itinerary = article.get("itinerary") or []
    neighborhoods = article.get("neighborhoods") or []
    return bool(itinerary) and not neighborhoods


def regenerate_article(iata: str) -> bool:
    """Re-run generate_destination_guide() and UPDATE (not insert) the
    existing row. Keeps the cover photo and id; overwrites the body
    fields (lead, top_picks, neighborhoods, infos_pratiques, faq, etc.)
    and nulls out the legacy `itinerary`.

    Returns True on success. Logs and returns False on any failure —
    the caller (a background task) doesn't propagate the error to the
    HTTP response, so users get the stale article rather than an error.
    """
    if not db:
        return False
    article = generate_destination_guide(iata)
    if not article:
        logger.warning("Regen returned None for %s", iata)
        return False

    # Don't touch the cover photo — Unsplash already resolved one and
    # re-querying could land on a different image, breaking the cache
    # and confusing returning visitors.
    update = {
        "title": article.get("title"),
        "h1": article.get("h1"),
        "slug": article.get("slug"),
        "meta_description": article.get("meta_description"),
        "lead": article.get("lead"),
        "nut_graf": article.get("nut_graf"),
        "top_picks": article.get("top_picks") or [],
        "neighborhoods": article.get("neighborhoods") or [],
        "infos_pratiques": article.get("infos_pratiques") or {},
        "faq": article.get("faq") or [],
        "sources": article.get("sources") or [],
        "tags": article.get("tags") or [],
        "itinerary": None,  # drop the legacy 3-day block
        "word_count": article.get("word_count"),
        "generated_at": article.get("generated_at"),
    }
    try:
        db.table("articles").update(update).eq("iata", iata).execute()
        logger.info("Article regenerated for %s (new format, %s words)",
                    iata, article.get("word_count"))
        return True
    except Exception as e:
        logger.error("Regen update failed for %s: %s", iata, e)
        return False
