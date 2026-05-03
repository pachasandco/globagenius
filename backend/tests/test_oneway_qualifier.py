"""V5+ P1: tests for the one-way qualifier (option C — pre-baseline).

Pure-function contract: given a candidate one-way price + a list of recent
historical prices on the same (origin, destination, direction), decide
whether the candidate qualifies as a deal.

A candidate qualifies when:
  - we have at least ONEWAY_MIN_OBSERVATIONS prices in the history window
  - the candidate price is at most median * (1 - ONEWAY_DISCOUNT_PCT_FLOOR/100)
    (i.e. ≥ 60% below the median by default)
"""
from app.analysis.oneway_qualifier import (
    qualify_oneway,
    OnewayQualification,
)


def test_returns_none_with_no_history():
    result = qualify_oneway(price=100.0, recent_prices=[])
    assert result is None


def test_returns_none_when_too_few_observations():
    # Default min observations = 5; 4 should reject.
    result = qualify_oneway(price=50.0, recent_prices=[200.0, 210.0, 220.0, 230.0])
    assert result is None


def test_qualifies_when_price_at_least_60pct_below_median():
    # Median of [200, 220, 240, 260, 280] = 240. 60% off = 96. Price 90 → qualifies.
    history = [200.0, 220.0, 240.0, 260.0, 280.0]
    result = qualify_oneway(price=90.0, recent_prices=history)
    assert result is not None
    assert isinstance(result, OnewayQualification)
    assert result.price == 90.0
    assert result.median == 240.0
    assert result.discount_pct >= 60.0


def test_rejected_when_discount_too_small():
    # Median 200. Price 100 → 50% off, below the 60% floor → reject.
    history = [200.0] * 5
    result = qualify_oneway(price=100.0, recent_prices=history)
    assert result is None


def test_qualifies_at_exactly_the_floor():
    # Median 200. Price = 200 * 0.40 = 80 → exactly 60% off → qualifies.
    history = [200.0] * 5
    result = qualify_oneway(price=80.0, recent_prices=history)
    assert result is not None
    assert abs(result.discount_pct - 60.0) < 0.01


def test_median_is_robust_to_outliers():
    # One outlier at 1000 must NOT pull the median up.
    history = [200.0, 200.0, 200.0, 200.0, 200.0, 1000.0]
    result = qualify_oneway(price=70.0, recent_prices=history)
    # Median is 200. Price 70 → 65% off → qualifies.
    assert result is not None
    assert result.median == 200.0


def test_zero_or_negative_history_prices_ignored():
    # Travelpayouts can return 0 for unavailable rows; we must not divide
    # by them or let them pull the median.
    history = [0.0, 0.0, 200.0, 200.0, 200.0, 200.0, 200.0]
    result = qualify_oneway(price=70.0, recent_prices=history)
    assert result is not None
    assert result.median == 200.0


def test_zero_or_negative_candidate_price_rejected():
    history = [200.0] * 5
    assert qualify_oneway(price=0.0, recent_prices=history) is None
    assert qualify_oneway(price=-50.0, recent_prices=history) is None


def test_custom_floor_can_be_passed():
    # Lowering the floor to 30% should let a 50% off deal qualify.
    history = [200.0] * 5
    # price 100 = 50% off median 200
    result = qualify_oneway(price=100.0, recent_prices=history, discount_floor_pct=30.0)
    assert result is not None
    assert abs(result.discount_pct - 50.0) < 0.01


def test_custom_min_observations():
    # Allow a tighter min to test boundary.
    result = qualify_oneway(
        price=80.0,
        recent_prices=[200.0, 200.0, 200.0],
        min_observations=3,
    )
    assert result is not None
