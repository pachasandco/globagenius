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


# ---------- Grouped flight alerts (Phase 2) ----------

def test_format_grouped_flight_alerts_single_offer():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [{"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 89, "discount_pct": 55}]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="premium")
    assert "LISBONNE" in msg
    assert "1 offre" in msg  # singular
    assert "2 offres" not in msg
    assert "Sept" in msg
    assert "89€" in msg
    assert "-55%" in msg
    assert "/home?dest=LIS" in msg
    assert "🟠" in msg  # 55% → orange


def test_format_grouped_flight_alerts_multiple_months():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [
        {"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 89, "discount_pct": 55},
        {"departure_date": "2026-10-15", "return_date": "2026-10-22", "price": 112, "discount_pct": 48},
        {"departure_date": "2026-11-20", "return_date": "2026-11-27", "price": 95, "discount_pct": 52},
    ]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="premium")
    assert "3 offres" in msg
    assert msg.count("📅") == 3
    assert "Sept" in msg and "Oct" in msg and "Nov" in msg


def test_format_grouped_flight_alerts_same_month_concat():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [
        {"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 89, "discount_pct": 55},
        {"departure_date": "2026-09-15", "return_date": "2026-09-22", "price": 112, "discount_pct": 48},
    ]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="premium")
    assert msg.count("📅 Sept") == 1  # single line
    assert "89€" in msg and "112€" in msg
    assert "·" in msg  # separator


def test_format_grouped_flight_alerts_caps_at_10():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [
        {"departure_date": f"2026-{((i % 12) + 1):02d}-01", "return_date": f"2026-{((i % 12) + 1):02d}-10",
         "price": 100 + i, "discount_pct": 60 - i}
        for i in range(15)
    ]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="premium")
    assert "15 offres" in msg  # header shows total
    assert "+ 5 autres" in msg  # cap overflow indicator


def test_format_grouped_flight_badge_red():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [{"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 50, "discount_pct": 65}]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="premium")
    assert "🔴" in msg


def test_format_grouped_flight_badge_orange():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [{"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 70, "discount_pct": 45}]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="premium")
    assert "🟠" in msg


def test_format_grouped_flight_badge_yellow():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [{"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 100, "discount_pct": 25}]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="free")
    assert "🟡" in msg


def test_format_grouped_flight_free_tier_upsell():
    from app.notifications.telegram import format_grouped_flight_alerts
    offers = [{"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 89, "discount_pct": 30}]
    msg = format_grouped_flight_alerts("Paris", "Lisbonne", "LIS", offers, tier="free")
    assert "premium" in msg.lower()


@pytest.mark.asyncio
async def test_send_grouped_flight_alerts_calls_bot():
    from app.notifications.telegram import send_grouped_flight_alerts
    offers = [{"departure_date": "2026-09-01", "return_date": "2026-09-10", "price": 89, "discount_pct": 55}]
    sent_messages = []
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=lambda chat_id, text: sent_messages.append((chat_id, text)))
    with patch("app.notifications.telegram._get_bot", return_value=mock_bot):
        result = await send_grouped_flight_alerts(
            chat_id=123,
            origin_city="Paris",
            dest_city="Lisbonne",
            destination_iata="LIS",
            offers=offers,
            tier="premium",
        )
    assert result is True
    assert len(sent_messages) == 1
    chat_id_sent, text_sent = sent_messages[0]
    assert chat_id_sent == 123
    assert "LISBONNE" in text_sent
    assert "89€" in text_sent
