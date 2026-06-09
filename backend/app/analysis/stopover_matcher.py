"""Stopover phase 1 (2026-06-09): chain 3 one-way tickets into a
two-destination trip — origin → hub (2-5 days), hub → final destination,
destination → origin — and qualify the chain against the round-trip
baseline for origin → destination DIRECT.

No new API needed: all three legs come from one-way fares already in
raw_flights (the hub → destination "connector" legs are scraped for a
curated whitelist of hub pairs — see config.STOPOVER_HUB_PAIRS).

This module is pure: no DB, no I/O. Inputs are plain dicts (the same
shape as raw_flights one-way rows) plus a round-trip baseline price.
Callers persist results and dispatch alerts — mirrors
split_ticket_matcher.py, which this extends from 2 legs to 3.
"""

from dataclasses import dataclass
from datetime import datetime

from app.thresholds import (
    STOPOVER_MAX_HUB_DAYS,
    STOPOVER_MAX_TOTAL_DAYS,
    STOPOVER_MIN_DEST_DAYS,
    STOPOVER_MIN_HUB_DAYS,
    STOPOVER_SAVINGS_EUR_FLOOR,
    STOPOVER_SAVINGS_RATIO_FLOOR,
)


@dataclass(frozen=True)
class StopoverChain:
    leg1: dict                    # origin → hub
    leg2: dict                    # hub → destination
    leg3: dict                    # destination → origin
    total: int                    # rounded EUR
    savings: int                  # rounded EUR vs direct roundtrip baseline
    roundtrip_baseline: int       # rounded EUR (origin → destination direct)
    hub_days: int
    dest_days: int


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _cheapest_per_date(legs: list[dict]) -> list[dict]:
    """Keep only the cheapest fare per departure date — chains never
    benefit from a more expensive fare on the same day, and this caps
    the triple loop below at (distinct dates)³ instead of (rows)³."""
    by_date: dict[str, dict] = {}
    for leg in legs:
        dep = (leg.get("departure_date") or "")[:10]
        price = leg.get("price") or 0
        if not dep or price <= 0:
            continue
        existing = by_date.get(dep)
        if existing is None or price < (existing.get("price") or 0):
            by_date[dep] = leg
    return list(by_date.values())


def find_stopover_chains(
    leg1s: list[dict],
    leg2s: list[dict],
    leg3s: list[dict],
    roundtrip_baseline: float,
) -> list[StopoverChain]:
    """Return at most one qualified chain — the one with the largest
    absolute savings vs the direct round-trip baseline.

    Date constraints:
      - hub stay  = leg2.departure − leg1.departure ∈ [2, 5] days
      - dest stay = leg3.departure − leg2.departure ≥ 3 days
      - total trip ≤ 30 days (stays comparable to the baseline cell)

    Price constraints:
      - total ≤ baseline × (1 − STOPOVER_SAVINGS_RATIO_FLOOR)
      - savings ≥ STOPOVER_SAVINGS_EUR_FLOOR
    """
    if roundtrip_baseline <= 0 or not leg1s or not leg2s or not leg3s:
        return []

    threshold_total = roundtrip_baseline * (1 - STOPOVER_SAVINGS_RATIO_FLOOR)

    best: StopoverChain | None = None
    for l1 in _cheapest_per_date(leg1s):
        d1 = _parse_date(l1.get("departure_date", ""))
        if d1 is None:
            continue
        for l2 in _cheapest_per_date(leg2s):
            d2 = _parse_date(l2.get("departure_date", ""))
            if d2 is None:
                continue
            hub_days = (d2 - d1).days
            if hub_days < STOPOVER_MIN_HUB_DAYS or hub_days > STOPOVER_MAX_HUB_DAYS:
                continue
            for l3 in _cheapest_per_date(leg3s):
                d3 = _parse_date(l3.get("departure_date", ""))
                if d3 is None:
                    continue
                dest_days = (d3 - d2).days
                if dest_days < STOPOVER_MIN_DEST_DAYS:
                    continue
                if (d3 - d1).days > STOPOVER_MAX_TOTAL_DAYS:
                    continue

                total = (l1.get("price") or 0) + (l2.get("price") or 0) + (l3.get("price") or 0)
                if total <= 0 or total > threshold_total:
                    continue
                savings = roundtrip_baseline - total
                if savings < STOPOVER_SAVINGS_EUR_FLOOR:
                    continue

                chain = StopoverChain(
                    leg1=l1,
                    leg2=l2,
                    leg3=l3,
                    total=int(round(total)),
                    savings=int(round(savings)),
                    roundtrip_baseline=int(round(roundtrip_baseline)),
                    hub_days=hub_days,
                    dest_days=dest_days,
                )
                if best is None or chain.savings > best.savings:
                    best = chain

    return [best] if best else []
