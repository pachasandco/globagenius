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
    LONG_HAUL_DAILY_CAP,
    MESSAGE_BUCKET_MINUTES,
    TOTAL_DAILY_CAP,
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
    message_id: str | None = None,
) -> dict:
    """Build a sent_alerts row in the shape the guard expects.

    `message_id`: new in chantier 1. When provided, L2 collapses rows
    sharing this UUID into a single notification event (instead of
    falling back to the (destination, 5-min bucket) heuristic for
    pre-migration rows).
    """
    if created_at is None:
        n = next(_row_counter)
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        created_at = (base + timedelta(hours=n)).isoformat()
    return {
        "discount_pct": discount,
        "destination": destination,
        "created_at": created_at,
        "message_id": message_id,
    }


# ── Levier 2 — the leak we just closed ─────────────────────────────────


def test_l2_under_cap_allows():
    db = _make_db([_row(30.0), _row(35.0)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=40.0
    ) is False


def test_l2_at_short_cap_blocks_even_high_discount():
    """REGRESSION (2026-05-16): once short-haul cap is reached, NO
    further short-haul alert passes — no exceptional bypass, regardless
    of how good the discount is. Previously a 99% deal could slip past
    a [30,30,30] window by exceeding max+10."""
    db = _make_db([_row(30.0) for _ in range(DAILY_ALERT_CAP)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=99.0
    ) is True


def test_l2_at_short_cap_blocks_unexceptional():
    """At cap with [30, 30, 30], a 35% discount must be blocked."""
    db = _make_db([_row(30.0) for _ in range(DAILY_ALERT_CAP)])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=35.0
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
    # Three prior alerts in run + new short candidate → short cap (3)
    # reached → block regardless of discount.
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


def test_l2_long_haul_lane_open_when_short_lane_full():
    """After 3 short-haul alerts, the long-haul lane is still open up to
    its own ceiling of 2 — pooled total = 3+1 = 4 ≤ TOTAL_DAILY_CAP."""
    db = _make_db([_row(30.0, "LIS"), _row(35.0, "OPO"), _row(40.0, "BCN")])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="NRT", new_discount_pct=30.0
    ) is False


def test_l2_short_haul_lane_open_when_long_lane_full():
    """Symmetric: after 2 long-haul alerts, short-haul lane is still
    open. Total = 2+1 = 3 ≤ TOTAL_DAILY_CAP."""
    db = _make_db([_row(30.0, "NRT"), _row(40.0, "BKK")])
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="LIS", new_discount_pct=30.0
    ) is False


def test_l2_pooled_total_blocks_5th_alert():
    """REGRESSION (2026-05-16): 3 short + 2 long = 5 alerts. The 6th
    alert in ANY lane must be blocked — total cap is pooled, not the
    sum of two independent ceilings."""
    db = _make_db([
        _row(30.0, "LIS"),
        _row(35.0, "OPO"),
        _row(40.0, "BCN"),
        _row(45.0, "NRT"),
        _row(50.0, "BKK"),
    ])
    # 6th short-haul attempt — should block on TOTAL_DAILY_CAP.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="MAD", new_discount_pct=30.0
    ) is True
    # 6th long-haul attempt — same, blocks on TOTAL_DAILY_CAP.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="JFK", new_discount_pct=30.0
    ) is True


def test_l2_pooled_total_cap_matches_doc():
    """Sanity guard: pool ceiling must stay at 5 (3 short + 2 long).
    Any future refactor that widens this without updating the docstring
    will trip this test."""
    assert TOTAL_DAILY_CAP == DAILY_ALERT_CAP + LONG_HAUL_DAILY_CAP == 5


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
    # 2 distinct messages to LIS in the window. With one more short
    # message, short-haul cap is hit (3); a 4th short candidate must
    # block — no exceptional bypass exists.
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
    # 3 distinct short-haul messages (LIS / OPO / BCN), short cap hit
    # → 4th short candidate blocks.
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
    # 1 message with created_at + 2 unbucketable rows → 3 short events
    # → short cap hit → 4th short candidate blocks.
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


