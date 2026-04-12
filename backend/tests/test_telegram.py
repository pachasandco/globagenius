import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.notifications.telegram import format_deal_alert, format_admin_report, format_digest, send_deal_alert


def test_format_deal_alert():
    package = {
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "flight_price": 89.0,
        "accommodation_price": 420.0,
        "total_price": 509.0,
        "discount_pct": 47.9,
        "score": 84,
    }
    flight = {"source_url": "https://flights.example.com", "airline": "TAP Portugal"}
    accommodation = {
        "name": "Hotel Lisboa Plaza",
        "rating": 4.3,
        "source_url": "https://hotel.example.com",
    }
    msg = format_deal_alert(package, flight, accommodation)
    assert "Lisbon" in msg or "CDG" in msg  # City name or IATA code
    assert "509" in msg
    assert "47.9" in msg
    assert "84" in msg
    assert "https://flights.example.com" in msg
    assert "https://hotel.example.com" in msg


def test_format_admin_report():
    stats = {
        "flight_scrapes": 12,
        "accommodation_scrapes": 6,
        "total_flights": 2340,
        "total_accommodations": 1890,
        "errors": 2,
        "packages_qualified": 47,
        "qualification_rate": 3.2,
        "alerts_sent": 12,
        "active_baselines": 186,
    }
    msg = format_admin_report(stats)
    assert "12" in msg
    assert "47" in msg
    assert "3.2" in msg


def test_format_digest():
    packages = [
        {
            "origin": "CDG",
            "destination": "LIS",
            "total_price": 509.0,
            "discount_pct": 47.9,
            "score": 84,
            "departure_date": "2026-05-10",
            "return_date": "2026-05-17",
        },
        {
            "origin": "LYS",
            "destination": "BCN",
            "total_price": 320.0,
            "discount_pct": 52.1,
            "score": 78,
            "departure_date": "2026-05-15",
            "return_date": "2026-05-20",
        },
    ]
    msg = format_digest(packages)
    assert "CDG" in msg
    assert "LYS" in msg
    assert "Top" in msg or "top" in msg or "DIGEST" in msg


@pytest.mark.asyncio
async def test_send_deal_alert_premium_tier_includes_booking_link():
    pkg = {
        "origin": "CDG", "destination": "BCN",
        "total_price": 100, "discount_pct": 50, "score": 85,
        "departure_date": "2026-05-12", "return_date": "2026-05-19",
    }
    flight_data = {"source_url": "https://example.com/book", "airline": "AF"}
    acc_data = {"name": "Hotel X", "rating": 4.5, "source_url": "https://example.com/hotel"}

    sent_messages = []

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=lambda chat_id, text: sent_messages.append(text))

    with patch("app.notifications.telegram._get_bot", return_value=mock_bot):
        await send_deal_alert("123", pkg, flight_data, acc_data, tier="premium")

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "https://example.com/book" in msg
    # Premium messages should NOT show the upgrade CTA
    assert "compte premium" not in msg.lower()


@pytest.mark.asyncio
async def test_send_deal_alert_free_tier_includes_upgrade_cta():
    pkg = {
        "origin": "CDG", "destination": "BCN",
        "total_price": 150, "discount_pct": 25, "score": 60,
        "departure_date": "2026-05-12", "return_date": "2026-05-19",
    }
    flight_data = {"source_url": "https://example.com/book", "airline": "AF"}
    acc_data = {"name": "Hotel X", "rating": 4.5, "source_url": "https://example.com/hotel"}

    sent_messages = []

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=lambda chat_id, text: sent_messages.append(text))

    with patch("app.notifications.telegram._get_bot", return_value=mock_bot):
        await send_deal_alert("123", pkg, flight_data, acc_data, tier="free")

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "compte premium" in msg.lower()


@pytest.mark.asyncio
async def test_send_deal_alert_default_tier_is_premium_for_backward_compat():
    """Calls without explicit tier default to premium (legacy behavior)."""
    pkg = {
        "origin": "CDG", "destination": "BCN", "total_price": 100,
        "discount_pct": 45, "score": 80,
        "departure_date": "2026-05-12", "return_date": "2026-05-19",
    }
    flight_data = {"source_url": "https://example.com/book", "airline": "AF"}
    acc_data = {"name": "Hotel X", "rating": 4.5, "source_url": "https://example.com/hotel"}

    sent_messages = []

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=lambda chat_id, text: sent_messages.append(text))

    with patch("app.notifications.telegram._get_bot", return_value=mock_bot):
        await send_deal_alert("123", pkg, flight_data, acc_data)

    assert len(sent_messages) == 1
    # Default tier is premium → no upgrade CTA
    assert "compte premium" not in sent_messages[0].lower()
