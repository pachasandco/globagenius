"""V5+: tests for the split-ticket combo matcher.

A combo qualifies when:
  outbound.price + inbound.price <= roundtrip_baseline * 0.85
  AND savings >= 100 EUR
  AND inbound.departure_date - outbound.departure_date in [4, 30] days
"""
from app.analysis.split_ticket_matcher import (
    find_split_ticket_combos,
    SplitTicketCombo,
)


def _ow(direction: str, dep: str, price: float, airline: str = "X", url: str = "u") -> dict:
    """Tiny helper to build a one-way row dict."""
    if direction == "outbound":
        origin, destination = "CDG", "BKK"
    else:
        origin, destination = "BKK", "CDG"
    return {
        "origin": origin,
        "destination": destination,
        "departure_date": dep,
        "price": price,
        "airline": airline,
        "source_url": url,
        "trip_type": "one_way",
        "direction": direction,
    }


def test_returns_empty_when_no_outbound():
    combos = find_split_ticket_combos(
        outbounds=[],
        inbounds=[_ow("inbound", "2026-04-22", 270)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_returns_empty_when_no_inbound():
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270)],
        inbounds=[],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_qualifies_when_total_15pct_below_baseline_and_savings_above_100():
    # Baseline 780, total 540 → savings 240 (-30%). Stay = 18 days (in [4, 30]).
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270, airline="French Bee")],
        inbounds=[_ow("inbound", "2026-04-22", 270, airline="Norse")],
        roundtrip_baseline=780.0,
    )
    assert len(combos) == 1
    c = combos[0]
    assert c.outbound["airline"] == "French Bee"
    assert c.inbound["airline"] == "Norse"
    assert c.total == 540
    assert c.savings == 240


def test_rejected_when_savings_below_100_eur_floor():
    # Total 720, baseline 780 → savings 60 (only ~7.7%). Below 100€ floor.
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 360)],
        inbounds=[_ow("inbound", "2026-04-22", 360)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_rejected_when_total_within_15pct_of_baseline():
    # Total 670, baseline 780 → 14.1% saving (under 15%) but 110€ saving.
    # 0.85 * 780 = 663 → total 670 > threshold → rejected.
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 335)],
        inbounds=[_ow("inbound", "2026-04-22", 335)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_rejected_when_stay_too_short():
    # 3-day stay (< 4-day floor)
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270)],
        inbounds=[_ow("inbound", "2026-04-07", 270)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_rejected_when_stay_too_long():
    # 35-day stay (> 30-day ceiling)
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270)],
        inbounds=[_ow("inbound", "2026-05-09", 270)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_rejected_when_inbound_before_outbound():
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-22", 270)],
        inbounds=[_ow("inbound", "2026-04-04", 270)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_picks_best_pair_when_multiple_candidates():
    # Two outbounds + two inbounds → 4 candidate pairs.
    # Only the cheapest qualifying pair (max savings) should be returned.
    combos = find_split_ticket_combos(
        outbounds=[
            _ow("outbound", "2026-04-04", 270, airline="A"),
            _ow("outbound", "2026-04-05", 320, airline="B"),  # more expensive
        ],
        inbounds=[
            _ow("inbound", "2026-04-22", 280, airline="C"),
            _ow("inbound", "2026-04-23", 310, airline="D"),  # more expensive
        ],
        roundtrip_baseline=780.0,
    )
    assert len(combos) == 1
    c = combos[0]
    assert c.outbound["airline"] == "A"
    assert c.inbound["airline"] == "C"
    assert c.total == 550


def test_rejected_when_baseline_zero_or_missing():
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270)],
        inbounds=[_ow("inbound", "2026-04-22", 270)],
        roundtrip_baseline=0.0,
    )
    assert combos == []
