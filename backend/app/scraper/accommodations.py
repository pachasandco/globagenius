import logging
import asyncio
from datetime import datetime, timedelta, timezone
from app.config import IATA_TO_CITY
from app.scraper.normalizer import normalize_accommodation

logger = logging.getLogger(__name__)

SOURCE = "google_hotels"


async def _scrape_city_playwright(city: str, check_in: str, check_out: str) -> list[dict]:
    """Scrape hotels using Playwright + LLM (free)."""
    from app.scraper.browser.google_hotels import scrape_hotels_page

    result = await scrape_hotels_page(city, check_in, check_out)
    if not result:
        return []

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
        nights = max((co - ci).days, 1)
    except (ValueError, TypeError):
        nights = 7

    normalized = []
    for hotel in result.get("hotels", []):
        try:
            ppn = float(hotel.get("price_per_night", 0))
            total = float(hotel.get("total_price", 0))
            if not ppn and not total:
                continue
            if not total:
                total = ppn * nights
            if not ppn:
                ppn = round(total / nights, 2)

            rating = hotel.get("rating")
            if rating:
                rating = float(rating)
                if rating > 5:
                    rating = round(rating / 2, 1)

            raw = {
                "name": hotel.get("name", "Hotel"),
                "city": city,
                "pricePerNight": ppn,
                "totalPrice": total,
                "currency": "EUR",
                "rating": rating,
                "checkIn": check_in,
                "checkOut": check_out,
                "url": hotel.get("url", ""),
                "source": SOURCE,
            }
            normalized.append(normalize_accommodation(raw))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to normalize hotel: {e}")

    return normalized


def _scrape_city_apify(city: str, check_in: str, check_out: str) -> list[dict]:
    """Fallback: scrape via Apify Booking.com actor."""
    try:
        from app.scraper.apify_client import run_actor
    except ImportError:
        return []

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
        raw_items = run_actor("voyager/booking-scraper", run_input)
    except Exception as e:
        logger.warning(f"Apify fallback failed for {city}: {e}")
        return []

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
        nights = max((co - ci).days, 1)
    except (ValueError, TypeError):
        nights = 7

    normalized = []
    for item in raw_items:
        price = item.get("price")
        if not price:
            continue
        total_price = float(price)
        raw_rating = item.get("rating")
        rating = round(float(raw_rating) / 2, 1) if raw_rating else None

        raw = {
            "name": item.get("name", "Unknown"),
            "city": city,
            "pricePerNight": round(total_price / nights, 2),
            "totalPrice": total_price,
            "currency": "EUR",
            "rating": rating,
            "checkIn": check_in,
            "checkOut": check_out,
            "url": item.get("url", ""),
            "source": "booking",
        }
        try:
            normalized.append(normalize_accommodation(raw))
        except Exception:
            pass

    return normalized


async def scrape_accommodations_for_city(city: str, check_in: str, check_out: str) -> list[dict]:
    """Scrape hotels: Apify primary (reliable), Playwright as future option."""
    # Primary: Apify (reliable)
    hotels = _scrape_city_apify(city, check_in, check_out)
    if hotels:
        return hotels

    # Fallback: Playwright (experimental)
    try:
        hotels = await _scrape_city_playwright(city, check_in, check_out)
        if hotels:
            return hotels
    except Exception as e:
        logger.warning(f"Playwright fallback failed for {city}: {e}")

    return []


async def scrape_accommodations_for_destinations(destinations: set[str]) -> tuple[list[dict], int]:
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
            continue

        city_count = 0
        for dep, duration in sample_ranges:
            check_in = dep.strftime("%Y-%m-%d")
            check_out = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")
            try:
                items = await scrape_accommodations_for_city(city, check_in, check_out)
                all_accommodations.extend(items)
                city_count += len(items)
            except Exception as e:
                errors += 1
                logger.error(f"Failed to scrape {city}: {e}")

            await asyncio.sleep(2)

        if city_count:
            logger.info(f"Scraped {city_count} accommodations in {city}")

    return all_accommodations, errors
