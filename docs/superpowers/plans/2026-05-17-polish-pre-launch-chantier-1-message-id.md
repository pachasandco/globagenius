# Chantier 1 — `sent_alerts.message_id` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the N-rows-per-Telegram-message duplication in `sent_alerts` by introducing a `message_id uuid` column shared by all rows of the same grouped alert, with a safe dry-run-then-backfill of the ~3200 historical rows.

**Architecture:** Migration 039 adds the column + index. Python generates the UUID at dispatch time (one per `send_grouped_flight_alerts` call) and attaches it to all rows of the upsert batch. The existing `(user_id, alert_key)` unique index is preserved (it serves the 168h offer-level dedup, which is orthogonal). The 5-minute bucket dedup in `levier_2_daily_cap_blocks` stays as a fallback for pre-migration rows where `message_id IS NULL`.

**Tech Stack:** Python 3.12, FastAPI, Supabase Postgres, pytest, supabase-py.

---

## File Structure

**Create:**
- `backend/supabase/migrations/039_sent_alerts_message_id.sql` — column + index.
- `backend/scripts/backfill_message_id.py` — dry-run report + actual backfill.
- `backend/tests/test_backfill_message_id.py` — unit tests for the grouping logic.

**Modify:**
- `backend/app/scheduler/jobs.py` — 3 upsert call-sites (lines ~1170, ~1866, ~2125) generate a `message_id` before insert.
- `backend/app/notifications/dispatch_guards.py` — `levier_2_daily_cap_blocks` prefers `message_id` over the bucket-5min when present.
- `backend/tests/test_dispatch_guards.py` — 2 new tests (mixed old/new rows, message_id collapsing).

**Note:** Spec calls for a CHECK constraint at +1 month (line ~150 of the spec). That's a separate operational step — out of this plan, tracked in ROADMAP.

---

## Task 1: Migration 039 — add `message_id` column + index

**Files:**
- Create: `backend/supabase/migrations/039_sent_alerts_message_id.sql`

- [ ] **Step 1: Write the migration**

Create `backend/supabase/migrations/039_sent_alerts_message_id.sql`:

```sql
-- Migration 039: message_id on sent_alerts
--
-- Before: a grouped Telegram alert with N offers writes N rows to
-- sent_alerts, each with a distinct alert_key but the same created_at.
-- CTR, L2 cap counts, and any per-message analytics inherit the
-- "N rows per message" inflation, and L2 leans on a fragile 5-min
-- bucket dedup to compensate.
--
-- After: every row of the same Telegram message shares one UUID.
-- - Python generates the UUID at dispatch time (one per
--   send_grouped_flight_alerts call).
-- - Historical rows are backfilled in a separate, idempotent script
--   (scripts/backfill_message_id.py).
-- - The existing (user_id, alert_key) unique index is preserved —
--   it serves the 168h offer-level dedup which is orthogonal.

ALTER TABLE sent_alerts
  ADD COLUMN IF NOT EXISTS message_id uuid;

CREATE INDEX IF NOT EXISTS idx_sent_alerts_message_id
  ON sent_alerts(message_id);
```

- [ ] **Step 2: Apply manually in Supabase SQL Editor**

(Same pattern as migration 038 in the previous session.) Paste the SQL into Supabase SQL Editor → Run. Expected: `Success. No rows returned`.

- [ ] **Step 3: Verify column exists from Python**

Run (from `backend/`):

```bash
.venv/bin/python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
from app.db import db
r = db.table('sent_alerts').select('message_id').limit(1).execute()
print('OK, column readable:', r.data)
"
```

