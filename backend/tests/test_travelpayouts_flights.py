from app.scraper.travelpayouts_flights import (
    _window_label,
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


def _priced_entry(price=412, dep="2026-05-12", ret="2026-05-19", airline="AF",
                  transfers=0, dur_to=480, dur_back=520,
                  origin_airport="CDG", destination_airport="JFK",
                  link="/search/CDG1205JFK19051"):
    return {
        "origin_airport": origin_airport,
        "destination_airport": destination_airport,
        "departure_at": f"{dep}T10:00:00+02:00",
        "return_at": f"{ret}T18:00:00+02:00",
        "price": price,
        "airline": airline,
        "transfers": transfers,
        "return_transfers": transfers,
        "duration_to": dur_to,
        "duration_back": dur_back,
        "link": link,
    }


def test_scrape_flights_for_route_aggregates_priced_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fake_entries = [
        _priced_entry(price=412),
        _priced_entry(price=398, dep="2026-05-15", ret="2026-05-22"),
        _priced_entry(price=450, dep="2026-06-01", ret="2026-06-08"),
    ]

    with patch("app.scraper.travelpayouts_flights.get_prices_for_dates",
               return_value=fake_entries):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 3
    prices = sorted(f["price"] for f in flights)
    assert prices == [398.0, 412.0, 450.0]
    for f in flights:
        assert f["origin"] == "CDG"
        assert f["destination"] == "JFK"
        assert f["source"] == "travelpayouts"
        assert f["trip_duration_days"] == 7


def test_scrape_flights_for_route_skips_unusable_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fake_entries = [
        _priced_entry(price=412),
        _priced_entry(price=0),  # zero price → rejected
        _priced_entry(price=200, dep="2026-05-12", ret="2026-06-15"),  # 34 days → rejected
    ]

    with patch("app.scraper.travelpayouts_flights.get_prices_for_dates",
               return_value=fake_entries):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 1
    assert flights[0]["price"] == 412.0


def test_normalize_priced_entry_maps_all_fields():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry, SOURCE
    entry = _priced_entry()
    result = _normalize_priced_entry(entry)
    assert result is not None
    assert result["origin"] == "CDG"
    assert result["destination"] == "JFK"
    assert result["departure_date"] == "2026-05-12"
    assert result["return_date"] == "2026-05-19"
    assert result["price"] == 412.0
    assert result["airline"] == "AF"
    assert result["stops"] == 0
    assert result["trip_duration_days"] == 7
    assert result["duration_minutes"] == 480  # outbound leg duration
    assert result["source"] == SOURCE
    assert result["source_url"].startswith("https://www.aviasales.com")
    assert "/search/CDG1205JFK19051" in result["source_url"]


def test_normalize_priced_entry_rejects_duration_zero():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-12", ret="2026-05-12")
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_rejects_duration_above_12():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-12", ret="2026-05-25")  # 13 days
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_accepts_duration_one_day():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-12", ret="2026-05-13")
    result = _normalize_priced_entry(entry)
    assert result is not None
    assert result["trip_duration_days"] == 1


def test_normalize_priced_entry_accepts_duration_12_days():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-01", ret="2026-05-13")  # exactly 12 days
    result = _normalize_priced_entry(entry)
    assert result is not None
    assert result["trip_duration_days"] == 12


def test_normalize_priced_entry_rejects_zero_price():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(price=0)
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_rejects_missing_departure_at():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry()
    entry["departure_at"] = ""
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_rejects_missing_return_at():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry()
    entry["return_at"] = ""
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_uses_origin_airport_not_city():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(origin_airport="CDG")
    result = _normalize_priced_entry(entry)
    assert result["origin"] == "CDG"  # not "PAR"


def test_normalize_priced_entry_extracts_stops_from_transfers():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(transfers=2)
    result = _normalize_priced_entry(entry)
    assert result["stops"] == 2


def test_normalize_priced_entry_uses_api_link_in_url():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(link="/search/CDG1205JFK19051?t=abc")
    result = _normalize_priced_entry(entry)
    assert result["source_url"] == "https://www.aviasales.com/search/CDG1205JFK19051?t=abc"


def test_normalize_priced_entry_falls_back_to_built_url_when_link_missing():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(link="")
    result = _normalize_priced_entry(entry)
    assert result["source_url"].startswith("https://www.aviasales.com")


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


def test_scrape_all_flights_scrapes_every_airport():
    """With the rotation removed, scrape_all_flights must hit every airport
    in MVP_AIRPORTS on every call."""
    from app.scraper.travelpayouts_flights import scrape_all_flights
    import asyncio

    seen = []

    def fake_airport(origin):
        seen.append(origin)
        return [{"origin": origin, "price": 100.0}]

    with patch("app.scraper.travelpayouts_flights.scrape_flights_for_airport", side_effect=fake_airport), \
         patch("app.scraper.travelpayouts_flights.settings") as mock_settings:
        mock_settings.MVP_AIRPORTS = ["CDG", "ORY", "LYS", "MRS", "NCE", "BOD", "NTE", "TLS"]
        flights, errors, baselines = asyncio.run(scrape_all_flights())

    assert isinstance(flights, list)
    assert isinstance(errors, int)
    assert isinstance(baselines, list)
    assert errors == 0
    assert seen == ["CDG", "ORY", "LYS", "MRS", "NCE", "BOD", "NTE", "TLS"]
    assert len(flights) == 8  # one fake flight per airport
    assert baselines == []


def test_scrape_all_flights_counts_errors_per_airport():
    from app.scraper.travelpayouts_flights import scrape_all_flights
    import asyncio

    def fake_airport(origin):
        if origin == "LYS":
            raise RuntimeError("api down")
        return [{"origin": origin, "price": 100.0}]

    with patch("app.scraper.travelpayouts_flights.scrape_flights_for_airport", side_effect=fake_airport), \
         patch("app.scraper.travelpayouts_flights.settings") as mock_settings:
        mock_settings.MVP_AIRPORTS = ["LYS", "MRS"]
        flights, errors, baselines = asyncio.run(scrape_all_flights())

    assert errors == 1
    assert len(flights) == 1
    assert flights[0]["origin"] == "MRS"
