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
