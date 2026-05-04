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


def _reverify_via_vueling(
    origin: str, destination: str, departure_date: str, initial_price: float
) -> bool | None:
    """Re-verify via Vueling direct endpoint. Returns None if not covered.

    Vueling's GetAllFlights endpoint takes (year, month, day, monthsRange)
    and returns the cheapest fare per departure day across the range. We
    request a 1-month window centred on the departure month and look up
    the requested date in the response."""
    try:
        from app.scraper.tier1_vueling import get_calendar_fares, is_demoted
        if is_demoted(origin, destination):
            return None
        # Parse YYYY-MM-DD into year/month for the API call.
        try:
            year = int(departure_date[:4])
            month = int(departure_date[5:7])
        except (ValueError, IndexError):
            return None
        fares = get_calendar_fares(
            origin=origin,
            destination=destination,
            year=year,
            month=month,
            months_range=1,
        )
        max_acceptable = initial_price * (1.0 + PRICE_TOLERANCE_PCT / 100.0)
        for fare in fares:
            if fare.get("departure_date") == departure_date:
                if 0 < fare["price"] <= max_acceptable:
                    return True
        return False if fares else None
    except Exception as e:
        logger.warning(f"Vueling reverify {origin}->{destination}: {e}")
        return None


def _reverify_via_travelpayouts(
    origin: str, destination: str, departure_date: str, return_date: str | None,
    initial_price: float, tolerance_pct: float = PRICE_TOLERANCE_PCT,
) -> tuple[bool | None, float | None]:
    """Cross-check the live A/R price via Travelpayouts.

    Returns a tuple `(verdict, cheapest_match)`:
      - verdict True if TP confirms a fare close to `initial_price`,
        False if TP returns prices that are too high (> tolerance),
        None if TP returned nothing for that route.
      - cheapest_match: the cheapest TP fare matching the dates, or
        None when no match was found.

    Used as a sanity gate behind the calendar-based Tier 1 endpoints,
    which expose ONE-WAY prices and can mislead the pipeline if their
    A/R extrapolation is off. The cheapest_match is exposed so the
    caller can adopt the more accurate TP price when it's higher than
    our Tier 1 estimate (still within tolerance) — that way the
    Telegram alert quotes the price the user actually sees on click.
    """
    try:
        results = get_prices_for_dates(origin, destination)
    except Exception as e:
        logger.warning(f"TP cross-check {origin}->{destination}: {e}")
        return None, None
    if not results:
        return None, None
    max_acceptable = initial_price * (1.0 + tolerance_pct / 100.0)
    cheapest_match: float | None = None
    for entry in results:
        if entry.get("departure_at", "")[:10] != departure_date:
            continue
        if return_date and entry.get("return_at", "")[:10] != return_date:
            continue
        live_price = float(entry.get("price") or 0)
        if live_price <= 0:
            continue
        if cheapest_match is None or live_price < cheapest_match:
            cheapest_match = live_price
    if cheapest_match is None:
        return None, None
    return cheapest_match <= max_acceptable, cheapest_match


