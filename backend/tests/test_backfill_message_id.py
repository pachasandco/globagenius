"""Tests for the backfill script's grouping logic.

The grouping logic is what assigns one message_id per Telegram
message in historical sent_alerts rows. Wrong grouping = wrong stats
forever, so this is the test that has to be correct above all.
"""
from datetime import datetime, timezone

from scripts.backfill_message_id import group_rows_into_messages


def _row(user_id: str, dest: str, ts: str, alert_key: str, price: float | None = 100.0):
    """Build a sent_alerts row fixture in the shape the grouper expects.

    `price` defaults to a non-NULL sentinel because the backfill script
    intentionally skips pre-migration-037 rows where price IS NULL. Most
    grouping tests are post-037 by default; tests that exercise the
    skip-pre-037 behaviour can pass `price=None` explicitly.
    """
    return {
        "id": f"id-{alert_key}",
        "user_id": user_id,
        "destination": dest,
        "alert_key": alert_key,
        "created_at": ts,
        "message_id": None,
        "price": price,
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


from unittest.mock import MagicMock


class _FakeNot:
    """Implements the `.not_.is_(col, val)` postgrest filter shape.
    Currently only `not_.is_('price', 'null')` is exercised."""

    def __init__(self, parent: "_FakeTable"):
        self._parent = parent

    def is_(self, col, val):
        assert col == "price" and val == "null", \
            f"_FakeNot.is_ only supports ('price', 'null'); got ({col!r}, {val!r})"
        self._parent._filtered = [
            r for r in self._parent._filtered if r.get("price") is not None
        ]
        return self._parent


class _FakeTable:
    """In-memory fake of the supabase-py table interface, scoped to
    sent_alerts. Implements the subset of methods the backfill script
    uses (select.is_/not_.is_/order/range, update.in_)."""

    def __init__(self, rows: list[dict]):
        self.rows = rows
        # Track update calls so tests can inspect them
        self.update_calls: list[tuple[dict, list[str]]] = []
        self._filtered: list[dict] = list(rows)

    def select(self, _cols):  # noqa: D401
        # Reset the filter chain on a new select call.
        self._filtered = list(self.rows)
        return self

    def is_(self, col, val):
        # Only "is_('message_id', 'null')" is used by the script.
        assert col == "message_id" and val == "null", \
            f"_FakeTable.is_ only supports ('message_id', 'null'); got ({col!r}, {val!r})"
        self._filtered = [r for r in self._filtered if r.get("message_id") is None]
        return self

    @property
    def not_(self) -> "_FakeNot":
        return _FakeNot(self)

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


def test_apply_backfill_skips_pre_migration_037_rows():
    """Pre-migration-037 rows have NULL price and aren't groupable
    safely (we can't reconstruct whether 80 rows at the same second
    were 1 grouped message or 80 distinct messages). The backfill
    must leave them alone — they keep message_id=NULL and L2's
    5-min bucket fallback handles them at runtime."""
    from scripts.backfill_message_id import apply_backfill

    rows = [
        # Two post-037 rows (price set) — should be backfilled together
        _row("u1", "LIS", "2026-05-10T03:00:00.000+00:00", "ak_new1", price=100.0),
        _row("u1", "LIS", "2026-05-10T03:00:00.000+00:00", "ak_new2", price=100.0),
        # Two pre-037 rows (price NULL) — must be skipped
        _row("u1", "MAD", "2026-04-01T03:00:00.000+00:00", "ak_old1", price=None),
        _row("u1", "MAD", "2026-04-01T03:00:00.000+00:00", "ak_old2", price=None),
    ]
    db = _fake_db(rows)
    updated = apply_backfill(db=db, batch_size=10)
    assert updated == 2  # only the 2 post-037 rows
    # Post-037 rows got a shared UUID
    new_rows = [r for r in rows if r["alert_key"].startswith("ak_new")]
    assert new_rows[0]["message_id"] is not None
    assert new_rows[0]["message_id"] == new_rows[1]["message_id"]
    # Pre-037 rows kept message_id=None
    old_rows = [r for r in rows if r["alert_key"].startswith("ak_old")]
    assert all(r["message_id"] is None for r in old_rows)


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
