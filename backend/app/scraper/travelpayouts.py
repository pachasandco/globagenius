"""Travelpayouts / Aviasales API integration.

Free source for:
- Price baselines (GraphQL + REST cheap prices)
- Fare mistake detection (special_offers)
- Seasonal destination discovery (price map)

Docs: https://support.travelpayouts.com/hc/en-us/sections/201008338
"""

import logging
from datetime import datetime, timedelta, timezone
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.travelpayouts.com/graphql/v1/query"
REST_URL = "https://api.travelpayouts.com"
PRICE_MAP_URL = "https://map.aviasales.com"


def _headers() -> dict:
    return {"x-access-token": settings.TRAVELPAYOUTS_TOKEN}


def _get(url: str, params: dict = None) -> dict | None:
    if not settings.TRAVELPAYOUTS_TOKEN:
        return None
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=_headers(), params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Travelpayouts request failed: {e}")
        return None


def _graphql(query: str) -> dict | None:
    if not settings.TRAVELPAYOUTS_TOKEN:
        return None
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                GRAPHQL_URL,
                headers={**_headers(), "Content-Type": "application/json"},
                json={"query": query},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Travelpayouts GraphQL failed: {e}")
        return None


# ─── PRICE BASELINES ───

def get_cheap_prices(origin: str, destination: str, depart_month: str = "") -> list[dict]:
    """Get cheapest prices for a route. REST v1/prices/cheap.
    depart_month format: YYYY-MM (optional)."""
    params = {
        "origin": origin,
        "destination": destination,
        "currency": "eur",
    }
    if depart_month:
        params["depart_date"] = depart_month

    data = _get(f"{REST_URL}/v1/prices/cheap", params)
    if not data or not data.get("success"):
        return []

    prices = []
    for dest_code, flights in data.get("data", {}).items():
        for key, flight in flights.items():
            prices.append({
                "origin": origin,
                "destination": dest_code,
                "price": flight.get("price", 0),
                "airline": flight.get("airline", ""),
                "departure_at": flight.get("departure_at", ""),
                "return_at": flight.get("return_at", ""),
                "expires_at": flight.get("expires_at", ""),
            })

    return prices


def get_month_matrix(origin: str, destination: str) -> list[dict]:
    """Get prices grouped by month. REST v2/prices/month-matrix."""
    params = {
        "origin": origin,
        "destination": destination,
        "currency": "eur",
    }
    data = _get(f"{REST_URL}/v2/prices/month-matrix", params)
    if not data or not data.get("success"):
        return []

    return data.get("data", [])


def get_calendar_prices(origin: str, destination: str, depart_month: str = "") -> list[dict]:
    """Get one cheapest price per departure day.

    `depart_month` format: YYYY-MM (e.g. "2026-05"). If empty, the API
    returns the full window it has cached (typically several months).
    Calls /v1/prices/calendar with calendar_type=departure_date."""
    params = {
        "origin": origin,
        "destination": destination,
        "calendar_type": "departure_date",
        "currency": "eur",
    }
    if depart_month:
        params["depart_date"] = depart_month
    data = _get(f"{REST_URL}/v1/prices/calendar", params)
    if not data or not data.get("success"):
        return []

    entries = data.get("data") or {}
    result = []
    for day, flight in entries.items():
        if not isinstance(flight, dict):
            continue
        result.append({
            "departure_at": flight.get("departure_at") or day,
            "return_at": flight.get("return_at", ""),
            "expires_at": flight.get("expires_at", ""),
            "price": flight.get("price", 0),
            "airline": flight.get("airline", ""),
            "flight_number": flight.get("flight_number", 0),
            "transfers": flight.get("transfers", 0),
        })
    return result


