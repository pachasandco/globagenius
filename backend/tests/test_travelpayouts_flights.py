from app.scraper.travelpayouts_flights import (
    _window_label,
    _normalize_calendar_entry,
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