Expected output: `OK, column readable: [{'message_id': None}]` (or similar — value is None on existing rows, that's intentional).

- [ ] **Step 4: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/supabase/migrations/039_sent_alerts_message_id.sql
git commit -m "feat(db): migration 039 — sent_alerts.message_id

Adds a UUID column (nullable for now) plus an index. Python
dispatch will populate it for new rows; a separate backfill
script handles the ~3200 historical rows.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Backfill grouping logic — write the failing test

**Files:**
- Create: `backend/tests/test_backfill_message_id.py`

- [ ] **Step 1: Write the failing test for grouping**

Create `backend/tests/test_backfill_message_id.py`:

```python
"""Tests for the backfill script's grouping logic.

The grouping logic is what assigns one message_id per Telegram
message in historical sent_alerts rows. Wrong grouping = wrong stats
forever, so this is the test that has to be correct above all.
"""
from datetime import datetime, timezone

from scripts.backfill_message_id import group_rows_into_messages


def _row(user_id: str, dest: str, ts: str, alert_key: str):
    """Build a sent_alerts row fixture in the shape the grouper expects."""
    return {
        "id": f"id-{alert_key}",
        "user_id": user_id,
        "destination": dest,
        "alert_key": alert_key,
        "created_at": ts,
        "message_id": None,
    }


def test_three_rows_same_message_grouped():
    """Three rows from the same grouped alert (3 offers, same
    user, same destination, same second) collapse into one message."""
    rows = [
        _row("u1", "LIS", "2026-05-05T03:00:00.000123+00:00", "ak1"),
        _row("u1", "LIS", "2026-05-05T03:00:00.000456+00:00", "ak2"),
        _row("u1", "LIS", "2026-05-05T03:00:00.000789+00:00", "ak3"),
    ]
    groups = group_rows_into_messages(rows)
    assert len(groups) == 1
    assert {r["alert_key"] for r in groups[0]} == {"ak1", "ak2", "ak3"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `backend/`):

```bash
.venv/bin/pytest tests/test_backfill_message_id.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.backfill_message_id'` (the module doesn't exist yet).

---

## Task 3: Backfill grouping logic — minimal implementation

**Files:**
- Create: `backend/scripts/__init__.py` (if missing)
- Create: `backend/scripts/backfill_message_id.py`

