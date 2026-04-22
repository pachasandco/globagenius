#!/usr/bin/env python3
"""One-shot script to seed priority_destinations table.

Run once after deploying migration 007 to populate the table immediately
without waiting for the Monday 3am cron job.

Usage:
    cd backend
    python scripts/seed_destinations.py
    python scripts/seed_destinations.py --dry-run   # preview scores, no DB write
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.analysis.destination_updater import compute_priority_destinations, update_priority_destinations_in_db


def main():
    parser = argparse.ArgumentParser(description="Seed priority_destinations table")
    parser.add_argument("--dry-run", action="store_true", help="Preview scores without writing to DB")
    parser.add_argument("--max-count", type=int, default=40, help="Number of destinations to keep (default: 40)")
    args = parser.parse_args()

    rows = compute_priority_destinations(max_count=args.max_count)

    print(f"\n{'='*65}")
    print(f"{'DESTINATION PRIORITY RANKING':^65}")
    print(f"{'='*65}")
    print(f"  {'#':>2}  {'IATA':<5} {'Destination':<30} {'Score':>6}  {'Type':<10}")
    print(f"  {'-'*2}  {'-'*4} {'-'*30} {'-'*6}  {'-'*10}")

    for i, r in enumerate(rows, 1):
        kind = "LONG-HAUL" if r["is_long_haul"] else "court"
        tp = f" (TP: {r['tp_price']:.0f}€)" if r.get("tp_price") else ""
        print(f"  {i:>2}. {r['iata']:<5} {r['label_fr']:<30} {r['score']:>6.1f}  {kind}{tp}")

    long_haul = [r for r in rows if r["is_long_haul"]]
    print(f"\n  Total: {len(rows)} destinations | Long-haul: {len(long_haul)} | Season: {rows[0]['season']}")
    print(f"{'='*65}\n")

    if args.dry_run:
        print("Dry-run mode — no DB write.")
        return

    from app.db import db
    if not db:
        print("ERROR: No database connection. Check SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    count = update_priority_destinations_in_db(db, max_count=args.max_count)
    if count:
        print(f"✅ {count} destinations upserted into priority_destinations table.")
        print("   The enrichment job will now use this list on its next run.")
    else:
        print("❌ Upsert failed. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
