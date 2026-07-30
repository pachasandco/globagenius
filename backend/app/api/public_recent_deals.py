"""Public round-trip showcase for the landing page.

The historical endpoint mixed rows from ``sent_alerts`` (where the trip shape
was not reliably available) with qualified flights. That allowed one-way floor
prices to dominate the marketing showcase. This router is registered before
that legacy route and deliberately exposes only verified round trips carrying
a real return date.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from fastapi import APIRouter

from app.config import IATA_TO_CITY
from app.db import db

router = APIRouter()

POOL_SIZE = 12
MIN_DISCOUNT_PCT = 40.0
PROVINCE_AIRPORTS = {"LYS", "MRS", "NCE", "BOD", "NTE", "TLS", "BSL"}
PARIS_AIRPORTS = {"CDG", "ORY", "BVA"}
FRENCH_ORIGINS = PARIS_AIRPORTS | PROVINCE_AIRPORTS
LONG_HAUL_DESTINATIONS = {
    "PUJ", "CUN", "JFK", "EWR", "YUL", "MIA", "LAX", "SFO", "BKK",
    "DXB", "MRU", "RUN", "PPT", "GIG", "EZE", "MLE", "SIN", "HKG",
    "NRT", "HND", "ICN", "BOM", "DEL", "CPT", "JNB", "BOG", "LIM",
}


def _safe_baseline(price: float, discount_pct: float, stored_baseline: object) -> int | None:
    """Return a commercially credible baseline for a displayed round trip."""
    try:
        baseline = float(stored_baseline or 0)
    except (TypeError, ValueError):
        baseline = 0
    if baseline > price:
        return round(baseline)
    if 0 < discount_pct < 95:
        implied = price / (1 - discount_pct / 100)
        if implied > price:
            return round(implied)
    return None


def build_round_trip_candidates(
    qualified_rows: Iterable[dict],
    raw_rows: Iterable[dict],
) -> list[dict]:
    """Join qualified rows to raw flights and reject non-round-trip records."""
    raw_by_id = {row.get("id"): row for row in raw_rows if row.get("id")}
    candidates: list[dict] = []

    for qualified in qualified_rows:
        flight = raw_by_id.get(qualified.get("item_id"))
        if not flight:
            continue

        trip_type = flight.get("trip_type") or qualified.get("trip_type") or "round_trip"
        return_date = flight.get("return_date")
        if trip_type != "round_trip" or not return_date:
            continue

        origin = flight.get("origin")
        destination = flight.get("destination")
        if not origin or not destination or origin not in FRENCH_ORIGINS:
            continue

        try:
            price = float(qualified.get("price") or 0)
            discount = float(qualified.get("discount_pct") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0 or discount < MIN_DISCOUNT_PCT or discount >= 95:
            continue

        baseline = _safe_baseline(price, discount, qualified.get("baseline_price"))
        if baseline is None:
            continue

        candidates.append({
            "destination": destination,
            "origin": origin,
            "origin_city": "Paris" if origin in PARIS_AIRPORTS else IATA_TO_CITY.get(origin, origin),
            "dest_city": IATA_TO_CITY.get(destination, destination),
            "price": round(price),
            "baseline": baseline,
            "discount_pct": round(discount),
            "trip_type": "round_trip",
            "return_date": return_date,
            "is_province": origin in PROVINCE_AIRPORTS,
            "is_long_haul": destination in LONG_HAUL_DESTINATIONS,
            "detected_at": qualified.get("created_at"),
        })

    return candidates


def _showcase_score(candidate: dict) -> int:
    """Rank real value without rewarding suspiciously tiny one-way-like prices."""
    score = int(candidate.get("discount_pct") or 0)
    if candidate.get("is_long_haul"):
        score += 15
    if candidate.get("is_province"):
        score += 5
    return score


def select_showcase_deals(candidates: Iterable[dict], limit: int = POOL_SIZE) -> list[dict]:
    """Deduplicate and balance the first cards across long haul and province."""
    best_by_destination: dict[str, dict] = {}
    for candidate in candidates:
        destination = candidate.get("destination")
        if not destination:
            continue
        existing = best_by_destination.get(destination)
        if existing is None or _showcase_score(candidate) > _showcase_score(existing):
            best_by_destination[destination] = candidate

    ranked = sorted(best_by_destination.values(), key=_showcase_score, reverse=True)
    long_haul = [item for item in ranked if item.get("is_long_haul")]
    province = [item for item in ranked if item.get("is_province")]

    selected: list[dict] = []
    seen_destinations: set[str] = set()

    def add(item: dict | None) -> None:
        if not item or len(selected) >= limit:
            return
        destination = item.get("destination")
        if not destination or destination in seen_destinations:
            return
        seen_destinations.add(destination)
        selected.append(item)

    # The first six cards are the part most visitors see. Keep them varied and
    # representative of the product rather than six ultra-cheap European fares.
    first_six_sources = [
        long_haul[0] if len(long_haul) > 0 else None,
        province[0] if len(province) > 0 else None,
        ranked[0] if len(ranked) > 0 else None,
        long_haul[1] if len(long_haul) > 1 else None,
        province[1] if len(province) > 1 else None,
        ranked[1] if len(ranked) > 1 else None,
    ]
    for item in first_six_sources:
        add(item)

    for item in ranked:
        add(item)
        if len(selected) >= limit:
            break

    return selected


@router.get("/api/stats/recent-deals")
def recent_round_trip_deals():
    """Return only genuine round trips for landing proof and hero cards."""
    if not db:
        return {"deals": []}

    now = datetime.now(timezone.utc)
    cutoff_90d = (now - timedelta(days=90)).isoformat()
    cutoff_30d = now - timedelta(days=30)

    try:
        qualified_rows = (
            db.table("qualified_items")
            .select("item_id,price,baseline_price,discount_pct,created_at,trip_type")
            .eq("type", "flight")
            .gte("created_at", cutoff_90d)
            .gte("discount_pct", MIN_DISCOUNT_PCT)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )
    except Exception:
        return {"deals": []}

    item_ids = [row.get("item_id") for row in qualified_rows if row.get("item_id")]
    if not item_ids:
        return {"deals": []}

    try:
        raw_rows = (
            db.table("raw_flights")
            .select("id,origin,destination,return_date,trip_type,direction")
            .in_("id", item_ids)
            .execute()
            .data
            or []
        )
    except Exception:
        return {"deals": []}

    candidates = build_round_trip_candidates(qualified_rows, raw_rows)

    recent: list[dict] = []
    older: list[dict] = []
    for candidate in candidates:
        detected_at = candidate.get("detected_at")
        try:
            detected = datetime.fromisoformat(str(detected_at).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            detected = datetime.min.replace(tzinfo=timezone.utc)
        (recent if detected >= cutoff_30d else older).append(candidate)

    pool = select_showcase_deals(recent, POOL_SIZE)
    if len(pool) < POOL_SIZE:
        used = {item["destination"] for item in pool}
        supplements = select_showcase_deals(
            [item for item in older if item.get("destination") not in used],
            POOL_SIZE - len(pool),
        )
        pool.extend(supplements)

    return {"deals": pool[:POOL_SIZE]}