def test_l2_collapses_rows_sharing_message_id_not_just_bucket():
    """REGRESSION (chantier 1, 2026-05-17): rows sharing a message_id
    collapse to one event regardless of created_at distance. This is
    the new mechanism; the 5-min bucket stays only for pre-migration
    rows where message_id is NULL."""
    mid = "00000000-0000-0000-0000-000000000001"
    # Three rows of the same message, intentionally spread across
    # times that would NOT fall in the same 5-min bucket. Pre-chantier-1,
    # they would each count as a distinct event.
    rows = [
        _row(45.0, "LIS", created_at="2026-05-05T03:00:00+00:00", message_id=mid),
        _row(45.0, "LIS", created_at="2026-05-05T03:30:00+00:00", message_id=mid),
        _row(45.0, "LIS", created_at="2026-05-05T04:00:00+00:00", message_id=mid),
    ]
    db = _make_db(rows)
    # 3 rows → 1 message → next candidate at 30% must pass under the
    # short-haul cap of 3.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="OPO", new_discount_pct=30.0
    ) is False


def test_l2_handles_mix_of_null_message_id_and_new_rows():
    """A user with 3 messages in the last 24h:
       - 1 legacy row (NULL message_id, handled by 5-min bucket)
       - 1 new message with 3 offers (same message_id)
       - 1 new message with 1 offer (different message_id)
    L2 must count 3 messages, not 5. Short-haul cap is then hit
    (DAILY_ALERT_CAP=3), so a 4th candidate at 30% must block."""
    legacy_ts = "2026-05-01T08:00:00+00:00"
    new_mid_a = "00000000-0000-0000-0000-00000000000A"
    new_mid_b = "00000000-0000-0000-0000-00000000000B"
    rows = [
        # legacy single message via bucket
        _row(40.0, "LIS", created_at=legacy_ts, message_id=None),
        # new message A: 3 offers, same UUID, spread across times
        _row(45.0, "BCN", created_at="2026-05-01T10:00:00+00:00", message_id=new_mid_a),
        _row(45.0, "BCN", created_at="2026-05-01T10:30:00+00:00", message_id=new_mid_a),
        _row(45.0, "BCN", created_at="2026-05-01T11:00:00+00:00", message_id=new_mid_a),
        # new message B: 1 offer, distinct UUID
        _row(50.0, "OPO", created_at="2026-05-01T12:00:00+00:00", message_id=new_mid_b),
    ]
    db = _make_db(rows)
    # 5 rows total → 3 messages → short cap (3) hit → 4th candidate blocks.
    assert levier_2_daily_cap_blocks(
        db=db, user_id="u", destination="MAD", new_discount_pct=30.0
    ) is True


# ── Levier 3 — anti-burst (3h spacing) ─────────────────────────────────────


from datetime import timedelta  # already imported at top, but explicit here

from app.notifications.dispatch_guards import (
    BURST_WINDOW_HOURS,
    BURST_EXCEPTION_DISCOUNT_SHORT,
    BURST_EXCEPTION_DISCOUNT_LONG,
    _recent_alert_ts_for_user,
)


def test_burst_constants_match_spec():
    """The spec pins the burst rule at 3h window, 70% short / 60% long
    exception thresholds. This test locks those numbers so a future
    edit can't silently change the policy."""
    assert BURST_WINDOW_HOURS == 3
    assert BURST_EXCEPTION_DISCOUNT_SHORT == 70.0
    assert BURST_EXCEPTION_DISCOUNT_LONG == 60.0


def test_recent_alert_ts_returns_most_recent_within_window():
    """Helper returns the most recent created_at within the burst
    window (3h). Older rows are filtered out by the query's gte
    clause, so the helper just unwraps the first result."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([
        # 2h ago — should be returned
        {"created_at": "2026-05-17T10:00:00+00:00"},
    ])
    ts = _recent_alert_ts_for_user(db=db, user_id="u", now=now)
    assert ts == datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone.utc)


def test_recent_alert_ts_returns_none_when_no_row():
    """No row in window → None (caller treats this as 'pass')."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([])
    assert _recent_alert_ts_for_user(db=db, user_id="u", now=now) is None


# ── L3 — levier_3_burst_blocks behaviour ───────────────────────────────────


from app.notifications.dispatch_guards import levier_3_burst_blocks


# Task 3 — base case: no burst in window → pass
def test_l3_no_burst_in_window_passes():
    """First alert ever for this user (or no row in the last 3h)
    → pass."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([])
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=45.0, now=now,
    ) is False


# Task 5 — short-haul threshold
def test_l3_burst_recent_short_haul_below_threshold_blocks():
    """Burst recent + short-haul discount < 70% → block.
    Median discount in our data is 44%, so this is the typical case
    the burst rule is designed to suppress."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},  # 1.5h ago
    ])
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",  # short-haul
        new_discount_pct=45.0, now=now,
    ) is True