def get_prices_for_dates(
    origin: str,
    destination: str,
    departure_month: str = "",
    return_month: str = "",
    limit: int = 1000,
) -> list[dict]:
    """Get real round-trip prices via /aviasales/v3/prices_for_dates.

    Returns up to `limit` round-trips with origin_airport, destination_airport,
    departure_at, return_at, price, transfers, return_transfers, duration_to,
    duration_back, link.

    `departure_month` / `return_month` format: YYYY-MM (optional).
    `one_way=false` is forced — this endpoint is round-trips only by design."""
    params = {
        "origin": origin,
        "destination": destination,
        "currency": "eur",
        "one_way": "false",
        "sorting": "price",
        "direct": "false",
        "limit": limit,
    }
    if departure_month:
        params["departure_at"] = departure_month
    if return_month:
        params["return_at"] = return_month

    data = _get(f"{REST_URL}/aviasales/v3/prices_for_dates", params)
    if not data or not data.get("success"):
        return []

    entries = data.get("data") or []
    result = []
    for flight in entries:
        if not isinstance(flight, dict):
            continue
        result.append({
            "origin_airport": flight.get("origin_airport", ""),
            "destination_airport": flight.get("destination_airport", ""),
            "departure_at": flight.get("departure_at", ""),
            "return_at": flight.get("return_at", ""),
            "price": flight.get("price", 0),
            "airline": flight.get("airline", ""),
            "flight_number": flight.get("flight_number", ""),
            "transfers": flight.get("transfers", 0),
            "return_transfers": flight.get("return_transfers", 0),
            "duration_to": flight.get("duration_to", 0),
            "duration_back": flight.get("duration_back", 0),
            "link": flight.get("link", ""),
        })
    return result


def get_prices_graphql(origin: str, destination: str, depart_month: str, limit: int = 20) -> list[dict]:
    """Get prices via GraphQL — more flexible than REST."""
    query = f"""{{
      prices_one_way(
        params: {{ origin: "{origin}", destination: "{destination}", depart_months: "{depart_month}-01" }}
        sorting: VALUE_ASC
        paging: {{ limit: {limit}, offset: 0 }}
      ) {{
        departure_at
        value
        trip_duration
        airline
        ticket_link
      }}
    }}"""

    data = _graphql(query)
    if not data:
        return []

    return data.get("data", {}).get("prices_one_way", [])


# ─── FARE MISTAKE DETECTION ───

def get_special_offers() -> list[dict]:
    """Get abnormally low prices (fare mistakes / flash sales)."""
    data = _get(f"{REST_URL}/v2/prices/special-offers")
    if not data:
        return []

    return data.get("data", [])


# ─── DESTINATION DISCOVERY ───

def get_price_map(origin: str, period: str = "season") -> list[dict]:
    """Get destinations with prices from origin.
    period: season, year, month."""
    params = {
        "origin": origin,
        "period": period,
        "direct": "false",
        "currency": "eur",
    }
    data = _get(f"{PRICE_MAP_URL}/prices.json", params)
    if not data:
        return []

    # Returns list of {destination, price, airline, departure_at, ...}
    return data if isinstance(data, list) else []


def get_cheap_destinations(origin: str, limit: int = 20) -> list[dict]:
    """Get cheapest destinations from an airport (no destination specified)."""
    params = {
        "origin": origin,
        "currency": "eur",
    }
    data = _get(f"{REST_URL}/v1/prices/cheap", params)
    if not data or not data.get("success"):
        return []

    destinations = []
    for dest_code, flights in data.get("data", {}).items():
        for key, flight in flights.items():
            destinations.append({
                "destination": dest_code,
                "price": flight.get("price", 0),
                "airline": flight.get("airline", ""),
                "departure_at": flight.get("departure_at", ""),
            })

    destinations.sort(key=lambda x: x["price"])
    return destinations[:limit]


# ─── BASELINE BUILDER ───

def build_baseline_from_travelpayouts(origin: str, destination: str) -> dict | None:
    """Build a price baseline using Travelpayouts data.
    Uses month-matrix or cheap prices to get median price."""
    # Try month matrix first
    months = get_month_matrix(origin, destination)
    if months:
        prices = [m.get("value", 0) for m in months if m.get("value")]
        if len(prices) >= 3:
            import numpy as np
            return {
                "avg_price": round(float(np.median(prices)), 2),
                "std_dev": round(float(np.std(prices)), 2),
                "sample_count": len(prices),
                "source": "travelpayouts_month_matrix",
            }

    # Fallback to cheap prices over 6 months
    now = datetime.now(timezone.utc)
    all_prices = []
    for i in range(6):
        month = (now + timedelta(days=30 * i)).strftime("%Y-%m")
        prices = get_cheap_prices(origin, destination, month)
        all_prices.extend([p["price"] for p in prices if p.get("price")])

    if len(all_prices) >= 3:
        import numpy as np
        return {
            "avg_price": round(float(np.median(all_prices)), 2),
            "std_dev": round(float(np.std(all_prices)), 2),
            "sample_count": len(all_prices),
            "source": "travelpayouts_cheap",
        }

    return None
