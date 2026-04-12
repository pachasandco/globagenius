from app.scraper.travelpayouts_flights import (
    _window_label,
    _normalize_calendar_entry,
    _build_aviasales_url,
    SOURCE,
)


def test_window_label_returns_1m_for_short_horizon():
    assert _window_label(5) == "1m"
    assert _window_label(30) == "1m"


def test_window_label_returns_2m_for_two_months():
    assert _window_label(31) == "2m"
    assert _window_label(60) == "2m"


def test_window_label_returns_3m_for_three_months():
    assert _window_label(61) == "3m"
    assert _window_label(90) == "3m"


def test_window_label_returns_4m_for_four_months():
    assert _window_label(91) == "4m"
    assert _window_label(120) == "4m"


def test_window_label_returns_6m_beyond_4_months():
    assert _window_label(121) == "6m"
    assert _window_label(365) == "6m"


def test_normalize_calendar_entry_maps_all_fields():
    entry = {
        "departure_at": "2026-05-12T10:00:00+02:00",
        "return_at": "2026-05-19T18:00:00-04:00",
        "expires_at": "2026-04-13T10:00:00Z",
        "price": 412,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }
    result = _normalize_calendar_entry(entry, origin="CDG", destination="JFK")
    assert result is not None
    assert result["origin"] == "CDG"
    assert result["destination"] == "JFK"
    assert result["price"] == 412.0
    assert result["departure_date"] == "2026-05-12"
    assert result["return_date"] == "2026-05-19"
    assert result["airline"] == "AF"
    assert result["stops"] == 0
    assert result["source"] == SOURCE
    assert result["source_url"].startswith("https://www.aviasales.com/search/")


def test_normalize_calendar_entry_falls_back_when_return_at_missing():
    entry = {
        "departure_at": "2026-05-12T10:00:00+02:00",
        "return_at": "",
        "expires_at": "",
        "price": 412,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 1,
    }
    result = _normalize_calendar_entry(entry, origin="CDG", destination="JFK")
    assert result is not None
    assert result["return_date"] == "2026-05-19"  # depart + 7 days
    assert result["stops"] == 1


def test_normalize_calendar_entry_returns_none_for_zero_price():
    entry = {
        "departure_at": "2026-05-12T10:00:00+02:00",
        "return_at": "2026-05-19T18:00:00-04:00",
        "expires_at": "",
        "price": 0,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }
    assert _normalize_calendar_entry(entry, origin="CDG", destination="JFK") is None


def test_normalize_calendar_entry_returns_none_for_missing_departure_at():
    entry = {
        "departure_at": "",
        "return_at": "",
        "expires_at": "",
        "price": 412,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }
    assert _normalize_calendar_entry(entry, origin="CDG", destination="JFK") is None


def test_build_aviasales_url_happy_path():
    url = _build_aviasales_url("CDG", "JFK", "2026-05-12", "2026-05-19")
    assert url == "https://www.aviasales.com/search/CDG1205JFK19051"


def test_build_aviasales_url_falls_back_on_invalid_date():
    url = _build_aviasales_url("CDG", "JFK", "not-a-date", "2026-05-19")
    assert url.startswith("https://www.aviasales.com/search?")
    assert "origin=CDG" in url
    assert "destination=JFK" in url


def test_build_aviasales_url_falls_back_on_empty_dates():
    url = _build_aviasales_url("CDG", "JFK", "", "")
    assert url.startswith("https://www.aviasales.com/search?")


from unittest.mock import patch
from datetime import datetime, timezone


def _calendar_entry(price: int, day: int, month: int = 5):
    return {
        "departure_at": f"2026-{month:02d}-{day:02d}T10:00:00+02:00",
        "return_at": f"2026-{month:02d}-{(day + 7):02d}T18:00:00+02:00",
        "expires_at": "2026-04-13T10:00:00Z",
        "price": price,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }


def test_scrape_flights_for_route_calls_three_months_and_aggregates():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fixed_now = datetime(2026, 4, 12, tzinfo=timezone.utc)

    def fake_get_calendar(origin, destination, month):
        return {
            "2026-05": [_calendar_entry(412, 12), _calendar_entry(398, 13)],
            "2026-06": [_calendar_entry(450, 14, month=6)],
            "2026-07": [_calendar_entry(380, 15, month=7)],
        }.get(month, [])

    with patch("app.scraper.travelpayouts_flights.get_calendar_prices", side_effect=fake_get_calendar), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 4
    prices = sorted(f["price"] for f in flights)
    assert prices == [380.0, 398.0, 412.0, 450.0]
    for f in flights:
        assert f["origin"] == "CDG"
        assert f["destination"] == "JFK"
        assert f["source"] == "travelpayouts"


def test_scrape_flights_for_route_skips_unusable_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fixed_now = datetime(2026, 4, 12, tzinfo=timezone.utc)

    def fake_get_calendar(origin, destination, month):
        if month == "2026-05":
            return [_calendar_entry(412, 12), {"departure_at": "", "price": 0}]
        return []

    with patch("app.scraper.travelpayouts_flights.get_calendar_prices", side_effect=fake_get_calendar), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 1
    assert flights[0]["price"] == 412.0
