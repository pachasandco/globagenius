import logging
from datetime import datetime, timedelta, timezone
from app.config import IATA_TO_CITY
from app.scraper.amadeus_client import search_hotels_by_city, search_hotel_offers
from app.scraper.normalizer import normalize_accommodation

logger = logging.getLogger(__name__)

SOURCE = "amadeus"

# IATA city codes (different from airport codes for some cities)
CITY_CODES = {
    "LIS": "LIS", "BCN": "BCN", "FCO": "ROM", "ATH": "ATH",
    "PRG": "PRG", "RAK": "RAK", "IST": "IST", "AMS": "AMS",
    "MAD": "MAD", "BER": "BER", "DUB": "DUB", "NAP": "NAP",
    "BUD": "BUD", "OPO": "OPO", "JFK": "NYC", "BKK": "BKK",
    "DXB": "DXB", "NRT": "TYO",
}


def scrape_accommodations_for_city(city_code: str, city_name: str, check_in: str, check_out: str) -> list[dict]:
    """Scrape hotel offers for a city via Amadeus."""
    # Step 1: Get hotel list for the city
    hotels = search_hotels_by_city(city_code)
    if not hotels:
        logger.info(f"No hotels found for city {city_code}")
        return []

    # Take top 20 hotel IDs
    hotel_ids = [h.get("hotelId") for h in hotels[:20] if h.get("hotelId")]
    if not hotel_ids:
        return []

    # Step 2: Get offers for these hotels
    offers = search_hotel_offers(hotel_ids, check_in, check_out)

    # Step 3: Normalize
    normalized = []
    for offer_data in offers:
        hotel_info = offer_data.get("hotel", {})
        hotel_offers = offer_data.get("offers", [])

        for ho in hotel_offers:
            price_info = ho.get("price", {})
            total = price_info.get("total")
            if not total:
                continue

            total_price = float(total)
            try:
                ci = datetime.strptime(check_in, "%Y-%m-%d")
                co = datetime.strptime(check_out, "%Y-%m-%d")
                nights = max((co - ci).days, 1)
            except (ValueError, TypeError):
                nights = 1

            # Rating from Amadeus (1-5 stars)
            rating_str = hotel_info.get("rating")
            rating = float(rating_str) if rating_str else None

            raw = {
                "name": hotel_info.get("name", "Hotel"),
                "city": city_name,
                "pricePerNight": round(total_price / nights, 2),
                "totalPrice": total_price,
                "currency": price_info.get("currency", "EUR"),
                "rating": rating,
                "checkIn": check_in,
                "checkOut": check_out,
                "url": f"https://www.booking.com/searchresults.html?ss={city_name}&checkin={check_in}&checkout={check_out}",
                "source": SOURCE,
            }

            try:
                normalized.append(normalize_accommodation(raw))
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
        city_name = IATA_TO_CITY.get(iata_code)
        city_code = CITY_CODES.get(iata_code, iata_code)
        if not city_name:
            logger.warning(f"No city mapping for {iata_code}, skipping")
            continue

        city_count = 0
        for dep, duration in sample_ranges:
            check_in = dep.strftime("%Y-%m-%d")
            check_out = (dep + timedelta(days=duration)).strftime("%Y-%m-%d")
            try:
                items = scrape_accommodations_for_city(city_code, city_name, check_in, check_out)
                all_accommodations.extend(items)
                city_count += len(items)
            except Exception as e:
                errors += 1
                logger.error(f"Failed to scrape {city_name} ({check_in}): {e}")

        if city_count:
            logger.info(f"Scraped {city_count} accommodations in {city_name}")

    return all_accommodations, errors
