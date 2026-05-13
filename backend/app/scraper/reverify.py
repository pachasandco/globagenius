"""Real-time price re-verification before alerting.

Two-tier strategy:
- Tier 1 routes (Ryanair/Transavia direct): re-fetch via the same direct
  endpoint that produced the deal — sub-minute freshness.
- Tier 2 routes (Travelpayouts): re-fetch via Travelpayouts as before.

This eliminates the cache-lag problem on Tier 1: we never confirm a deal
using a stale cache that already contained the deal we're verifying.

Credibility safeguard (2026-05): every Tier 1 confirmation is now also
cross-checked against Travelpayouts before dispatch — the user lands on
an Aviasales URL after clicking, and TP is exactly the source backing
that page. If our Tier 1 number diverges materially from what TP would
show, we'd be advertising a price the user won't actually see. The
cross-check has three outcomes:

- TP much higher than our estimate (>+15%): reject. The user would land
  on a meaningfully more expensive page → broken promise.
- TP much lower than our estimate (-30% or more): reject. Some other
  carrier on the same route is cheaper than what we're advertising →
  the alert isn't a deal once the user sees the cheapest fare.
- TP within band: when TP > initial (within +15%), adopt the TP price
  so the alert quotes exactly what the user sees on click.

The flight dict is annotated with `_price_confidence` so the Telegram
formatter can drop the "✅ Vol vérifié" claim when only one source
confirmed the price.
"""

import logging
from app.scraper.travelpayouts import get_prices_for_dates

logger = logging.getLogger(__name__)

# Tightened from 5% to 3% (2026-05). With 5%, a 53€ alert could land on
# a 55–56€ page — small absolute gap but consistent enough to feel like
# bait-and-switch. 3% keeps the gap below ~2€ on typical short-haul fares.
PRICE_TOLERANCE_PCT = 3.0

# Cross-check bounds against Travelpayouts. TP is what the user actually
# sees on click (Aviasales is a TP product). These bounds replace the
# Vueling-only 50% / 30% pair with stricter, universal limits.
#
# The upper bound is asymmetric on purpose: a 15% over-quote burns
# credibility ("you said 80€, it's 95€"); a 30% under-quote burns it
# differently ("you said 80€, but Wizz at 56€ is right there"). Both
# are rejection conditions.
TP_CROSS_CHECK_REJECT_HIGH = 1.15  # TP >  initial * 1.15 → reject
TP_CROSS_CHECK_REJECT_LOW = 0.70   # TP <  initial * 0.70 → reject
TP_CROSS_CHECK_ADOPT_MAX = 1.10    # initial < TP ≤ initial * 1.10 → adopt TP


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


