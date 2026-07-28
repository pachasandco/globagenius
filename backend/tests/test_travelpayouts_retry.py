"""Tests for the Travelpayouts retry + circuit breaker layer (2026-06-09)."""
from unittest.mock import MagicMock

import httpx
import pytest

import app.scraper.travelpayouts as tp


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    """Context-manager stand-in for httpx.Client driven by a script:
    each .get()/.post() pops the next action — an Exception to raise or
    a payload to return."""

    script: list = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def _next(self):
        action = _FakeClient.script.pop(0)
        if isinstance(action, Exception):
            raise action
        return _FakeResponse(action)

    def get(self, *args, **kwargs):
        return self._next()

    def post(self, *args, **kwargs):
        return self._next()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(tp, "_consecutive_failures", 0)
    monkeypatch.setattr(tp, "_breaker_open_until", 0.0)
    monkeypatch.setattr(tp.time, "sleep", lambda s: None)
    monkeypatch.setattr(tp.settings, "TRAVELPAYOUTS_TOKEN", "test-token")
    monkeypatch.setattr(tp.httpx, "Client", _FakeClient)
    _FakeClient.script = []


def test_get_retries_on_timeout_then_succeeds():
    _FakeClient.script = [
        httpx.ConnectTimeout("boom"),
        {"success": True, "data": {}},
    ]
    assert tp._get("https://x.test/v1") == {"success": True, "data": {}}
    assert _FakeClient.script == []  # both attempts consumed


def test_get_gives_up_after_max_attempts():
    _FakeClient.script = [httpx.ConnectTimeout("boom")] * tp.MAX_ATTEMPTS
    assert tp._get("https://x.test/v1") is None
    assert _FakeClient.script == []


def test_get_does_not_retry_hard_4xx():
    err = httpx.HTTPStatusError(
        "400", request=MagicMock(), response=MagicMock(status_code=400)
    )
    _FakeClient.script = [err, {"success": True}]
    assert tp._get("https://x.test/v1") is None
    # The second scripted action must NOT have been consumed.
    assert len(_FakeClient.script) == 1


def test_429_and_5xx_are_transient():
    for status in (429, 503):
        err = httpx.HTTPStatusError(
            str(status), request=MagicMock(), response=MagicMock(status_code=status)
        )
        _FakeClient.script = [err, {"success": True}]
        assert tp._get("https://x.test/v1") == {"success": True}


def test_breaker_opens_after_consecutive_failures_and_skips_calls():
    # Each exhausted _get counts as ONE failure; BREAKER_THRESHOLD of
    # them open the breaker.
    for _ in range(tp.BREAKER_THRESHOLD):
        _FakeClient.script = [httpx.ConnectTimeout("boom")] * tp.MAX_ATTEMPTS
        assert tp._get("https://x.test/v1") is None
    assert tp._breaker_is_open()
    # While open, no HTTP call is attempted at all.
    _FakeClient.script = [{"success": True}]
    assert tp._get("https://x.test/v1") is None
    assert len(_FakeClient.script) == 1


def test_success_resets_consecutive_failure_count():
    _FakeClient.script = [httpx.ConnectTimeout("boom")] * tp.MAX_ATTEMPTS
    assert tp._get("https://x.test/v1") is None
    _FakeClient.script = [{"success": True}]
    assert tp._get("https://x.test/v1") == {"success": True}
    assert tp._consecutive_failures == 0


def test_graphql_uses_same_retry_layer():
    _FakeClient.script = [
        httpx.ConnectTimeout("boom"),
        {"data": {"prices_one_way": []}},
    ]
    assert tp._graphql("{ x }") == {"data": {"prices_one_way": []}}
