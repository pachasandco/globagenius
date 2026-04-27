"""Tier 1 scraper — Vueling direct JSON endpoint.

Vueling (VY) operates from CDG, ORY, BCN and several French airports.
Their booking engine exposes a calendar fares API used by vueling.com.

Polling: every 20 min alongside Ryanair/Transavia (Tier 1 cycle).
Fallback: demotion to Travelpayouts after MAX_FAILURES.
"""

import logging
import httpx
from datetime import datetime, timedelta, timezone
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

SOURCE = "vueling_direct"

_BASE = "https://booking.vueling.com/api"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.vueling.com/fr",
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
    outbound_date_from: str,
    outbound_date_to: str,
) -> list[dict]:
    """Fetch cheapest round-trip fares from Vueling for a date window.

    Uses Vueling's CheapSeats calendar endpoint — returns lowest prices
    per departure date for the given window.
    """
    route_key = f"{origin}-{destination}"

    params = {
        "origin": origin,
        "destination": destination,
        "beginDate": outbound_date_from,
        "endDate": outbound_date_to,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "isRoundTrip": "true",
        "currency": "EUR",
    }

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(
                f"{_BASE}/CheapSeats/GetCalendarFares",
                params=params,
                headers=_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(f"Vueling rate-limited on {route_key}")
        else:
            logger.warning(f"Vueling HTTP {e.response.status_code} on {route_key}")
        if _mark_failure(route_key):
            logger.warning(f"Vueling {route_key} demoted to Travelpayouts after {MAX_FAILURES} failures")
        return []
    except Exception as e:
        logger.warning(f"Vueling request failed for {route_key}: {e}")
        if _mark_failure(route_key):
            logger.warning(f"Vueling {route_key} demoted to Travelpayouts after {MAX_FAILURES} failures")
        return []

    _mark_success(route_key)

    # Vueling returns either a list of fare objects or {"outboundDates": [...]}
    fares: list[dict] = []
    if isinstance(data, list):
        fares = data
    elif isinstance(data, dict):
        fares = (
            data.get("outboundDates")
            or data.get("fares")
            or data.get("dates")
            or []
        )

    results = []
    for fare in fares:
        # Field names vary slightly between API versions — try both
        dep_date = (
            fare.get("departureDate")
            or fare.get("date")
            or fare.get("DepartureDate")
            or ""
        )[:10]

        price = (
            fare.get("price")
            or fare.get("amount")
            or fare.get("totalAmount")
            or fare.get("Price")
            or (fare.get("priceBreakdown") or {}).get("totalAmount")
        )

        if not dep_date or not price:
            continue

        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        try:
            dep_dt = datetime.strptime(dep_date, "%Y-%m-%d")
            # Vueling calendar endpoint is outbound-only; estimate 7-day return
            ret_dt = dep_dt + timedelta(days=7)
            ret_date = ret_dt.strftime("%Y-%m-%d")
            trip_duration_days = 7
        except ValueError:
            continue

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
                f"https://www.vueling.com/fr/vols-pas-cher"
                f"?ori={origin}&dst={destination}"
                f"&depDate={dep_date}&retDate={ret_date}&adt=1&inf=0&chd=0"
            ),
        }

        normalized = normalize_flight(raw, source=SOURCE)
        normalized["trip_duration_days"] = trip_duration_days
        normalized["duration_minutes"] = 0
        results.append(normalized)

    return results


def scrape_route(origin: str, destination: str) -> list[dict]:
    """Scrape one Vueling Tier 1 route for the next 8 months."""
    if is_demoted(origin, destination):
        return []

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    all_flights: list[dict] = []

    # 4 chunks of 2 months
    for chunk in range(4):
        dep_from = (today + timedelta(days=30 + chunk * 60)).strftime("%Y-%m-%d")
        dep_to   = (today + timedelta(days=89 + chunk * 60)).strftime("%Y-%m-%d")

        flights = get_calendar_fares(
            origin=origin,
            destination=destination,
            outbound_date_from=dep_from,
            outbound_date_to=dep_to,
        )
        all_flights.extend(flights)

        if not flights:
            break

    if all_flights:
        logger.info(f"Vueling Tier1 {origin}->{destination}: {len(all_flights)} fares")

    return all_flights
