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


def test_get_calendar_prices_omits_depart_date_when_month_not_provided():
    captured = {}

    def fake_get(url, params=None):
        captured["params"] = params
        return {"success": True, "data": {}}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_calendar_prices("CDG", "JFK")

    assert "depart_date" not in captured["params"]
    assert captured["params"]["origin"] == "CDG"
    assert captured["params"]["destination"] == "JFK"


def test_get_calendar_prices_includes_depart_date_when_month_provided():
    captured = {}

    def fake_get(url, params=None):
        captured["params"] = params
        return {"success": True, "data": {}}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_calendar_prices("CDG", "JFK", "2026-05")

    assert captured["params"]["depart_date"] == "2026-05"


from app.scraper.travelpayouts import get_prices_for_dates


def test_get_prices_for_dates_parses_response():
    fake_response = {
        "data": [
            {
                "flight_number": "1248",
                "link": "/search/CDG0205BCN06051?t=...",
                "origin_airport": "CDG",
                "destination_airport": "BCN",
                "departure_at": "2026-05-02T18:35:00+02:00",
                "airline": "AF",
                "destination": "BCN",
                "return_at": "2026-05-06T21:15:00+02:00",
                "origin": "PAR",
                "price": 100,
                "gate": "Kiwi.com",
                "return_transfers": 0,
                "duration": 220,
                "duration_to": 105,
                "duration_back": 115,
                "transfers": 0,
            }
        ],
        "success": True,
    }
    with patch("app.scraper.travelpayouts._get", return_value=fake_response):
        result = get_prices_for_dates("CDG", "BCN")

    assert len(result) == 1
    r = result[0]
    assert r["origin_airport"] == "CDG"
    assert r["destination_airport"] == "BCN"
    assert r["departure_at"] == "2026-05-02T18:35:00+02:00"
    assert r["return_at"] == "2026-05-06T21:15:00+02:00"
    assert r["price"] == 100
    assert r["airline"] == "AF"
    assert r["transfers"] == 0
    assert r["return_transfers"] == 0
    assert r["duration_to"] == 105
    assert r["duration_back"] == 115
    assert r["link"] == "/search/CDG0205BCN06051?t=..."


def test_get_prices_for_dates_returns_empty_on_no_data():
    with patch("app.scraper.travelpayouts._get", return_value=None):
        assert get_prices_for_dates("CDG", "BCN") == []


def test_get_prices_for_dates_returns_empty_on_unsuccessful_response():
    with patch("app.scraper.travelpayouts._get", return_value={"success": False}):
        assert get_prices_for_dates("CDG", "BCN") == []


def test_get_prices_for_dates_returns_empty_on_empty_data_list():
    with patch("app.scraper.travelpayouts._get", return_value={"success": True, "data": []}):
        assert get_prices_for_dates("CDG", "BCN") == []


def test_get_prices_for_dates_forces_one_way_false():
    captured = {}

    def fake_get(url, params=None):
        captured["url"] = url
        captured["params"] = params
        return {"success": True, "data": []}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_prices_for_dates("CDG", "BCN")

    assert "/aviasales/v3/prices_for_dates" in captured["url"]
    assert captured["params"]["one_way"] == "false"
    assert captured["params"]["origin"] == "CDG"
    assert captured["params"]["destination"] == "BCN"
    assert captured["params"]["currency"] == "eur"


def test_get_prices_for_dates_includes_optional_months():
    captured = {}

    def fake_get(url, params=None):
        captured["params"] = params
        return {"success": True, "data": []}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_prices_for_dates("CDG", "BCN", departure_month="2026-05", return_month="2026-05")

    assert captured["params"]["departure_at"] == "2026-05"
    assert captured["params"]["return_at"] == "2026-05"


def test_get_prices_for_dates_omits_optional_months_when_blank():
    captured = {}

    def fake_get(url, params=None):
        captured["params"] = params
        return {"success": True, "data": []}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_prices_for_dates("CDG", "BCN")

    assert "departure_at" not in captured["params"]
    assert "return_at" not in captured["params"]
