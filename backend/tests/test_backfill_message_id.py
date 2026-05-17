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
