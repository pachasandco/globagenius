"""Tests for the deep healthcheck endpoint.

The shallow /health endpoint just confirms the process is alive.
/health/deep additionally checks each external dependency and reports
status per component so a load balancer or monitoring system can
detect a degraded — but not crashed — instance.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_health_deep_returns_200_when_all_components_healthy():
    """Happy path: DB, Stripe key, Telegram token all present → 200 + ok."""
    from app.main import app
    client = TestClient(app)

    # Mock the DB ping query so we don't need a real Supabase
    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", "sk_test_x"), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", "tok"), \
         patch("app.api.routes.settings.BREVO_API_KEY", "xkeysib-x"):
        r = client.get("/health/deep")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["components"]["db"] == "ok"
    assert body["components"]["stripe"] == "ok"
    assert body["components"]["telegram"] == "ok"
    assert body["components"]["brevo"] == "ok"


def test_health_deep_returns_503_when_db_is_down():
    """If the DB ping raises, /health/deep returns 503 with detail."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.side_effect = RuntimeError("connection refused")

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", "sk_test_x"), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", "tok"), \
         patch("app.api.routes.settings.BREVO_API_KEY", "xkeysib-x"):
        r = client.get("/health/deep")
    assert r.status_code == 503
    body = r.json()
    # FastAPI wraps HTTPException detail in {"detail": ...}
    detail = body.get("detail", body)
    assert detail["status"] == "degraded"
    assert detail["components"]["db"] == "error"


def test_health_deep_returns_503_when_stripe_key_missing():
    """Misconfig: Stripe key empty → degraded."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", ""), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", "tok"), \
         patch("app.api.routes.settings.BREVO_API_KEY", "xkeysib-x"):
        r = client.get("/health/deep")
    assert r.status_code == 503
    body = r.json()
    detail = body.get("detail", body)
    assert detail["components"]["stripe"] == "missing"


def test_health_deep_lists_telegram_brevo_status_individually():
    """Each component is reported separately so we can spot a partial outage."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", "sk_test_x"), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", ""), \
         patch("app.api.routes.settings.BREVO_API_KEY", ""):
        r = client.get("/health/deep")
    body = r.json()
    detail = body.get("detail", body)
    assert detail["components"]["telegram"] == "missing"
    assert detail["components"]["brevo"] == "missing"
