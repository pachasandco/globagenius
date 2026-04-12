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


def test_scrape_flights_for_route_aggregates_calendar_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fake_entries = [
        _calendar_entry(412, 12),
        _calendar_entry(398, 13),
        _calendar_entry(450, 14),
    ]

    with patch("app.scraper.travelpayouts_flights.get_calendar_prices",
               return_value=fake_entries):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 3
    prices = sorted(f["price"] for f in flights)
    assert prices == [398.0, 412.0, 450.0]
    for f in flights:
        assert f["origin"] == "CDG"
        assert f["destination"] == "JFK"
        assert f["source"] == "travelpayouts"


def test_scrape_flights_for_route_skips_unusable_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fake_entries = [
        _calendar_entry(412, 12),
        {"departure_at": "", "price": 0},
    ]

    with patch("app.scraper.travelpayouts_flights.get_calendar_prices",
               return_value=fake_entries):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 1
    assert flights[0]["price"] == 412.0


def test_scrape_flights_for_airport_filters_long_haul_from_non_cdg():
    from app.scraper.travelpayouts_flights import scrape_flights_for_airport

    seen_routes = []

    def fake_route(origin, destination):
        seen_routes.append((origin, destination))
        return [{"price": 100.0, "destination": destination}]

    with patch("app.scraper.travelpayouts_flights.get_priority_destinations",
               return_value=["BCN", "JFK", "LIS", "BKK"]), \
         patch("app.scraper.travelpayouts_flights.scrape_flights_for_route", side_effect=fake_route):
        flights = scrape_flights_for_airport("LYS")

    destinations_called = [d for _, d in seen_routes]
    assert "BCN" in destinations_called
    assert "LIS" in destinations_called
    assert "JFK" not in destinations_called  # long-haul, blocked from LYS
    assert "BKK" not in destinations_called  # long-haul, blocked from LYS
    assert len(flights) == 2


def test_scrape_flights_for_airport_keeps_long_haul_from_cdg():
    from app.scraper.travelpayouts_flights import scrape_flights_for_airport

    seen_routes = []

    def fake_route(origin, destination):
        seen_routes.append((origin, destination))
        return [{"price": 100.0, "destination": destination}]

    with patch("app.scraper.travelpayouts_flights.get_priority_destinations",
               return_value=["BCN", "JFK", "BKK"]), \
         patch("app.scraper.travelpayouts_flights.scrape_flights_for_route", side_effect=fake_route):
        flights = scrape_flights_for_airport("CDG")

    destinations_called = [d for _, d in seen_routes]
    assert destinations_called == ["BCN", "JFK", "BKK"]
    assert len(flights) == 3


def test_scrape_flights_for_airport_skips_self_destination():
    from app.scraper.travelpayouts_flights import scrape_flights_for_airport

    seen_routes = []

    def fake_route(origin, destination):
        seen_routes.append((origin, destination))
        return []

    with patch("app.scraper.travelpayouts_flights.get_priority_destinations",
               return_value=["CDG", "BCN"]), \
         patch("app.scraper.travelpayouts_flights.scrape_flights_for_route", side_effect=fake_route):
        scrape_flights_for_airport("CDG")

    destinations_called = [d for _, d in seen_routes]
    assert destinations_called == ["BCN"]


def test_scrape_all_flights_returns_tuple_of_three():
    from app.scraper.travelpayouts_flights import scrape_all_flights
    import asyncio

    fixed_now = datetime(2026, 4, 12, 10, tzinfo=timezone.utc)

    def fake_airport(origin):
        return [{"origin": origin, "price": 100.0}]

    with patch("app.scraper.travelpayouts_flights.scrape_flights_for_airport", side_effect=fake_airport), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now), \
         patch("app.scraper.travelpayouts_flights.settings") as mock_settings:
        mock_settings.MVP_AIRPORTS = ["CDG", "ORY", "LYS", "MRS", "NCE", "BOD", "NTE", "TLS"]
        flights, errors, baselines = asyncio.run(scrape_all_flights())

    assert isinstance(flights, list)
    assert isinstance(errors, int)
    assert isinstance(baselines, list)
    assert errors == 0
    assert len(flights) == 2  # AIRPORTS_PER_CYCLE = 2
    assert baselines == []


def test_scrape_all_flights_counts_errors_per_airport():
    from app.scraper.travelpayouts_flights import scrape_all_flights
    import asyncio

    fixed_now = datetime(2026, 4, 12, 10, tzinfo=timezone.utc)

    def fake_airport(origin):
        if origin == "LYS":
            raise RuntimeError("api down")
        return [{"origin": origin, "price": 100.0}]

    with patch("app.scraper.travelpayouts_flights.scrape_flights_for_airport", side_effect=fake_airport), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now), \
         patch("app.scraper.travelpayouts_flights.settings") as mock_settings:
        mock_settings.MVP_AIRPORTS = ["LYS", "MRS"]
        flights, errors, baselines = asyncio.run(scrape_all_flights())

    assert errors == 1
    assert len(flights) == 1
    assert flights[0]["origin"] == "MRS"
