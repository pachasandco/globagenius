"""Tests for the V5 flight-only scorer (60% discount, 25% popularity, 15% flexibility)."""
from app.analysis.scorer import compute_score


def test_compute_score_high_deal():
    score = compute_score(
        discount_pct=55.0,
        destination_code="BCN",
        date_flexibility=3,
    )
    assert 70 <= score <= 100


def test_compute_score_low_deal():
    score = compute_score(
        discount_pct=40.0,
        destination_code="ZAG",
        date_flexibility=0,
    )
    assert score < 70


def test_compute_score_max_caps_at_100():
    # 80% discount + max popularity + max flexibility — must hit 100, not 85.
    score = compute_score(
        discount_pct=80.0,
        destination_code="BCN",
        date_flexibility=5,
    )
    assert score == 100


def test_compute_score_no_rating_arg_works():
    # accommodation_rating param kept for API compat — passing None must work.
    score = compute_score(
        discount_pct=50.0,
        destination_code="LIS",
        date_flexibility=2,
        accommodation_rating=None,
    )
    assert 0 < score < 100


def test_compute_score_rating_arg_is_ignored():
    # V5: hotel rating no longer contributes. Same inputs minus rating
    # should yield the same score whether the arg is passed or not.
    score_with = compute_score(
        discount_pct=50.0,
        destination_code="LIS",
        date_flexibility=2,
        accommodation_rating=5.0,
    )
    score_without = compute_score(
        discount_pct=50.0,
        destination_code="LIS",
        date_flexibility=2,
    )
    assert score_with == score_without


def test_compute_score_unknown_destination():
    score = compute_score(
        discount_pct=50.0,
        destination_code="XXX",
        date_flexibility=2,
    )
    assert 0 < score < 100


def test_compute_score_discount_dominates():
    # 60% weight on discount — a 60% discount should already deliver
    # the full discount component (60 * 60/60 = 60 pts) regardless of pop/flex.
    score = compute_score(
        discount_pct=60.0,
        destination_code="XXX",   # default popularity (low)
        date_flexibility=0,
    )
    # Lower bound: 60 (discount) + 25 * (30/MAX_POP) (popularity) + 0 (flex)
    # Whatever the popularity ceiling, the discount alone delivers 60 pts.
    assert score >= 60


def test_compute_score_popularity_only_low():
    # No discount, low popularity destination, no flex — must be very low
    # but non-zero (popularity gives a small floor).
    score = compute_score(
        discount_pct=0.0,
        destination_code="ZAG",
        date_flexibility=0,
    )
    assert 0 <= score < 25
