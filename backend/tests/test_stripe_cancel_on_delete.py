"""V9: tests for the Stripe-subscription cancellation that runs before
account deletion (both user-initiated and admin-initiated).

The bug being fixed: account deletion used to nuke the user row from
the DB without ever telling Stripe. The subscription kept renewing and
billing the now-deleted user — guaranteed dispute, RGPD-non-compliant.

These tests pin down the helper's invariants:
  - returns cleanly when the user has no subscription
  - returns cleanly when STRIPE_SECRET_KEY is missing
  - calls stripe.Subscription.cancel(sub_id) when both are present
  - swallows Stripe errors so a Stripe outage doesn't block deletion
"""
from unittest.mock import MagicMock, patch

import pytest


def _db_with_user_prefs(prefs_data: list | None):
    """Build a db mock whose user_preferences select returns prefs_data."""
    db = MagicMock()

    def _table(name: str):
        t = MagicMock()
        if name == "user_preferences":
            chain = (
                t.select.return_value
                .eq.return_value
            )
            chain.execute.return_value = MagicMock(data=prefs_data or [])
        return t

    db.table.side_effect = _table
    return db


def test_cancel_returns_no_subscription_when_user_has_none():
    """A free user with no stripe_subscription_id → no Stripe call."""
    from app.api import routes

    db_mock = _db_with_user_prefs([
        {"stripe_subscription_id": None, "stripe_customer_id": None},
    ])
    cancel_spy = MagicMock()
    with patch.object(routes, "db", db_mock), \
         patch("stripe.Subscription.cancel", cancel_spy), \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test_x"):
        result = routes._cancel_stripe_subscription_for_user("u1")

    assert result["had_subscription"] is False
    assert result["cancelled"] is False
    cancel_spy.assert_not_called()


def test_cancel_returns_no_subscription_when_user_not_in_db():
    """A user_id with no row at all → no error, no call."""
    from app.api import routes

    db_mock = _db_with_user_prefs([])
    with patch.object(routes, "db", db_mock), \
         patch("stripe.Subscription.cancel") as cancel_spy:
        result = routes._cancel_stripe_subscription_for_user("ghost")

    assert result["had_subscription"] is False
    cancel_spy.assert_not_called()


def test_cancel_calls_stripe_when_user_has_active_subscription():
    """The happy path. user has stripe_subscription_id → we cancel it."""
    from app.api import routes

    db_mock = _db_with_user_prefs([
        {"stripe_subscription_id": "sub_abc123", "stripe_customer_id": "cus_xxx"},
    ])
    with patch.object(routes, "db", db_mock), \
         patch("stripe.Subscription.cancel") as cancel_spy, \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test_x"):
        cancel_spy.return_value = MagicMock(id="sub_abc123", status="canceled")
        result = routes._cancel_stripe_subscription_for_user("u1")

    cancel_spy.assert_called_once_with("sub_abc123")
    assert result["had_subscription"] is True
    assert result["cancelled"] is True
    assert result["subscription_id"] == "sub_abc123"
    assert result["error"] is None


def test_cancel_does_not_raise_when_stripe_invalid_request():
    """Subscription already cancelled / not found → log & return,
    don't propagate. Account deletion must still go through."""
    from app.api import routes
    import stripe as stripe_module

    db_mock = _db_with_user_prefs([
        {"stripe_subscription_id": "sub_zombie", "stripe_customer_id": "cus_x"},
    ])
    err = stripe_module.error.InvalidRequestError("No such subscription", "sub_id")
    with patch.object(routes, "db", db_mock), \
         patch("stripe.Subscription.cancel", side_effect=err), \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test_x"):
        result = routes._cancel_stripe_subscription_for_user("u1")

    assert result["had_subscription"] is True
    assert result["cancelled"] is False
    assert result["error"]
    assert "stripe_invalid" in result["error"]


def test_cancel_does_not_raise_when_stripe_unknown_error():
    """Network / 5xx / unexpected exception → swallowed."""
    from app.api import routes

    db_mock = _db_with_user_prefs([
        {"stripe_subscription_id": "sub_test", "stripe_customer_id": "cus_x"},
    ])
    with patch.object(routes, "db", db_mock), \
         patch("stripe.Subscription.cancel", side_effect=RuntimeError("boom")), \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test_x"):
        result = routes._cancel_stripe_subscription_for_user("u1")

    assert result["cancelled"] is False
    assert "stripe_unknown" in (result["error"] or "")


def test_cancel_returns_no_stripe_key_when_secret_unset():
    """If STRIPE_SECRET_KEY is empty (dev / misconfigured prod) we
    refuse to call Stripe but still return cleanly."""
    from app.api import routes

    db_mock = _db_with_user_prefs([
        {"stripe_subscription_id": "sub_xxx", "stripe_customer_id": "cus_x"},
    ])
    with patch.object(routes, "db", db_mock), \
         patch("stripe.Subscription.cancel") as cancel_spy, \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", ""):
        result = routes._cancel_stripe_subscription_for_user("u1")

    cancel_spy.assert_not_called()
    assert result["had_subscription"] is True
    assert result["cancelled"] is False
    assert result["error"] == "no_stripe_key"
