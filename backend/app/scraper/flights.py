import logging
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

# Best actor: johnvc/Google-Flights-Data-Scraper-Flight-and-Price-Search
FLIGHT_ACTOR_ID = "johnvc/Google-Flights-Data-Scraper-Flight-and-Price-Search"
SOURCE = "google_flights"

# Sample dates: 6 dates spread across 15-90 day window
SAMPLE_DATES_COUNT = 4
TRIP_DURATIONS = [5, 7]

# Top destinations to search (IATA codes)
TOP_DESTINATIONS = [
    "LIS", "BCN", "FCO", "ATH", "AMS", "PRG", "BUD", "RAK",
    "IST", "MAD", "BER", "DUB", "NAP", "OPO",
]


def _generate_sample_dates() -> list[str]:
    now = datetime.now(timezone.utc)
    step = 75 // SAMPLE_DATES_COUNT  # spread across 15-90 days
    return [
        (now + timedelta(days=15 + i * step)).strftime("%Y-%m-%d")
        for i in range(SAMPLE_DATES_COUNT)
    ]


def _extract_flights_from_result(result: dict, origin: str) -> list[dict]:
    """Extract individual flights from the actor's nested output format."""
    extracted = []

    for category in ["best_flights", "other_flights"]:
        flights_list = result.get(category, [])
        for flight_group in flights_list:
            flights = flight_group.get("flights", [])
            price = flight_group.get("price")
            if not price or not flights:
                continue

            # Get first and last leg for origin/destination
            first_leg = flights[0]
            last_leg = flights[-1]

            dep_airport = first_leg.get("departure_airport", {})
            arr_airport = last_leg.get("arrival_airport", {})

            dep_code = dep_airport.get("id", origin)
            arr_code = arr_airport.get("id", "")

            if not arr_code:
                continue

            # Parse departure/arrival times for dates
            dep_time = dep_airport.get("time", "")
            arr_time = arr_airport.get("time", "")
            dep_date = dep_time.split(" ")[0] if " " in dep_time else ""
            arr_date = arr_time.split(" ")[0] if " " in arr_time else ""

            # Get airline from first leg
            airline = first_leg.get("airline", "")
            stops = len(flights) - 1

            # Build booking URL
            booking_token = flight_group.get("booking_token", "")

            extracted.append({
                "price": float(price),
                "currency": "EUR",
                "origin": dep_code,
                "destination": arr_code,
                "departureDate": dep_date,
                "returnDate": result.get("search_parameters", {}).get("return_date", ""),
                "airline": airline,
                "stops": stops,
                "url": f"https://www.google.com/travel/flights?q=flights+from+{dep_code}+to+{arr_code}" if not booking_token else "",
            })

    return extracted


def scrape_flights_for_route(origin: str, destination: str, dep_date: str, ret_date: str) -> list[dict]:
    """Scrape flights for a specific route and dates."""
    run_input = {
        "departure_airport_code": origin,
        "arrival_airport_code": destination,
        "departure_date": dep_date,
        "return_date": ret_date,
        "adults": 1,
        "currency": "EUR",
    }

    try:
        raw_items = run_actor(FLIGHT_ACTOR_ID, run_input)
    except Exception as e:
        logger.warning(f"Actor failed for {origin}→{destination} {dep_date}: {e}")
        return []

    normalized = []
    for item in raw_items:
        flights = _extract_flights_from_result(item, origin)
        for flight_data in flights:
            try:
                normalized.append(normalize_flight(flight_data, source=SOURCE))
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Failed to normalize flight: {e}")

    return normalized


def scrape_flights_for_airport(origin: str) -> list[dict]:
    """Scrape flights for one origin to all top destinations."""
    all_normalized = []
    departure_dates = _generate_sample_dates()

    for dest in TOP_DESTINATIONS:
        if dest == origin:
            continue
        for dep_date in departure_dates:
            for duration in TRIP_DURATIONS:
                dep = datetime.strptime(dep_date, "%Y-%m-%d")
                ret_date = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")

                flights = scrape_flights_for_route(origin, dest, dep_date, ret_date)
                all_normalized.extend(flights)

                if flights:
                    logger.info(f"  {origin}→{dest} {dep_date} ({duration}n): {len(flights)} flights")

    return all_normalized


def scrape_all_flights() -> tuple[list[dict], int]:
    """Scrape flights for all MVP airports."""
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
