"""Tier 1 scraper — Ryanair direct JSON endpoint.

Uses Ryanair's non-official but stable availability endpoint.
Covers CDG, ORY, BVA and all Ryanair-served routes.

Polling: every 15-30 min on hot routes (configured in TIER1_ROUTES).
Fallback: if 3 consecutive failures, route is demoted to Travelpayouts.
"""

import logging
import httpx
from datetime import datetime, timedelta, timezone
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

SOURCE = "ryanair_direct"

# Ryanair availability API — returns cheapest prices per date range
_BASE = "https://www.ryanair.com/api/farfnd/v4"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.ryanair.com/fr/fr",
}

# Failure counter per route — reset on success
_failure_counts: dict[str, int] = {}
MAX_FAILURES = 3


def _mark_failure(route_key: str) -> bool:
    """Increment failure counter. Returns True if route should be demoted."""
    _failure_counts[route_key] = _failure_counts.get(route_key, 0) + 1
    return _failure_counts[route_key] >= MAX_FAILURES


def _mark_success(route_key: str) -> None:
    _failure_counts.pop(route_key, None)


def is_demoted(origin: str, destination: str) -> bool:
    """True if this route has hit MAX_FAILURES and should use Travelpayouts fallback."""
    return _failure_counts.get(f"{origin}-{destination}", 0) >= MAX_FAILURES


def get_cheapest_fares(
    origin: str,
    destination: str,
    outbound_date_from: str,
    outbound_date_to: str,
    inbound_date_from: str = "",
    inbound_date_to: str = "",
    flex_days_out: int = 6,
    flex_days_in: int = 6,
) -> list[dict]:
    """Fetch cheapest round-trip fares from Ryanair for a date window.

    outbound_date_from / outbound_date_to: YYYY-MM-DD window for departure.
    inbound_date_from / inbound_date_to: YYYY-MM-DD window for return.
    flex_days_out / flex_days_in: flexibility in days around each bound.

    Returns list of normalized flight dicts (same format as raw_flights).
    """
    route_key = f"{origin}-{destination}"
    params = {
        "departureAirportIataCode": origin,
        "arrivalAirportIataCode": destination,
        "outboundDepartureDateFrom": outbound_date_from,
        "outboundDepartureDateTo": outbound_date_to,
        "currency": "EUR",
        "priceValueTo": 9999,
        "outboundDepartureDaysOfWeek": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY,SUNDAY",
        "inboundDepartureDaysOfWeek": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY,SUNDAY",
    }
    if inbound_date_from:
        params["inboundDepartureDateFrom"] = inbound_date_from
    if inbound_date_to:
        params["inboundDepartureDateTo"] = inbound_date_to

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(
                f"{_BASE}/roundTripFares",
                params=params,
                headers=_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(f"Ryanair rate-limited on {route_key}")
        else:
            logger.warning(f"Ryanair HTTP {e.response.status_code} on {route_key}")
        if _mark_failure(route_key):
            logger.warning(f"Ryanair {route_key} demoted to Travelpayouts after {MAX_FAILURES} failures")
        return []
    except Exception as e:
        logger.warning(f"Ryanair request failed for {route_key}: {e}")
        if _mark_failure(route_key):
            logger.warning(f"Ryanair {route_key} demoted to Travelpayouts after {MAX_FAILURES} failures")
        return []

    _mark_success(route_key)

    fares = data.get("fares") or []
    results = []
    for fare in fares:
        outbound = fare.get("outbound") or {}
        inbound = fare.get("inbound") or {}
        summary = fare.get("summary") or {}

        dep_date = (outbound.get("departureDate") or "")[:10]
        ret_date = (inbound.get("departureDate") or "")[:10]
        price = summary.get("price", {}).get("value") or outbound.get("price", {}).get("value")

        if not dep_date or not ret_date or not price:
            continue

        try:
            dep_dt = datetime.strptime(dep_date, "%Y-%m-%d")
            ret_dt = datetime.strptime(ret_date, "%Y-%m-%d")
            trip_duration_days = (ret_dt - dep_dt).days
        except ValueError:
            continue

        if trip_duration_days < 1 or trip_duration_days > 12:
            continue

        raw = {
            "price": float(price),
            "currency": "EUR",
            "origin": origin,
            "destination": destination,
            "departureDate": dep_date,
            "returnDate": ret_date,
            "airline": "FR",  # Ryanair IATA code
            "stops": 0,  # Ryanair is always direct
            "url": (
                f"https://www.ryanair.com/fr/fr/trip/flights/select"
                f"?adults=1&dateOut={dep_date}&dateIn={ret_date}"
                f"&originIata={origin}&destinationIata={destination}"
            ),
        }

        normalized = normalize_flight(raw, source=SOURCE)
        normalized["trip_duration_days"] = trip_duration_days
        normalized["duration_minutes"] = 0  # not provided by this endpoint
        results.append(normalized)

    return results


def scrape_route(origin: str, destination: str) -> list[dict]:
    """Scrape one Ryanair Tier 1 route for the next 8 months.

    Strategy: query overlapping 14-day departure windows. The Ryanair
    /roundTripFares endpoint returns ONE cheapest fare per call, and that
    fare tends to use the longest possible trip duration in the window
    requested. To get short A/R (1-12 days), we MUST keep the window
    narrow. With 14-day departure windows and a 14-day return window
    that follows immediately, the API returns trips of ~7-13 days.

    We sweep the next ~8 months in 14-day departure steps."""
    if is_demoted(origin, destination):
        return []

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    all_flights = []
    seen_keys: set[str] = set()

    # 16 windows of 14 days each = ~ 7.5 months ahead, starting at day +14.
    consecutive_empty = 0
    for chunk in range(16):
        dep_from = (today + timedelta(days=14 + chunk * 14)).strftime("%Y-%m-%d")
        dep_to   = (today + timedelta(days=27 + chunk * 14)).strftime("%Y-%m-%d")
        # Return window: 4 days after dep_from to 14 days after dep_to,
        # capping trip duration to about 1-12 days.
        ret_from = (today + timedelta(days=18 + chunk * 14)).strftime("%Y-%m-%d")
        ret_to   = (today + timedelta(days=39 + chunk * 14)).strftime("%Y-%m-%d")

        flights = get_cheapest_fares(
            origin=origin,
            destination=destination,
            outbound_date_from=dep_from,
            outbound_date_to=dep_to,
            inbound_date_from=ret_from,
            inbound_date_to=ret_to,
        )

        if flights:
            consecutive_empty = 0
            # Dedup across overlapping windows on (dep, ret, price)
            for f in flights:
                k = f"{f.get('departure_date')}|{f.get('return_date')}|{f.get('price')}"
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                all_flights.append(f)
        else:
            consecutive_empty += 1
            # Bail out after 3 consecutive empty windows — route likely
            # has no service in that period or is fully booked.
            if consecutive_empty >= 3:
                break

    if all_flights:
        logger.info(f"Ryanair Tier1 {origin}->{destination}: {len(all_flights)} fares (across windows)")

    return all_flights
