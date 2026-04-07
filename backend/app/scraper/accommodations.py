import logging
from datetime import datetime, timedelta, timezone
from app.config import IATA_TO_CITY
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_accommodation

logger = logging.getLogger(__name__)

# voyager/booking-scraper — 3.3M runs, most popular
ACCOMMODATION_ACTOR_ID = "voyager/booking-scraper"
SOURCE = "booking"


def _extract_accommodations(items: list[dict], city: str, check_in: str, check_out: str) -> list[dict]:
    """Map Booking.com actor output to our normalizer format."""
    extracted = []
    for item in items:
        price = item.get("price")
        if not price:
            continue

        total_price = float(price)

        # Calculate nights
        try:
            ci = datetime.strptime(check_in, "%Y-%m-%d")
            co = datetime.strptime(check_out, "%Y-%m-%d")
            nights = max((co - ci).days, 1)
        except (ValueError, TypeError):
            nights = 1

        # Rating: Booking uses /10
        raw_rating = item.get("rating")
        if raw_rating:
            rating = round(float(raw_rating) / 2, 1)  # Convert /10 to /5
        else:
            rating = None

        extracted.append({
            "name": item.get("name", "Unknown"),
            "city": city,
            "pricePerNight": round(total_price / nights, 2),
            "totalPrice": total_price,
            "currency": "EUR",
            "rating": rating,
            "checkIn": check_in,
            "checkOut": check_out,
            "url": item.get("url", ""),
            "source": SOURCE,
        })

    return extracted


def scrape_accommodations_for_city(city: str, check_in: str, check_out: str) -> list[dict]:
    """Scrape accommodations for a specific city and date range."""
    run_input = {
        "search": city,
        "checkIn": check_in,
        "checkOut": check_out,
        "currency": "EUR",
        "adults": 1,
        "rooms": 1,
        "maxItems": 20,
        "sortBy": "price",
    }

    try:
        raw_items = run_actor(ACCOMMODATION_ACTOR_ID, run_input)
    except Exception as e:
        logger.warning(f"Booking actor failed for {city} {check_in}: {e}")
        return []

    accommodations = _extract_accommodations(raw_items, city, check_in, check_out)

    normalized = []
    for acc in accommodations:
        try:
            normalized.append(normalize_accommodation(acc))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to normalize accommodation: {e}")

    return normalized


def scrape_accommodations_for_destinations(destinations: set[str]) -> tuple[list[dict], int]:
    """Scrape accommodations for destination IATA codes."""
    all_accommodations = []
    errors = 0
    now = datetime.now(timezone.utc)

    sample_ranges = [
        (now + timedelta(days=20), 5),
        (now + timedelta(days=30), 7),
        (now + timedelta(days=50), 7),
    ]

    for iata_code in destinations:
        city = IATA_TO_CITY.get(iata_code)
        if not city:
            logger.warning(f"No city mapping for {iata_code}, skipping")
            continue

        city_count = 0
        for dep, duration in sample_ranges:
            check_in = dep.strftime("%Y-%m-%d")
            check_out = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")
            try:
                items = scrape_accommodations_for_city(city, check_in, check_out)
                all_accommodations.extend(items)
                city_count += len(items)
            except Exception as e:
                errors += 1
                logger.error(f"Failed to scrape {city} ({check_in}): {e}")

        if city_count:
            logger.info(f"Scraped {city_count} accommodations in {city}")

    return all_accommodations, errors
