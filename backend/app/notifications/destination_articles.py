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

    # Fetch cover photo. Best-effort — a missing photo doesn't block insertion.
    photo_query = article.get("photo_query") or article.get("destination") or iata
    photo = fetch_destination_photo(iata, query_hint=photo_query)
    if photo:
        article["cover_photo"] = photo["url"]
        article["photo_id"] = photo["photo_id"]
        article["photographer_name"] = photo["photographer_name"]
        article["photographer_url"] = photo["photographer_url"]
    else:
        # Explicit empty values so the column exists and frontend can
        # branch cleanly on falsy checks.
        article["cover_photo"] = ""
        article["photo_id"] = ""
        article["photographer_name"] = ""
        article["photographer_url"] = ""

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
