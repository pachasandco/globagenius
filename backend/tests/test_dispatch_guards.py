"""Tests for the V10 dispatch guards (alert fatigue mitigation).

The guards ride between the qualifier and the Telegram send, so they
have to keep working even when DB rows are missing fields (legacy
schema), when the in-memory in-run counter is the only signal, and
when one-off "exceptional" deals try to interrupt past the cap.
"""
import itertools
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.notifications.dispatch_guards import (
    DAILY_ALERT_CAP,
    EXCEPTIONAL_BYPASS_CEILING,
    EXCEPTIONAL_DISCOUNT_GAP,
    LONG_HAUL_DAILY_CAP,
    MESSAGE_BUCKET_MINUTES,
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


_row_counter = itertools.count()


def _row(
    discount: float,
    destination: str = "LIS",
    created_at: str | None = None,
) -> dict:
    """Build a sent_alerts row in the shape the guard expects.

    The default `created_at` is unique per call (each call increments
    a module-level counter), so multiple `_row()` calls produce rows
    that L2 treats as DISTINCT messages — matching the test intent
    where every helper call represents a separate notification event.

    To test the multi-row-per-message scenario (a grouped alert that
    wrote N rows for N offers), pass an explicit `created_at` shared
    across the rows that belong to the same message.
    """
    if created_at is None:
        n = next(_row_counter)
        # Spread rows hours apart so they always fall in distinct
        # MESSAGE_BUCKET_MINUTES buckets, regardless of how many tests run.
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        created_at = (base + timedelta(hours=n)).isoformat()
    return {
        "discount_pct": discount,
        "destination": destination,
        "created_at": created_at,
    }


# ── Levier 2 — the leak we just closed ─────────────────────────────────


def test_l2_under_cap_allows():
    db = _make_db([_row(30.0), _row(35.0)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=40.0
    ) is False


def test_l2_at_cap_blocks_unexceptional():
    """At cap with [30, 30, 30], a 35% discount must NOT pass — it's
    not 10 points above the best (max=30)."""
    db = _make_db([_row(30.0) for _ in range(DAILY_ALERT_CAP)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=35.0
    ) is True


def test_l2_at_cap_allows_exceptional_over_max():
    """At cap with [30, 30, 30], a 41% discount passes — exceeds the
    best by EXCEPTIONAL_DISCOUNT_GAP+1 points."""
    db = _make_db([_row(30.0) for _ in range(DAILY_ALERT_CAP)])
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
    db = _make_db([_row(30.0) for _ in range(n)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=99.0
    ) is True


def test_l2_legacy_rows_without_discount_pct_are_ignored():
    """Pre-migration 037 rows have NULL discount_pct. They don't count
    toward the cap — the guard becomes effective progressively as new
    rows land. (Fail-open contract preserved from the previous
    implementation.)"""
    db = _make_db([
        {"discount_pct": None, "destination": "LIS", "created_at": "2026-01-01T00:00:00+00:00"}
        for _ in range(5)
    ])
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


# ── Multi-row dedup (2026-05-05 — radio silence bug) ───────────────────────


def test_l2_collapses_multi_row_message_into_one_event():
    """REGRESSION (2026-05-05): a grouped Telegram alert with N offers
    writes N rows to sent_alerts (one per offer's alert_key for the
    168h dedup). Without message-level dedup, a single 3-offer message
    saturated DAILY_ALERT_CAP by itself — the user got one Telegram,
    L2 saw 3 rows, every subsequent alert was blocked for 24h.

    Three rows sharing (destination, created_at within
    MESSAGE_BUCKET_MINUTES) must collapse to ONE notification event —
    so a 4th candidate at 30% (under cap) must pass.
    """
    same_ts = "2026-05-05T03:00:00+00:00"
    rows = [
        _row(45.0, "LIS", created_at=same_ts),  # offer 1
        _row(45.0, "LIS", created_at=same_ts),  # offer 2 (same message)
        _row(45.0, "LIS", created_at=same_ts),  # offer 3 (same message)
    ]
    db = _make_db(rows)
    # 3 rows → 1 message → cap not reached → 30% must pass.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="OPO", new_discount_pct=30.0
    ) is False


def test_l2_two_grouped_messages_count_as_two_events():
    """Two grouped alerts (LIS with 3 offers, OPO with 1 offer)
    should count as 2 events, not 4. After both, a 3rd short-haul
    candidate at 30% must still pass the cap (under DAILY_ALERT_CAP=3)."""
    rows = [
        _row(45.0, "LIS", created_at="2026-05-05T03:00:00+00:00"),
        _row(45.0, "LIS", created_at="2026-05-05T03:00:00+00:00"),
        _row(45.0, "LIS", created_at="2026-05-05T03:00:00+00:00"),
        _row(53.0, "OPO", created_at="2026-05-05T05:00:00+00:00"),
    ]
    db = _make_db(rows)
    # 4 rows → 2 messages → 3rd candidate at 30% allowed.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="BCN", new_discount_pct=30.0
    ) is False


def test_l2_dedup_bucket_distinguishes_messages_far_apart():
    """Two rows at the SAME destination but well outside the
    MESSAGE_BUCKET_MINUTES window must NOT be collapsed — they
    represent two distinct re-emissions of the same destination."""
    far_apart_minutes = MESSAGE_BUCKET_MINUTES * 4  # well outside the bucket
    rows = [
        _row(40.0, "LIS", created_at="2026-05-05T03:00:00+00:00"),
        _row(40.0, "LIS", created_at=(
            datetime(2026, 5, 5, 3, far_apart_minutes, 0, tzinfo=timezone.utc).isoformat()
        )),
    ]
    db = _make_db(rows)
    # 2 distinct messages to LIS in the window. With one more,
    # short-haul cap is hit; a 4th 35% candidate is blocked
    # (35 < max(40, 40) + 10 = 50).
    rows.append(_row(40.0, "OPO", created_at="2026-05-05T08:00:00+00:00"))
    db = _make_db(rows)
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="BCN", new_discount_pct=35.0
    ) is True


def test_l2_dedup_bucket_collapses_seconds_apart():
    """Rows within the MESSAGE_BUCKET_MINUTES window (e.g. 30 seconds
    apart from the same dispatch loop) must collapse to one event."""
    rows = [
        _row(45.0, "LIS", created_at="2026-05-05T03:00:00+00:00"),
        _row(45.0, "LIS", created_at="2026-05-05T03:00:30+00:00"),
        _row(45.0, "LIS", created_at="2026-05-05T03:01:15+00:00"),
    ]
    db = _make_db(rows)
    # 3 rows seconds apart → 1 message → cap empty for next 3 candidates.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="OPO", new_discount_pct=30.0
    ) is False


