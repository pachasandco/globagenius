from unittest.mock import patch
from app.scraper.travelpayouts import get_calendar_prices


def test_get_calendar_prices_parses_response():
    fake_response = {
        "data": {
            "2026-05-12": {
                "origin": "PAR",
                "destination": "NYC",
                "airline": "AF",
                "departure_at": "2026-05-12T10:00:00+02:00",
                "return_at": "2026-05-19T18:00:00-04:00",
                "expires_at": "2026-04-13T10:00:00Z",
                "price": 412,
                "flight_number": 22,
                "transfers": 0,
            },
            "2026-05-13": {
                "origin": "PAR",
                "destination": "NYC",
                "airline": "DL",
                "departure_at": "2026-05-13T11:00:00+02:00",
                "return_at": "2026-05-20T19:00:00-04:00",
                "expires_at": "2026-04-13T10:00:00Z",
                "price": 398,
                "flight_number": 41,
                "transfers": 1,
            },
        },
        "success": True,
    }
    with patch("app.scraper.travelpayouts._get", return_value=fake_response):
        result = get_calendar_prices("CDG", "JFK", "2026-05")
    assert len(result) == 2
    prices = sorted(r["price"] for r in result)
    assert prices == [398, 412]
    by_price = {r["price"]: r for r in result}
    assert by_price[412]["airline"] == "AF"
    assert by_price[412]["departure_at"] == "2026-05-12T10:00:00+02:00"
    assert by_price[412]["transfers"] == 0
    assert by_price[398]["transfers"] == 1


def test_get_calendar_prices_returns_empty_on_no_data():
    with patch("app.scraper.travelpayouts._get", return_value=None):
        assert get_calendar_prices("CDG", "JFK", "2026-05") == []


def test_get_calendar_prices_returns_empty_on_unsuccessful_response():
    with patch("app.scraper.travelpayouts._get", return_value={"success": False}):
        assert get_calendar_prices("CDG", "JFK", "2026-05") == []


def test_get_calendar_prices_returns_empty_on_empty_data_dict():
    with patch("app.scraper.travelpayouts._get", return_value={"success": True, "data": {}}):
        assert get_calendar_prices("CDG", "JFK", "2026-05") == []


def test_get_calendar_prices_falls_back_to_day_key_when_departure_at_missing():
    fake_response = {
        "data": {
            "2026-05-12": {
                "airline": "AF",
                "price": 412,
                "transfers": 0,
                # departure_at intentionally absent
            },
        },
        "success": True,
    }
    with patch("app.scraper.travelpayouts._get", return_value=fake_response):
        result = get_calendar_prices("CDG", "JFK", "2026-05")
    assert len(result) == 1
    assert result[0]["departure_at"] == "2026-05-12"
