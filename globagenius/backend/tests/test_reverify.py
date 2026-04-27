from unittest.mock import patch
import asyncio
from app.scraper.reverify import reverify_flight_price


def _flight(origin="CDG", destination="BCN", departure_date="2026-05-12",
            return_date="2026-05-19", price=100.0, airline="AF"):
    return {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "price": price,
        "airline": airline,
    }


def _api_entry(price, departure_date="2026-05-12", return_date="2026-05-19", airline="AF"):
    return {
        "origin_airport": "CDG",
        "destination_airport": "BCN",
        "departure_at": f"{departure_date}T10:00:00+02:00",
        "return_at": f"{return_date}T18:00:00+02:00",
        "price": price,
        "airline": airline,
        "transfers": 0,
        "duration_to": 100,
        "duration_back": 110,
        "link": "/search/...",
    }


def test_reverify_returns_true_when_price_unchanged():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(100)]):
        assert asyncio.run(reverify_flight_price(flight)) is True


def test_reverify_returns_true_when_price_decreased():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(85)]):
        assert asyncio.run(reverify_flight_price(flight)) is True


def test_reverify_returns_true_within_5_pct_tolerance():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(105)]):
        assert asyncio.run(reverify_flight_price(flight)) is True


def test_reverify_returns_false_above_5_pct_tolerance():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(106)]):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_returns_false_when_flight_disappeared():
    flight = _flight(price=100.0, departure_date="2026-05-12")
    # API returns flights for different dates -> no match
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(80, departure_date="2026-06-01")]):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_returns_false_when_api_returns_empty():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates", return_value=[]):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_returns_false_on_api_exception():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               side_effect=RuntimeError("network down")):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_matches_on_dates_only_when_airline_differs():
    """If the API returns the same dates with a different airline, accept it
    as long as the price is within tolerance — the user might book either."""
    flight = _flight(price=100.0, airline="AF")
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(98, airline="VY")]):
        assert asyncio.run(reverify_flight_price(flight)) is True
