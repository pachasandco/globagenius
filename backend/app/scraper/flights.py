import logging
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

# Best actor: johnvc/Google-Flights-Data-Scraper-Flight-and-Price-Search
FLIGHT_ACTOR_ID = "johnvc/Google-Flights-Data-Scraper-Flight-and-Price-Search"
SOURCE = "google_flights"

# Sample dates across 15 days to 6 months window
SAMPLE_WINDOWS = [15, 30, 60, 90, 120, 180]  # days ahead
TRIP_DURATIONS = [5, 7]

# Top destinations to search (IATA codes)
TOP_DESTINATIONS = [
    "LIS", "BCN", "FCO", "ATH", "AMS", "PRG", "BUD", "RAK",
    "IST", "MAD", "BER", "DUB", "NAP", "OPO",
]


def _generate_sample_dates() -> list[tuple[str, int]]:
    """Generate sample departure dates with their window (days ahead).
    Returns [(date_str, days_ahead), ...]"""
    now = datetime.now(timezone.utc)
    return [
        ((now + timedelta(days=d)).strftime("%Y-%m-%d"), d)
        for d in SAMPLE_WINDOWS
    ]


def _extract_price_insights(result: dict) -> dict | None:
    """Extract Google Flights price insights (history, typical range)."""
    insights = result.get("price_insights")
    if not insights:
        return None

    return {
        "lowest_price": insights.get("lowest_price"),
        "price_level": insights.get("price_level"),  # "low", "typical", "high"
        "typical_price_range": insights.get("typical_price_range", []),
        "price_history": insights.get("price_history", []),  # [[timestamp, price], ...]
    }


def _extract_flights_from_result(result: dict, origin: str) -> list[dict]:
    """Extract individual flights from the actor's nested output format."""
    extracted = []

    # Get price insights for this route (provided by Google Flights)
    insights = _extract_price_insights(result)
    typical_range = insights.get("typical_price_range", []) if insights else []
    typical_avg = sum(typical_range) / len(typical_range) if typical_range else None

    for category in ["best_flights", "other_flights"]:
        flights_list = result.get(category, [])
        for flight_group in flights_list:
            flights = flight_group.get("flights", [])
            price = flight_group.get("price")
            if not price or not flights:
                continue

            first_leg = flights[0]
            last_leg = flights[-1]

            dep_airport = first_leg.get("departure_airport", {})
            arr_airport = last_leg.get("arrival_airport", {})

            dep_code = dep_airport.get("id", origin)
            arr_code = arr_airport.get("id", "")

            if not arr_code:
                continue

            dep_time = dep_airport.get("time", "")
            dep_date = dep_time.split(" ")[0] if " " in dep_time else ""

            airline = first_leg.get("airline", "")
            stops = len(flights) - 1

            flight_data = {
                "price": float(price),
                "currency": "EUR",
                "origin": dep_code,
                "destination": arr_code,
                "departureDate": dep_date,
                "returnDate": result.get("search_parameters", {}).get("return_date", ""),
                "airline": airline,
                "stops": stops,
                "url": f"https://www.google.com/travel/flights?q=flights+from+{dep_code}+to+{arr_code}",
            }

            # Attach price insights for baseline bootstrapping
            if typical_avg:
                flight_data["_typical_avg"] = typical_avg
                flight_data["_typical_range"] = typical_range
                flight_data["_price_level"] = insights.get("price_level", "")

            extracted.append(flight_data)

    return extracted, insights


def scrape_flights_for_route(origin: str, destination: str, dep_date: str, ret_date: str) -> tuple[list[dict], dict | None]:
    """Scrape flights for a specific route and dates. Returns (flights, price_insights)."""
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
        return [], None

    normalized = []
    route_insights = None
    for item in raw_items:
        flights, insights = _extract_flights_from_result(item, origin)
        if insights:
            route_insights = insights
        for flight_data in flights:
            try:
                normalized.append(normalize_flight(flight_data, source=SOURCE))
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Failed to normalize flight: {e}")

    return normalized, route_insights


def _window_label(days_ahead: int) -> str:
    """Convert days ahead to a window label: 1m, 2m, 3m, 4m, 6m."""
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


def bootstrap_baseline_from_insights(origin: str, destination: str, insights: dict, days_ahead: int = 30) -> dict | None:
    """Create a baseline from Google Flights price insights.
    Route key includes time window: CDG-LIS-3m (for 3 month ahead trips)."""
    typical_range = insights.get("typical_price_range", [])
    price_history = insights.get("price_history", [])

    if not typical_range and not price_history:
        return None

    if price_history:
        prices = [p[1] for p in price_history]
        import numpy as np
        avg_price = round(float(np.mean(prices)), 2)
        std_dev = round(float(np.std(prices)), 2)
        sample_count = len(prices)
    elif typical_range:
        avg_price = round(sum(typical_range) / len(typical_range), 2)
        std_dev = round((typical_range[1] - typical_range[0]) / 4, 2)
        sample_count = 2
    else:
        return None

    window = _window_label(days_ahead)

    # Save both: route-specific baseline AND route+window baseline
    return {
        "route_key": f"{origin}-{destination}-{window}",
        "type": "flight",
        "avg_price": avg_price,
        "std_dev": max(std_dev, 1.0),
        "sample_count": sample_count,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_flights_for_airport(origin: str) -> tuple[list[dict], list[dict]]:
    """Scrape flights for one origin to all top destinations across multiple time windows.
    Returns (normalized_flights, bootstrapped_baselines)."""
    all_normalized = []
    baselines = []
    sample_dates = _generate_sample_dates()  # [(date, days_ahead), ...]

    for dest in TOP_DESTINATIONS:
        if dest == origin:
            continue
        seen_windows = set()
        for dep_date, days_ahead in sample_dates:
            for duration in TRIP_DURATIONS:
                dep = datetime.strptime(dep_date, "%Y-%m-%d")
                ret_date = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")

                flights, insights = scrape_flights_for_route(origin, dest, dep_date, ret_date)
                all_normalized.extend(flights)

                # Bootstrap baseline per time window (1m, 2m, 3m, 4m, 6m)
                window = _window_label(days_ahead)
                if insights and window not in seen_windows:
                    baseline = bootstrap_baseline_from_insights(origin, dest, insights, days_ahead)
                    if baseline:
                        baselines.append(baseline)
                        seen_windows.add(window)
                        logger.info(f"  Baseline {origin}-{dest}-{window}: avg={baseline['avg_price']}€ std={baseline['std_dev']}€ ({baseline['sample_count']} pts)")

                if flights:
                    logger.info(f"  {origin}→{dest} {dep_date} ({duration}n, {window}): {len(flights)} flights")

    return all_normalized, baselines


def scrape_all_flights() -> tuple[list[dict], int, list[dict]]:
    """Scrape flights for all MVP airports. Returns (flights, errors, baselines)."""
    all_flights = []
    all_baselines = []
    errors = 0

    for airport in settings.MVP_AIRPORTS:
        try:
            flights, baselines = scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            all_baselines.extend(baselines)
            logger.info(f"Scraped {len(flights)} flights + {len(baselines)} baselines from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors, all_baselines
