"""Flight scraper backed by the Travelpayouts API.

Replaces the previous Google Flights / Playwright / Apify pipeline.
Single source for flight prices, free, no bot detection."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from app.config import settings
from app.scraper.normalizer import normalize_flight
from app.scraper.travelpayouts import get_prices_for_dates
from app.analysis.route_selector import is_long_haul, get_priority_destinations

logger = logging.getLogger(__name__)

SOURCE = "travelpayouts"

DEFAULT_TRIP_DURATION_DAYS = 7


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



def _normalize_priced_entry(entry: dict) -> dict | None:
    """Map a Travelpayouts prices_for_dates entry to the raw_flights row format.

    Returns None if the entry is unusable: missing dates, zero price, or
    trip duration outside [1, 12] days."""
    departure_at = entry.get("departure_at") or ""
    return_at = entry.get("return_at") or ""
    price = entry.get("price") or 0
    if not departure_at or not return_at or not price:
        return None

    departure_date = departure_at[:10]
    return_date = return_at[:10]
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
    except ValueError:
        return None

    trip_duration_days = (ret - dep).days
    if trip_duration_days < 1 or trip_duration_days > 12:
        return None

    origin = entry.get("origin_airport") or ""
    destination = entry.get("destination_airport") or ""
    if not origin or not destination:
        return None

    link = entry.get("link") or ""
    if link:
        source_url = f"https://www.aviasales.com{link}"
    else:
        source_url = _build_aviasales_url(origin, destination, departure_date, return_date)

    duration_minutes = int(entry.get("duration_to") or 0)

    raw = {
        "price": float(price),
        "currency": "EUR",
        "origin": origin,
        "destination": destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "airline": entry.get("airline", ""),
        "stops": int(entry.get("transfers") or 0),
        "url": source_url,
    }

    normalized = normalize_flight(raw, source=SOURCE)
    normalized["trip_duration_days"] = trip_duration_days
    normalized["duration_minutes"] = duration_minutes
    return normalized


def scrape_flights_for_route(origin: str, destination: str) -> list[dict]:
    """Fetch real round-trip prices for one route via Travelpayouts."""
    flights = []
    for entry in get_prices_for_dates(origin, destination):
        normalized = _normalize_priced_entry(entry)
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


async def scrape_all_flights() -> tuple[list[dict], int, list[dict]]:
    """Top-level scraper. Scrapes ALL MVP_AIRPORTS on every cron run.

    Travelpayouts is free and fast enough that rotating over airports is
    unnecessary — every cron scans every airport, so users get alerts
    as soon as a deal is detected rather than waiting for their airport
    to come up in a daily rotation.

    Signature kept compatible with the legacy flights.py module:
    returns (flights, errors, baselines). Baselines are always empty
    here — they are populated by job_travelpayouts_enrichment instead."""
    airports = list(settings.MVP_AIRPORTS)

    logger.info(f"Scraping all {len(airports)} airports: {airports}")

    all_flights = []
    errors = 0
    for airport in airports:
        try:
            flights = scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            logger.info(f"Scraped {len(flights)} flights from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors, []