- [ ] **Step 1: Ensure `scripts/` is a package**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
test -f scripts/__init__.py || touch scripts/__init__.py
```

- [ ] **Step 2: Implement `group_rows_into_messages`**

Create `backend/scripts/backfill_message_id.py`:

```python
"""Backfill message_id on historical sent_alerts rows.

Two phases:
1. Dry-run: print a CSV-style report describing how rows would be
   grouped, so the operator can spot anomalies (e.g. a single group
   of 50 rows = ambiguous historical data) before mutating anything.
2. Apply: assign UUIDs and UPDATE rows in batches of 500.

Grouping rule: rows missing message_id are grouped by
    (user_id, destination, created_at to the second)
Two simultaneous messages to different destinations remain distinct
because destination is in the key. Microsecond differences from the
same upsert batch collapse to the same second.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Iterable

logger = logging.getLogger(__name__)


def _bucket_key(row: dict) -> tuple[str, str, str]:
    """Return the grouping key for a row: (user_id, destination, ts_seconds)."""
    ts = row["created_at"]
    # ISO 8601 from Supabase: "2026-05-05T03:00:00.000123+00:00"
    # We strip everything after the second.
    ts_seconds = ts[:19]
    return (row["user_id"], row.get("destination") or "", ts_seconds)


def group_rows_into_messages(rows: Iterable[dict]) -> list[list[dict]]:
    """Group sent_alerts rows by (user_id, destination, ts_second).
    Returns a list of groups; each group is a list of rows that belong
    to the same Telegram message."""
    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        buckets[_bucket_key(row)].append(row)
    return list(buckets.values())
```

- [ ] **Step 3: Run the test to verify it passes**

Run (from `backend/`):

```bash
.venv/bin/pytest tests/test_backfill_message_id.py::test_three_rows_same_message_grouped -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/__init__.py backend/scripts/backfill_message_id.py backend/tests/test_backfill_message_id.py
git commit -m "feat(backfill): grouping logic for sent_alerts.message_id

Groups historical rows by (user_id, destination, second) — the
empirical signature of a grouped Telegram alert.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Grouping — cross-destination + cross-user isolation tests

**Files:**
- Modify: `backend/tests/test_backfill_message_id.py`

- [ ] **Step 1: Append two more failing tests**

Append to `backend/tests/test_backfill_message_id.py`:

```python
def test_different_destinations_same_user_same_second_stay_distinct():
    """If a dispatch tick fires two messages to the same user at the
    exact same second but to different destinations (BCN and MAD),
    they remain two distinct events."""
    rows = [
        _row("u1", "BCN", "2026-05-05T03:00:00.000111+00:00", "ak1"),
        _row("u1", "MAD", "2026-05-05T03:00:00.000222+00:00", "ak2"),
    ]
    groups = group_rows_into_messages(rows)
    assert len(groups) == 2
    dests = {g[0]["destination"] for g in groups}
    assert dests == {"BCN", "MAD"}


def test_different_users_never_share_a_group():
    """A row for user A at the same second/destination as user B
    must never collapse into one message."""
    rows = [
        _row("uA", "LIS", "2026-05-05T03:00:00.000111+00:00", "ak1"),
        _row("uB", "LIS", "2026-05-05T03:00:00.000222+00:00", "ak2"),
    ]
    groups = group_rows_into_messages(rows)
    assert len(groups) == 2
    assert {g[0]["user_id"] for g in groups} == {"uA", "uB"}
```

- [ ] **Step 2: Run all tests in the file**

```bash
.venv/bin/pytest tests/test_backfill_message_id.py -v
```

Expected: 3 PASS. (The grouping function from Task 3 already handles these cases — `user_id` and `destination` are part of the bucket key, so no new code needed. This task locks the invariant against future regressions.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_backfill_message_id.py
git commit -m "test(backfill): cross-dest and cross-user isolation invariants

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Backfill — dry-run report

**Files:**
- Modify: `backend/scripts/backfill_message_id.py`
- Modify: `backend/tests/test_backfill_message_id.py`

- [ ] **Step 1: Write the failing test for the report builder**

Append to `backend/tests/test_backfill_message_id.py`:

```python
from scripts.backfill_message_id import build_dry_run_report


def test_dry_run_report_counts_groups_and_distribution():
    """The report tells the operator: how many groups, how rows are
    distributed across group sizes, and which groups look suspect
    (>10 rows = unusual)."""
    rows = (
        # 1 group of 3
        [_row("u1", "LIS", "2026-05-05T03:00:00.000+00:00", f"ak{i}") for i in range(3)]
        # 2 groups of 1 (one-off alerts)
        + [_row("u1", "BCN", "2026-05-05T05:00:00.000+00:00", "ak4")]
        + [_row("u2", "MAD", "2026-05-05T07:00:00.000+00:00", "ak5")]
        # 1 suspect group of 12
        + [_row("u3", "ROM", "2026-05-05T09:00:00.000+00:00", f"ak{i}") for i in range(10, 22)]
    )
    report = build_dry_run_report(rows)
    assert report["total_rows"] == 17
    assert report["total_groups"] == 4
    # Distribution: 1 group of 3, 2 groups of 1, 1 group of 12
    assert report["size_distribution"] == {1: 2, 3: 1, 12: 1}
    # Only the >10 group is flagged as suspect
    assert len(report["suspect_groups"]) == 1
    assert report["suspect_groups"][0]["size"] == 12
    assert report["suspect_groups"][0]["destination"] == "ROM"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/pytest tests/test_backfill_message_id.py::test_dry_run_report_counts_groups_and_distribution -v
```

Expected: FAIL with `ImportError: cannot import name 'build_dry_run_report'`.

- [ ] **Step 3: Implement `build_dry_run_report`**

Append to `backend/scripts/backfill_message_id.py`:

```python
SUSPECT_GROUP_THRESHOLD = 10  # groups larger than this look anomalous in our data


def build_dry_run_report(rows: Iterable[dict]) -> dict:
    """Build a dict describing how the backfill would group rows.

    Returns:
      {
        "total_rows": int,
        "total_groups": int,
        "size_distribution": {group_size: count_of_groups},
        "suspect_groups": [{"user_id", "destination", "created_at", "size"}],
      }

    `suspect_groups` lists every group strictly larger than
    SUSPECT_GROUP_THRESHOLD — those are worth eyeballing before
    committing to the actual UPDATE, because in our data a Telegram
    message typically holds 1-4 offers.
    """
    groups = group_rows_into_messages(list(rows))
    size_distribution: dict[int, int] = defaultdict(int)
    suspect_groups: list[dict] = []
    total_rows = 0
    for grp in groups:
        size = len(grp)
        size_distribution[size] += 1
        total_rows += size
        if size > SUSPECT_GROUP_THRESHOLD:
            head = grp[0]
            suspect_groups.append({
                "user_id": head["user_id"],
                "destination": head.get("destination") or "",
                "created_at": head["created_at"],
                "size": size,
            })
    return {
        "total_rows": total_rows,
        "total_groups": len(groups),
        "size_distribution": dict(size_distribution),
        "suspect_groups": suspect_groups,
    }
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
.venv/bin/pytest tests/test_backfill_message_id.py::test_dry_run_report_counts_groups_and_distribution -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/backfill_message_id.py backend/tests/test_backfill_message_id.py
git commit -m "feat(backfill): dry-run report builder

Returns total/distribution/suspect groups so the operator can
spot anomalies before applying the actual UPDATE.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Backfill — apply phase (UPDATE in batches)

**Files:**
- Modify: `backend/scripts/backfill_message_id.py`
- Modify: `backend/tests/test_backfill_message_id.py`

- [ ] **Step 1: Write the failing idempotence test**

Append to `backend/tests/test_backfill_message_id.py`:

```python
from unittest.mock import MagicMock


class _FakeTable:
    """In-memory fake of the supabase-py table interface, scoped to
    sent_alerts. Only implements the methods the backfill script uses
    (select.is_/order/range, update.in_)."""

    def __init__(self, rows: list[dict]):
        self.rows = rows
        # Track update calls so tests can inspect them
        self.update_calls: list[tuple[dict, list[str]]] = []

    def select(self, _cols):  # noqa: D401
        return self

    def is_(self, col, val):
        # Only "is_('message_id', 'null')" is used by the script.
        assert col == "message_id" and val == "null"
        self._filtered = [r for r in self.rows if r.get("message_id") is None]
        return self

    def order(self, _col):
        return self

    def range(self, start, end_inclusive):
        self._slice = self._filtered[start : end_inclusive + 1]
        return self

    def execute(self):
        out = MagicMock()
        out.data = list(self._slice)
        return out

    def update(self, fields):
        self._pending_update = fields
        return self

    def in_(self, col, ids):
        assert col == "id"
        self.update_calls.append((self._pending_update, list(ids)))
        # Mutate the in-memory rows so subsequent SELECTs see the change
        for r in self.rows:
            if r["id"] in ids:
                r.update(self._pending_update)
        out = MagicMock()
        out.data = [r for r in self.rows if r["id"] in ids]
        return out


def _fake_db(rows):
    db = MagicMock()
    fake_table = _FakeTable(rows)
    db.table.return_value = fake_table
    db._fake_table = fake_table
    return db


def test_apply_backfill_is_idempotent():
    """A second run on already-backfilled data does nothing (no UPDATE
    issued) because the WHERE message_id IS NULL filter returns empty."""
    from scripts.backfill_message_id import apply_backfill

    rows = [
        _row("u1", "LIS", "2026-05-05T03:00:00.000+00:00", "ak1"),
        _row("u1", "LIS", "2026-05-05T03:00:00.000+00:00", "ak2"),
    ]
    db = _fake_db(rows)
    # First run: assigns UUIDs.
    n1 = apply_backfill(db=db, batch_size=10)
    assert n1 == 2  # two rows updated
    assert all(r["message_id"] is not None for r in rows)
    assigned_uuid = rows[0]["message_id"]
    assert rows[1]["message_id"] == assigned_uuid  # same group → same UUID

    # Second run: nothing to do.
    n2 = apply_backfill(db=db, batch_size=10)
    assert n2 == 0
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
.venv/bin/pytest tests/test_backfill_message_id.py::test_apply_backfill_is_idempotent -v
```

Expected: FAIL with `ImportError: cannot import name 'apply_backfill'`.

- [ ] **Step 3: Implement `apply_backfill`**

Append to `backend/scripts/backfill_message_id.py`:

```python
def apply_backfill(*, db, batch_size: int = 500) -> int:
    """Assign a message_id to every sent_alerts row that still has
    NULL. Process in batches; each batch is committed independently
    (no global transaction) so a crash mid-run leaves a partial but
    consistent state — the next run resumes via `message_id IS NULL`.

    Returns the total number of rows updated."""
    table = db.table("sent_alerts")
    total_updated = 0
    while True:
        # Pull next batch of un-backfilled rows.
        resp = (
            table.select("id,user_id,destination,alert_key,created_at,message_id")
            .is_("message_id", "null")
            .order("created_at")
            .range(0, batch_size - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break

        # Group and assign one UUID per group.
        groups = group_rows_into_messages(batch)
        for grp in groups:
            new_id = str(uuid.uuid4())
            ids = [r["id"] for r in grp]
            table.update({"message_id": new_id}).in_("id", ids).execute()
            total_updated += len(ids)

    return total_updated
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
.venv/bin/pytest tests/test_backfill_message_id.py::test_apply_backfill_is_idempotent -v
```

Expected: PASS.

- [ ] **Step 5: Run the full test file to confirm no regression**

```bash
.venv/bin/pytest tests/test_backfill_message_id.py -v
```

Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/backfill_message_id.py backend/tests/test_backfill_message_id.py
git commit -m "feat(backfill): apply phase with idempotent batches

apply_backfill processes rows where message_id IS NULL in batches
of 500, committing each batch. Re-running on a fully-backfilled
table is a no-op.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Backfill — CLI entry point

**Files:**
- Modify: `backend/scripts/backfill_message_id.py`

- [ ] **Step 1: Add the `__main__` block**

Append to `backend/scripts/backfill_message_id.py`:

```python
def _print_report(report: dict) -> None:
    print(f"Total rows missing message_id : {report['total_rows']}")
    print(f"Total groups (= messages)      : {report['total_groups']}")
    print("Size distribution:")
    for size in sorted(report["size_distribution"].keys()):
        print(f"  {size:>3} row(s) per group : {report['size_distribution'][size]} groups")
    if report["suspect_groups"]:
        print(f"\nSUSPECT groups (>{SUSPECT_GROUP_THRESHOLD} rows):")
        for g in report["suspect_groups"]:
            print(f"  user={g['user_id'][:8]} dest={g['destination']} ts={g['created_at']} size={g['size']}")
    else:
        print(f"\nNo suspect groups (threshold > {SUSPECT_GROUP_THRESHOLD}).")


def _fetch_all_null_rows(db) -> list[dict]:
    """Pull all rows with NULL message_id, paginating in 1000-row chunks."""
    all_rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("sent_alerts")
            .select("id,user_id,destination,alert_key,created_at,message_id")
            .is_("message_id", "null")
            .order("created_at")
            .range(offset, offset + 999)
            .execute()
        )
        chunk = resp.data or []
        all_rows.extend(chunk)
        if len(chunk) < 1000:
            break
        offset += 1000
    return all_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill sent_alerts.message_id")
    parser.add_argument("--apply", action="store_true",
                        help="Actually run the UPDATE. Without this flag, only a dry-run report is printed.")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    # Lazy import so `python -m scripts.backfill_message_id --help` works
    # without DB credentials.
    from app.db import db
    if db is None:
        print("ERROR: Supabase DB not configured (check .env).", file=sys.stderr)
        return 2

    rows = _fetch_all_null_rows(db)
    report = build_dry_run_report(rows)
    _print_report(report)

    if not args.apply:
        print("\nDRY-RUN. Re-run with --apply to perform the UPDATE.")
        return 0

    if report["suspect_groups"]:
        # Refuse silently — operator must investigate first.
        print("\nABORT: suspect groups present. Investigate before applying.", file=sys.stderr)
        return 3

    updated = apply_backfill(db=db, batch_size=args.batch_size)
    print(f"\n✅ Updated {updated} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Sanity-check the CLI parses arguments**

Run (from `backend/`):

```bash
.venv/bin/python3 -m scripts.backfill_message_id --help
```

Expected: argparse usage printed; exit code 0.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/backfill_message_id.py
git commit -m "feat(backfill): CLI with dry-run-by-default + suspect-group guard

python -m scripts.backfill_message_id  → dry-run report
python -m scripts.backfill_message_id --apply  → actual UPDATE
The --apply path refuses to run if dry-run flagged suspect
groups (>10 rows per message), forcing operator review.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Dispatcher — generate `message_id` at each upsert call site (site 1 of 3)

**Files:**
- Modify: `backend/app/scheduler/jobs.py` (around line 1170)

- [ ] **Step 1: Inspect the existing upsert block**

Run:

```bash
sed -n '1155,1180p' /Users/moussa/Documents/PROJETS/globegenius/backend/app/scheduler/jobs.py
```

Expected output (verify shape — line numbers may drift slightly with prior edits):

```python
            rows = []
            for k in keys_to_store:
                lane = free_lane_by_key.get(k)
                stored_key = f"{lane}:{k}" if lane else k
                rows.append({
                    "user_id": uid,
                    "chat_id": chat_id,
                    "alert_key": stored_key,
                    "destination": grp_dest,
                    "alert_type": "flight",
                    "price": best_price,
                    "discount_pct": best_discount,
                })
            try:
                db.table("sent_alerts").upsert(
                    rows, on_conflict="user_id,alert_key"
                ).execute()
```

- [ ] **Step 2: Edit the block to inject `message_id`**

Modify `backend/app/scheduler/jobs.py` around the grouped-flight upsert call. Replace the block above with:

```python
            import uuid
            message_id = str(uuid.uuid4())
            rows = []
            for k in keys_to_store:
                lane = free_lane_by_key.get(k)
                stored_key = f"{lane}:{k}" if lane else k
                rows.append({
                    "user_id": uid,
                    "chat_id": chat_id,
                    "alert_key": stored_key,
                    "destination": grp_dest,
                    "alert_type": "flight",
                    "price": best_price,
                    "discount_pct": best_discount,
                    "message_id": message_id,
                })
            try:
                db.table("sent_alerts").upsert(
                    rows, on_conflict="user_id,alert_key"
                ).execute()
```

(The `import uuid` should ideally move to the top of the file if not already imported. Check first: `grep -n "^import uuid" backend/app/scheduler/jobs.py`. If not present, add it to the imports block.)

- [ ] **Step 3: Run all backend tests to catch regressions**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
.venv/bin/pytest tests/test_dispatch_guards.py tests/test_backfill_message_id.py -v
```

Expected: all PASS. (No test currently exercises the dispatcher call-site directly — that's by design, the unit logic is tested via `dispatch_guards` and `backfill_message_id` separately.)

- [ ] **Step 4: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): generate message_id for grouped flight alerts (site 1/3)

Every grouped-flight upsert now attaches a single UUID shared
by all rows of the same Telegram message. Sites 2 and 3
(oneway, split-ticket) come in follow-up commits.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Dispatcher — `message_id` for oneway alerts (site 2 of 3)

**Files:**
- Modify: `backend/app/scheduler/jobs.py` (around line 1866)

- [ ] **Step 1: Inspect the oneway upsert block**

```bash
sed -n '1855,1875p' /Users/moussa/Documents/PROJETS/globegenius/backend/app/scheduler/jobs.py
```

Verify the block contains `db.table("sent_alerts").upsert(...)` and that `rows` is built locally just before. The `alert_type` should be `"one_way"`.

- [ ] **Step 2: Apply the same pattern as Task 8**

Add immediately before the `rows = []` (or its equivalent) line:

```python
            message_id = str(uuid.uuid4())
```

And add `"message_id": message_id,` to each dict appended to `rows`.

- [ ] **Step 3: Confirm tests still green**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py tests/test_backfill_message_id.py -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): generate message_id for one-way alerts (site 2/3)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Dispatcher — `message_id` for split-ticket alerts (site 3 of 3)

**Files:**
- Modify: `backend/app/scheduler/jobs.py` (around line 2125)

- [ ] **Step 1: Inspect the split-ticket upsert block**

```bash
sed -n '2115,2145p' /Users/moussa/Documents/PROJETS/globegenius/backend/app/scheduler/jobs.py
```

Verify it contains `"alert_type": "split_ticket"` and `db.table("sent_alerts").upsert(...)`.

- [ ] **Step 2: Apply the same pattern**

Add `message_id = str(uuid.uuid4())` just before the row build, and `"message_id": message_id,` to each appended dict.

- [ ] **Step 3: Grep verifies all 3 sites are wired**

```bash
grep -c '"message_id": message_id' backend/app/scheduler/jobs.py
```

Expected output: `3` (one per site).

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py tests/test_backfill_message_id.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): generate message_id for split-ticket alerts (site 3/3)

All three dispatcher call-sites now attach a message_id to
the rows they write. New sent_alerts rows have non-null
message_id from this commit forward; historical rows are
handled by scripts/backfill_message_id.py.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: L2 cap prefers `message_id` over the 5-min bucket — failing test

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Locate the `_row` test helper**

```bash
grep -n "^def _row" backend/tests/test_dispatch_guards.py
```

Note the helper signature — we'll extend it to accept an optional `message_id` argument.

- [ ] **Step 2: Extend `_row` (additive change)**

In `backend/tests/test_dispatch_guards.py`, replace the existing `_row` definition with:

```python
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
```

- [ ] **Step 3: Run existing tests to confirm no regression**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: all 25 existing tests still PASS (the extra `message_id=None` kwarg defaults preserve the old behaviour).

- [ ] **Step 4: Add the new failing test**

Append to `backend/tests/test_dispatch_guards.py`:

```python
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
```

- [ ] **Step 5: Run the new test to verify it fails**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_l2_collapses_rows_sharing_message_id_not_just_bucket -v
```

Expected: FAIL — the current implementation only knows about the bucket-5min, so three rows 30 minutes apart count as 3 events, the cap is hit, the 30% candidate blocks. The assertion `is False` will fail (got True).

---

## Task 12: L2 cap — implement the `message_id` preference

**Files:**
- Modify: `backend/app/notifications/dispatch_guards.py`

- [ ] **Step 1: Locate the dedup section in `levier_2_daily_cap_blocks`**

```bash
grep -n "seen_buckets\|_message_bucket_key" backend/app/notifications/dispatch_guards.py
```

Note the inner loop around the existing dedup (it iterates `sent` rows and builds `unique_messages`).

- [ ] **Step 2: Modify the dedup loop to prefer `message_id`**

In `backend/app/notifications/dispatch_guards.py`, find the block that currently looks like:

```python
    seen_buckets: set[tuple[str, str]] = set()
    unique_messages: list[dict] = []
    for r in sent:
        if r.get("discount_pct") is None:
            continue
        bucket = _message_bucket_key(r)
        if bucket is None:
            unique_messages.append(r)
            continue
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        unique_messages.append(r)
```

Replace it with:

```python
    # Two dedup mechanisms, applied in order:
    # 1. `message_id` (chantier 1, 2026-05-17): authoritative — rows
    #    sharing a UUID belong to one Telegram message regardless of
    #    timing.
    # 2. `(destination, 5-min bucket)` fallback: kept for pre-migration
    #    rows where message_id is NULL. Removed once the backfill +
    #    CHECK constraint guarantee no NULL rows remain.
    seen_message_ids: set[str] = set()
    seen_buckets: set[tuple[str, str]] = set()
    unique_messages: list[dict] = []
    for r in sent:
        if r.get("discount_pct") is None:
            continue
        mid = r.get("message_id")
        if mid is not None:
            if mid in seen_message_ids:
                continue
            seen_message_ids.add(mid)
            unique_messages.append(r)
            continue
        bucket = _message_bucket_key(r)
        if bucket is None:
            unique_messages.append(r)
            continue
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        unique_messages.append(r)
```

- [ ] **Step 3: Ensure the SELECT also fetches `message_id`**

In the same function, find the `.select("discount_pct,destination,created_at")` line and change it to:

```python
.select("discount_pct,destination,created_at,message_id")
```

- [ ] **Step 4: Run the failing test to verify it now passes**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_l2_collapses_rows_sharing_message_id_not_just_bucket -v
```

Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regression**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: 26 PASS (25 existing + 1 new).

- [ ] **Step 6: Commit**

```bash
git add backend/app/notifications/dispatch_guards.py backend/tests/test_dispatch_guards.py
git commit -m "fix(alerts): L2 prefers message_id over 5-min bucket dedup

When a row carries a message_id (new rows from chantier 1), L2
collapses on the UUID — authoritative grouping. When message_id
is NULL (pre-migration rows), L2 falls back to the existing
(destination, 5-min bucket) heuristic. Both mechanisms coexist
until the backfill is complete and the CHECK constraint lands.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Mixed-rows test (NULL message_id + new rows)

**Files:**
- Modify: `backend/tests/test_dispatch_guards.py`

- [ ] **Step 1: Append the mixed-rows test**

Append to `backend/tests/test_dispatch_guards.py`:

```python
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
```

- [ ] **Step 2: Run the test to confirm it passes**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py::test_l2_handles_mix_of_null_message_id_and_new_rows -v
```

Expected: PASS (the implementation from Task 12 already handles both paths).

- [ ] **Step 3: Run the full suite**

```bash
.venv/bin/pytest tests/test_dispatch_guards.py -v
```

Expected: 27 PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_dispatch_guards.py
git commit -m "test(alerts): L2 correctly counts mix of legacy + new message_id rows

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Operational backfill — dry-run then apply (manual)

**Files:** none (operational step against production DB).

- [ ] **Step 1: Run the dry-run report**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
.venv/bin/python3 -m scripts.backfill_message_id
```

Expected output structure:

```
Total rows missing message_id : 3196
Total groups (= messages)      : ~1500-2500
Size distribution:
    1 row(s) per group : N groups
    2 row(s) per group : N groups
    3 row(s) per group : N groups
    ...
No suspect groups (threshold > 10).

DRY-RUN. Re-run with --apply to perform the UPDATE.
```

- [ ] **Step 2: Validate the report**

Check that:
- `total_rows` matches expected (~3200 historical rows).
- Median group size is 1–4 (typical Telegram message holds 1–4 offers).
- No suspect groups, OR if any suspect groups: investigate before continuing (likely a real-world quirk worth understanding — do **not** skip this check).

- [ ] **Step 3: Apply the backfill**

If the dry-run was clean:

```bash
.venv/bin/python3 -m scripts.backfill_message_id --apply
```

Expected final line: `✅ Updated N rows.` where N matches `total_rows` from the dry-run.

- [ ] **Step 4: Verify in DB**

```bash
.venv/bin/python3 -c "
from dotenv import load_dotenv; load_dotenv('.env')
from app.db import db
r = db.table('sent_alerts').select('id', count='exact').is_('message_id', 'null').limit(1).execute()
print(f'Rows still missing message_id: {r.count}')
"
```

Expected: `Rows still missing message_id: 0` (or a very small number if new rows landed during the backfill — those will be auto-handled by the Python dispatcher from Task 8/9/10 onwards, so a second `--apply` run is safe).

---

## Task 15: Open a PR for chantier 1

**Files:** none (Git/GitHub step).

- [ ] **Step 1: Push the branch**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git push -u origin polish-pre-launch
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "feat: chantier 1 — sent_alerts.message_id" --body "$(cat <<'EOF'
## Summary

- Migration 039 adds `sent_alerts.message_id uuid` + index.
- Dispatcher generates one UUID per `send_grouped_flight_alerts` call (3 call-sites).
- L2 cap prefers `message_id` over the 5-min bucket dedup; bucket stays as a fallback for pre-migration rows.
- Backfill script with mandatory dry-run + suspect-group guard.

Spec: `docs/superpowers/specs/2026-05-17-polish-pre-launch-design.md`.

## Test plan

- [ ] `pytest backend/tests/test_dispatch_guards.py` → 27 PASS
- [ ] `pytest backend/tests/test_backfill_message_id.py` → 4 PASS
- [ ] Manual: dry-run report shows no suspect groups on prod data
- [ ] Manual: `--apply` brings the `WHERE message_id IS NULL` count to 0
- [ ] Smoke: send one alert post-deploy, verify the new row has a non-null `message_id`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## Self-Review

**Spec coverage check** (against `docs/superpowers/specs/2026-05-17-polish-pre-launch-design.md` chantier 1):

- ✅ Migration 039 with `IF NOT EXISTS` (Task 1)
- ✅ Backfill dry-run with CSV-like distribution + suspect groups (Tasks 5, 7, 14)
- ✅ Backfill batches of 500, commit-per-batch, idempotent (Task 6)
- ✅ Three dispatcher call-sites attach `message_id` (Tasks 8, 9, 10)
- ✅ Invariant: new inserts always have non-null `message_id` (Tasks 8–10)
- ✅ L2 prefers `message_id` over 5-min bucket; bucket stays as fallback (Task 12)
- ✅ Tests: same-message grouping, distinct-message separation, cross-user isolation, idempotence, mixed legacy+new rows (Tasks 2, 4, 6, 11, 13)
- ⚠️ **NOT included by design**: the CHECK constraint at +1 month — that's an operational step out of plan scope (logged in ROADMAP).

**Placeholder scan**: no TBD/TODO/FIXME in the plan steps. The "implement later" trap is avoided — every step has either runnable code or a runnable command.

**Type consistency**: `group_rows_into_messages`, `build_dry_run_report`, `apply_backfill`, `main` all line up across tasks. The test helper `_row` adds `message_id=None` defaulting kwarg additively (no signature break for existing tests).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-polish-pre-launch-chantier-1-message-id.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
