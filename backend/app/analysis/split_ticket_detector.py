"""Detect when 2x one-way is cheaper than the equivalent round-trip.

For each (origin, destination) in the curated top routes, we:

1. Pull recent one-way fares in both directions from `raw_flights`.
2. Pair an outbound and inbound on the same day-pair (return ≥ 4 days
   after departure, ≤ 14 days for sanity).
3. Look up the cheapest round-trip on the exact same day-pair.
4. Qualify the pair if:
     savings_pct >= 15% AND savings_eur >= 100€

Persists to qualified_items with deal_subtype='split_ticket' and a
metadata payload describing both legs.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from app.db import db
from app.config import settings
from app.notifications.aviasales import build_aviasales_url_oneway

logger = logging.getLogger(__name__)

MIN_SAVINGS_PCT = 15.0
MIN_SAVINGS_EUR = 100.0
MIN_NIGHTS = 4
MAX_NIGHTS = 14
LOOKBACK_HOURS = 24


def _build_legs_metadata(out: dict, inb: dict, rt_price: float, savings: float) -> dict:
    out_url = out.get("source_url") or build_aviasales_url_oneway(
        out["origin"], out["destination"], out["departure_date"],
        marker=settings.TRAVELPAYOUTS_MARKER or None,
    )
    in_url = inb.get("source_url") or build_aviasales_url_oneway(
        inb["origin"], inb["destination"], inb["departure_date"],
        marker=settings.TRAVELPAYOUTS_MARKER or None,
    )
    return {
        "outbound": {
            "airline": out.get("airline"),
            "price": float(out["price"]),
            "departure_date": out["departure_date"],
            "booking_url": out_url,
        },
        "inbound": {
            "airline": inb.get("airline"),
            "price": float(inb["price"]),
            "departure_date": inb["departure_date"],
            "booking_url": in_url,
        },
        "roundtrip_equivalent_price": round(float(rt_price), 2),
        "savings_eur": round(float(savings), 2),
        "savings_pct": round(savings / float(rt_price) * 100, 1),
    }


def detect_split_tickets_for_route(origin: str, destination: str) -> list[dict]:
    """Return qualified split-ticket dicts ready for upsert into qualified_items."""
    if not db:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).isoformat()

    try:
        out_resp = (
            db.table("raw_flights")
            .select("id, origin, destination, departure_date, price, airline, source_url")
            .eq("origin", origin)
            .eq("destination", destination)
            .eq("trip_type", "oneway")
            .gte("scraped_at", cutoff)
            .execute()
        )
        in_resp = (
            db.table("raw_flights")
            .select("id, origin, destination, departure_date, price, airline, source_url")
            .eq("origin", destination)
            .eq("destination", origin)
            .eq("trip_type", "oneway")
            .gte("scraped_at", cutoff)
            .execute()
        )
        rt_resp = (
            db.table("raw_flights")
            .select("id, departure_date, return_date, price")
            .eq("origin", origin)
            .eq("destination", destination)
            .eq("trip_type", "roundtrip")
            .gte("scraped_at", cutoff)
            .execute()
        )
    except Exception as e:
        logger.warning(f"split_ticket fetch failed {origin}->{destination}: {e}")
        return []

    outbounds = out_resp.data or []
    inbounds = in_resp.data or []
    roundtrips = rt_resp.data or []

    # Cheapest round-trip per (departure_date, return_date)
    rt_by_dates: dict[tuple[str, str], float] = {}
    for rt in roundtrips:
        dep = (rt.get("departure_date") or "")[:10]
        ret = (rt.get("return_date") or "")[:10]
        if not dep or not ret:
            continue
        price = float(rt.get("price") or 0)
        if price <= 0:
            continue
        key = (dep, ret)
        if key not in rt_by_dates or price < rt_by_dates[key]:
            rt_by_dates[key] = price

    # Cheapest outbound per departure_date
    cheapest_out: dict[str, dict] = {}
    for o in outbounds:
        dep = (o.get("departure_date") or "")[:10]
        if not dep:
            continue
        price = float(o.get("price") or 0)
        if price <= 0:
            continue
        existing = cheapest_out.get(dep)
        if not existing or price < float(existing["price"]):
            cheapest_out[dep] = o

    # Cheapest inbound per departure_date
    cheapest_in: dict[str, dict] = {}
    for i in inbounds:
        dep = (i.get("departure_date") or "")[:10]
        if not dep:
            continue
        price = float(i.get("price") or 0)
        if price <= 0:
            continue
        existing = cheapest_in.get(dep)
        if not existing or price < float(existing["price"]):
            cheapest_in[dep] = i

    qualified: list[dict] = []
    for (rt_dep, rt_ret), rt_price in rt_by_dates.items():
        try:
            d_dep = datetime.strptime(rt_dep, "%Y-%m-%d")
            d_ret = datetime.strptime(rt_ret, "%Y-%m-%d")
        except ValueError:
            continue
        nights = (d_ret - d_dep).days
        if nights < MIN_NIGHTS or nights > MAX_NIGHTS:
            continue

        out = cheapest_out.get(rt_dep)
        inb = cheapest_in.get(rt_ret)
        if not out or not inb:
            continue

        split_total = float(out["price"]) + float(inb["price"])
        savings = float(rt_price) - split_total
        if savings < MIN_SAVINGS_EUR:
            continue
        if savings / float(rt_price) * 100 < MIN_SAVINGS_PCT:
            continue

        metadata = _build_legs_metadata(out, inb, rt_price, savings)
        qualified.append({
            "outbound_flight_id": out["id"],
            "split_total": split_total,
            "rt_price": rt_price,
            "savings": savings,
            "discount_pct": round(savings / float(rt_price) * 100, 2),
            "metadata": metadata,
            "departure_date": rt_dep,
            "return_date": rt_ret,
            "origin": origin,
            "destination": destination,
        })

    return qualified


def upsert_split_qualified_items(qualified: list[dict]) -> int:
    """Persist split-ticket detections to qualified_items.

    item_id references the outbound raw_flights row; the inbound is captured
    inside `metadata`. Score is the savings_pct rounded to int."""
    if not db or not qualified:
        return 0
    inserted = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for q in qualified:
        try:
            row = {
                "type": "flight",
                "deal_subtype": "split_ticket",
                "item_id": q["outbound_flight_id"],
                "price": round(q["split_total"], 2),
                "baseline_price": round(q["rt_price"], 2),
                "discount_pct": q["discount_pct"],
                "score": int(q["discount_pct"]),
                "status": "active",
                "metadata": q["metadata"],
                "reverified_at": now_iso,
            }
            db.table("qualified_items").upsert(
                row, on_conflict="item_id"
            ).execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to upsert split_ticket: {e}")
    return inserted