async def reverify_flight_price(flight: dict) -> bool:
    """Return True if the deal is still valid, False otherwise.

    For Tier 1 routes: tries Ryanair direct first, then Transavia direct,
    then falls back to Travelpayouts if both return None (not covered).

    For Tier 2 routes: uses Travelpayouts only (unchanged behaviour).

    For Vueling Tier 1 in particular, the calendar endpoint exposes
    one-way leadprices that we double to estimate an A/R. To catch
    cases where the estimate diverges from the real Aviasales market
    price (which is what the user lands on after clicking), we add a
    second-source cross-check against Travelpayouts. A mismatch >
    PRICE_TOLERANCE_PCT against the live TP A/R rejects the deal.

    Any unrecoverable API error returns False."""
    origin = flight["origin"]
    destination = flight["destination"]
    initial_price = float(flight["price"])
    departure_date = flight["departure_date"]
    return_date = flight["return_date"]
    source = flight.get("source", "")

    # --- Tier 1: try direct endpoints first ---
    if _is_tier1_route(origin, destination):
        # Build a priority list. The fare's own source goes first because
        # confirming a Vueling fare via Vueling (or a Ryanair fare via
        # Ryanair) is the most accurate. Other endpoints serve as a
        # cross-check/fallback when the primary source returns nothing.
        ordered: list[str] = []
        if source == "vueling_direct":
            ordered = ["vueling", "ryanair"]
        elif source == "ryanair_direct":
            ordered = ["ryanair", "vueling"]
        else:
            # travelpayouts or unknown: try both, ryanair first by convention.
            ordered = ["ryanair", "vueling"]

        for kind in ordered:
            if kind == "ryanair":
                result = _reverify_via_ryanair(origin, destination, departure_date, return_date, initial_price)
                tag = "Ryanair"
            elif kind == "vueling":
                result = _reverify_via_vueling(origin, destination, departure_date, initial_price)
                tag = "Vueling"
            else:
                continue
            if result is not None:
                # For Vueling fares, do NOT trust the same-source calendar
                # alone — it confirms the leadprice we already saw.
                # Cross-check against Travelpayouts to confirm the live
                # A/R matches what the user will see on Aviasales.
                if result and source == "vueling_direct" and tag == "Vueling":
                    # Cross-check against Travelpayouts. Two-sided gate:
                    # - if TP is materially HIGHER than our estimate
                    #   (>+50%), our 2.2× extrapolation was way off →
                    #   reject; the user would land on a price they'd
                    #   feel was misleading.
                    # - if TP is materially LOWER than our estimate
                    #   (-30% or more), we'd be advertising a deal that
                    #   isn't actually a deal — the user clicks and
                    #   immediately sees a much cheaper fare on
                    #   Aviasales. Reject too. This caught a real
                    #   incident on 2026-05-04: alert dispatched at
                    #   422€ when TP showed 294€ for the same route/
                    #   dates, with Wizz at 122€ on Aviasales.
                    _, tp_cheapest = _reverify_via_travelpayouts(
                        origin, destination, departure_date, return_date, initial_price,
                        tolerance_pct=50.0,
                    )
                    if tp_cheapest is not None and tp_cheapest > initial_price * 1.5:
                        logger.info(
                            f"Reverify Vueling {origin}->{destination} {departure_date}: "
                            f"OK at source but REJECTED — TP quotes {tp_cheapest}€ vs "
                            f"our {initial_price}€ estimate (>+50%)"
                        )
                        return False
                    if tp_cheapest is not None and tp_cheapest < initial_price * 0.70:
                        logger.info(
                            f"Reverify Vueling {origin}->{destination} {departure_date}: "
                            f"OK at source but REJECTED — TP cheaper at {tp_cheapest}€ vs "
                            f"our {initial_price}€ (-{round((1 - tp_cheapest/initial_price)*100)}%); "
                            f"user would land on a much cheaper fare"
                        )
                        return False
                    # If TP returns a higher (but plausible) price than
                    # our 2.2× estimate, adopt it. The user will see the
                    # exact price we promise. We only bump up, never
                    # down, so we don't turn a real bargain into a
                    # non-deal because TP happens to surface a slightly
                    # cheaper fare (the under-30% gap kept above).
                    if tp_cheapest is not None and tp_cheapest > initial_price:
                        flight["price"] = round(tp_cheapest, 2)
                        flight["_price_source"] = "tp_cross_check"
                        logger.info(
                            f"Reverify Vueling {origin}->{destination} {departure_date}: "
                            f"price adjusted from {initial_price}€ to {tp_cheapest}€ "
                            f"per Travelpayouts cross-check"
                        )
                if result:
                    logger.info(f"Reverify {tag} {origin}->{destination} {departure_date}: OK")
                else:
                    logger.info(f"Reverify {tag} {origin}->{destination} {departure_date}: REJECTED")
                return result

        # Try Transavia (kept for backward-compat, currently always None
        # because the scraper is globally disabled).
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
