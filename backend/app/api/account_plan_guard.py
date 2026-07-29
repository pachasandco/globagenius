"""Normalized account-plan endpoint registered before the base Freemium router."""

from fastapi import APIRouter, Depends

from app.api.freemium import account_plan as _account_plan
from app.api.preferences_freemium import (
    has_pending_premium_trial,
    normalize_free_subscriptions,
)
from app.api.routes import get_current_user

router = APIRouter()


@router.get("/api/account/plan")
def account_plan_guarded(user: dict = Depends(get_current_user)):
    """Return plan status and apply the Freemium cutover after trial expiry."""
    result = _account_plan(user)
    user_id = user.get("sub") or user.get("user_id")
    pending_trial = bool(user_id and has_pending_premium_trial(user_id))
    result["trial_available"] = pending_trial

    if user_id and result.get("plan") == "freemium" and not pending_trial:
        normalize_free_subscriptions(user_id)

    return result
