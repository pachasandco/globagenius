import logging
import asyncio
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

SOURCE = "google_flights"

SAMPLE_WINDOWS = [30, 90, 180]
TRIP_DURATIONS = [7]

# Dynamic destinations — selected by season via route_selector
def _get_top_destinations() -> list[str]:
    try:
        from app.analysis.route_selector import get_priority_destinations
        return get_priority_destinations(max_count=10)
    except Exception:
        return ["LIS", "BCN", "FCO", "ATH", "PRG", "RAK", "IST", "AMS"]

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


def _generate_sample_dates() -> list[tuple[str, int]]:
    now = datetime.now(timezone.utc)
    return [
        ((now + timedelta(days=d)).strftime("%Y-%m-%d"), d)
        for d in SAMPLE_WINDOWS
    ]


def bootstrap_baseline_from_insights(origin: str, destination: str, insights: dict, days_ahead: int = 30) -> dict | None:
    """Create baseline from price insights (Google Flights typical range)."""
    typical_low = insights.get("typical_low")
    typical_high = insights.get("typical_high")

    if not typical_low or not typical_high:
        return None

    avg_price = round((typical_low + typical_high) / 2, 2)
    std_dev = round((typical_high - typical_low) / 4, 2)

    window = _window_label(days_ahead)

    return {
        "route_key": f"{origin}-{destination}-{window}",
        "type": "flight",
        "avg_price": avg_price,
        "std_dev": max(std_dev, 1.0),
        "sample_count": 2,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _scrape_route_playwright(origin: str, destination: str, dep_date: str, ret_date: str) -> tuple[list[dict], dict | None]:
    """Scrape a route using Playwright + LLM (Fairtrail approach). Zero API cost."""
    from app.scraper.browser.google_flights import scrape_flights_page

    result = await scrape_flights_page(origin, destination, dep_date, ret_date)
    if not result:
        return [], None

    normalized = []
    for flight in result.get("flights", []):
        try:
            mapped = {
                "price": float(flight.get("price", 0)),
                "currency": "EUR",
                "origin": flight.get("origin", origin),
                "destination": flight.get("destination", destination),
                "departureDate": dep_date,
                "returnDate": ret_date,
                "airline": flight.get("airline", ""),
                "stops": int(flight.get("stops", 0)),
                "url": flight.get("url", ""),
            }
            if mapped["price"] > 0:
                normalized.append(normalize_flight(mapped, source=SOURCE))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to normalize flight: {e}")

    insights = result.get("price_insights")
    return normalized, insights


def _scrape_route_apify(origin: str, destination: str, dep_date: str, ret_date: str) -> tuple[list[dict], dict | None]:
    """Fallback: scrape via Apify actor."""
    try:
        from app.scraper.apify_client import run_actor
    except ImportError:
        return [], None

    run_input = {
        "departure_airport_code": origin,
        "arrival_airport_code": destination,
        "departure_date": dep_date,
        "return_date": ret_date,
        "adults": 1,
        "currency": "EUR",
    }

    try:
        raw_items = run_actor("johnvc/Google-Flights-Data-Scraper-Flight-and-Price-Search", run_input)
    except Exception as e:
        logger.warning(f"Apify fallback failed: {e}")
        return [], None

    normalized = []
    insights = None
    for item in raw_items:
        # Extract price insights
        pi = item.get("price_insights")
        if pi:
            typical_range = pi.get("typical_price_range", [])
            if typical_range and len(typical_range) == 2:
                insights = {"typical_low": typical_range[0], "typical_high": typical_range[1], "price_level": pi.get("price_level")}

            # Extract flights from nested format
            price_history = pi.get("price_history", [])
            if price_history:
                import numpy as np
                prices = [p[1] for p in price_history]
                insights = insights or {}
                insights["typical_low"] = insights.get("typical_low", float(np.percentile(prices, 25)))
                insights["typical_high"] = insights.get("typical_high", float(np.percentile(prices, 75)))

        for category in ["best_flights", "other_flights"]:
            for fg in item.get(category, []):
                price = fg.get("price")
                flights = fg.get("flights", [])
                if not price or not flights:
                    continue
                first = flights[0]
                last = flights[-1]
                arr = last.get("arrival_airport", {}).get("id", "")
                if not arr:
                    continue
                dep_time = first.get("departure_airport", {}).get("time", "")
                mapped = {
                    "price": float(price),
                    "currency": "EUR",
                    "origin": first.get("departure_airport", {}).get("id", origin),
                    "destination": arr,
                    "departureDate": dep_time.split(" ")[0] if " " in dep_time else dep_date,
                    "returnDate": ret_date,
                    "airline": first.get("airline", ""),
                    "stops": len(flights) - 1,
                    "url": f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{arr}",
                }
                try:
                    normalized.append(normalize_flight(mapped, source=SOURCE))
                except Exception:
                    pass

    return normalized, insights


async def scrape_flights_for_route(origin: str, destination: str, dep_date: str, ret_date: str) -> tuple[list[dict], dict | None]:
    """Scrape flights: Playwright primary (free), Apify fallback (paid)."""
    # Primary: Playwright (free, Fairtrail approach)
    try:
        flights, insights = await _scrape_route_playwright(origin, destination, dep_date, ret_date)
        if flights:
            return flights, insights
        logger.info(f"Playwright returned 0 flights for {origin}→{destination}, trying Apify")
    except Exception as e:
        logger.warning(f"Playwright failed for {origin}→{destination}: {e}")

    # Fallback: Apify (paid but reliable)
    return _scrape_route_apify(origin, destination, dep_date, ret_date)


async def scrape_flights_for_airport(origin: str) -> tuple[list[dict], list[dict]]:
    """Scrape flights for one origin to all top destinations."""
    all_normalized = []
    baselines = []
    sample_dates = _generate_sample_dates()

    for dest in _get_top_destinations():
        if dest == origin:
            continue
        seen_windows = set()
        for dep_date, days_ahead in sample_dates:
            for duration in TRIP_DURATIONS:
                dep = datetime.strptime(dep_date, "%Y-%m-%d")
                ret_date = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")

                flights, insights = await scrape_flights_for_route(origin, dest, dep_date, ret_date)
                all_normalized.extend(flights)

                window = _window_label(days_ahead)
                if insights and window not in seen_windows:
                    baseline = bootstrap_baseline_from_insights(origin, dest, insights, days_ahead)
                    if baseline:
                        baselines.append(baseline)
                        seen_windows.add(window)
                        logger.info(f"  Baseline {origin}-{dest}-{window}: avg={baseline['avg_price']}€")

                if flights:
                    logger.info(f"  {origin}→{dest} {dep_date} ({duration}n, {window}): {len(flights)} flights")

                # Delay between requests to avoid detection
                await asyncio.sleep(2)

    return all_normalized, baselines


async def scrape_all_flights() -> tuple[list[dict], int, list[dict]]:
    """Scrape flights for a rotating subset of airports."""
    airports = settings.MVP_AIRPORTS
    # Use current hour to rotate airports (survives restarts)
    hour = datetime.now(timezone.utc).hour
    cycle_index = hour // 4  # 0-5, changes every 4 hours
    start_idx = (cycle_index * AIRPORTS_PER_CYCLE) % len(airports)
    cycle_airports = [
        airports[(start_idx + i) % len(airports)]
        for i in range(AIRPORTS_PER_CYCLE)
    ]

    logger.info(f"Cycle (hour={hour}, idx={cycle_index}): scraping airports {cycle_airports}")

    all_flights = []
    all_baselines = []
    errors = 0

    for airport in cycle_airports:
        try:
            flights, baselines = await scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            all_baselines.extend(baselines)
            logger.info(f"Scraped {len(flights)} flights + {len(baselines)} baselines from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors, all_baselines
