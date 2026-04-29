"""V5: tests for one-way and split-ticket Telegram formatters."""
from app.notifications.telegram import (
    format_oneway_deal_alert,
    format_split_ticket_alert,
)


def _oneway_flight(direction: str = "outbound", price: float = 220.0) -> dict:
    return {
        "origin": "CDG",
        "destination": "JFK",
        "departure_date": "2026-06-15",
        "price": price,
        "source_url": "https://example.com/book",
        "direction": direction,
        "airline": "FB",
    }


def test_format_oneway_outbound_basic():
    msg = format_oneway_deal_alert(
        _oneway_flight("outbound"),
        discount_pct=58.0,
        baseline_price=520.0,
    )
    assert "Aller simple" in msg
    assert "Retour simple" not in msg
    assert "220" in msg
    assert "-58" in msg
    assert "JFK" in msg
    assert "CDG" in msg


def test_format_oneway_inbound_uses_retour_label():
    msg = format_oneway_deal_alert(
        _oneway_flight("inbound"),
        discount_pct=45.0,
        baseline_price=400.0,
    )
    assert "Retour simple" in msg
    assert "Aller simple" not in msg


def test_format_oneway_includes_return_estimate_when_provided():
    msg = format_oneway_deal_alert(
        _oneway_flight("outbound"),
        discount_pct=58.0,
        baseline_price=520.0,
        return_estimate=280.0,
    )
    assert "280" in msg
    assert "Retour estimé" in msg


def test_format_oneway_omits_return_estimate_when_missing():
    msg = format_oneway_deal_alert(
        _oneway_flight("outbound"),
        discount_pct=58.0,
        baseline_price=520.0,
    )
    assert "Retour estimé" not in msg


def test_format_split_ticket_shows_total_and_savings():
    outbound = {
        "origin": "CDG",
        "destination": "BKK",
        "departure_date": "2026-04-04",
        "price": 270.0,
        "source_url": "https://example.com/out",
        "airline": "French Bee",
    }
    inbound = {
        "origin": "BKK",
        "destination": "CDG",
        "departure_date": "2026-04-22",
        "price": 270.0,
        "source_url": "https://example.com/in",
        "airline": "Norse",
    }
    msg = format_split_ticket_alert(outbound, inbound, roundtrip_baseline=780.0)
    assert "540" in msg                     # total
    assert "780" in msg                     # baseline
    assert "240" in msg                     # savings
    assert "French Bee" in msg
    assert "Norse" in msg
    assert "Combo malin" in msg
    assert "séparément" in msg


def test_format_split_ticket_handles_missing_airline_gracefully():
    outbound = {
        "origin": "CDG",
        "destination": "BKK",
        "departure_date": "2026-04-04",
        "price": 270.0,
        "source_url": "https://example.com/out",
    }
    inbound = {
        "origin": "BKK",
        "destination": "CDG",
        "departure_date": "2026-04-22",
        "price": 270.0,
        "source_url": "https://example.com/in",
    }
    msg = format_split_ticket_alert(outbound, inbound, roundtrip_baseline=780.0)
    assert "—" in msg                       # placeholder dash
    assert "540" in msg
