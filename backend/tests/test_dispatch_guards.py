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
    LONG_HAUL_DAILY_CAP,
    levier_1_destination_cooldown_blocks,
    levier_2_daily_cap_blocks,
)


def _row(discount: float, destination: str = "LIS") -> dict:
    """Build a sent_alerts row in the shape the guard expects."""
    return {"discount_pct": discount, "destination": destination}


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
    db = _make_db([_row(30.0), _row(35.0)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=40.0
    ) is False


def test_l2_at_cap_blocks_unexceptional():
    """At cap with [30, 30, 30], a 35% discount must NOT pass — it's
    not 10 points above the best (max=30)."""
    db = _make_db([_row(30.0)] * DAILY_ALERT_CAP)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=35.0
    ) is True


def test_l2_at_cap_allows_exceptional_over_max():
    """At cap with [30, 30, 30], a 41% discount passes — exceeds the
    best by EXCEPTIONAL_DISCOUNT_GAP+1 points."""
    db = _make_db([_row(30.0)] * DAILY_ALERT_CAP)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=41.0
    ) is False


def test_l2_high_discount_in_window_raises_the_bar():
    """REGRESSION (2026-05-05): when the window contains a 50% deal
    plus two 30% deals, a 40% candidate must NOT pass. Previously the
    code compared against MIN(window)=30 → threshold 40 → allow.
    Switching to MAX(window)=50 → threshold 60 → block."""
    db = _make_db([_row(30.0), _row(30.0), _row(50.0)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=40.0
    ) is True


def test_l2_hard_ceiling_blocks_even_extreme_discount():
    """Hard ceiling: once the user has already received
    DAILY_ALERT_CAP + EXCEPTIONAL_BYPASS_CEILING alerts in the window,
    no further alert passes — not even a 99% discount. Worst case is
    deterministic."""
    n = DAILY_ALERT_CAP + EXCEPTIONAL_BYPASS_CEILING
    db = _make_db([_row(30.0)] * n)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=99.0
    ) is True


def test_l2_legacy_rows_without_discount_pct_are_ignored():
    """Pre-migration 037 rows have NULL discount_pct. They don't count
    toward the cap — the guard becomes effective progressively as new
    rows land. (Fail-open contract preserved from the previous
    implementation.)"""
    db = _make_db([{"discount_pct": None, "destination": "LIS"}] * 5)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=15.0
    ) is False


def test_l2_in_run_pending_counts_against_cap():
    """Multiple destinations dispatched in the same run (e.g. MAD + FAO
    + BCN simultaneously) all see 0 in DB, so the in-run counter is the
    only signal preventing a 3× breach in one tick."""
    db = _make_db([])  # nothing in DB
    # Two prior short-haul alerts already dispatched in this run.
    pending_two = [
        {"discount_pct": 30.0, "destination": "MAD"},
        {"discount_pct": 30.0, "destination": "FAO"},
    ]
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=30.0,
        pending_in_run_alerts=pending_two,
    ) is False  # 2 < cap → allow
    # Three prior alerts in run + new candidate of 35% → at cap, not
    # exceptional vs max=30, threshold=40 → block.
    pending_three = pending_two + [{"discount_pct": 30.0, "destination": "BCN"}]
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=35.0,
        pending_in_run_alerts=pending_three,
    ) is True


def test_l2_db_error_fails_open():
    """If the sent_alerts query crashes, the guard MUST fail open —
    better a duplicate alert than a silent backlog."""
    db = MagicMock()
    db.table.side_effect = Exception("supabase down")
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=15.0
    ) is False


# ── Long-haul cap (2026-05-05 — replaces the old "always pass" bypass) ─────


def test_l2_long_haul_under_cap_allows():
    """The first long-haul alert of the day always passes."""
    db = _make_db([])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="NRT", new_discount_pct=30.0
    ) is False


def test_l2_long_haul_at_cap_blocks():
    """REGRESSION (2026-05-05): long-haul used to bypass entirely
    (`if is_long_haul(destination): return False`). It now obeys
    LONG_HAUL_DAILY_CAP. With 2 long-haul alerts already in the window,
    a 3rd one — even at 80% discount — must be blocked."""
    db = _make_db([_row(40.0, "NRT"), _row(50.0, "BKK")])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="JFK", new_discount_pct=80.0
    ) is True


def test_l2_long_haul_does_not_count_short_haul_against_its_cap():
    """The two caps are independent: a long-haul candidate is NOT
    blocked just because the user already received 3 short-haul alerts.
    The user can still get short_cap + long_cap alerts in 24h."""
    db = _make_db([_row(30.0, "LIS"), _row(35.0, "OPO"), _row(40.0, "BCN")])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="NRT", new_discount_pct=30.0
    ) is False


def test_l2_short_haul_does_not_count_long_haul_against_its_cap():
    """Symmetric: a short-haul candidate isn't blocked because long-haul
    alerts filled their lane. Two long-haul alerts + a 30% short-haul
    candidate → allow (short-haul lane still empty)."""
    db = _make_db([_row(30.0, "NRT"), _row(40.0, "BKK")])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=30.0
    ) is False


def test_l2_long_haul_in_run_counter_works():
    """The in-run counter respects destination class: a long-haul alert
    dispatched earlier in the same run counts against the long-haul
    cap, not the short-haul cap."""
    db = _make_db([])
    pending = [
        {"discount_pct": 50.0, "destination": "NRT"},
        {"discount_pct": 60.0, "destination": "BKK"},
    ]
    # 3rd long-haul attempt → over LONG_HAUL_DAILY_CAP → block
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="JFK",
        new_discount_pct=70.0,
        pending_in_run_alerts=pending,
    ) is True
    # Short-haul is unaffected by those 2 in-run long-haul alerts → allow
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=30.0,
        pending_in_run_alerts=pending,
    ) is False


def test_l2_long_haul_has_no_exceptional_bypass():
    """Long-haul has no +10pts exception: at the cap of 2, even a
    massive discount is blocked. The cap is a feature, not a default."""
    db = _make_db([_row(40.0, "NRT"), _row(50.0, "BKK")])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="JFK", new_discount_pct=99.0
    ) is True


def test_l2_long_haul_cap_constants_match_doc():
    """Sanity guard so a future refactor that changes the number can't
    silently widen the cap without touching this test."""
    assert LONG_HAUL_DAILY_CAP == 2


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
