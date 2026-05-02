"""V9: tests for the two webhook events that revoke premium access.

Audit found the webhook handled checkout.session.completed and
customer.subscription.updated/deleted, but NOT charge.refunded or
invoice.payment_failed. Without those:
  - A user requesting their 30-day refund kept premium until the next
    nightly sync (could keep accessing premium content for 24h+).
  - A user whose card expired kept premium during Stripe's dunning
    grace period (3-7 days).

These tests pin the new behaviour: each event flips is_premium to
False and stamps premium_expires_at to "now" so the next request
correctly downgrades the user.
"""
from unittest.mock import MagicMock, patch

import pytest


def _build_db_capturing_updates():
    """Tiny db mock that captures every user_preferences UPDATE payload
    so the test can assert what was written without re-implementing
    the supabase chain."""
    captured: list[dict] = []
    db = MagicMock()

    def _table(name):
        t = MagicMock()
        if name == "user_preferences":
            def _update(payload):
                captured.append(payload)
                upd = MagicMock()
                upd_eq = MagicMock()
                upd_eq.execute.return_value = MagicMock(data=[payload])
                upd.eq.return_value = upd_eq
                return upd
            t.update.side_effect = _update
        return t

    db.table.side_effect = _table
    return db, captured


@pytest.mark.asyncio
async def test_charge_refunded_revokes_premium_immediately():
    """V9: a charge.refunded event flips is_premium=False and pins
    premium_expires_at to now. No grace period for refunds."""
    from app.api import routes
    from fastapi import Request

    db_mock, captured = _build_db_capturing_updates()

    # Build a Stripe event payload as the API would deliver it.
    fake_event = {
        "type": "charge.refunded",
        "data": {"object": {"customer": "cus_refund123"}},
    }
    body_bytes = b'{"fake": "payload"}'

    # Mock the request object minimally
    req = MagicMock(spec=Request)
    async def _body():
        return body_bytes
    req.body = _body
    req.headers = {"stripe-signature": "fake_sig"}

    with patch.object(routes, "db", db_mock), \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test"), \
         patch.object(routes.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"), \
         patch("stripe.Webhook.construct_event", return_value=fake_event):
        await routes.stripe_webhook(req)

    assert len(captured) == 1, "Expected exactly one user_preferences update"
    payload = captured[0]
    assert payload["is_premium"] is False
    assert "premium_expires_at" in payload
    assert payload["premium_expires_at"]  # non-empty ISO timestamp


@pytest.mark.asyncio
async def test_invoice_payment_failed_revokes_premium_immediately():
    """V9: a failed renewal payment must downgrade immediately so the
    user doesn't keep premium during Stripe's dunning grace period."""
    from app.api import routes
    from fastapi import Request

    db_mock, captured = _build_db_capturing_updates()

    fake_event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_failed456"}},
    }
    body_bytes = b'{}'
    req = MagicMock(spec=Request)
    async def _body():
        return body_bytes
    req.body = _body
    req.headers = {"stripe-signature": "fake_sig"}

    with patch.object(routes, "db", db_mock), \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test"), \
         patch.object(routes.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"), \
         patch("stripe.Webhook.construct_event", return_value=fake_event):
        await routes.stripe_webhook(req)

    assert len(captured) == 1
    payload = captured[0]
    assert payload["is_premium"] is False
    assert payload["premium_expires_at"]


@pytest.mark.asyncio
async def test_unknown_event_type_is_ignored_without_db_writes():
    """A Stripe event we don't handle (e.g. invoice.upcoming) must be a
    no-op — no DB update, no exception."""
    from app.api import routes
    from fastapi import Request

    db_mock, captured = _build_db_capturing_updates()

    fake_event = {
        "type": "invoice.upcoming",
        "data": {"object": {"customer": "cus_anything"}},
    }
    req = MagicMock(spec=Request)
    async def _body():
        return b"{}"
    req.body = _body
    req.headers = {"stripe-signature": "fake_sig"}

    with patch.object(routes, "db", db_mock), \
         patch.object(routes.settings, "STRIPE_SECRET_KEY", "sk_test"), \
         patch.object(routes.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"), \
         patch("stripe.Webhook.construct_event", return_value=fake_event):
        result = await routes.stripe_webhook(req)

    assert captured == []
    assert result == {"ok": True}
