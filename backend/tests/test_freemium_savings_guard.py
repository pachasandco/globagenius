from app.notifications.freemium_savings_guard import (
    _credible_roundtrip_value,
    summarize_matching_deals_credible,
)


PREFS = {
    "airport_codes": ["CDG"],
    "blocked_destinations": [],
    "flight_trip_types": ["round_trip", "one_way"],
}


def _deal(
    destination: str,
    price: float,
    baseline: float,
    discount: float,
    date: str,
    trip_type: str = "round_trip",
) -> dict:
    return {
        "origin": "CDG",
        "destination": destination,
        "departure_date": date,
        "price": price,
        "baseline_price": baseline,
        "discount_pct": discount,
        "trip_type": trip_type,
    }


def test_best_missed_is_ranked_by_euro_saving_not_discount_percentage():
    deals = [
        _deal("BCN", 90, 220, 59.1, "2026-09-10"),  # saving 130 €
        _deal("NRT", 500, 1100, 54.5, "2026-10-12"),  # saving 600 €
    ]

    stats = summarize_matching_deals_credible(deals, [], PREFS)

    assert stats["best_missed"]["destination"] == "NRT"
    assert stats["best_missed"]["savings"] == 600
    assert stats["best_missed"]["discount_pct"] == 54.5


def test_tokyo_with_implausibly_low_roundtrip_baseline_is_not_marketed():
    suspicious_tokyo = _deal("NRT", 162, 352, 54.0, "2026-10-12")

    assert _credible_roundtrip_value(suspicious_tokyo) is None


def test_suspicious_tokyo_does_not_hide_a_credible_alternative():
    deals = [
        _deal("NRT", 162, 352, 54.0, "2026-10-12"),
        _deal("BCN", 100, 220, 54.5, "2026-09-10"),
    ]

    stats = summarize_matching_deals_credible(deals, [], PREFS)

    assert stats["matching"] == 2
    assert stats["missed"] == 2
    assert stats["best_missed"]["destination"] == "BCN"
    assert stats["best_missed"]["savings"] == 120


def test_one_way_fare_is_not_presented_as_roundtrip_saving():
    one_way = _deal("NRT", 190, 410, 53.7, "2026-10-12", trip_type="one_way")

    assert _credible_roundtrip_value(one_way) is None


def test_incoherent_declared_discount_is_rejected():
    # 400 -> 300 is a 25% saving, not the declared 54%.
    incoherent = _deal("BCN", 300, 400, 54.0, "2026-09-10")

    assert _credible_roundtrip_value(incoherent) is None
