import logging
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

# Primary: Google Flights (best EUR support, most reliable)
# Fallback: Skyscanner
FLIGHT_ACTORS = [
    {"id": "misceres/google-flights-scraper", "source": "google_flights"},
]

# Sampling strategy: pick ~6 dates spread across the 15-90 day window
# rather than scraping every single date (saves Apify credits)
SAMPLE_DATES_COUNT = 6
TRIP_DURATIONS = [3, 5, 7]  # nights


def _generate_sample_dates(days_ahead_start: int = 15, days_ahead_end: int = 90) -> list[str]:
    """Generate evenly spaced sample departure dates."""
    now = datetime.now(timezone.utc)
    step = (days_ahead_end - days_ahead_start) // SAMPLE_DATES_COUNT
    dates = []
    for i in range(SAMPLE_DATES_COUNT):
        d = now + timedelta(days=days_ahead_start + i * step)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def scrape_flights_for_airport(origin: str) -> list[dict]:
    """Scrape flights for one origin airport across sampled dates and trip durations."""
    all_normalized = []
    departure_dates = _generate_sample_dates()

    for actor_def in FLIGHT_ACTORS:
        actor_id = actor_def["id"]
        source = actor_def["source"]

        for dep_date in departure_dates:
            for duration in TRIP_DURATIONS:
                dep = datetime.strptime(dep_date, "%Y-%m-%d")
                ret_date = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")

                run_input = {
                    "departureDate": dep_date,
                    "returnDate": ret_date,
                    "originAirportCode": origin,
                    "currency": "EUR",
                    "maxStops": 1,
                    "adults": 1,
                }

                try:
                    raw_items = run_actor(actor_id, run_input)
                except Exception as e:
                    logger.warning(f"Actor {actor_id} failed for {origin} {dep_date}: {e}")
                    continue

                for item in raw_items:
                    try:
                        # Map actor output fields to our expected format
                        mapped = _map_google_flights_output(item, origin, dep_date, ret_date)
                        if mapped:
                            all_normalized.append(normalize_flight(mapped, source=source))
                    except (KeyError, TypeError, ValueError) as e:
                        logger.warning(f"Failed to normalize flight item: {e}")

    return all_normalized


def _map_google_flights_output(item: dict, origin: str, dep_date: str, ret_date: str) -> dict | None:
    """Map Google Flights actor output to our expected format."""
    price = item.get("price") or item.get("totalPrice")
    if not price:
        return None

    return {
        "price": float(price),
        "currency": item.get("currency", "EUR"),
        "origin": item.get("originAirport", {}).get("code", origin) if isinstance(item.get("originAirport"), dict) else origin,
        "destination": item.get("destinationAirport", {}).get("code", "") if isinstance(item.get("destinationAirport"), dict) else item.get("destination", ""),
        "departureDate": item.get("departureDate", dep_date),
        "returnDate": item.get("returnDate", ret_date),
        "airline": item.get("airline") or item.get("carrier") or item.get("airlines", [""])[0] if isinstance(item.get("airlines"), list) else item.get("airline", ""),
        "stops": item.get("stops", 0) if isinstance(item.get("stops"), int) else 0,
        "url": item.get("url") or item.get("bookingUrl") or item.get("deepLink") or "",
    }


def scrape_all_flights() -> tuple[list[dict], int]:
    """Scrape flights for all MVP airports. Returns (normalized_items, error_count)."""
    all_flights = []
    errors = 0

    for airport in settings.MVP_AIRPORTS:
        try:
            flights = scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            logger.info(f"Scraped {len(flights)} flights from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors
