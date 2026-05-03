"""Tiny utilities shared across Stripe-touching code (webhook + sync job)."""


def stripe_subscription_period_end(sub) -> int | None:
    """Return the current_period_end timestamp from a Stripe Subscription
    or subscription event payload.

    Stripe moved this field from the subscription root to subscription.items
    in API version 2025-03-31. We read either shape so the code keeps working
    across API versions and avoids a null premium_expires_at after signup.

    Accepts both stripe-python objects (attribute access) and plain dicts
    (the event payload arrives as a dict).
    """
    period_end = _read(sub, "current_period_end")
    if period_end:
        return period_end

    items = _read(sub, "items")
    if not items:
        return None

    items_data = _read(items, "data")
    if not items_data:
        return None

    return _read(items_data[0], "current_period_end")


def _read(obj, key):
    """Read a key from either a dict or a stripe-python attr-style object."""
    if hasattr(obj, "get"):
        return obj.get(key)
    return getattr(obj, key, None)
