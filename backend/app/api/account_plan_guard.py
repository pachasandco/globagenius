"""Normalized account-plan endpoint registered before the base Freemium router."""

from fastapi import APIRouter, Depends

from app.api.freemium import account_plan as _account_plan
from app.api.preferences_freemium import normalize_free_subscriptions
from app.api.routes import get_current_user

router = APIRouter()


@router.get("/api/account/plan")
def account_plan_guarded(user: dict = Depends(get_current_user)):
    """Return the effective plan after the definitive Freemium cutover."""
    result = _account_plan(user)
    user_id = user.get("sub") or user.get("user_id")
    result["trial_available"] = False
    result["trial_expires_at"] = None

    if user_id and result.get("plan") == "freemium":
        normalize_free_subscriptions(user_id)

    return result
