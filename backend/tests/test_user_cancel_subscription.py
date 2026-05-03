"""Tests for the user-initiated subscription cancellation endpoint.

Reuses the helper _cancel_stripe_subscription_for_user(user_id) added
in cc7d1ac. Difference vs delete_account: the user keeps their account,
they just don't pay anymore. The underlying Stripe call is the same,
so we can rely on the helper's existing test coverage and only assert
the endpoint glue: auth, idempotency, response shape.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _client_with_auth(user_id: str = "u1"):
    """Spin up a TestClient and patch get_current_user to return user_id."""
    from app.main import app
    from app.api import routes

    async def fake_get_current_user():
        return {"sub": user_id, "user_id": user_id}

    app.dependency_overrides[routes.get_current_user] = fake_get_current_user
    return TestClient(app)


def test_cancel_subscription_requires_auth():
    """Unauthenticated requests are 401, never reach the helper."""
    from app.main import app
    client = TestClient(app)
    r = client.post("/api/users/me/cancel-subscription")
    assert r.status_code in (401, 403)


def test_cancel_subscription_calls_helper_and_returns_ok():
    """Authenticated user with active subscription → helper called,
    response says cancelled=true."""
    from app.api import routes

    client = _client_with_auth("u1")
    helper_mock = MagicMock(return_value={
        "had_subscription": True,
        "cancelled": True,
        "subscription_id": "sub_x",
        "error": None,
    })
    try:
        with patch.object(routes, "_cancel_stripe_subscription_for_user", helper_mock):
            r = client.post("/api/users/me/cancel-subscription")
        assert r.status_code == 200
        body = r.json()
        assert body["cancelled"] is True
        assert body["had_subscription"] is True
        helper_mock.assert_called_once_with("u1")
    finally:
        from app.main import app
        app.dependency_overrides.clear()


def test_cancel_subscription_returns_200_when_user_has_no_subscription():
    """Free user (or already cancelled): no Stripe call, 200 with had_subscription=false.
    Idempotent — clicking the button twice doesn't 500."""
    from app.api import routes

    client = _client_with_auth("u1")
    helper_mock = MagicMock(return_value={
        "had_subscription": False,
        "cancelled": False,
        "subscription_id": None,
        "error": None,
    })
    try:
        with patch.object(routes, "_cancel_stripe_subscription_for_user", helper_mock):
            r = client.post("/api/users/me/cancel-subscription")
        assert r.status_code == 200
        body = r.json()
        assert body["had_subscription"] is False
    finally:
        from app.main import app
        app.dependency_overrides.clear()


def test_cancel_subscription_returns_502_when_stripe_errors():
    """Stripe outage: surface a 502 so the frontend can show
    'réessayez dans quelques minutes' rather than a silent success."""
    from app.api import routes

    client = _client_with_auth("u1")
    helper_mock = MagicMock(return_value={
        "had_subscription": True,
        "cancelled": False,
        "subscription_id": "sub_x",
        "error": "stripe_unknown: connection error",
    })
    try:
        with patch.object(routes, "_cancel_stripe_subscription_for_user", helper_mock):
            r = client.post("/api/users/me/cancel-subscription")
        assert r.status_code == 502
        assert "stripe" in r.json().get("detail", "").lower()
    finally:
        from app.main import app
        app.dependency_overrides.clear()
