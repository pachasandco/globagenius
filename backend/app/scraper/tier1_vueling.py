"""Tier 1 scraper — Vueling direct JSON endpoint.

Vueling (VY) operates from CDG, ORY, BCN and several French airports.
Their public booking widget calls https://apiwww.vueling.com/api which
returns one cheapest fare per departure date, no auth required.

Polling: every 20 min alongside Ryanair (Tier 1 cycle).
Fallback: per-route demotion to Travelpayouts after MAX_FAILURES.

Note: the calendar endpoint returns OUTBOUND-only fares (one-way prices
per departure day). For round-trip parity with the rest of the pipeline
we approximate the return at +7 days, which matches our typical short-
break window. Real return prices are reconciled later via Travelpayouts.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

SOURCE = "vueling_direct"

# Public booking-widget API. Found in the inline JS of
# https://www.vueling.com/en/book-your-flight/find-your-flight
# (`var corporative7ApiUrl = "https://apiwww.vueling.com/api/"`).
_BASE = "https://apiwww.vueling.com/api"

_HEADERS = {
    # Akamai 401s a bare python-requests UA — use a real browser UA.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.vueling.com/",
    "Origin": "https://www.vueling.com",
}

_failure_counts: dict[str, int] = {}
MAX_FAILURES = 3


def _mark_failure(route_key: str) -> bool:
    _failure_counts[route_key] = _failure_counts.get(route_key, 0) + 1
    return _failure_counts[route_key] >= MAX_FAILURES


def _mark_success(route_key: str) -> None:
    _failure_counts.pop(route_key, None)


def is_demoted(origin: str, destination: str) -> bool:
    return _failure_counts.get(f"{origin}-{destination}", 0) >= MAX_FAILURES


def get_calendar_fares(
    origin: str,
    destination: str,
    year: int,
    month: int,
    months_range: int = 3,
) -> list[dict]:
    """Fetch cheapest fares from Vueling for a (year, month) window.

    The endpoint returns one cheapest flight per calendar day across
    `months_range` months starting at the given (year, month, day=1).
    No auth, just a normal-browser User-Agent.
    """
    route_key = f"{origin}-{destination}"

    params = {
        "originCode": origin,
        "destinationCode": destination,
        "year": str(year),
        "month": str(month),
        "day": "1",
        "currencyCode": "EUR",
        "monthsRange": str(months_range),
    }

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(
                f"{_BASE}/FlightPrice/GetAllFlights",
                params=params,
                headers=_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(f"Vueling rate-limited on {route_key}")
        else:
            logger.warning(
                f"Vueling HTTP {e.response.status_code} on {route_key}"
            )
        if _mark_failure(route_key):
            logger.warning(
                f"Vueling {route_key} demoted to Travelpayouts after {MAX_FAILURES} failures"
            )
        return []
    except Exception as e:
        logger.warning(f"Vueling request failed for {route_key}: {e}")
        if _mark_failure(route_key):
            logger.warning(
                f"Vueling {route_key} demoted to Travelpayouts after {MAX_FAILURES} failures"
            )
        return []

    _mark_success(route_key)

    # Endpoint returns a JSON array of items shaped like:
    #   {DepartureDate: "2026-06-01T05:10:00", ArrivalDate: "...",
    #    Price: 95.99, IsInvalidPrice: false, ClassOfService: "N", ...}
    if not isinstance(data, list):
        logger.warning(f"Vueling unexpected response shape for {route_key}: {type(data).__name__}")
        return []

    results = []
    for fare in data:
        if not isinstance(fare, dict):
            continue
        if fare.get("IsInvalidPrice"):
            continue

        dep_raw = fare.get("DepartureDate") or ""
        dep_date = dep_raw[:10]
        if not dep_date:
            continue

        price = fare.get("Price")
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue

        try:
            dep_dt = datetime.strptime(dep_date, "%Y-%m-%d")
        except ValueError:
            continue

        # Calendar endpoint is one-way per day. Approximate return at +7d
        # so the row fits the round-trip pipeline schema. Real return is
        # reconciled later via Travelpayouts when both legs match.
        ret_dt = dep_dt + timedelta(days=7)
        ret_date = ret_dt.strftime("%Y-%m-%d")
        trip_duration_days = 7

        raw = {
            "price": price,
            "currency": "EUR",
            "origin": origin,
            "destination": destination,
            "departureDate": dep_date,
            "returnDate": ret_date,
            "airline": "VY",  # Vueling IATA code
            "stops": 0,
            "url": (
                f"https://tickets.vueling.com/searchAvailability.html"
                f"?marketDateOut={dep_date}&marketDateIn={ret_date}"
                f"&marketOrigin={origin}&marketDestination={destination}"
                f"&marketAdt=1&marketCurrency=EUR"
            ),
        }

        normalized = normalize_flight(raw, source=SOURCE)
        normalized["trip_duration_days"] = trip_duration_days
        normalized["duration_minutes"] = 0
        results.append(normalized)

    return results


def scrape_route(origin: str, destination: str) -> list[dict]:
    """Scrape one Vueling Tier 1 route for the next ~7 months.

    Sweeps in two `monthsRange=3` calls to cover ~6 months. Smaller spans
    keep the response payload manageable and avoid timeouts."""
    if is_demoted(origin, destination):
        return []

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    all_flights: list[dict] = []
    seen_keys: set[str] = set()

    # Two contiguous month-windows: [today, +3m) and [+3m, +6m).
    for offset in (0, 3):
        start = today.replace(day=1) + timedelta(days=offset * 30)
        flights = get_calendar_fares(
            origin=origin,
            destination=destination,
            year=start.year,
            month=start.month,
            months_range=3,
        )
        if not flights:
            # Likely demoted by now or no service in that window.
            break

        # Dedup across overlapping months on (dep, ret, price).
        for f in flights:
            k = f"{f.get('departure_date')}|{f.get('return_date')}|{f.get('price')}"
            if k in seen_keys:
                continue
            seen_keys.add(k)
            all_flights.append(f)

    if all_flights:
        logger.info(
            f"Vueling Tier1 {origin}->{destination}: {len(all_flights)} fares"
        )

    return all_flights
