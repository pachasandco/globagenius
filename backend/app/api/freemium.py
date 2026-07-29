"""Freemium account status, teasers and the monthly deal joker."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.routes import _get_user_tier, get_current_user
from app.db import db
from app.freemium_policy import (
    FREEMIUM_EXCEPTIONAL_ALERTS_PER_MONTH,
    FREEMIUM_EXCEPTIONAL_MIN_DISCOUNT_PCT,
    FREEMIUM_MONTHLY_UNLOCKS,
    FREEMIUM_REGULAR_ALERTS_PER_WEEK,
)

router = APIRouter()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _user_id(user: dict) -> str:
    value = user.get("sub") or user.get("user_id")
    if not value:
        raise HTTPException(status_code=401, detail="Authentification requise")
    return value


def _last_unlock(user_id: str) -> datetime | None:
    if not db:
        return None
    response = (
        db.table("sent_alerts")
        .select("created_at")
        .eq("user_id", user_id)
        .like("alert_key", "funlock:%")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _parse_dt(response.data[0].get("created_at"))


@router.get("/api/account/plan")
def account_plan(user: dict = Depends(get_current_user)):
    """Return the effective plan and user-facing Freemium allowances."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    user_id = _user_id(user)
    user_response = (
        db.table("users")
        .select("badge,badge_number")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    user_row = user_response.data[0] if user_response.data else {}
    grant_response = (
        db.table("premium_grants")
        .select("granted_by,expires_at,revoked,reason")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    grant = grant_response.data[0] if grant_response.data else {}
    is_premium = _get_user_tier(user_id) == "premium"
    is_og = bool(user_row.get("badge"))
    expires_at = _parse_dt(grant.get("expires_at"))

    if is_og:
        plan = "og"
        label = "Premium OG"
    elif is_premium and grant.get("granted_by") == "auto_premium_trial":
        plan = "premium_trial"
        label = "Premium Découverte"
    elif is_premium:
        plan = "premium"
        label = "Premium"
    else:
        plan = "freemium"
        label = "Freemium"

    unlock_used_at = _last_unlock(user_id)
    unlock_available_at = (
        unlock_used_at + timedelta(days=30) if unlock_used_at else datetime.now(timezone.utc)
    )

    return {
        "plan": plan,
        "label": label,
        "is_premium": is_premium,
        "is_og": is_og,
        "badge_number": user_row.get("badge_number"),
        "trial_expires_at": expires_at.isoformat() if plan == "premium_trial" and expires_at else None,
        "freemium": {
            "primary_airports": 1,
            "regular_alerts_per_week": FREEMIUM_REGULAR_ALERTS_PER_WEEK,
            "exceptional_alerts_per_month": FREEMIUM_EXCEPTIONAL_ALERTS_PER_MONTH,
            "monthly_unlocks": FREEMIUM_MONTHLY_UNLOCKS,
            "unlock_available": is_premium or unlock_available_at <= datetime.now(timezone.utc),
            "unlock_available_at": unlock_available_at.isoformat(),
        },
    }


@router.get("/api/freemium/teasers")
def freemium_teasers(limit: int = 12, user: dict = Depends(get_current_user)):
    """Show actionable proof without exposing exact price, dates or link."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    user_id = _user_id(user)
    preferences_response = (
        db.table("user_preferences")
        .select("airport_codes,blocked_destinations")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    preferences = preferences_response.data[0] if preferences_response.data else {}
    airports = preferences.get("airport_codes") or ["CDG"]
    primary_airport = airports[0] if airports else "CDG"
    blocked = set(preferences.get("blocked_destinations") or [])

    freshness_cutoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    qualified_response = (
        db.table("qualified_items")
        .select("id,item_id,discount_pct,score,price,baseline_price,created_at")
        .eq("status", "active")
        .eq("type", "flight")
        .eq("trip_type", "round_trip")
        .gte("discount_pct", FREEMIUM_EXCEPTIONAL_MIN_DISCOUNT_PCT)
        .gte("reverified_at", freshness_cutoff)
        .order("score", desc=True)
        .limit(max(limit * 4, 20))
        .execute()
    )
    qualified = qualified_response.data or []
    item_ids = [row.get("item_id") for row in qualified if row.get("item_id")]
    if not item_ids:
        return {"items": [], "plan": "premium" if _get_user_tier(user_id) == "premium" else "freemium"}

    flight_response = (
        db.table("raw_flights")
        .select("id,origin,destination,trip_type")
        .in_("id", item_ids)
        .execute()
    )
    flights = {row.get("id"): row for row in (flight_response.data or [])}

    items = []
    seen_routes: set[str] = set()
    for deal in qualified:
        flight = flights.get(deal.get("item_id")) or {}
        origin = flight.get("origin") or ""
        destination = flight.get("destination") or ""
        if origin != primary_airport or not destination or destination in blocked:
            continue
        route_key = f"{origin}-{destination}"
        if route_key in seen_routes:
            continue
        seen_routes.add(route_key)
        price = float(deal.get("price") or 0)
        baseline = float(deal.get("baseline_price") or 0)
        estimated_savings = max(0, round(baseline - price)) if baseline and price else None
        items.append(
            {
                "id": deal.get("id"),
                "origin": origin,
                "destination": destination,
                "discount_pct": int(round(float(deal.get("discount_pct") or 0))),
                "estimated_savings_eur": estimated_savings,
                "locked": _get_user_tier(user_id) != "premium",
            }
        )
        if len(items) >= max(1, min(limit, 24)):
            break

    plan = "premium" if _get_user_tier(user_id) == "premium" else "freemium"
    return {"items": items, "plan": plan}


@router.post("/api/freemium/unlock/{deal_id}")
def unlock_deal(deal_id: str, user: dict = Depends(get_current_user)):
    """Consume the monthly joker and return the selected deal in full."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    user_id = _user_id(user)
    is_premium = _get_user_tier(user_id) == "premium"
    now = datetime.now(timezone.utc)
    last_unlock = _last_unlock(user_id)
    if not is_premium and last_unlock and last_unlock + timedelta(days=30) > now:
        next_date = (last_unlock + timedelta(days=30)).isoformat()
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Votre joker mensuel a déjà été utilisé.",
                "available_at": next_date,
            },
        )

    qualified_response = (
        db.table("qualified_items")
        .select("id,item_id,discount_pct,score,price,baseline_price,status")
        .eq("id", deal_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if not qualified_response.data:
        raise HTTPException(status_code=404, detail="Ce deal n'est plus disponible")
    deal = qualified_response.data[0]

    flight_response = (
        db.table("raw_flights")
        .select(
            "id,origin,destination,departure_date,return_date,airline,stops,"
            "source_url,trip_duration_days,duration_minutes,trip_type,direction"
        )
        .eq("id", deal.get("item_id"))
        .limit(1)
        .execute()
    )
    if not flight_response.data:
        raise HTTPException(status_code=404, detail="Les détails de ce vol ne sont plus disponibles")
    flight = flight_response.data[0]

    if not is_premium:
        preferences_response = (
            db.table("user_preferences")
            .select("telegram_chat_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        chat_id = 0
        if preferences_response.data:
            chat_id = preferences_response.data[0].get("telegram_chat_id") or 0
        db.table("sent_alerts").insert(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "alert_key": f"funlock:{deal_id}",
                "destination": flight.get("destination"),
                "alert_type": "flight",
                "price": deal.get("price"),
                "discount_pct": deal.get("discount_pct"),
            }
        ).execute()

    return {
        "unlocked": True,
        "consumed_joker": not is_premium,
        "deal": {
            "id": deal.get("id"),
            "origin": flight.get("origin"),
            "destination": flight.get("destination"),
            "departure_date": flight.get("departure_date"),
            "return_date": flight.get("return_date"),
            "airline": flight.get("airline"),
            "stops": flight.get("stops"),
            "trip_duration_days": flight.get("trip_duration_days"),
            "duration_minutes": flight.get("duration_minutes"),
            "trip_type": flight.get("trip_type") or "round_trip",
            "price": deal.get("price"),
            "baseline_price": deal.get("baseline_price"),
            "discount_pct": deal.get("discount_pct"),
            "source_url": flight.get("source_url"),
        },
    }
