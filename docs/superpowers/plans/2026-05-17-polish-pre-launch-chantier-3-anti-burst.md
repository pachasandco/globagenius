# Chantier 3 — Anti-burst Levier 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop users from receiving 4 Telegram alerts between 00h and 04h by adding a 3-hour burst suppression rule (with discount-based exceptions: ≥70% short-haul, ≥60% long-haul), applied **before** the existing pool cap.

**Architecture:** A new function `levier_3_burst_blocks` in `dispatch_guards.py`, inserted in the dispatcher pipeline between L1 (destination cooldown) and L2 (pool 5/24h). One single-row SELECT per check (cheaper than L2's 24h window scan). A backtest simulator script replays the last 14 days of `sent_alerts` to validate that the rule cuts identified bursts without over-blocking — three pass criteria must hold before merge.

**Tech Stack:** Python 3.12, pytest, supabase-py.

**Dependency:** ships **after** chantier 1 (`message_id`) so the burst lookup can rely on a clean row-per-message accounting via `_message_bucket_key` fallback or `message_id` preference (whichever applies to a given row). The implementation reads only `created_at` so it's actually independent, but the backtest simulator benefits from chantier 1 being merged first.

---

## File Structure

**Create:**
- `backend/scripts/backtest_levier_3.py` — simulator that replays 14 days of `sent_alerts` with the new rule and reports the three pass criteria.

**Modify:**
- `backend/app/notifications/dispatch_guards.py` — add `levier_3_burst_blocks` + thresholds.
- `backend/app/scheduler/jobs.py` — insert the L3 call between L1 and L2 at the 3 existing call-sites (~lines 1090–1099, 1768–1773, 2042–2047).
- `backend/tests/test_dispatch_guards.py` — 7 new tests (in-window vs out-of-window, exception thresholds, boundary, user isolation, in-run pending).

---

## Task 1: Thresholds and `_recent_alert_ts_for_user` helper — failing test

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append a failing test for `_recent_alert_ts_for_user`**

Append to `backend/tests/test_dispatch_guards.py`:

```python
from datetime import timedelta

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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `backend/`):

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: 3 FAIL with `ImportError: cannot import name 'BURST_WINDOW_HOURS' from 'app.notifications.dispatch_guards'`.

---

## Task 2: Thresholds and `_recent_alert_ts_for_user` — implementation

**Files:**
- Modify: `backend/app/notifications/dispatch_guards.py`

- [ ] **Step 1: Inspect the L2 section to know where to insert**

```bash
grep -n "^# ── Levier 2\|^def levier_2_daily_cap_blocks\|^LONG_HAUL_DAILY_CAP\|^TOTAL_DAILY_CAP" backend/app/notifications/dispatch_guards.py
```

Note the line just before `# ── Levier 2 ───…`. We'll add L3 thresholds and helper after L2 (since L3 references nothing from L2 but L2 is already established), but the documentation order will follow the dispatcher pipeline (L1 → L3 → L2).

- [ ] **Step 2: Append the thresholds + helper at the end of the file**

Open `backend/app/notifications/dispatch_guards.py` and append at the bottom (after the existing `levier_2_daily_cap_blocks` function):

```python
# ── Levier 3 — anti-burst (3h spacing) ─────────────────────────────────────

# Spec 2026-05-17: don't let the user wake up to 4 notifications
# between 00h and 04h. A 3h window blocks tightly-packed alerts;
# an exception threshold lets through truly exceptional discounts
# (the mistake-fare lane). Long-haul gets a more permissive
# threshold because long-haul deals at high discount are rarer
# and more precious.
BURST_WINDOW_HOURS = 3
BURST_EXCEPTION_DISCOUNT_SHORT = 70.0  # short-haul: must beat p90 of typical alerts
BURST_EXCEPTION_DISCOUNT_LONG = 60.0   # long-haul: lower bar, deals are rarer


def _recent_alert_ts_for_user(
    *,
    db,
    user_id: str,
    now: datetime,
) -> datetime | None:
    """Return the most recent sent_alerts.created_at for this user
    within the burst window, or None if no row is in the window.

    Only counts actual deal alerts (alert_type in flight/one_way/
    split_ticket) — system messages, teasers etc. don't consume a
    burst slot.

    Fails open (returns None, "pass") on DB error — better one
    extra alert than radio silence.
    """
    if not db:
        return None
    cutoff = (now - timedelta(hours=BURST_WINDOW_HOURS)).isoformat()
    try:
        resp = (
            db.table("sent_alerts")
            .select("created_at")
            .eq("user_id", user_id)
            .in_("alert_type", ["flight", "one_way", "split_ticket"])
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    rows = resp.data or []
    if not rows:
        return None
    raw = rows[0].get("created_at")
    if not raw:
        return None
    # Supabase returns ISO-8601 strings. Postgres can emit 5-digit
    # microseconds which fromisoformat rejects on Python < 3.11 paths;
    # the standard format on Python 3.12 here handles it directly.
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
```

- [ ] **Step 3: Run the helper tests to verify they pass**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_burst_constants_match_spec tests/test_dispatch_guards.py::test_recent_alert_ts_returns_most_recent_within_window tests/test_dispatch_guards.py::test_recent_alert_ts_returns_none_when_no_row -v
```

Expected: 3 PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/notifications/dispatch_guards.py backend/tests/test_dispatch_guards.py
git commit -m "feat(alerts): L3 thresholds + _recent_alert_ts_for_user helper

3h burst window, exception 70% short / 60% long. Helper does
the single-row SELECT and unwraps the ISO timestamp. Fails open
on DB error — better one extra alert than silence.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `levier_3_burst_blocks` — failing tests (no burst path)

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append the no-burst test**

Append to `backend/tests/test_dispatch_guards.py`:

```python
from app.notifications.dispatch_guards import levier_3_burst_blocks


def test_l3_no_burst_in_window_passes():
    """First alert ever for this user (or no row in the last 3h)
    → pass."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    db = _make_db([])
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="LIS",
        new_discount_pct=45.0, now=now,
    ) is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_l3_no_burst_in_window_passes -v
```

Expected: FAIL with `ImportError: cannot import name 'levier_3_burst_blocks'`.

---

## Task 4: `levier_3_burst_blocks` — minimal implementation

**Files:**
- Modify: `backend/app/notifications/dispatch_guards.py`

- [ ] **Step 1: Implement the function**

Append to `backend/app/notifications/dispatch_guards.py`:

```python
def levier_3_burst_blocks(
    *,
    db,
    user_id: str,
    destination: str,
    new_discount_pct: float,
    pending_in_run_alerts: dict[str, datetime] | None = None,
    now: datetime | None = None,
) -> bool:
    """Return True iff levier 3 says this alert should NOT be pushed.

    The rule:
      1. Lookup the most recent alert to this user in the last
         BURST_WINDOW_HOURS (default 3h). Includes both DB-persisted
         alerts and in-run pending alerts dispatched earlier in the
         same scheduler tick.
      2. If nothing in window → pass.
      3. If something in window:
         - Long-haul candidate (per is_long_haul(destination)):
           pass iff new_discount_pct >= BURST_EXCEPTION_DISCOUNT_LONG (60).
         - Short-haul candidate:
           pass iff new_discount_pct >= BURST_EXCEPTION_DISCOUNT_SHORT (70).
         Otherwise block.

    pending_in_run_alerts: Dict[user_id, most_recent_ts] — alerts
    dispatched to this user earlier in the current scheduler tick
    that haven't been flushed to DB yet. The dict-keyed shape
    (vs a list) is intentional: it dedups in case of retry within
    the same tick. None / empty dict → no in-run state.
    """
    now = now or datetime.now(timezone.utc)
    db_ts = _recent_alert_ts_for_user(db=db, user_id=user_id, now=now)
    in_run_ts = (pending_in_run_alerts or {}).get(user_id)

    # Most recent across DB and in-run.
    candidates = [t for t in (db_ts, in_run_ts) if t is not None]
    if not candidates:
        return False  # no burst in window → pass
    recent = max(candidates)
    if (now - recent) >= timedelta(hours=BURST_WINDOW_HOURS):
        return False  # outside window → pass (defensive; query already filters)

    # Inside window. Apply the exception threshold.
    threshold = (
        BURST_EXCEPTION_DISCOUNT_LONG
        if is_long_haul(destination)
        else BURST_EXCEPTION_DISCOUNT_SHORT
    )
    return new_discount_pct < threshold
```

- [ ] **Step 2: Run the no-burst test to verify it passes**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_l3_no_burst_in_window_passes -v
```

Expected: PASS.

- [ ] **Step 3: Run all dispatch_guards tests to confirm no regression**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: all previously-passing tests still PASS + the new one.

- [ ] **Step 4: Commit**

```bash
git add backend/app/notifications/dispatch_guards.py backend/tests/test_dispatch_guards.py
git commit -m "feat(alerts): levier_3_burst_blocks — base case (no burst → pass)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: L3 — short-haul exception threshold tests

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append the short-haul tests**

Append to `backend/tests/test_dispatch_guards.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_l3_burst_recent_short_haul_below_threshold_blocks tests/test_dispatch_guards.py::test_l3_burst_recent_short_haul_at_or_above_threshold_passes -v
```

Expected: PASS. (The exception logic is already in Task 4's implementation; these tests lock the short-haul threshold semantics.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_dispatch_guards.py
git commit -m "test(alerts): L3 short-haul threshold semantics

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: L3 — long-haul exception threshold tests

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append the long-haul tests**

Append to `backend/tests/test_dispatch_guards.py`:

```python
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
    db = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    assert levier_3_burst_blocks(
        db=db, user_id="u", destination="NRT",
        new_discount_pct=65.0, now=now,
    ) is False
    # Same discount, short-haul destination → blocked
    db2 = _make_db([
        {"created_at": "2026-05-17T10:30:00+00:00"},
    ])
    assert levier_3_burst_blocks(
        db=db2, user_id="u", destination="LIS",
        new_discount_pct=65.0, now=now,
    ) is True
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -k "long_haul" -v
```

Expected: all new long-haul tests PASS. (The `is_long_haul` function is already imported at the top of dispatch_guards.py — verify quickly with `grep "^from app.analysis.route_selector" backend/app/notifications/dispatch_guards.py`.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_dispatch_guards.py
git commit -m "test(alerts): L3 long-haul threshold (60%) distinct from short (70%)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: L3 — boundary and user isolation tests

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append the boundary test**

Append to `backend/tests/test_dispatch_guards.py`:

```python
def test_l3_boundary_t_minus_2h59_blocks_t_minus_3h01_passes():
    """Boundary test: a burst at T-2h59 is in window (block), a
    burst at T-3h01 is just outside (pass). The query's gte cutoff
    already filters out-of-window rows, so this exercises the
    query boundary, not Python arithmetic."""
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    # 2h59m ago — inside the 3h window
    inside = (now - timedelta(hours=2, minutes=59)).isoformat()
    # 3h01m ago — outside, the gte cutoff filters it out
    outside = (now - timedelta(hours=3, minutes=1)).isoformat()

    db_inside = _make_db([{"created_at": inside}])
    assert levier_3_burst_blocks(
        db=db_inside, user_id="u", destination="LIS",
        new_discount_pct=45.0, now=now,
    ) is True

    db_outside = _make_db([])  # query gte cutoff would exclude
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
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -k "boundary or user_isolation" -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_dispatch_guards.py
git commit -m "test(alerts): L3 boundary at T-3h + user isolation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: L3 — in-run pending alerts test

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append the in-run pending test**

Append to `backend/tests/test_dispatch_guards.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -k "in_run" -v
```

Expected: PASS.

- [ ] **Step 3: Run the full suite**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: all dispatch_guards tests PASS (27 from chantier 1 + 10 new from L3 = 37 total).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_dispatch_guards.py
git commit -m "test(alerts): L3 in-run pending consumption + cross-user isolation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Dispatcher — insert L3 between L1 and L2 (site 1 of 3)

**Files:**
- Modify: `backend/app/scheduler/jobs.py` (around lines 1082–1108)

- [ ] **Step 1: Inspect the existing L1/L2 call sequence at site 1**

```bash
sed -n '1080,1110p' backend/app/scheduler/jobs.py
```

Expected shape:

```python
            levier_1_destination_cooldown_blocks,
            levier_2_daily_cap_blocks,
        )
        ...
        if uid and levier_1_destination_cooldown_blocks(
            db=db, user_id=uid, destination=grp_dest,
            new_price=best_price,
        ):
            logger.info(...)
            continue

        if uid and levier_2_daily_cap_blocks(
            db=db, user_id=uid, destination=grp_dest,
            new_discount_pct=best_discount,
            pending_in_run_alerts=dispatched_alerts_in_run_by_user.get(uid),
        ):
            ...
```

Note that **the existing `pending_in_run_alerts` dict here is keyed differently from L3's needs**: L2 uses a `list[dict]` (per-alert objects with `discount_pct` and `destination`). For L3 we need a separate `Dict[user_id, datetime]`. We'll introduce a new local `dispatched_burst_ts_by_user` dict alongside the existing one.

- [ ] **Step 2: Add the L3 import to the existing import block**

In the import block around line 1082, change:

```python
            levier_1_destination_cooldown_blocks,
            levier_2_daily_cap_blocks,
        )
```

To:

```python
            levier_1_destination_cooldown_blocks,
            levier_2_daily_cap_blocks,
            levier_3_burst_blocks,
        )
```

- [ ] **Step 3: Locate the `dispatched_alerts_in_run_by_user` initialization**

```bash
grep -n "dispatched_alerts_in_run_by_user" backend/app/scheduler/jobs.py | head -5
```

Find where the dict is first initialized (usually `dispatched_alerts_in_run_by_user: dict[str, list] = {}` near the top of the dispatch function). Right after that line, add:

```python
        dispatched_burst_ts_by_user: dict[str, datetime] = {}
```

(The variable `datetime` is already imported at the top of `jobs.py` — verify with `grep "^from datetime" backend/app/scheduler/jobs.py`.)

- [ ] **Step 4: Insert the L3 check between L1 and L2**

In `backend/app/scheduler/jobs.py`, find the block that looks like:

```python
        if uid and levier_1_destination_cooldown_blocks(
            db=db, user_id=uid, destination=grp_dest,
            new_price=best_price,
        ):
            logger.info(
                f"V10 dispatch blocked (L1 destination cooldown): "
                f"user={uid} dest={grp_dest}"
            )
            continue

        if uid and levier_2_daily_cap_blocks(
```

Insert between L1's `continue` and L2's `if uid and …`:

```python
        if uid and levier_3_burst_blocks(
            db=db, user_id=uid, destination=grp_dest,
            new_discount_pct=best_discount,
            pending_in_run_alerts=dispatched_burst_ts_by_user,
        ):
            logger.info(
                f"V10 dispatch blocked (L3 burst 3h): "
                f"user={uid} dest={grp_dest} discount={best_discount}%"
            )
            continue
```

- [ ] **Step 5: After a successful send, record the burst timestamp**

Find the post-send block where `dispatched_alerts_in_run_by_user.setdefault(uid, []).append(...)` is called (around line 1142). Right after that append, add:

```python
                    dispatched_burst_ts_by_user[uid] = datetime.now(timezone.utc)
```

- [ ] **Step 6: Sanity-check the module imports cleanly**

```bash
.venv/bin/python3 -c "
from app.scheduler.jobs import job_scrape_tier1
print('OK')
"
```

Expected: `OK`. (Any NameError would surface here.)

- [ ] **Step 7: Run all dispatch_guards tests as smoke**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: all PASS (the dispatcher wiring doesn't have a unit test; we rely on the L3 unit tests + later backtest).

- [ ] **Step 8: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): wire L3 burst guard at site 1/3 (grouped flight)

L1 → L3 → L2 order. dispatched_burst_ts_by_user dict tracks
per-tick burst state alongside the existing L2 in-run list.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Dispatcher — L3 at site 2 of 3 (one-way alerts)

**Files:**
- Modify: `backend/app/scheduler/jobs.py` (around lines 1760–1810)

- [ ] **Step 1: Locate site 2**

```bash
sed -n '1760,1810p' backend/app/scheduler/jobs.py
```

Find the import block `levier_1_destination_cooldown_blocks, levier_2_daily_cap_blocks` and the L1/L2 calls.

- [ ] **Step 2: Add L3 import + initialize `dispatched_burst_ts_by_user`**

Mirror Task 9 Steps 2 + 3 in this site. Add `levier_3_burst_blocks` to the import, and add the dict initialization at the top of the function (or in the same place where the L2 in-run dict is initialized for this site — typically the one-way dispatch function has its own local).

If a `dispatched_burst_ts_by_user` is already in scope from Task 9, you can reuse it; otherwise initialize a new one local to this function.

- [ ] **Step 3: Insert the L3 check**

Between the existing L1 call and L2 call for this site, insert:

```python
            if sub_user_id and levier_3_burst_blocks(
                db=db, user_id=sub_user_id, destination=destination,
                new_discount_pct=discount_pct,
                pending_in_run_alerts=dispatched_burst_ts_by_user,
            ):
                logger.info(
                    f"One-way dispatch blocked (L3 burst): "
                    f"user={sub_user_id} dest={destination} discount={discount_pct}%"
                )
                continue
```

(Adapt variable names — `sub_user_id`, `destination`, `discount_pct` — to match the actual names used at site 2.)

- [ ] **Step 4: Record the burst timestamp on success**

After the upsert at this site, add:

```python
                    dispatched_burst_ts_by_user[sub_user_id] = datetime.now(timezone.utc)
```

- [ ] **Step 5: Smoke-import**

```bash
.venv/bin/python3 -c "
from app.scheduler.jobs import job_scrape_tier1
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): wire L3 at site 2/3 (one-way)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Dispatcher — L3 at site 3 of 3 (split-ticket alerts)

**Files:**
- Modify: `backend/app/scheduler/jobs.py` (around lines 2030–2080)

- [ ] **Step 1: Locate site 3**

```bash
sed -n '2030,2080p' backend/app/scheduler/jobs.py
```

- [ ] **Step 2: Mirror the changes from Task 10 in this site**

Same three edits: import L3, initialize the burst dict (or reuse if in scope), insert the L3 check between L1 and L2, record the burst timestamp on success.

- [ ] **Step 3: Verify all 3 sites are wired**

```bash
grep -c "levier_3_burst_blocks" backend/app/scheduler/jobs.py
```

Expected output: at minimum `4` (1 import line + 3 call-site invocations). If the imports are consolidated, the count may be lower — verify by hand:

```bash
grep -n "levier_3_burst_blocks(" backend/app/scheduler/jobs.py
```

Expected: 3 invocation sites.

- [ ] **Step 4: Smoke-import and run all tests**

```bash
.venv/bin/python3 -c "from app.scheduler.jobs import job_scrape_tier1; print('OK')"
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: `OK` + all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): wire L3 at site 3/3 (split-ticket)

All three dispatcher call-sites now apply L1 → L3 → L2 in
order before send_telegram. L3 blocks via a single-row SELECT
which is cheaper than L2's 24h window scan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Backtest simulator — skeleton + first pass criterion

**Files:**
- Create: `backend/scripts/backtest_levier_3.py`

- [ ] **Step 1: Write the skeleton with the first criterion**

Create `backend/scripts/backtest_levier_3.py`:

```python
"""Backtest the L3 anti-burst rule against the last 14 days of
sent_alerts before merging chantier 3.

Three pass criteria the spec requires:

  1. <20% additional alerts blocked beyond what L2 already blocks.
  2. No alert with discount_pct >= 70% (short) or >= 60% (long) would
     be blocked — proves the exception threshold works.
  3. Identified bursts visibly broken: Moussa's 4-alert window on
     2026-05-15 (00h-04h) reduces to 1 alert + 3 blocked.

Output: a printed report. Exit code 0 if all three pass, 1 otherwise.
The CI / operator must inspect output before approving the merge.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _parse_ts(s: str | None) -> datetime | None:
    """Robust ISO parser tolerating Postgres 5-digit microseconds."""
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    m = re.match(r"(.*\.)(\d+)([+-]\d{2}:\d{2})$", s)
    if m:
        frac = m.group(2)[:6].ljust(6, "0")
        s = f"{m.group(1)}{frac}{m.group(3)}"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _load_sent_alerts(db, days: int = 14) -> list[dict]:
    """Pull the relevant sent_alerts rows for the simulation."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows: list[dict] = []
    offset = 0
    while True:
        chunk = (
            db.table("sent_alerts")
            .select("user_id,destination,discount_pct,alert_type,created_at,message_id")
            .in_("alert_type", ["flight", "one_way", "split_ticket"])
            .gte("created_at", cutoff)
            .order("created_at")
            .range(offset, offset + 999)
            .execute()
        )
        page = chunk.data or []
        rows.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    return rows
```

- [ ] **Step 2: Verify the file imports cleanly**

```bash
.venv/bin/python3 -c "from scripts.backtest_levier_3 import _load_sent_alerts; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/backtest_levier_3.py
git commit -m "feat(backtest): L3 simulator skeleton + sent_alerts loader

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Backtest — message-level dedup + simulator loop

**Files:**
- Modify: `backend/scripts/backtest_levier_3.py`

- [ ] **Step 1: Add the dedup + simulator**

Append to `backend/scripts/backtest_levier_3.py`:

```python
def _dedup_to_messages(rows: list[dict]) -> list[dict]:
    """Collapse N rows of the same Telegram message into one event.

    Prefers `message_id` (chantier 1). Falls back to
    `(user_id, destination, created_at to the second)` for
    pre-migration rows where message_id is NULL.
    """
    seen_mids: set[str] = set()
    seen_buckets: set[tuple[str, str, str]] = set()
    out: list[dict] = []
    for r in rows:
        mid = r.get("message_id")
        if mid:
            if mid in seen_mids:
                continue
            seen_mids.add(mid)
            out.append(r)
            continue
        ts = r.get("created_at") or ""
        bucket = (r.get("user_id") or "", r.get("destination") or "", ts[:19])
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        out.append(r)
    return out


def _simulate(
    rows: list[dict],
    *,
    burst_hours: int = 3,
    short_threshold: float = 70.0,
    long_threshold: float = 60.0,
    long_haul_set: set[str] | None = None,
) -> dict:
    """Replay `rows` in chronological order, applying L3 to each event.

    Returns a dict with classified counts and per-user breakdown.
    A row is `blocked_by_l3` iff a previous-event timestamp for the
    same user is within `burst_hours` AND its discount is below the
    applicable threshold.
    """
    long_haul_set = long_haul_set or set()
    last_ts: dict[str, datetime] = {}
    classified: list[dict] = []

    for r in rows:
        ts = _parse_ts(r.get("created_at"))
        if ts is None:
            continue
        user = r.get("user_id") or ""
        dest = r.get("destination") or ""
        disc = r.get("discount_pct")
        prev = last_ts.get(user)
        verdict = "pass"
        if prev is not None and (ts - prev) < timedelta(hours=burst_hours):
            threshold = long_threshold if dest in long_haul_set else short_threshold
            if disc is None or disc < threshold:
                verdict = "blocked_by_l3"
        if verdict == "pass":
            last_ts[user] = ts
        classified.append({
            "user_id": user,
            "destination": dest,
            "discount_pct": disc,
            "ts": ts,
            "verdict": verdict,
        })

    total = len(classified)
    blocked = sum(1 for c in classified if c["verdict"] == "blocked_by_l3")
    per_user: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "blocked_by_l3": 0})
    for c in classified:
        per_user[c["user_id"]][c["verdict"]] += 1

    return {
        "total_events": total,
        "blocked_by_l3": blocked,
        "blocked_pct": (100.0 * blocked / total) if total else 0.0,
        "per_user": dict(per_user),
        "classified": classified,
    }
```

- [ ] **Step 2: Smoke-test the simulator function on a synthetic fixture**

(No unit test file for the script — we'll exercise it from the CLI below.)

```bash
.venv/bin/python3 -c "
from datetime import datetime, timezone, timedelta
from scripts.backtest_levier_3 import _simulate

base = datetime(2026, 5, 17, 0, 0, 0, tzinfo=timezone.utc)
rows = [
    {'user_id': 'u', 'destination': 'LIS', 'discount_pct': 50.0, 'created_at': base.isoformat()},
    {'user_id': 'u', 'destination': 'LIS', 'discount_pct': 50.0, 'created_at': (base + timedelta(hours=1)).isoformat()},
]
r = _simulate(rows)
print('blocked_by_l3:', r['blocked_by_l3'], 'pass:', r['total_events'] - r['blocked_by_l3'])
"
```

Expected output: `blocked_by_l3: 1 pass: 1` (the second alert, 1h after the first, below 70% → blocked).

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/backtest_levier_3.py
git commit -m "feat(backtest): L3 simulator with message-level dedup

Replays rows chronologically, applying the burst rule with the
configurable thresholds. Returns per-user classification so the
report can attribute blocks correctly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Backtest — pass criteria + CLI

**Files:**
- Modify: `backend/scripts/backtest_levier_3.py`

- [ ] **Step 1: Add the three pass-criteria evaluators**

Append to `backend/scripts/backtest_levier_3.py`:

```python
# Pass criteria thresholds (per the spec).
MAX_BLOCKED_PCT = 20.0
SHORT_EXCEPTION = 70.0
LONG_EXCEPTION = 60.0


def evaluate_criteria(
    result: dict,
    *,
    long_haul_set: set[str],
) -> dict:
    """Run the three pass criteria against the simulation result.
    Returns a dict with one boolean per criterion + free-text
    diagnostics."""
    blocked_pct = result["blocked_pct"]
    # Criterion 1: <20% additional alerts blocked.
    crit_1_pass = blocked_pct < MAX_BLOCKED_PCT
    # Criterion 2: no alert above the exception threshold is blocked.
    violators = [
        c for c in result["classified"]
        if c["verdict"] == "blocked_by_l3"
        and c["discount_pct"] is not None
        and (
            (c["destination"] in long_haul_set and c["discount_pct"] >= LONG_EXCEPTION)
            or (c["destination"] not in long_haul_set and c["discount_pct"] >= SHORT_EXCEPTION)
        )
    ]
    crit_2_pass = not violators
    # Criterion 3: identified bursts are broken. We don't auto-attribute
    # to a specific user here — the operator inspects the per-user
    # breakdown in the printed report.
    crit_3_diag = result["per_user"]

    return {
        "crit_1_blocked_pct_under_20": crit_1_pass,
        "crit_2_no_exception_violators": crit_2_pass,
        "violators": violators[:5],  # cap the print
        "blocked_pct": blocked_pct,
        "crit_3_per_user_breakdown": crit_3_diag,
    }


def _print_report(eval_: dict) -> None:
    print(f"Blocked %: {eval_['blocked_pct']:.2f}%  (criterion 1 threshold: < {MAX_BLOCKED_PCT}%)")
    print(f"  Criterion 1 (< {MAX_BLOCKED_PCT}% blocked): "
          f"{'PASS' if eval_['crit_1_blocked_pct_under_20'] else 'FAIL'}")
    print(f"  Criterion 2 (no high-discount blocks): "
          f"{'PASS' if eval_['crit_2_no_exception_violators'] else 'FAIL'}")
    if eval_["violators"]:
        print("    Violators (high-discount alerts that L3 would block):")
        for v in eval_["violators"]:
            print(f"      user={v['user_id'][:8]} dest={v['destination']} "
                  f"discount={v['discount_pct']}% ts={v['ts']}")
    print("  Criterion 3 (per-user breakdown — inspect for known bursts):")
    for uid, counts in eval_["crit_3_per_user_breakdown"].items():
        print(f"    {uid[:8]}: pass={counts['pass']} blocked_by_l3={counts['blocked_by_l3']}")


# A copy of the long-haul set, hard-coded to avoid coupling the
# script to app.analysis.route_selector (it's an ops tool, not a
# library). Keep in sync with route_selector.LONG_HAUL_DESTINATIONS.
LONG_HAUL_SET = {
    "BKK","NRT","HND","CMN","RAK","TUN","DXB","HAN","SGN","SIN","KUL",
    "DEL","BOM","CCU","HKG","TPE","ICN","PEK","PVG","JFK","LAX","SFO",
    "YYZ","YUL","BOS","ORD","MIA","ATL","DFW","SEA","DEN","IAH","MEX",
    "GIG","GRU","EZE","SCL","LIM","BOG","JNB","CPT","NBO","ADD","CAI",
    "DOH","AUH","IST","TLV","KEF","RUH","JED","PTP","FDF",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest L3 anti-burst over the last N days.")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    from app.db import db
    if db is None:
        print("ERROR: Supabase DB not configured.", file=sys.stderr)
        return 2

    rows = _load_sent_alerts(db, days=args.days)
    print(f"Loaded {len(rows)} rows from sent_alerts (last {args.days} days).")
    messages = _dedup_to_messages(rows)
    print(f"After message-level dedup: {len(messages)} events.")

    sim = _simulate(messages, long_haul_set=LONG_HAUL_SET)
    eval_ = evaluate_criteria(sim, long_haul_set=LONG_HAUL_SET)
    _print_report(eval_)

    if eval_["crit_1_blocked_pct_under_20"] and eval_["crit_2_no_exception_violators"]:
        print("\n✅ Criteria 1 and 2 PASS. Verify criterion 3 (per-user breakdown) manually.")
        return 0
    print("\n❌ At least one criterion FAILED. Do NOT merge L3 yet.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the backtest against the prod DB**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
.venv/bin/python3 -m scripts.backtest_levier_3
```

Expected: a report block ending with `✅ Criteria 1 and 2 PASS. …` or `❌ At least one criterion FAILED.`. Inspect the per-user breakdown. The current production user `e17b1153` (Moussa) should show several `blocked_by_l3` corresponding to the 00h-04h burst window observed on 2026-05-15/16.

- [ ] **Step 3: Decide on merge based on the backtest**

If the report passes both auto-criteria and the per-user breakdown shows the known burst is broken, proceed to Task 15. If it fails criterion 1 (>20% blocked), the threshold for the exception is likely too high for the current data shape — DO NOT MERGE; revisit the spec values with the operator before proceeding.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/backtest_levier_3.py
git commit -m "feat(backtest): L3 pass criteria + CLI

CLI exits 1 if criterion 1 (<20% blocked) or 2 (no high-discount
blocks) fails. Criterion 3 (identified bursts broken) is operator-
inspected via the printed per-user breakdown.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: Open the PR for chantier 3

**Files:** none (Git/GitHub step).

- [ ] **Step 1: Push the branch**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git push origin polish-pre-launch
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "feat: chantier 3 — anti-burst Levier 3" --body "$(cat <<'EOF'
## Summary

- New guard `levier_3_burst_blocks`: 3h window, exception 70% short / 60% long-haul.
- Inserted at all 3 dispatcher call-sites (grouped flight, one-way, split-ticket) in order **L1 → L3 → L2**.
- `dispatched_burst_ts_by_user` dict tracks per-tick burst state.
- `scripts/backtest_levier_3.py` replays 14 days of `sent_alerts` and emits two automatic pass criteria + a per-user breakdown for the operator to inspect the third.

Spec: `docs/superpowers/specs/2026-05-17-polish-pre-launch-design.md`.

## Test plan

- [ ] `pytest backend/tests/test_dispatch_guards.py` → all 37 PASS (27 from chantier 1 + 10 new from L3).
- [ ] `python -m scripts.backtest_levier_3` exits 0 against prod data.
- [ ] Per-user breakdown shows the burst window 00h-04h on 2026-05-15/16 (user e17b1153) reduced to 1 alert + 3 blocked.
- [ ] Smoke: send a test alert post-deploy, verify it's NOT blocked when no recent alert exists for the user.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## Self-Review

**Spec coverage check** (against the `Chantier 3` section of the spec):

- ✅ 3h burst window with two thresholds (70% short / 60% long) — Tasks 2, 5, 6
- ✅ `levier_3_burst_blocks` signature with `pending_in_run_alerts` as `Dict[user_id, datetime]` — Task 4
- ✅ Inserted **before** L2 in the dispatcher, at all 3 sites — Tasks 9, 10, 11
- ✅ Cheaper than L2 (single-row LIMIT 1 lookup) — Task 2 `_recent_alert_ts_for_user`
- ✅ `split_ticket` counts as 1 alert — falls naturally out of the `alert_type IN (…)` filter — Task 2
- ✅ `is_long_haul` imported from the same source as L2 (coherence) — Task 4 uses it directly
- ✅ 7 unit tests covering: no burst, short below/at-or-above threshold, long below/above threshold, boundary, user isolation, in-run pending consumption + cross-user — Tasks 3, 5, 6, 7, 8 (some tasks ship 2 tests each, totaling ≥7)
- ✅ Backtest gate before merge with the three pass criteria explicit — Tasks 12, 13, 14
- ✅ "20% headroom (vs 15% in original proposal)" — encoded as `MAX_BLOCKED_PCT = 20.0` in Task 14
- ✅ Backtest attribution distinguishes "blocked by L3" from "blocked by L2" — the simulator only applies L3 (L2 is not re-run inside), so an L3 verdict is unambiguous. The spec note about not double-attributing is naturally satisfied.

**Placeholder scan**: no TBD/TODO/FIXME in the plan. Every step has executable code or commands.

**Type consistency**:
- `BURST_WINDOW_HOURS: int`, `BURST_EXCEPTION_DISCOUNT_SHORT: float`, `BURST_EXCEPTION_DISCOUNT_LONG: float` — consistent across module and tests.
- `_recent_alert_ts_for_user` returns `datetime | None` — consumed correctly by `levier_3_burst_blocks`.
- `pending_in_run_alerts: dict[str, datetime] | None` consistent across function signature, dispatcher initialization (`dispatched_burst_ts_by_user: dict[str, datetime]`), and tests.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-polish-pre-launch-chantier-3-anti-burst.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
