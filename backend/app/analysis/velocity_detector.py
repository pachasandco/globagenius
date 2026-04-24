"""Velocity-based mistake fare detector.

Detects prices that have dropped sharply within a short time window — the
signature of an airline pricing error (mistake fare).

Algorithm:
  1. Store every Tier 1 price observation in price_snapshots (called by job_scrape_tier1).
  2. For each new price, look back 2 hours in price_snapshots for the same
     (origin, destination, departure_date, return_date).
  3. If current_price < reference_price × VELOCITY_DROP_THRESHOLD:
     → Emit a VelocityAlert with severity proportional to the drop.

Thresholds (tuned from industry data — mistake fares typically drop 50-90%):
  FARE_MISTAKE  : drop ≥ 60% in < 2h  (z_score override: always FARE_MISTAKE)
  FLASH_PROMO   : drop ≥ 40% in < 2h
  Ignored       : drop < 40%           (normal price fluctuation)

Integration:
  - Called from job_scrape_tier1 for every new Tier 1 flight.
  - VelocityAlerts bypass the normal z-score pipeline and go straight to
    reverify → dispatch, since speed is critical (deals last 2-8h max).
  - Deduplication still applies via sent_alerts table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# A price must drop by at least this fraction to trigger an alert
VELOCITY_DROP_FLASH_PROMO = 0.40   # 40% drop → FLASH_PROMO
VELOCITY_DROP_FARE_MISTAKE = 0.60  # 60% drop → FARE_MISTAKE

# Look-back window: compare current price against highest price in last N hours
LOOKBACK_HOURS = 2


@dataclass
class VelocityAlert:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    current_price: float
    reference_price: float   # highest price seen in the lookback window
    drop_pct: float          # (reference - current) / reference * 100
    alert_level: str         # "fare_mistake" or "flash_promo"
    airline: str
    source: str


def save_snapshot(db, flight: dict) -> bool:
    """Persist a price snapshot for a Tier 1 flight.

    Called on every Tier 1 scrape. Returns True on success."""
    if not db:
        return False
    try:
        db.table("price_snapshots").insert({
            "origin": flight["origin"],
            "destination": flight["destination"],
            "departure_date": flight.get("departure_date") or flight.get("departure_at", "")[:10],
            "return_date": flight.get("return_date") or flight.get("return_at", "")[:10],
            "price": float(flight["price"]),
            "airline": flight.get("airline", ""),
            "source": flight.get("source", "tier1"),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        logger.warning(f"save_snapshot failed for {flight.get('origin')}->{flight.get('destination')}: {e}")
        return False


def detect_velocity_drop(db, flight: dict) -> VelocityAlert | None:
    """Check if this flight's price has dropped sharply vs the last 2 hours.

    Queries price_snapshots for (origin, destination, departure_date, return_date)
    in the last LOOKBACK_HOURS. Returns a VelocityAlert if a significant drop
    is detected, None otherwise.

    Returns None (not a mistake fare signal) if:
    - No prior snapshots exist for this route + date (cold start)
    - The price drop is below VELOCITY_DROP_FLASH_PROMO
    - Any DB error
    """
    if not db:
        return None

    origin = flight["origin"]
    destination = flight["destination"]
    dep_date = flight.get("departure_date") or flight.get("departure_at", "")[:10]
    ret_date = flight.get("return_date") or flight.get("return_at", "")[:10]
    current_price = float(flight["price"])

    lookback_from = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).isoformat()

    try:
        resp = (
            db.table("price_snapshots")
            .select("price, captured_at")
            .eq("origin", origin)
            .eq("destination", destination)
            .eq("departure_date", dep_date)
            .eq("return_date", ret_date)
            .gte("captured_at", lookback_from)
            .order("captured_at", desc=False)
            .execute()
        )
    except Exception as e:
        logger.warning(f"velocity_detector DB error for {origin}->{destination}: {e}")
        return None

    snapshots = resp.data or []
    if not snapshots:
        return None  # No history yet — can't detect velocity

    # Reference price: the HIGHEST price seen in the lookback window
    # (we want to catch the moment a price drops from a stable high)
    reference_price = max(float(s["price"]) for s in snapshots)

    if reference_price <= 0 or current_price >= reference_price:
        return None  # Price went up or stayed the same

    drop_pct = (reference_price - current_price) / reference_price * 100

    if drop_pct >= VELOCITY_DROP_FARE_MISTAKE * 100:
        alert_level = "fare_mistake"
    elif drop_pct >= VELOCITY_DROP_FLASH_PROMO * 100:
        alert_level = "flash_promo"
    else:
        return None  # Drop too small to be a mistake fare

    logger.info(
        f"Velocity drop detected: {origin}->{destination} {dep_date} "
        f"{reference_price}€ → {current_price}€ (-{drop_pct:.0f}%) [{alert_level}]"
    )

    return VelocityAlert(
        origin=origin,
        destination=destination,
        departure_date=dep_date,
        return_date=ret_date,
        current_price=current_price,
        reference_price=reference_price,
        drop_pct=round(drop_pct, 1),
        alert_level=alert_level,
        airline=flight.get("airline", ""),
        source=flight.get("source", "tier1"),
    )


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
