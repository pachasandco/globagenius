"""Backfill destination articles for IATAs that have triggered alerts.

Run from the backend dir with the prod .env loaded:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/backfill_destination_articles.py

The script is idempotent: if an article already exists for an IATA, it's
skipped. Failures on individual IATAs are logged but don't abort the run.
"""
import logging
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")

from app.db import db
from app.notifications.destination_articles import ensure_article_for_destination


def main() -> int:
    if not db:
        print("FAIL: db not configured")
        return 1

    sent = db.table("sent_alerts").select("destination").execute()
    alerted_iatas = sorted(
        {row["destination"] for row in (sent.data or []) if row.get("destination")}
    )
    if not alerted_iatas:
        print("No destinations to backfill.")
        return 0

    existing = db.table("articles").select("iata").not_.is_("iata", "null").execute()
    have = {row["iata"] for row in (existing.data or [])}

    todo = [iata for iata in alerted_iatas if iata not in have]
    print(f"Backfill plan: {len(todo)} IATAs to generate "
          f"({len(alerted_iatas)} alerted, {len(have)} already done).")
    print("To generate:", todo)
    print()

    succeeded = 0
    failed: list[str] = []
    for i, iata in enumerate(todo, 1):
        t0 = time.time()
        print(f"[{i}/{len(todo)}] {iata} ... ", end="", flush=True)
        try:
            ok = ensure_article_for_destination(iata)
        except Exception as e:
            ok = False
            print(f"EXCEPTION: {e}")
        elapsed = int(time.time() - t0)
        if ok:
            succeeded += 1
            print(f"OK ({elapsed}s)")
        else:
            failed.append(iata)
            print(f"FAIL ({elapsed}s)")

    print()
    print(f"Done. {succeeded}/{len(todo)} succeeded.")
    if failed:
        print(f"Failed: {failed}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
