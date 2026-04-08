"""Amadeus Self-Service API client.

Replaces Apify for flight and hotel data. Uses official Amadeus APIs:
- Flight Offers Search (GET /v2/shopping/flight-offers)
- Flight Price Analysis (GET /v1/analytics/itinerary-price-metrics)
- Flight Cheapest Date Search (GET /v1/shopping/flight-dates)
- Hotel Search (GET /v1/reference-data/locations/hotels/by-city)
- Hotel Offers (GET /v3/shopping/hotel-offers)

Docs: https://developers.amadeus.com/self-service
"""

import logging
import time
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
BASE_URL = "https://test.api.amadeus.com"  # Switch to api.amadeus.com for production

_token_cache = {"token": None, "expires_at": 0}


def _get_token() -> str | None:
    """Get or refresh OAuth2 access token."""
    if not settings.AMADEUS_API_KEY or not settings.AMADEUS_API_SECRET:
        logger.warning("AMADEUS_API_KEY or AMADEUS_API_SECRET not set")
        return None

    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(TOKEN_URL, data={
                "grant_type": "client_credentials",
                "client_id": settings.AMADEUS_API_KEY,
                "client_secret": settings.AMADEUS_API_SECRET,
            })
            resp.raise_for_status()
            data = resp.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = now + data.get("expires_in", 1799)
            logger.info("Amadeus token refreshed")
            return _token_cache["token"]
    except Exception as e:
        logger.error(f"Failed to get Amadeus token: {e}")
        return None


def _get(path: str, params: dict) -> dict | None:
    """Make authenticated GET request to Amadeus API."""
    token = _get_token()
    if not token:
        return None

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{BASE_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 429:
                logger.warning("Amadeus rate limited, waiting 1s")
                time.sleep(1)
                return _get(path, params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"Amadeus API error {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"Amadeus request failed: {e}")
        return None


# ─── FLIGHT APIs ───

def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    adults: int = 1,
    currency: str = "EUR",
    max_results: int = 10,
) -> list[dict]:
    """Search flight offers.
    GET /v2/shopping/flight-offers
    Returns list of flight offers with prices."""

    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": adults,
        "currencyCode": currency,
        "max": max_results,
        "nonStop": "false",
    }
    if return_date:
        params["returnDate"] = return_date

    data = _get("/v2/shopping/flight-offers", params)
    if not data:
        return []

    return data.get("data", [])


def get_price_metrics(
    origin: str,
    destination: str,
    departure_date: str,
    currency: str = "EUR",
) -> dict | None:
    """Get price analysis/metrics for a route.
    GET /v1/analytics/itinerary-price-metrics
    Returns min, max, median, first/third quartile prices."""

    params = {
        "originIataCode": origin,
        "destinationIataCode": destination,
        "departureDate": departure_date,
        "currencyCode": currency,
        "oneWay": "false",
    }

    data = _get("/v1/analytics/itinerary-price-metrics", params)
    if not data or not data.get("data"):
        return None

    return data["data"][0] if data["data"] else None


def search_cheapest_dates(
    origin: str,
    destination: str,
    departure_date: str | None = None,
) -> list[dict]:
    """Find cheapest travel dates.
    GET /v1/shopping/flight-dates
    Returns list of dates with prices."""

    params = {
        "origin": origin,
        "destination": destination,
        "oneWay": "false",
    }
    if departure_date:
        params["departureDate"] = departure_date

    data = _get("/v1/shopping/flight-dates", params)
    if not data:
        return []

    return data.get("data", [])


def search_destinations(
    origin: str,
    departure_date: str | None = None,
    max_price: int | None = None,
) -> list[dict]:
    """Find cheapest destinations from an airport.
    GET /v1/shopping/flight-destinations
    Returns list of destinations with prices."""

    params = {"origin": origin, "oneWay": "false"}
    if departure_date:
        params["departureDate"] = departure_date
    if max_price:
        params["maxPrice"] = max_price

    data = _get("/v1/shopping/flight-destinations", params)
    if not data:
        return []

    return data.get("data", [])


# ─── HOTEL APIs ───

def search_hotels_by_city(city_code: str) -> list[dict]:
    """Get hotel list for a city.
    GET /v1/reference-data/locations/hotels/by-city"""

    params = {"cityCode": city_code}
    data = _get("/v1/reference-data/locations/hotels/by-city", params)
    if not data:
        return []

    return data.get("data", [])


def search_hotel_offers(
    hotel_ids: list[str],
    check_in: str,
    check_out: str,
    adults: int = 1,
    currency: str = "EUR",
) -> list[dict]:
    """Get hotel offers/prices.
    GET /v3/shopping/hotel-offers"""

    params = {
        "hotelIds": ",".join(hotel_ids[:20]),  # Max 20 per request
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": adults,
        "currency": currency,
    }

    data = _get("/v3/shopping/hotel-offers", params)
    if not data:
        return []

    return data.get("data", [])
