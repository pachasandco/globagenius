"""V5+: tests for the split-ticket combo matcher.

A combo qualifies when:
  outbound.price + inbound.price <= roundtrip_baseline * 0.60   (>=40% saving)
  AND savings >= 100 EUR
  AND inbound.departure_date - outbound.departure_date in [4, 30] days

Note (v8): the savings ratio floor was raised from 15% to 40% to align
combo alerts with the global product promise of "−40% minimum".
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


def test_qualifies_when_total_at_least_40pct_below_baseline_and_savings_above_100():
    # Baseline 780, total 450 (out 220 + in 230) → savings 330 (-42.3%).
    # Stay = 18 days (in [4, 30]). Both ratio (>=40%) and absolute (>=100€)
    # gates pass.
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 220, airline="French Bee")],
        inbounds=[_ow("inbound", "2026-04-22", 230, airline="Norse")],
        roundtrip_baseline=780.0,
    )
    assert len(combos) == 1
    c = combos[0]
    assert c.outbound["airline"] == "French Bee"
    assert c.inbound["airline"] == "Norse"
    assert c.total == 450
    assert c.savings == 330


def test_rejected_when_savings_between_15pct_and_40pct():
    # Baseline 780, total 540 (out 270 + in 270) → savings 240 (-30.8%).
    # Old policy (v5..v7) would have qualified this; v8 raises the bar to
    # 40% so the same combo is now rejected.
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270)],
        inbounds=[_ow("inbound", "2026-04-22", 270)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_rejected_when_savings_below_100_eur_floor():
    # Total 720, baseline 780 → savings 60 (only ~7.7%). Below 100€ floor.
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 360)],
        inbounds=[_ow("inbound", "2026-04-22", 360)],
        roundtrip_baseline=780.0,
    )
    assert combos == []


def test_rejected_when_total_within_40pct_of_baseline():
    # Total 670, baseline 780 → 14.1% saving (way under 40%) — even though
    # the absolute savings (110€) clear the 100€ floor, the ratio gate
    # rejects.
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
    # All 4 pairs are below the 40% threshold (baseline 780, ratio floor
    # 468); the matcher should still return the pair with the largest
    # absolute savings: out=210 + in=210 = 420, savings 360.
    combos = find_split_ticket_combos(
        outbounds=[
            _ow("outbound", "2026-04-04", 210, airline="A"),
            _ow("outbound", "2026-04-05", 250, airline="B"),  # more expensive
        ],
        inbounds=[
            _ow("inbound", "2026-04-22", 210, airline="C"),
            _ow("inbound", "2026-04-23", 240, airline="D"),  # more expensive
        ],
        roundtrip_baseline=780.0,
    )
    assert len(combos) == 1
    c = combos[0]
    assert c.outbound["airline"] == "A"
    assert c.inbound["airline"] == "C"
    assert c.total == 420
    assert c.savings == 360


def test_rejected_when_baseline_zero_or_missing():
    combos = find_split_ticket_combos(
        outbounds=[_ow("outbound", "2026-04-04", 270)],
        inbounds=[_ow("inbound", "2026-04-22", 270)],
        roundtrip_baseline=0.0,
    )
    assert combos == []
