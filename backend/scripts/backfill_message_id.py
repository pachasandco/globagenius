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


def apply_backfill(*, db, batch_size: int = 500) -> int:
    """Assign a message_id to eligible sent_alerts rows. Process in
    batches; each batch is committed independently (no global
    transaction) so a crash mid-run leaves a partial but consistent
    state — the next run resumes via `message_id IS NULL`.

    Eligibility: `message_id IS NULL AND price IS NOT NULL`. Pre-037
    rows (price NULL) are intentionally left out — see
    `_fetch_all_null_rows` for the rationale.

    Returns the total number of rows updated."""
    table = db.table("sent_alerts")
    total_updated = 0
    while True:
        # Pull next batch of un-backfilled, post-037 rows.
        resp = (
            table.select("id,user_id,destination,alert_key,created_at,message_id")
            .is_("message_id", "null")
            .not_.is_("price", "null")
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
    """Pull rows eligible for backfill: NULL message_id AND post-migration-037
    (price IS NOT NULL).

    Pre-037 rows have NULL price/discount_pct/departure_date because those
    columns were added by migration 037. When 80+ such rows share the same
    created_at microsecond, we can't distinguish "1 grouped message of 80
    offers" from "80 separate one-offer messages" — historical telemetry
    is lost. Skipping them keeps message_id semantics trustworthy: every
    populated message_id corresponds to a verifiable grouped Telegram send.

    Pre-037 rows remain message_id=NULL and are handled by L2's existing
    5-min bucket fallback.
    """
    all_rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("sent_alerts")
            .select("id,user_id,destination,alert_key,created_at,message_id")
            .is_("message_id", "null")
            .not_.is_("price", "null")
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
