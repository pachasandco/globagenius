"""One-way fare scraper backed by Travelpayouts prices_for_dates.

Reuses the same endpoint as the round-trip scraper but with `one_way=True`.
Output rows carry `trip_type='oneway'` and a NULL `return_date` so the
analyzer can baseline them separately and the dispatcher can route them
through the oneway_exceptional template.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.scraper.travelpayouts import get_prices_for_dates
from app.notifications.aviasales import build_aviasales_url_oneway
from app.analysis.route_selector import is_long_haul, get_priority_destinations

logger = logging.getLogger(__name__)

SOURCE = "travelpayouts_oneway"


def _hash_oneway(origin: str, destination: str, departure_date: str, price: float) -> str:
    raw = f"{origin}|{destination}|{departure_date}|oneway|{price}|{SOURCE}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _normalize_oneway_entry(entry: dict) -> dict | None:
    """Map a Travelpayouts one-way entry to the raw_flights row format.

    Returns None if the entry is unusable (missing date / zero price) or if
    the departure falls outside the [+30 days, +240 days] window."""
    departure_at = entry.get("departure_at") or ""
    price = entry.get("price") or 0
    if not departure_at or not price:
        return None

    departure_date = departure_at[:10]
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        return None

    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    min_departure = today + timedelta(days=30)
    max_departure = today + timedelta(days=240)
    if dep < min_departure or dep > max_departure:
        return None

    origin = entry.get("origin_airport") or ""
    destination = entry.get("destination_airport") or ""
    if not origin or not destination:
        return None

    link = entry.get("link") or ""
    if link:
        source_url = f"https://www.aviasales.com{link}"
    else:
        source_url = build_aviasales_url_oneway(
            origin, destination, departure_date,
            marker=settings.TRAVELPAYOUTS_MARKER or None,
        )

    duration_minutes = int(entry.get("duration_to") or 0)
    price_eur = float(price)
    now = datetime.now(timezone.utc)

    return {
        "hash": _hash_oneway(origin, destination, departure_date, price_eur),
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": None,
        "price": price_eur,
        "airline": entry.get("airline") or None,
        "stops": int(entry.get("transfers") or 0),
        "source_url": source_url,
        "source": SOURCE,
        "trip_type": "oneway",
        "trip_duration_days": None,
        "duration_minutes": duration_minutes,
        "scraped_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=settings.DATA_FRESHNESS_HOURS)).isoformat(),
    }


def scrape_oneway_for_route(origin: str, destination: str) -> list[dict]:
    flights: list[dict] = []
    for entry in get_prices_for_dates(origin, destination, one_way=True):
        normalized = _normalize_oneway_entry(entry)
        if normalized:
            flights.append(normalized)
    return flights


def scrape_oneway_for_airport(origin: str) -> list[dict]:
    """Scrape one-way fares for one origin to all priority destinations.

    Skips long-haul destinations from non-CDG origins (same rule as the
    round-trip scraper)."""
    destinations = get_priority_destinations(max_count=40)
    out: list[dict] = []
    for dest in destinations:
        if dest == origin:
            continue
        if is_long_haul(dest) and origin != "CDG":
            continue
        try:
            flights = scrape_oneway_for_route(origin, dest)
            out.extend(flights)
            if flights:
                logger.info(f"  oneway {origin}->{dest}: {len(flights)} fares")
        except Exception as e:
            logger.warning(f"Failed oneway scrape {origin}->{dest}: {e}")
    return out


async def scrape_all_oneway_flights() -> tuple[list[dict], int]:
    """Top-level one-way scraper. Returns (flights, errors)."""
    airports = list(settings.MVP_AIRPORTS)
    logger.info(f"One-way scrape across {len(airports)} airports: {airports}")

    all_flights: list[dict] = []
    errors = 0
    for airport in airports:
        try:
            flights = scrape_oneway_for_airport(airport)
            all_flights.extend(flights)
            logger.info(f"One-way: {len(flights)} fares from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed one-way scrape from {airport}: {e}")
    return all_flights, errors
