import logging
from datetime import datetime, timedelta, timezone
from app.config import settings, IATA_TO_CITY
from app.scraper.amadeus_client import search_flights, get_price_metrics, search_destinations
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

SOURCE = "amadeus"

# 3 time windows
SAMPLE_WINDOWS = [30, 90, 180]
TRIP_DURATIONS = [7]

# Top destinations
TOP_DESTINATIONS = [
    "LIS", "BCN", "FCO", "ATH", "PRG", "RAK", "IST", "AMS",
]

# Rotate airports: 2 per cycle
AIRPORTS_PER_CYCLE = 2
_cycle_counter = 0


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


def _extract_flights_from_amadeus(offers: list[dict], origin: str, dep_date: str, ret_date: str) -> list[dict]:
    """Convert Amadeus flight offers to our format."""
    extracted = []
    for offer in offers:
        price = offer.get("price", {})
        total = price.get("grandTotal") or price.get("total")
        if not total:
            continue

        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        if not segments:
            continue

        first_seg = segments[0]
        last_seg = segments[-1]

        airline = first_seg.get("carrierCode", "")
        stops = len(segments) - 1
        dest_code = last_seg.get("arrival", {}).get("iataCode", "")

        if not dest_code:
            continue

        extracted.append({
            "price": float(total),
            "currency": price.get("currency", "EUR"),
            "origin": first_seg.get("departure", {}).get("iataCode", origin),
            "destination": dest_code,
            "departureDate": dep_date,
            "returnDate": ret_date,
            "airline": airline,
            "stops": stops,
            "url": f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{dest_code}+on+{dep_date}",
        })

    return extracted


def bootstrap_baseline_from_metrics(origin: str, destination: str, metrics: dict, days_ahead: int = 30) -> dict | None:
    """Create baseline from Amadeus price metrics (min, max, median, quartiles)."""
    price_metrics = metrics.get("priceMetrics", [])
    if not price_metrics:
        return None

    prices = {}
    for pm in price_metrics:
        quartile = pm.get("quartileRanking")
        amount = pm.get("amount")
        if quartile and amount:
            prices[quartile] = float(amount)

    median = prices.get("MEDIUM", prices.get("FIRST", 0))
    q1 = prices.get("FIRST", median * 0.8)
    q3 = prices.get("THIRD", median * 1.2)

    if median <= 0:
        return None

    # Estimate std_dev from interquartile range
    std_dev = (q3 - q1) / 1.35  # IQR to std approximation

    window = _window_label(days_ahead)

    return {
        "route_key": f"{origin}-{destination}-{window}",
        "type": "flight",
        "avg_price": round(median, 2),
        "std_dev": round(max(std_dev, 1.0), 2),
        "sample_count": len(price_metrics),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def scrape_flights_for_route(origin: str, destination: str, dep_date: str, ret_date: str) -> tuple[list[dict], dict | None]:
    """Search flights via Amadeus + get price metrics for baseline."""
    # Get flight offers
    offers = search_flights(origin, destination, dep_date, ret_date, max_results=10)
    normalized = []
    for flight_data in _extract_flights_from_amadeus(offers, origin, dep_date, ret_date):
        try:
            normalized.append(normalize_flight(flight_data, source=SOURCE))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to normalize flight: {e}")

    # Get price metrics for baseline
    metrics = get_price_metrics(origin, destination, dep_date)

    return normalized, metrics


def scrape_flights_for_airport(origin: str) -> tuple[list[dict], list[dict]]:
    """Scrape flights for one origin to all top destinations."""
    all_normalized = []
    baselines = []
    sample_dates = _generate_sample_dates()

    # Also try to discover cheap destinations
    try:
        cheap_dests = search_destinations(origin)
        for cd in cheap_dests[:5]:
            dest = cd.get("destination")
            if dest and dest not in TOP_DESTINATIONS:
                TOP_DESTINATIONS.append(dest)
                logger.info(f"  Discovered cheap destination: {origin}→{dest}")
    except Exception as e:
        logger.warning(f"Destination discovery failed: {e}")

    for dest in TOP_DESTINATIONS:
        if dest == origin:
            continue
        seen_windows = set()
        for dep_date, days_ahead in sample_dates:
            for duration in TRIP_DURATIONS:
                dep = datetime.strptime(dep_date, "%Y-%m-%d")
                ret_date = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")

                flights, metrics = scrape_flights_for_route(origin, dest, dep_date, ret_date)
                all_normalized.extend(flights)

                window = _window_label(days_ahead)
                if metrics and window not in seen_windows:
                    baseline = bootstrap_baseline_from_metrics(origin, dest, metrics, days_ahead)
                    if baseline:
                        baselines.append(baseline)
                        seen_windows.add(window)
                        logger.info(f"  Baseline {origin}-{dest}-{window}: avg={baseline['avg_price']}€ std={baseline['std_dev']}€")

                if flights:
                    logger.info(f"  {origin}→{dest} {dep_date} ({duration}n, {window}): {len(flights)} flights")

    return all_normalized, baselines


def scrape_all_flights() -> tuple[list[dict], int, list[dict]]:
    """Scrape flights for a rotating subset of airports."""
    global _cycle_counter

    airports = settings.MVP_AIRPORTS
    start_idx = (_cycle_counter * AIRPORTS_PER_CYCLE) % len(airports)
    cycle_airports = [
        airports[(start_idx + i) % len(airports)]
        for i in range(AIRPORTS_PER_CYCLE)
    ]
    _cycle_counter += 1

    logger.info(f"Cycle {_cycle_counter}: scraping airports {cycle_airports}")

    all_flights = []
    all_baselines = []
    errors = 0

    for airport in cycle_airports:
        try:
            flights, baselines = scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            all_baselines.extend(baselines)
            logger.info(f"Scraped {len(flights)} flights + {len(baselines)} baselines from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors, all_baselines