def _apply_tp_cross_check(flight: dict, tag: str) -> bool:
    """Cross-check the current price against Travelpayouts; mutate flight on adoption.

    Common gate applied behind every Tier 1 confirmation. TP is what the
    user lands on after clicking the Aviasales URL — if our Tier 1
    quote diverges from TP's view of the same route/dates, we'd be
    advertising a price the user won't actually see.

    Returns True when the deal survives the cross-check (either
    confirmed by TP, or no TP data found at all so we keep the Tier 1
    quote). Sets `_price_confidence` to one of:
      - "confirmed_tp"   : TP returned a comparable price, deal stands
      - "single_source"  : TP returned nothing, only the direct source
                           confirms — lower confidence
    Returns False when TP data exists but contradicts our quote enough
    to reject the alert.
    """
    origin = flight["origin"]
    destination = flight["destination"]
    departure_date = flight["departure_date"]
    return_date = flight["return_date"]
    initial_price = float(flight["price"])

    _, tp_cheapest = _reverify_via_travelpayouts(
        origin, destination, departure_date, return_date, initial_price,
        tolerance_pct=(TP_CROSS_CHECK_REJECT_HIGH - 1.0) * 100.0,
    )

    if tp_cheapest is None:
        # No TP data for this exact (route, dates). Keep the Tier 1
        # quote but flag lower confidence so the Telegram copy can
        # drop the "Vol vérifié" claim.
        flight["_price_confidence"] = "single_source"
        logger.info(
            f"Reverify {tag} {origin}->{destination} {departure_date}: "
            f"OK at source, TP has no data → single_source confidence"
        )
        return True

    if tp_cheapest > initial_price * TP_CROSS_CHECK_REJECT_HIGH:
        logger.info(
            f"Reverify {tag} {origin}->{destination} {departure_date}: "
            f"OK at source but REJECTED — TP quotes {tp_cheapest}€ vs "
            f"our {initial_price}€ "
            f"(+{round((tp_cheapest/initial_price - 1)*100)}%, "
            f"limit {round((TP_CROSS_CHECK_REJECT_HIGH - 1)*100)}%)"
        )
        return False

    if tp_cheapest < initial_price * TP_CROSS_CHECK_REJECT_LOW:
        logger.info(
            f"Reverify {tag} {origin}->{destination} {departure_date}: "
            f"OK at source but REJECTED — TP cheaper at {tp_cheapest}€ vs "
            f"our {initial_price}€ (-{round((1 - tp_cheapest/initial_price)*100)}%); "
            f"user would land on a much cheaper fare"
        )
        return False

    # Within band. Adopt TP price when it's higher than our quote (within
    # ADOPT_MAX), so the alert promises exactly what the user will see.
    # Never adjust downward — that would turn a real bargain into a
    # non-deal because TP surfaces a slightly cheaper fare.
    if initial_price < tp_cheapest <= initial_price * TP_CROSS_CHECK_ADOPT_MAX:
        flight["price"] = round(tp_cheapest, 2)
        flight["_price_source"] = "tp_cross_check"
        logger.info(
            f"Reverify {tag} {origin}->{destination} {departure_date}: "
            f"price adjusted from {initial_price}€ to {tp_cheapest}€ "
            f"per Travelpayouts cross-check"
        )

    flight["_price_confidence"] = "confirmed_tp"
    logger.info(
        f"Reverify {tag} {origin}->{destination} {departure_date}: "
        f"OK + TP confirmed (quoted={flight['price']}€, tp={tp_cheapest}€)"
    )
    return True


async def reverify_flight_price(flight: dict) -> bool:
    """Return True if the deal is still valid, False otherwise.

    For Tier 1 routes: tries the direct endpoint that produced the deal
    first, then falls back to Travelpayouts if it returns nothing. Every
    Tier 1 confirmation is then cross-checked against Travelpayouts via
    `_apply_tp_cross_check` — the user lands on an Aviasales URL after
    clicking, and Aviasales is a TP product. A divergence between our
    Tier 1 quote and TP's view either rejects the alert or adopts the
    higher TP number so we promise exactly what the user will see.

    For Tier 2 routes: uses Travelpayouts only (unchanged behaviour).

    Sets `flight["_price_confidence"]` so the Telegram formatter can
    differentiate alerts where TP confirmed the price (high confidence,
    "✅ Prix Aviasales confirmé") from those where only one source
    confirms ("🔍 Prix indicatif").

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
            if result is None:
                # Endpoint returned nothing, try the next one.
                continue
            if not result:
                logger.info(f"Reverify {tag} {origin}->{destination} {departure_date}: REJECTED")
                return False
            # Direct source confirmed → universal TP cross-check before
            # we hand the deal to dispatch. This catches the cases where
            # our Tier 1 number is right but doesn't match what the user
            # will see on Aviasales.
            return _apply_tp_cross_check(flight, tag)

        # Try Transavia (kept for backward-compat, currently always None
        # because the scraper is globally disabled).
        result = _reverify_via_transavia(origin, destination, departure_date, initial_price)
        if result is not None:
            if not result:
                logger.info(f"Reverify Transavia {origin}->{destination} {departure_date}: REJECTED")
                return False
            return _apply_tp_cross_check(flight, "Transavia")

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
            # TP itself confirmed → highest possible confidence for the
            # Aviasales URL we'll send (the user lands on this exact
            # source).
            flight["_price_confidence"] = "confirmed_tp"
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
