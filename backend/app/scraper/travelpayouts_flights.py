"""Flight scraper backed by the Travelpayouts API.

Replaces the previous Google Flights / Playwright / Apify pipeline.
Single source for flight prices, free, no bot detection."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from app.config import settings
from app.scraper.normalizer import normalize_flight
from app.scraper.travelpayouts import get_calendar_prices
from app.analysis.route_selector import is_long_haul, get_priority_destinations

logger = logging.getLogger(__name__)

SOURCE = "travelpayouts"

SAMPLE_MONTH_OFFSETS = [1, 2, 3]  # M+1, M+2, M+3
DEFAULT_TRIP_DURATION_DAYS = 7

AIRPORTS_PER_CYCLE = 2


def _window_label(days_ahead: int) -> str:
    if days_ahead <= 30:
        return "1m"
    elif days_ahead <= 60:
        return "2m"
    elif days_ahead <= 90:
        return "3m"
    elif days_ahead <= 120:
        return "4m"
    else:
        return "6m"


def _build_aviasales_url(origin: str, destination: str, dep_date: str, ret_date: str) -> str:
    """Build a deeplink to the Aviasales search results page.

    Format: https://www.aviasales.com/search/CDG1205JFK19051
    where the first date is depart (DDMM) and the second is return (DDMM).
    The trailing "1" is the number of adult passengers."""
    try:
        dep = datetime.strptime(dep_date, "%Y-%m-%d")
        ret = datetime.strptime(ret_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return f"https://www.aviasales.com/search?origin={quote(origin)}&destination={quote(destination)}"
    return (
        f"https://www.aviasales.com/search/"
        f"{origin}{dep.strftime('%d%m')}{destination}{ret.strftime('%d%m')}1"
    )


def _normalize_calendar_entry(entry: dict, origin: str, destination: str) -> dict | None:
    """Map a Travelpayouts calendar entry to the raw_flights row format.
    Returns None if the entry is unusable (missing date, zero price)."""
    departure_at = entry.get("departure_at") or ""
    price = entry.get("price") or 0
    if not departure_at or not price:
        return None

    departure_date = departure_at[:10]
    return_at = entry.get("return_at") or ""
    if return_at:
        return_date = return_at[:10]
    else:
        try:
            dep = datetime.strptime(departure_date, "%Y-%m-%d")
            return_date = (dep + timedelta(days=DEFAULT_TRIP_DURATION_DAYS)).strftime("%Y-%m-%d")
        except ValueError:
            return None

    raw = {
        "price": float(price),
        "currency": "EUR",
        "origin": origin,
        "destination": destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "airline": entry.get("airline", ""),
        "stops": int(entry.get("transfers", 0) or 0),
        "url": _build_aviasales_url(origin, destination, departure_date, return_date),
    }

    return normalize_flight(raw, source=SOURCE)


def _utcnow() -> datetime:
    """Indirection so tests can freeze time."""
    return datetime.now(timezone.utc)


def _target_months() -> list[str]:
    now = _utcnow()
    months = []
    for offset in SAMPLE_MONTH_OFFSETS:
        year = now.year + ((now.month - 1 + offset) // 12)
        month = ((now.month - 1 + offset) % 12) + 1
        months.append(f"{year:04d}-{month:02d}")
    return months


def scrape_flights_for_route(origin: str, destination: str) -> list[dict]:
    """Fetch 3 months of daily quotes for one route and normalize them."""
    flights = []
    for month in _target_months():
        entries = get_calendar_prices(origin, destination, month)
        for entry in entries:
            normalized = _normalize_calendar_entry(entry, origin, destination)
            if normalized:
                flights.append(normalized)
    return flights


def scrape_flights_for_airport(origin: str) -> list[dict]:
    """Scrape all priority destinations for one origin airport.

    Long-haul destinations are only scraped from CDG."""
    destinations = get_priority_destinations(max_count=25)
    all_flights = []
    for dest in destinations:
        if dest == origin:
            continue
        if is_long_haul(dest) and origin != "CDG":
            continue
        try:
            flights = scrape_flights_for_route(origin, dest)
            all_flights.extend(flights)
            if flights:
                logger.info(f"  {origin}->{dest}: {len(flights)} flights")
        except Exception as e:
            logger.warning(f"Failed to scrape {origin}->{dest}: {e}")
    return all_flights
