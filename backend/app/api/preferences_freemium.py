"""Freemium-aware preference update route.

Registered before the historical API router so the same public URL keeps working
while entitlements are normalized before the existing persistence logic runs.
"""

import logging

from fastapi import APIRouter, Depends

from app.api.routes import (
    PreferencesRequest,
    _get_user_tier,
    get_current_user,
    update_preferences as _update_preferences,
)
from app.db import db

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_free_subscriptions(user_id: str, primary_airport: str | None = None) -> None:
    """Keep exactly one Telegram subscription for an effective Freemium account."""
    if not db:
        return

    if not primary_airport:
        prefs = (
            db.table("user_preferences")
            .select("airport_codes")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not prefs.data:
            return
        airports = prefs.data[0].get("airport_codes") or []
        primary_airport = airports[0] if airports else "CDG"

    subscriptions = (
        db.table("telegram_subscribers")
        .select("airport_code")
        .eq("user_id", user_id)
        .execute()
    )
    for row in subscriptions.data or []:
        airport = row.get("airport_code")
        if airport and airport != primary_airport:
            db.table("telegram_subscribers").delete().eq("user_id", user_id).eq(
                "airport_code", airport
            ).execute()

    db.table("user_preferences").update(
        {
            "airport_codes": [primary_airport],
            "flight_trip_types": ["round_trip"],
            "include_split_tickets": False,
        }
    ).eq("user_id", user_id).execute()


def normalize_all_free_subscriptions() -> int:
    """Repair all Freemium accounts after the end of Premium trials."""
    if not db:
        return 0
    users = db.table("users").select("id").execute().data or []
    normalized = 0
    for row in users:
        user_id = row.get("id")
        if not user_id:
            continue
        try:
            if _get_user_tier(user_id) == "free":
                normalize_free_subscriptions(user_id)
                normalized += 1
        except Exception as exc:
            logger.warning("Free subscription normalization failed for %s: %s", user_id, exc)
    logger.info("Normalized Freemium subscriptions for %s users", normalized)
    return normalized


@router.put("/api/users/{user_id}/preferences")
def update_preferences_freemium(
    user_id: str,
    req: PreferencesRequest,
    user: dict = Depends(get_current_user),
):
    """Apply current plan limits, then reuse the established update route."""
    tier = _get_user_tier(user_id)
    effective_request = req

    if tier == "free":
        primary = req.airport_codes[0] if req.airport_codes else "CDG"
        effective_request = req.model_copy(
            update={
                "airport_codes": [primary],
                "flight_trip_types": ["round_trip"],
                "include_split_tickets": False,
                "deal_tier": "regular",
                "min_discount": None,
            }
        )

    result = _update_preferences(user_id, effective_request, user)
    if tier == "free":
        primary = effective_request.airport_codes[0] if effective_request.airport_codes else "CDG"
        normalize_free_subscriptions(user_id, primary)
        refreshed = (
            db.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ) if db else None
        if refreshed and refreshed.data:
            return refreshed.data[0]
    return result
