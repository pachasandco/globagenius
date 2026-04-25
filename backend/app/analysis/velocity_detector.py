"""Velocity-based mistake fare detector.

Detects prices that have dropped sharply within a short time window — the
signature of an airline pricing error (mistake fare).

Algorithm:
  1. Store every Tier 1 price observation in price_snapshots (bulk insert).
  2. For each new price, look back 2 hours in price_snapshots for the same
     (origin, destination, departure_date, return_date).
  3. If current_price < reference_price × VELOCITY_DROP_THRESHOLD:
     → Emit a VelocityAlert with severity proportional to the drop.

Thresholds (tuned from industry data — mistake fares typically drop 50-90%):
  FARE_MISTAKE  : drop ≥ 60% in < 2h  (z_score override: always FARE_MISTAKE)
  FLASH_PROMO   : drop ≥ 40% in < 2h
  Ignored       : drop < 40%           (normal price fluctuation)

Integration:
  - Called from job_scrape_tier1 for the full batch of Tier 1 flights.
  - VelocityAlerts bypass the normal z-score pipeline and go straight to
    reverify → dispatch, since speed is critical (deals last 2-8h max).
  - Deduplication still applies via sent_alerts table.

Performance:
  - save_snapshots_bulk: one INSERT per scrape run (not one per flight).
  - detect_velocity_drops_bulk: one SELECT covering all routes in the batch,
    then detection runs in memory. O(flights) instead of O(flights × queries).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

VELOCITY_DROP_FLASH_PROMO = 0.40   # 40% drop → FLASH_PROMO
VELOCITY_DROP_FARE_MISTAKE = 0.60  # 60% drop → FARE_MISTAKE
LOOKBACK_HOURS = 2


@dataclass
class VelocityAlert:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    current_price: float
    reference_price: float
    drop_pct: float
    alert_level: str         # "fare_mistake" or "flash_promo"
    airline: str
    source: str


# ── legacy single-flight API (kept for callers that haven't migrated) ────────

def save_snapshot(db, flight: dict) -> bool:
    """Single-flight snapshot insert. Prefer save_snapshots_bulk for batches."""
    return bool(save_snapshots_bulk(db, [flight]))


def detect_velocity_drop(db, flight: dict) -> VelocityAlert | None:
    """Single-flight velocity check. Prefer detect_velocity_drops_bulk for batches."""
    alerts = detect_velocity_drops_bulk(db, [flight])
    return alerts[0] if alerts else None


# ── bulk API ─────────────────────────────────────────────────────────────────

def save_snapshots_bulk(db, flights: list[dict]) -> int:
    """Insert all price snapshots in a single Supabase request.

    Returns the number of rows inserted (0 on error or empty input).
    """
    if not db or not flights:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for flight in flights:
        try:
            rows.append({
                "origin": flight["origin"],
                "destination": flight["destination"],
                "departure_date": flight.get("departure_date") or flight.get("departure_at", "")[:10],
                "return_date": flight.get("return_date") or flight.get("return_at", "")[:10],
                "price": float(flight["price"]),
                "airline": flight.get("airline", ""),
                "source": flight.get("source", "tier1"),
                "captured_at": now,
            })
        except (KeyError, TypeError, ValueError):
            continue

    if not rows:
        return 0

    try:
        db.table("price_snapshots").insert(rows).execute()
        return len(rows)
    except Exception as e:
        logger.warning(f"save_snapshots_bulk failed ({len(rows)} rows): {e}")
        return 0


def detect_velocity_drops_bulk(db, flights: list[dict]) -> list[VelocityAlert]:
    """Detect velocity drops for an entire batch in two DB round-trips.

    Round-trip 1: one SELECT covering all (origin, destination) pairs in the
                  batch for the last LOOKBACK_HOURS.
    Round-trip 2: nothing — detection runs in memory.

    Returns a list of VelocityAlert (may be empty).
    """
    if not db or not flights:
        return []

    lookback_from = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).isoformat()

    # Collect unique origins to bound the query
    origins = list({f["origin"] for f in flights})

    try:
        resp = (
            db.table("price_snapshots")
            .select("origin, destination, departure_date, return_date, price")
            .in_("origin", origins)
            .gte("captured_at", lookback_from)
            .execute()
        )
    except Exception as e:
        logger.warning(f"detect_velocity_drops_bulk DB error: {e}")
        return []

    # Build an in-memory index: (origin, dest, dep, ret) → max_price seen
    history: dict[tuple, float] = defaultdict(float)
    for row in (resp.data or []):
        key = (
            row.get("origin", ""),
            row.get("destination", ""),
            row.get("departure_date", ""),
            row.get("return_date", ""),
        )
        try:
            history[key] = max(history[key], float(row["price"]))
        except (TypeError, ValueError):
            continue

    alerts: list[VelocityAlert] = []
    for flight in flights:
        try:
            dep_date = flight.get("departure_date") or flight.get("departure_at", "")[:10]
            ret_date = flight.get("return_date") or flight.get("return_at", "")[:10]
            current_price = float(flight["price"])
            key = (flight["origin"], flight["destination"], dep_date, ret_date)

            reference_price = history.get(key, 0.0)
            if reference_price <= 0 or current_price >= reference_price:
                continue

            drop_pct = (reference_price - current_price) / reference_price * 100

            if drop_pct >= VELOCITY_DROP_FARE_MISTAKE * 100:
                alert_level = "fare_mistake"
            elif drop_pct >= VELOCITY_DROP_FLASH_PROMO * 100:
                alert_level = "flash_promo"
            else:
                continue

            logger.info(
                f"Velocity drop: {flight['origin']}->{flight['destination']} {dep_date} "
                f"{reference_price:.0f}€ → {current_price:.0f}€ (-{drop_pct:.0f}%) [{alert_level}]"
            )
            alerts.append(VelocityAlert(
                origin=flight["origin"],
                destination=flight["destination"],
                departure_date=dep_date,
                return_date=ret_date,
                current_price=current_price,
                reference_price=reference_price,
                drop_pct=round(drop_pct, 1),
                alert_level=alert_level,
                airline=flight.get("airline", ""),
                source=flight.get("source", "tier1"),
            ))
        except (KeyError, TypeError, ValueError):
            continue

    return alerts


def purge_old_snapshots(db) -> int:
    """Delete price_snapshots older than 24 hours. Returns count deleted."""
    if not db:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        resp = (
            db.table("price_snapshots")
            .delete()
            .lt("captured_at", cutoff)
            .execute()
        )
        count = len(resp.data or [])
        if count:
            logger.info(f"Purged {count} old price_snapshots")
        return count
    except Exception as e:
        logger.warning(f"purge_old_snapshots failed: {e}")
        return 0
