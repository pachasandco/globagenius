"""Real-time price re-verification before alerting.

Just before we insert a qualified_item, we re-fetch the route from
Travelpayouts and confirm the deal still exists at a comparable price.
This catches stale or expired offers, protecting users from false alerts."""

import logging
from app.scraper.travelpayouts import get_prices_for_dates

logger = logging.getLogger(__name__)

PRICE_TOLERANCE_PCT = 5.0  # accept up to 5% price increase since the scrape


async def reverify_flight_price(flight: dict) -> bool:
    """Return True if the deal is still valid, False otherwise.

    A deal is valid if the live API still returns at least one round-trip
    matching the same departure_date and return_date, at a price no more
    than PRICE_TOLERANCE_PCT above the originally-scraped price.

    Any API error returns False (better safe than sorry — we never
    show a deal we couldn't confirm)."""
    origin = flight["origin"]
    destination = flight["destination"]
    initial_price = float(flight["price"])
    departure_date = flight["departure_date"]
    return_date = flight["return_date"]

    try:
        results = get_prices_for_dates(origin, destination)
    except Exception as e:
        logger.warning(f"Reverify {origin}->{destination}: API exception {e}")
        return False

    if not results:
        logger.info(f"Reverify {origin}->{destination}: API returned no results, rejecting")
        return False

    max_acceptable = initial_price * (1.0 + PRICE_TOLERANCE_PCT / 100.0)

    for entry in results:
        if entry.get("departure_at", "")[:10] != departure_date:
            continue
        if entry.get("return_at", "")[:10] != return_date:
            continue
        live_price = float(entry.get("price") or 0)
        if 0 < live_price <= max_acceptable:
            logger.info(
                f"Reverify {origin}->{destination} {departure_date}->{return_date}: "
                f"OK (initial={initial_price}€, live={live_price}€, tolerance={max_acceptable:.0f}€)"
            )
            return True

    logger.info(
        f"Reverify {origin}->{destination} {departure_date}->{return_date}: "
        f"REJECTED (initial={initial_price}€, no matching entry within {PRICE_TOLERANCE_PCT}% tolerance)"
    )
    return False
