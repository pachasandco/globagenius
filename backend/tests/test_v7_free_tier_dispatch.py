"""V7: tests for the new free-tier dispatch policy.

Free tier behaviour after V7:
- Discounts in [40%, 50%) → full alert (max 3/week, unchanged).
- Discounts in [50%, 60%) → silent skip (no alert at all).
- Discounts in [60%, ∞)   → masked teaser, max 1/week (strict, persistent dedup).
- Weekly-quota 'limit reached' teaser: REMOVED.
"""

from app.thresholds import (
    GLOBAL_MIN_DISCOUNT_PCT,
    FREE_TIER_FULL_MAX_DISCOUNT_PCT,
    FREE_TIER_TEASER_MIN_DISCOUNT_PCT,
    FREE_TIER_WEEKLY_LIMIT,
)


def test_full_max_below_teaser_min():
    """The full-info ceiling must sit strictly below the teaser threshold —
    deals in [50%, 60%) are intentionally a 'dead band' (silent skip)."""
    assert FREE_TIER_FULL_MAX_DISCOUNT_PCT < FREE_TIER_TEASER_MIN_DISCOUNT_PCT


def test_global_min_below_full_max():
    """All free-tier full alerts must satisfy the global noise floor."""
    assert GLOBAL_MIN_DISCOUNT_PCT < FREE_TIER_FULL_MAX_DISCOUNT_PCT


def test_v7_thresholds_exact_values():
    """V7 product decisions: 40 / 50 / 60 / 3."""
    assert GLOBAL_MIN_DISCOUNT_PCT == 40
    assert FREE_TIER_FULL_MAX_DISCOUNT_PCT == 50
    assert FREE_TIER_TEASER_MIN_DISCOUNT_PCT == 60
    assert FREE_TIER_WEEKLY_LIMIT == 3


def test_dead_band_definition():
    """Confirm the 'dead band' [50, 60) covers exactly 10 percentage points
    and that 50 itself is in the dead band (silent skip), not a full alert."""
    dead_band_start = FREE_TIER_FULL_MAX_DISCOUNT_PCT  # inclusive lower bound
    dead_band_end = FREE_TIER_TEASER_MIN_DISCOUNT_PCT  # exclusive upper bound
    assert dead_band_end - dead_band_start == 10
    # 49.99% → full alert OK; 50% → dead band; 59.99% → still dead band; 60% → teaser.
    sample_full = 49.99
    sample_dead_lo = 50.0
    sample_dead_hi = 59.99
    sample_teaser = 60.0
    assert sample_full < FREE_TIER_FULL_MAX_DISCOUNT_PCT
    assert FREE_TIER_FULL_MAX_DISCOUNT_PCT <= sample_dead_lo < FREE_TIER_TEASER_MIN_DISCOUNT_PCT
    assert FREE_TIER_FULL_MAX_DISCOUNT_PCT <= sample_dead_hi < FREE_TIER_TEASER_MIN_DISCOUNT_PCT
    assert sample_teaser >= FREE_TIER_TEASER_MIN_DISCOUNT_PCT