def test_l2_dedup_does_not_collapse_different_destinations():
    """Two rows at the same timestamp but DIFFERENT destinations stay
    separate — they're two distinct grouped alerts that happened to
    flush in the same 5-min window."""
    same_ts = "2026-05-05T03:00:00+00:00"
    rows = [
        _row(40.0, "LIS", created_at=same_ts),
        _row(40.0, "OPO", created_at=same_ts),
        _row(40.0, "BCN", created_at=same_ts),
    ]
    db = _make_db(rows)
    # 3 distinct messages (LIS / OPO / BCN), at cap, 35% < 50 → block.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="MAD", new_discount_pct=35.0
    ) is True


def test_l2_dedup_handles_missing_created_at_per_row():
    """A row missing created_at (malformed, edge case) is counted on
    its own rather than silently dropped — preserves the fail-open
    contract: the guard never silently disables itself for rows it
    can't classify."""
    rows = [
        _row(40.0, "LIS", created_at="2026-05-05T03:00:00+00:00"),
        {"discount_pct": 40.0, "destination": "LIS"},  # no created_at
        {"discount_pct": 40.0, "destination": "LIS"},  # no created_at
    ]
    db = _make_db(rows)
    # 1 message with created_at + 2 unbucketable rows → 3 events.
    # 35% candidate at cap, not exceptional vs max=40, threshold=50 → block.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="OPO", new_discount_pct=35.0
    ) is True


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
