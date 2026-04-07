import logging
from datetime import datetime, timedelta, timezone
from app.config import IATA_TO_CITY
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_accommodation

logger = logging.getLogger(__name__)

# Booking.com — most reliable for EUR + European cities
ACCOMMODATION_ACTOR = {"id": "dtrungtin/booking-scraper", "source": "booking"}


def scrape_accommodations_for_city(
    city: str, check_in: str, check_out: str
) -> list[dict]:
    """Scrape accommodations for a specific city and date range."""
    run_input = {
        "search": city,
        "checkIn": check_in,
        "checkOut": check_out,
        "currency": "EUR",
        "adults": 1,
        "rooms": 1,
        "sortBy": "price",
        "maxItems": 30,
    }

    raw_items = run_actor(ACCOMMODATION_ACTOR["id"], run_input)

    normalized = []
    for item in raw_items:
        try:
            mapped = _map_booking_output(item, city, check_in, check_out)
            if mapped:
                normalized.append(normalize_accommodation(mapped))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to normalize accommodation item: {e}")

    return normalized


def _map_booking_output(item: dict, city: str, check_in: str, check_out: str) -> dict | None:
    """Map Booking.com actor output to our expected format."""
    price = item.get("price") or item.get("totalPrice")
    if not price:
        return None

    total_price = float(price)

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
        nights = max((co - ci).days, 1)
    except (ValueError, TypeError):
        nights = 1

    price_per_night = round(total_price / nights, 2)

    # Booking.com rates /10, we want /5
    raw_rating = item.get("rating") or item.get("guestRating") or item.get("reviewScore")
    if raw_rating:
        rating = float(raw_rating)
        if rating > 5:
            rating = round(rating / 2, 1)
    else:
        rating = None

    return {
        "name": item.get("name") or item.get("hotelName") or "Unknown",
        "city": city,
        "pricePerNight": price_per_night,
        "totalPrice": total_price,
        "currency": item.get("currency", "EUR"),
        "rating": rating,
        "checkIn": check_in,
        "checkOut": check_out,
        "url": item.get("url") or item.get("link") or "",
        "source": ACCOMMODATION_ACTOR["source"],
    }


def scrape_accommodations_for_destinations(destinations: set[str]) -> tuple[list[dict], int]:
    """Scrape accommodations for destination IATA codes with sample date ranges."""
    all_accommodations = []
    errors = 0
    now = datetime.now(timezone.utc)

    sample_ranges = [
        (now + timedelta(days=20), 5),
        (now + timedelta(days=30), 7),
        (now + timedelta(days=45), 7),
    ]

    for iata_code in destinations:
        city = IATA_TO_CITY.get(iata_code)
        if not city:
            logger.warning(f"No city mapping for IATA code {iata_code}, skipping")
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
                logger.error(f"Failed to scrape accommodations in {city} ({check_in}): {e}")

        logger.info(f"Scraped {city_count} accommodations in {city}")

    return all_accommodations, errors
