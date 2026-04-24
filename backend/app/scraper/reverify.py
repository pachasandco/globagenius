"""Real-time price re-verification before alerting.

Two-tier strategy:
- Tier 1 routes (Ryanair/Transavia direct): re-fetch via the same direct
  endpoint that produced the deal — sub-minute freshness.
- Tier 2 routes (Travelpayouts): re-fetch via Travelpayouts as before.

This eliminates the cache-lag problem on Tier 1: we never confirm a deal
using a stale cache that already contained the deal we're verifying."""

import logging
from app.scraper.travelpayouts import get_prices_for_dates

logger = logging.getLogger(__name__)

PRICE_TOLERANCE_PCT = 5.0  # accept up to 5% price increase since the scrape


def _is_tier1_route(origin: str, destination: str) -> bool:
    """True if this route is in the Tier 1 list."""
    try:
        from app.scraper.tier1_routes import TIER1_ROUTES
        return any(o == origin and d == destination for o, d, _ in TIER1_ROUTES)
    except Exception:
        return False


def _reverify_via_ryanair(
    origin: str, destination: str, departure_date: str, return_date: str, initial_price: float
) -> bool | None:
    """Re-verify via Ryanair direct endpoint. Returns None if not covered."""
    try:
        from app.scraper.tier1_ryanair import get_cheapest_fares, is_demoted
        if is_demoted(origin, destination):
            return None
        fares = get_cheapest_fares(
            origin=origin,
            destination=destination,
            outbound_date_from=departure_date,
            outbound_date_to=departure_date,
            inbound_date_from=return_date,
            inbound_date_to=return_date,
        )
        max_acceptable = initial_price * (1.0 + PRICE_TOLERANCE_PCT / 100.0)
        for fare in fares:
            if fare.get("departure_date") == departure_date and fare.get("return_date") == return_date:
                if 0 < fare["price"] <= max_acceptable:
                    return True
        return False if fares else None  # None = endpoint returned nothing, try next
    except Exception as e:
        logger.warning(f"Ryanair reverify {origin}->{destination}: {e}")
        return None


def _reverify_via_transavia(
    origin: str, destination: str, departure_date: str, initial_price: float
) -> bool | None:
    """Re-verify via Transavia direct endpoint. Returns None if not covered."""
    try:
        from app.scraper.tier1_transavia import get_lowest_fares, is_demoted
        if is_demoted(origin, destination):
            return None
        fares = get_lowest_fares(
            origin=origin,
            destination=destination,
            outbound_date_from=departure_date,
            outbound_date_to=departure_date,
        )
        max_acceptable = initial_price * (1.0 + PRICE_TOLERANCE_PCT / 100.0)
        for fare in fares:
            if fare.get("departure_date") == departure_date:
                if 0 < fare["price"] <= max_acceptable:
                    return True
        return False if fares else None
    except Exception as e:
        logger.warning(f"Transavia reverify {origin}->{destination}: {e}")
        return None


async def reverify_flight_price(flight: dict) -> bool:
    """Return True if the deal is still valid, False otherwise.

    For Tier 1 routes: tries Ryanair direct first, then Transavia direct,
    then falls back to Travelpayouts if both return None (not covered).

    For Tier 2 routes: uses Travelpayouts only (unchanged behaviour).

    Any unrecoverable API error returns False."""
    origin = flight["origin"]
    destination = flight["destination"]
    initial_price = float(flight["price"])
    departure_date = flight["departure_date"]
    return_date = flight["return_date"]
    source = flight.get("source", "")

    # --- Tier 1: try direct endpoints first ---
    if _is_tier1_route(origin, destination):
        # Try Ryanair
        if source == "ryanair_direct" or source == "travelpayouts":
            result = _reverify_via_ryanair(origin, destination, departure_date, return_date, initial_price)
            if result is not None:
                if result:
                    logger.info(f"Reverify Ryanair {origin}->{destination} {departure_date}: OK")
                else:
                    logger.info(f"Reverify Ryanair {origin}->{destination} {departure_date}: REJECTED")
                return result

        # Try Transavia
        result = _reverify_via_transavia(origin, destination, departure_date, initial_price)
        if result is not None:
            if result:
                logger.info(f"Reverify Transavia {origin}->{destination} {departure_date}: OK")
            else:
                logger.info(f"Reverify Transavia {origin}->{destination} {departure_date}: REJECTED")
            return result

        logger.info(f"Reverify Tier1 {origin}->{destination}: direct endpoints returned nothing, falling back to Travelpayouts")

    # --- Tier 2 (or Tier 1 fallback): Travelpayouts ---
    try:
        results = get_prices_for_dates(origin, destination)
    except Exception as e:
        logger.warning(f"Reverify {origin}->{destination}: Travelpayouts exception {e}")
        return False

    if not results:
        logger.info(f"Reverify {origin}->{destination}: Travelpayouts returned no results, rejecting")
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
                f"Reverify TP {origin}->{destination} {departure_date}: "
                f"OK (initial={initial_price}€, live={live_price}€)"
            )
            return True

    logger.info(
        f"Reverify {origin}->{destination} {departure_date}: "
        f"REJECTED (initial={initial_price}€, no match within {PRICE_TOLERANCE_PCT}%)"
    )
    return False
