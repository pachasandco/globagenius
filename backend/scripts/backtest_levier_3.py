"""Backtest the L3 anti-burst rule against the last 14 days of
sent_alerts before merging chantier 3.

Three pass criteria the spec requires:

  1. <20% additional alerts blocked beyond what L2 already blocks.
  2. No alert with discount_pct >= 70% (short) or >= 60% (long) would
     be blocked — proves the exception threshold works.
  3. Identified bursts visibly broken: e.g. user e17b1153's 4-alert
     window on 2026-05-15 (00h-04h) reduces to 1 alert + 3 blocked.

Output: a printed report. Exit code 0 if criteria 1 and 2 pass,
1 otherwise. The operator inspects criterion 3 via the printed
per-user breakdown.
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


# Pass criteria thresholds (per the spec).
MAX_BLOCKED_PCT = 20.0
SHORT_EXCEPTION = 70.0
LONG_EXCEPTION = 60.0


def evaluate_criteria(
    result: dict,
    *,
    long_haul_set: set[str],
) -> dict:
    """Run the two automatic pass criteria against the simulation
    result. The third criterion (identified bursts broken) is
    operator-inspected via the per-user breakdown."""
    blocked_pct = result["blocked_pct"]
    crit_1_pass = blocked_pct < MAX_BLOCKED_PCT
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
    return {
        "crit_1_blocked_pct_under_20": crit_1_pass,
        "crit_2_no_exception_violators": crit_2_pass,
        "violators": violators[:5],
        "blocked_pct": blocked_pct,
        "crit_3_per_user_breakdown": result["per_user"],
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


# Long-haul set hard-coded to avoid coupling the script to
# app.analysis.route_selector (it's an ops tool, not a library).
# Keep in sync with route_selector.LONG_HAUL_DESTINATIONS.
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