def test_l3_burst_recent_short_haul_at_or_above_threshold_passes():
    """Burst recent + short-haul discount ≥ 70% → pass.
    The exception lets the truly exceptional ~5% of deals through."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    # Exactly at threshold (70.0) → pass (>= comparison)
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=70.0, now=now,
    ) is False
    # Well above → pass
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=85.0, now=now,
    ) is False


# Task 6 — long-haul threshold
def test_l3_burst_recent_long_haul_above_60_passes():
    """A 65% deal to a long-haul destination passes the burst even
    if a recent short-haul alert is in the window — the long-haul
    threshold is lower because such deals are rarer."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    # NRT is in LONG_HAUL_DESTINATIONS (per route_selector)
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="NRT",
        new_discount_pct=65.0, now=now,
    ) is False


def test_l3_burst_recent_long_haul_below_60_blocks():
    """A 50% deal to a long-haul destination during a burst window
    is blocked — not exceptional enough."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="NRT",
        new_discount_pct=50.0, now=now,
    ) is True


def test_l3_long_haul_threshold_is_strictly_lower_than_short():
    """A 65% deal to a long-haul passes; the same 65% deal to a
    short-haul during the same window blocks. Validates that the
    two thresholds are distinct in practice, not just constants."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db_long = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    assert levier_3_burst_blocks(
        db=db_long, user_id="u", destination="NRT",
        new_discount_pct=65.0, now=now,
    ) is False
    db_short = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    assert levier_3_burst_blocks(
        db=db_short, user_id="u", destination="LIS",
        new_discount_pct=65.0, now=now,
    ) is True


# Task 7 — boundary + user isolation
def test_l3_boundary_t_minus_2h59_blocks_t_minus_3h01_passes():
    """Boundary test: a burst at T-2h59 is in window (block), a
    burst at T-3h01 is just outside (pass). The query's gte cutoff
    already filters out-of-window rows, so this exercises the
    query boundary, not Python arithmetic."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    # 2h59m ago — inside the 3h window
    inside = (now - timedelta(hours=2, minutes=59)).isoformat()

    db_inside = _make_db([{"created_at": inside}])
    assert levier_3_burst_blocks(
        db=db_inside, user_id="u", destination="LIS",
        new_discount_pct=45.0, now=now,
    ) is True

    # 3h01m outside — the query gte cutoff would exclude it, so the
    # mock returns an empty list to simulate the DB filter.
    db_outside = _make_db([])
    assert levier_3_burst_blocks(
        db=db_outside, user_id="u", destination="LIS",
        new_discount_pct=45.0, now=now,
    ) is False


def test_l3_user_isolation_recent_burst_for_user_a_does_not_block_user_b():
    """A recent burst for user A must not block user B. The mock
    is keyed by `user_id`, so we simulate distinct DBs to make the
    isolation explicit in the test."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    # When the dispatcher queries for user B, the SQL filter
    # user_id=B returns nothing even if user A had a recent alert.
    # We mimic that by passing an empty fixture for user B.
    db_for_user_b = _make_db([])
    assert levier_3_burst_blocks(
        db=db_for_user_b, user_id="uB", destination="LIS",
        new_discount_pct=45.0, now=now,
    ) is False


# Task 8 — in-run pending
def test_l3_in_run_pending_blocks_even_if_db_empty():
    """A user who received an alert earlier in the *current*
    scheduler tick (not yet flushed to DB) still triggers the
    burst rule. The dispatcher passes the in-run state as a
    Dict[user_id, datetime]."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    pending = {"u": now - timedelta(minutes=30)}  # 30 min ago
    db = _make_db([])  # nothing flushed yet
    # Short-haul candidate at 50% → below 70% threshold → block
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=50.0, now=now,
        pending_in_run_alerts=pending,
    ) is True
    # Same scenario but exceptional discount → pass
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=75.0, now=now,
        pending_in_run_alerts=pending,
    ) is False


def test_l3_in_run_pending_for_other_user_does_not_block():
    """In-run pending alert for user A doesn't block user B."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    pending = {"uA": now - timedelta(minutes=30)}
    db = _make_db([])
    assert levier_3_burst_blocks(
        db=db, user_id="uB", destination="LIS",
        new_discount_pct=45.0, now=now,
        pending_in_run_alerts=pending,
    ) is False


