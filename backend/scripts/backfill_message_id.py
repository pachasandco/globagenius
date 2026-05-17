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
