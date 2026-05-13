"""Backfill cover_photo on existing guides that were saved without one.

Earlier versions of `ensure_article_for_destination` would insert a guide
even when the Unsplash search returned no results, leaving the row with
`cover_photo=""`. The writer now skips insertion in that case, but the
guides created before that fix still need their photo.

This script walks every article with an IATA but no cover_photo, runs
the Unsplash search with progressively-broader queries (mirrors what the
writer does), and updates the row in place. Idempotent: rows that
already have a photo are left alone, and queries that still find nothing
are skipped (logged as warning) rather than overwritten with junk.

Run from the backend dir with the prod .env loaded:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/backfill_missing_cover_photos.py
"""
import logging
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_photos")

from app.db import db
from app.notifications.unsplash import fetch_destination_photo


def main() -> int:
    if not db:
        print("FAIL: db not configured")
        return 1

    rows = (
        db.table("articles")
        .select("iata,destination,country,cover_photo")
        .not_.is_("iata", "null")
        .execute()
    )
    candidates = [
        r for r in (rows.data or [])
        if not (r.get("cover_photo") or "").strip()
    ]
    logger.info("Found %d guides without cover_photo", len(candidates))

    fixed = skipped = 0
    for r in candidates:
        iata = (r.get("iata") or "").upper()
        destination = r.get("destination") or ""
        country = r.get("country") or ""

        # Strip airport descriptors that confuse Unsplash search ("Londres
        # Stansted" -> "Londres", "Milan Bergame" -> "Milan"). The first
        # word of a multi-word destination name is almost always the city
        # itself in our catalogue.
        city_only = destination.split(" ")[0] if destination else ""

        queries: list[str] = []
        if destination:
            queries.append(destination)
        if city_only and city_only != destination:
            queries.append(city_only)
        if destination and country:
            queries.append(f"{destination} {country}".strip())
        if city_only and country:
            queries.append(f"{city_only} {country}".strip())
        if country:
            queries.append(country)
        if city_only:
            queries.append(f"{city_only} skyline")
        # Deduplicate while preserving order.
        seen: set[str] = set()
        queries = [q for q in queries if q and not (q in seen or seen.add(q))]

        photo = None
        used_query: str | None = None
        for q in queries:
            photo = fetch_destination_photo(iata, query_hint=q)
            if photo:
                used_query = q
                break
            # Polite delay between Unsplash calls so we don't trip the
            # 50 req / hour rate limit on the demo plan.
            time.sleep(0.4)

        if not photo:
            logger.warning(
                "No Unsplash result for %s after %d queries (%s) — leaving row untouched",
                iata, len(queries), queries,
            )
            skipped += 1
            continue

        try:
            db.table("articles").update({
                "cover_photo": photo["url"],
                "photo_id": photo["photo_id"],
                "photographer_name": photo["photographer_name"],
                "photographer_url": photo["photographer_url"],
            }).eq("iata", iata).execute()
            logger.info(
                "Updated %s (%s) via query %r -> %s by %s",
                iata, destination, used_query, photo["url"][:60], photo["photographer_name"],
            )
            fixed += 1
        except Exception as e:
            logger.error("Update failed for %s: %s", iata, e)
            skipped += 1

        # Polite delay between rows.
        time.sleep(0.5)

    logger.info("Done. fixed=%d skipped=%d", fixed, skipped)
    return 0 if skipped == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