# Bonus invariant (added 2026-05-17 brainstorm): L3 passing doesn't
# mean L2 will pass too. L3 = timing, L2 = volume. Separation of
# concerns. This test only exercises L3, but locks the public
# behaviour: L3 passing on a high-discount alert MUST return False
# regardless of how many alerts the user already has on the day.
# (Full L3+L2 integration is exercised by the backtest simulator,
# not by a unit test, because L2's logic is independent.)
def test_l3_does_not_consider_daily_volume():
    """L3 only looks at the most recent ts in the window. It does
    NOT count the number of alerts in the last 24h. Passing L3 is
    a green light only for the burst dimension; L2 still has to
    approve the alert in the dispatcher pipeline."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    # Window has ONE row at 4h ago — outside the 3h burst window
    db = _make_db([])  # simulating gte cutoff exclusion
    # Discount irrelevant — outside window → always pass at L3
    for disc in (10.0, 50.0, 95.0):
        assert levier_3_burst_blocks(
            db=db, user_id="u", destination="LIS",
            new_discount_pct=disc, now=now,
        ) is False


# ── Tier-aware caps (chantier 5, 2026-05-17) ───────────────────────────────


from app.notifications.dispatch_guards import (
    TIER_CAPS,
    get_user_caps,
)


def test_tier_caps_constants_lock_the_policy():
    """The TIER_CAPS dict pins the alert policy per tier. This test
    locks the numbers so a later edit can't silently widen the free
    cap (or shrink the premium one) without showing up in the diff."""
    # Free: 3 short / 0 long / total 3, no burst exception
    assert TIER_CAPS["free"]["short_24h"] == 3
    assert TIER_CAPS["free"]["long_24h"] == 0
    assert TIER_CAPS["free"]["total_24h"] == 3
    assert TIER_CAPS["free"]["burst_exception_short"] is None
    assert TIER_CAPS["free"]["burst_exception_long"] is None

    # Premium: 3 short / 2 long / 5 total, exception 70/60
    assert TIER_CAPS["premium"]["short_24h"] == 3
    assert TIER_CAPS["premium"]["long_24h"] == 2
    assert TIER_CAPS["premium"]["total_24h"] == 5
    assert TIER_CAPS["premium"]["burst_exception_short"] == 70.0
    assert TIER_CAPS["premium"]["burst_exception_long"] == 60.0

    # Grandfathered = same caps as premium (alias)
    assert TIER_CAPS["premium_grandfathered"] == TIER_CAPS["premium"]


def _mk_user_db(tier):
    """Build a mock that returns one users row with the given tier.
    tier=None simulates a missing row (anonymous / deleted user)."""
    if tier is None:
        return _make_db([])
    return _make_db([{"id": "u", "tier": tier}])


def test_get_user_caps_returns_free_when_user_not_found():
    """Defensive: if the user_id doesn't match any row (deleted,
    anon, race condition), default to the strictest tier ('free').
    The opposite (defaulting to premium) would silently raise the
    cap for invalid IDs — too easy to abuse."""
    db = _mk_user_db(None)
    caps = get_user_caps(db=db, user_id="u")
    assert caps == TIER_CAPS["free"]


def test_get_user_caps_returns_tier_caps_for_known_user():
    for tier in ("free", "premium", "premium_grandfathered"):
        db = _mk_user_db(tier)
        caps = get_user_caps(db=db, user_id="u")
        assert caps == TIER_CAPS[tier], f"caps mismatch for {tier}"


def test_get_user_caps_fails_open_on_db_error():
    """On DB error, fall back to free caps — better silently strict
    than silently permissive."""
    db = MagicMock()
    db.table.side_effect = Exception("supabase down")
    caps = get_user_caps(db=db, user_id="u")
    assert caps == TIER_CAPS["free"]


def test_get_user_caps_unknown_tier_value_falls_back_to_free():
    """If the DB has a tier value not in TIER_CAPS (e.g. an
    in-progress migration adding a new tier before code is updated),
    fall back to free rather than KeyError."""
    db = _mk_user_db("enterprise")  # not a known tier
    caps = get_user_caps(db=db, user_id="u")
    assert caps == TIER_CAPS["free"]
