"""Tests for the V10 dispatch guards (alert fatigue mitigation).

The guards ride between the qualifier and the Telegram send, so they
have to keep working even when DB rows are missing fields (legacy
schema), when the in-memory in-run counter is the only signal, and
when one-off "exceptional" deals try to interrupt past the cap.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.notifications.dispatch_guards import (
    DAILY_ALERT_CAP,
    EXCEPTIONAL_BYPASS_CEILING,
    EXCEPTIONAL_DISCOUNT_GAP,
    levier_1_destination_cooldown_blocks,
    levier_2_daily_cap_blocks,
)


# ── helpers ─────────────────────────────────────────────────────────────


def _make_db(rows: list[dict]):
    """Build a Supabase-shaped chained mock that returns `rows` from the
    final `.execute()` call regardless of the .select/.eq/.gte chain."""
    final = MagicMock()
    final.data = rows
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.gte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = final
    db = MagicMock()
    db.table.return_value = chain
    return db


# ── Levier 2 — the leak we just closed ─────────────────────────────────


def test_l2_under_cap_allows():
    db = _make_db([{"discount_pct": 30.0}, {"discount_pct": 35.0}])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=40.0
    ) is False


def test_l2_at_cap_blocks_unexceptional():
    """At cap with [30, 30, 30], a 35% discount must NOT pass — it's
    not 10 points above the best (max=30)."""
    db = _make_db([{"discount_pct": 30.0}] * DAILY_ALERT_CAP)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=35.0
    ) is True


def test_l2_at_cap_allows_exceptional_over_max():
    """At cap with [30, 30, 30], a 41% discount passes — exceeds the
    best by EXCEPTIONAL_DISCOUNT_GAP+1 points."""
    db = _make_db([{"discount_pct": 30.0}] * DAILY_ALERT_CAP)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=41.0
    ) is False


def test_l2_high_discount_in_window_raises_the_bar():
    """REGRESSION (2026-05-05): when the window contains a 50% deal
    plus two 30% deals, a 40% candidate must NOT pass. Previously the
    code compared against MIN(window)=30 → threshold 40 → allow.
    Switching to MAX(window)=50 → threshold 60 → block."""
    db = _make_db([
        {"discount_pct": 30.0},
        {"discount_pct": 30.0},
        {"discount_pct": 50.0},
    ])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=40.0
    ) is True


def test_l2_hard_ceiling_blocks_even_extreme_discount():
    """Hard ceiling: once the user has already received
    DAILY_ALERT_CAP + EXCEPTIONAL_BYPASS_CEILING alerts in the window,
    no further alert passes — not even a 99% discount. Worst case is
    deterministic."""
    n = DAILY_ALERT_CAP + EXCEPTIONAL_BYPASS_CEILING
    db = _make_db([{"discount_pct": 30.0}] * n)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=99.0
    ) is True


def test_l2_long_haul_bypasses_cap():
    """Long-haul destinations are rare enough that the per-24h cap
    would suppress genuinely valuable alerts. They bypass."""
    db = _make_db([{"discount_pct": 30.0}] * DAILY_ALERT_CAP)
    # NRT is in LONG_HAUL_DESTINATIONS
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="NRT", new_discount_pct=15.0
    ) is False


def test_l2_legacy_rows_without_discount_pct_are_ignored():
    """Pre-migration 037 rows have NULL discount_pct. They don't count
    toward the cap — the guard becomes effective progressively as new
    rows land. (Fail-open contract preserved from the previous
    implementation.)"""
    db = _make_db([{"discount_pct": None}] * 5)  # 5 legacy rows
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=15.0
    ) is False


def test_l2_in_run_pending_counts_against_cap():
    """Multiple destinations dispatched in the same run (e.g. MAD + FAO
    + BCN simultaneously) all see 0 in DB, so the in-run counter is the
    only signal preventing a 3× breach in one tick."""
    db = _make_db([])  # nothing in DB
    # Two prior alerts already dispatched in this run for this user.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=30.0,
        pending_in_run_discounts=[30.0, 30.0],
    ) is False  # 2 < cap → allow
    # Three prior alerts in run + new candidate of 35% → at cap, not
    # exceptional vs max=30, threshold=40 → block.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=35.0,
        pending_in_run_discounts=[30.0, 30.0, 30.0],
    ) is True


def test_l2_db_error_fails_open():
    """If the sent_alerts query crashes, the guard MUST fail open —
    better a duplicate alert than a silent backlog."""
    db = MagicMock()
    db.table.side_effect = Exception("supabase down")
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=15.0
    ) is False


# ── Levier 1 — destination cooldown ─────────────────────────────────────


def test_l1_no_prior_alert_allows():
    db = _make_db([])
    assert levier_1_destination_cooldown_blocks(
        db=db, user_id="u", destination="LIS", new_price=100.0
    ) is False


def test_l1_recent_alert_blocks():
    db = _make_db([{"price": 120.0, "created_at": datetime.now(timezone.utc).isoformat()}])
    assert levier_1_destination_cooldown_blocks(
        db=db, user_id="u", destination="LIS", new_price=110.0
    ) is True


def test_l1_significant_drop_overrides():
    """A new price below 70% of the previous alerted price re-fires."""
    db = _make_db([{"price": 200.0, "created_at": datetime.now(timezone.utc).isoformat()}])
    assert levier_1_destination_cooldown_blocks(
        db=db, user_id="u", destination="LIS", new_price=130.0
    ) is False  # 130 < 200 * 0.7 = 140 → significant drop → allow


def test_l1_legacy_row_without_price_fails_open():
    """Pre-migration 037 rows with NULL price can't be compared. The
    guard fails open — at most one duplicate; future rows fix it."""
    db = _make_db([{"price": None, "created_at": datetime.now(timezone.utc).isoformat()}])
    assert levier_1_destination_cooldown_blocks(
        db=db, user_id="u", destination="LIS", new_price=110.0
    ) is False
