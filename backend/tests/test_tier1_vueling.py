"""Tests for the Vueling Tier 1 scraper after the apiwww.vueling.com migration.

The old booking.vueling.com endpoint is dead. We mock httpx to verify
the parser handles the new GetAllFlights array shape correctly:
{DepartureDate, Price, IsInvalidPrice, ...}.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.scraper import tier1_vueling


def _make_response(status_code=200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.raise_for_status = MagicMock(return_value=None)
    if status_code >= 400:
        err = httpx.HTTPStatusError("err", request=MagicMock(), response=resp)
        resp.raise_for_status.side_effect = err
    return resp


@pytest.fixture(autouse=True)
def reset_failure_counts():
    tier1_vueling._failure_counts.clear()
    yield
    tier1_vueling._failure_counts.clear()


def test_parses_valid_fares_into_normalized_flights():
    """Happy path: API returns 2 valid fares, both should be parsed."""
    api_response = [
        {
            "DepartureDate": "2026-06-01T05:10:00",
            "ArrivalDate": "2026-06-01T07:30:00",
            "DepartureStation": "ORY",
            "ArrivalStation": "BCN",
            "Price": 95.99,
            "Tax": 0.0,
            "IsInvalidPrice": False,
        },
        {
            "DepartureDate": "2026-06-02T08:00:00",
            "ArrivalDate": "2026-06-02T10:30:00",
            "DepartureStation": "ORY",
            "ArrivalStation": "BCN",
            "Price": 120.00,
            "IsInvalidPrice": False,
        },
    ]

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _make_response(200, api_response)

    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        flights = tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)

    assert len(flights) == 2
    f0 = flights[0]
    assert f0["origin"] == "ORY"
    assert f0["destination"] == "BCN"
    assert f0["departure_date"] == "2026-06-01"
    assert f0["return_date"] == "2026-06-08"  # +7d approximation
    assert f0["price"] == 95.99
    assert f0["source"] == "vueling_direct"
    assert f0["trip_duration_days"] == 7


def test_invalid_prices_are_dropped():
    """IsInvalidPrice=True entries must be skipped, valid ones kept."""
    api_response = [
        {"DepartureDate": "2026-06-01T05:10:00", "Price": 95.99, "IsInvalidPrice": True},
        {"DepartureDate": "2026-06-02T05:10:00", "Price": 120.00, "IsInvalidPrice": False},
    ]
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _make_response(200, api_response)

    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        flights = tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)

    assert len(flights) == 1
    assert flights[0]["departure_date"] == "2026-06-02"


def test_zero_or_missing_price_is_dropped():
    api_response = [
        {"DepartureDate": "2026-06-01T05:10:00", "Price": 0, "IsInvalidPrice": False},
        {"DepartureDate": "2026-06-02T05:10:00", "Price": None, "IsInvalidPrice": False},
        {"DepartureDate": "2026-06-03T05:10:00", "Price": 50.0, "IsInvalidPrice": False},
    ]
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _make_response(200, api_response)

    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        flights = tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)

    assert len(flights) == 1
    assert flights[0]["price"] == 50.0


def test_unexpected_response_shape_returns_empty():
    """Should return [] without crashing if response is not a list."""
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _make_response(200, {"unexpected": "dict"})

    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        flights = tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)

    assert flights == []


def test_http_error_marks_failure_and_demotes_after_3():
    """3 consecutive HTTP errors must demote the route."""
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _make_response(500)

    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        for _ in range(3):
            tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)

    assert tier1_vueling.is_demoted("ORY", "BCN") is True


def test_success_resets_failure_counter():
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client

    # First call: HTTP error
    mock_client.get.return_value = _make_response(500)
    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)
    assert tier1_vueling._failure_counts.get("ORY-BCN") == 1

    # Second call: success — counter must reset
    mock_client.get.return_value = _make_response(200, [
        {"DepartureDate": "2026-06-01T05:10:00", "Price": 50.0, "IsInvalidPrice": False}
    ])
    with patch.object(tier1_vueling.httpx, "Client", return_value=mock_client):
        tier1_vueling.get_calendar_fares("ORY", "BCN", 2026, 6, 3)
    assert "ORY-BCN" not in tier1_vueling._failure_counts


def test_scrape_route_short_circuits_when_demoted():
    """If a route hits MAX_FAILURES, scrape_route must return [] without
    calling the network."""
    tier1_vueling._failure_counts["ORY-BCN"] = tier1_vueling.MAX_FAILURES

    with patch.object(tier1_vueling.httpx, "Client") as client_factory:
        flights = tier1_vueling.scrape_route("ORY", "BCN")

    assert flights == []
    client_factory.assert_not_called()
