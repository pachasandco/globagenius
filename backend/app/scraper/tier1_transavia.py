"""Tier 1 scraper — Transavia direct JSON endpoint.

Transavia (HV) operates heavily from CDG and ORY with strong holiday
routes (Maroc, Canaries, Tunisie, Grèce, Portugal).

Endpoint: Transavia public availability API used by their website.
Polling: every 15-30 min on hot routes.
Fallback: demotion to Travelpayouts after MAX_FAILURES.
"""

import logging
import httpx
from datetime import datetime, timedelta, timezone
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

SOURCE = "transavia_direct"

_BASE = "https://www.transavia.com/api/v1"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.transavia.com/fr-FR/accueil/",
    "Origin": "https://www.transavia.com",
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


def get_lowest_fares(
    origin: str,
    destination: str,
    outbound_date_from: str,
    outbound_date_to: str,
) -> list[dict]:
    """Fetch lowest round-trip fares from Transavia for a date window.

    Uses /lowestFares endpoint which returns cheapest price per date.
    outbound_date_from / outbound_date_to: YYYY-MM-DD.
    """
    route_key = f"{origin}-{destination}"
    params = {
        "origin": origin,
        "destination": destination,
        "outboundDate": outbound_date_from,
        "outboundDateEnd": outbound_date_to,
        "adults": 1,
        "isReturn": "true",
        "currency": "EUR",
    }

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(
                f"{_BASE}/flights/lowestFares",
                params=params,
                headers=_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"Transavia HTTP {e.response.status_code} on {route_key}")
        if _mark_failure(route_key):
            logger.warning(f"Transavia {route_key} demoted after {MAX_FAILURES} failures")
        return []
    except Exception as e:
        logger.warning(f"Transavia request failed for {route_key}: {e}")
        if _mark_failure(route_key):
            logger.warning(f"Transavia {route_key} demoted after {MAX_FAILURES} failures")
        return []

    _mark_success(route_key)

    # Transavia returns {"outboundFares": [...], "inboundFares": [...]}
    # or a flat list of fare objects depending on endpoint version.
    # We handle both shapes.
    fares = []
    if isinstance(data, list):
        fares = data
    elif isinstance(data, dict):
        fares = data.get("outboundFares") or data.get("fares") or []

    results = []
    for fare in fares:
        dep_date = (fare.get("departureDate") or fare.get("date") or "")[:10]
        price = fare.get("price") or fare.get("lowestPrice") or fare.get("amount")
        if not dep_date or not price:
            continue

        # Estimate return date: Transavia lowest-fares endpoint gives outbound
        # only. We add a standard 7-day trip duration as estimate.
        # Will be refined when full itinerary endpoint is available.
        try:
            dep_dt = datetime.strptime(dep_date, "%Y-%m-%d")
            ret_dt = dep_dt + timedelta(days=7)
            ret_date = ret_dt.strftime("%Y-%m-%d")
            trip_duration_days = 7
        except ValueError:
            continue

        raw = {
            "price": float(price),
            "currency": "EUR",
            "origin": origin,
            "destination": destination,
            "departureDate": dep_date,
            "returnDate": ret_date,
            "airline": "HV",  # Transavia IATA
            "stops": 0,
            "url": (
                f"https://www.transavia.com/fr-FR/reservez-un-vol/vols/recherche/"
                f"?from={origin}&to={destination}&departure={dep_date}&return={ret_date}&adults=1"
            ),
        }

        normalized = normalize_flight(raw, source=SOURCE)
        normalized["trip_duration_days"] = trip_duration_days
        normalized["duration_minutes"] = 0
        results.append(normalized)

    return results


def scrape_route(origin: str, destination: str) -> list[dict]:
    """Scrape one Transavia Tier 1 route for the next 8 months."""
    if is_demoted(origin, destination):
        return []

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    all_flights = []

    for chunk in range(4):
        dep_from = (today + timedelta(days=30 + chunk * 60)).strftime("%Y-%m-%d")
        dep_to   = (today + timedelta(days=89 + chunk * 60)).strftime("%Y-%m-%d")

        flights = get_lowest_fares(
            origin=origin,
            destination=destination,
            outbound_date_from=dep_from,
            outbound_date_to=dep_to,
        )
        all_flights.extend(flights)

        if not flights:
            break

    if all_flights:
        logger.info(f"Transavia Tier1 {origin}->{destination}: {len(all_flights)} fares")

    return all_flights
