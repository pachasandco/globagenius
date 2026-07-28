"""Tests for the stopover phase 1 matcher (3-leg two-destination chains)."""
from app.analysis.stopover_matcher import find_stopover_chains


def _leg(origin: str, dest: str, date: str, price: float) -> dict:
    return {
        "origin": origin,
        "destination": dest,
        "departure_date": date,
        "price": price,
        "airline": "FR",
        "source_url": "https://example.test",
    }


# Reference chain: CDG → MAD (3 days) → LPA (7 days) → CDG.
LEG1 = _leg("CDG", "MAD", "2026-09-01", 40.0)
LEG2 = _leg("MAD", "LPA", "2026-09-04", 55.0)
LEG3 = _leg("LPA", "CDG", "2026-09-11", 60.0)
# Total = 155€. Baseline 400€ → savings 245€ (61%) → qualifies.


def test_qualifies_valid_chain():
    chains = find_stopover_chains([LEG1], [LEG2], [LEG3], roundtrip_baseline=400.0)
    assert len(chains) == 1
    chain = chains[0]
    assert chain.total == 155
    assert chain.savings == 245
    assert chain.hub_days == 3
    assert chain.dest_days == 7


def test_rejects_when_savings_ratio_below_floor():
    # Total 155 vs baseline 200 → 22.5% < 30% floor.
    assert find_stopover_chains([LEG1], [LEG2], [LEG3], roundtrip_baseline=200.0) == []


def test_rejects_when_savings_eur_below_floor():
    # Baseline 230 → savings 75€ < 80€ floor (ratio 32.6% passes).
    assert find_stopover_chains([LEG1], [LEG2], [LEG3], roundtrip_baseline=230.0) == []


def test_rejects_hub_stay_too_short():
    # 1 day at the hub = an airport transfer, not a stopover.
    leg2 = _leg("MAD", "LPA", "2026-09-02", 55.0)
    leg3 = _leg("LPA", "CDG", "2026-09-09", 60.0)
    assert find_stopover_chains([LEG1], [leg2], [leg3], roundtrip_baseline=400.0) == []


def test_rejects_hub_stay_too_long():
    leg2 = _leg("MAD", "LPA", "2026-09-08", 55.0)  # 7 days at hub > 5 max
    leg3 = _leg("LPA", "CDG", "2026-09-15", 60.0)
    assert find_stopover_chains([LEG1], [leg2], [leg3], roundtrip_baseline=400.0) == []


def test_rejects_dest_stay_too_short():
    leg3 = _leg("LPA", "CDG", "2026-09-05", 60.0)  # 1 day at final dest < 3 min
    assert find_stopover_chains([LEG1], [LEG2], [leg3], roundtrip_baseline=400.0) == []


def test_rejects_total_trip_too_long():
    leg3 = _leg("LPA", "CDG", "2026-10-15", 60.0)  # 44 days total > 30 max
    assert find_stopover_chains([LEG1], [LEG2], [leg3], roundtrip_baseline=400.0) == []


def test_returns_best_savings_chain_only():
    cheap_leg3 = _leg("LPA", "CDG", "2026-09-12", 30.0)
    chains = find_stopover_chains(
        [LEG1], [LEG2], [LEG3, cheap_leg3], roundtrip_baseline=400.0,
    )
    assert len(chains) == 1
    assert chains[0].leg3 is cheap_leg3
    assert chains[0].total == 125


def test_cheapest_per_date_dedup():
    expensive_same_day = _leg("CDG", "MAD", "2026-09-01", 200.0)
    chains = find_stopover_chains(
        [expensive_same_day, LEG1], [LEG2], [LEG3], roundtrip_baseline=400.0,
    )
    assert len(chains) == 1
    assert chains[0].leg1 is LEG1


def test_empty_inputs_and_bad_baseline():
    assert find_stopover_chains([], [LEG2], [LEG3], roundtrip_baseline=400.0) == []
    assert find_stopover_chains([LEG1], [], [LEG3], roundtrip_baseline=400.0) == []
    assert find_stopover_chains([LEG1], [LEG2], [], roundtrip_baseline=400.0) == []
    assert find_stopover_chains([LEG1], [LEG2], [LEG3], roundtrip_baseline=0) == []


def test_unparseable_dates_are_skipped():
    bad = _leg("CDG", "MAD", "not-a-date", 10.0)
    chains = find_stopover_chains([bad, LEG1], [LEG2], [LEG3], roundtrip_baseline=400.0)
    assert len(chains) == 1
    assert chains[0].leg1 is LEG1
