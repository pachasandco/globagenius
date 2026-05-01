"""Tests for the V8.3 scraper watchdog.

The watchdog runs every 2h and pings the admin Telegram chat when a
scraper logs successful runs but persists zero rows over the last 24h
— a sign the scraper is silently broken (the kind of failure V8.1
audited and fixed).
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _build_db_mock(*, rows_per_source: dict, runs_per_actor: dict):
    """Tiny db mock: returns count='exact'/head=True chains for both
    raw_flights and scrape_logs."""
    captured = {"calls": []}

    def fake_table(name):
        t = MagicMock()
        if name == "raw_flights":
            def _select(*args, **kwargs):
                # Track which source/trip_type filter is queried so we
                # can return the right count.
                state = {"source": None, "trip_type": None}

                def _eq(col, val):
                    state[col] = val
                    sub = MagicMock()
                    sub.gte.return_value.execute.return_value = MagicMock(
                        count=rows_per_source.get(state["source"] or state["trip_type"], 0)
                    )
                    return sub

                head_chain = MagicMock()
                head_chain.eq.side_effect = _eq
                return head_chain

            t.select.side_effect = _select
            return t
        if name == "scrape_logs":
            def _select(*args, **kwargs):
                state = {"actor_id": None}

                def _eq(col, val):
                    state[col] = val
                    sub = MagicMock()
                    sub.gte.return_value.execute.return_value = MagicMock(
                        count=runs_per_actor.get(state["actor_id"], 0)
                    )
                    return sub

                head_chain = MagicMock()
                head_chain.eq.side_effect = _eq
                return head_chain

            t.select.side_effect = _select
            return t
        return MagicMock()

    db_mock = MagicMock()
    db_mock.table.side_effect = fake_table
    db_mock._captured = captured
    return db_mock


@pytest.mark.asyncio
async def test_watchdog_silent_when_no_admin_chat_configured():
    """Without TELEGRAM_ADMIN_CHAT_ID we must not send anything, even if
    a scraper is broken."""
    from app.scheduler import jobs

    db_mock = _build_db_mock(
        rows_per_source={"ryanair_direct": 0, "vueling_direct": 0, "travelpayouts": 1000, "one_way": 0},
        runs_per_actor={"tier1": 50, "flights": 10, "flights_oneway": 6},
    )
    send_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs.settings, "TELEGRAM_ADMIN_CHAT_ID", ""), \
         patch("app.notifications.telegram.send_admin_alert", new=send_mock):
        await jobs.job_scraper_watchdog()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_watchdog_silent_when_all_scrapers_healthy():
    """All scrapers landing rows = no alert."""
    from app.scheduler import jobs
    jobs._watchdog_last_alert.clear()

    db_mock = _build_db_mock(
        rows_per_source={
            "ryanair_direct": 50, "vueling_direct": 200,
            "travelpayouts": 1000, "one_way": 100,
        },
        runs_per_actor={"tier1": 70, "flights": 12, "flights_oneway": 6},
    )
    send_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs.settings, "TELEGRAM_ADMIN_CHAT_ID", "12345"), \
         patch("app.notifications.telegram.send_admin_alert", new=send_mock):
        await jobs.job_scraper_watchdog()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_watchdog_alerts_on_silent_scraper():
    """Ryanair logs 50 runs but landed 0 rows → alert."""
    from app.scheduler import jobs
    jobs._watchdog_last_alert.clear()

    db_mock = _build_db_mock(
        rows_per_source={
            "ryanair_direct": 0, "vueling_direct": 200,
            "travelpayouts": 1000, "one_way": 100,
        },
        runs_per_actor={"tier1": 50, "flights": 12, "flights_oneway": 6},
    )
    send_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs.settings, "TELEGRAM_ADMIN_CHAT_ID", "12345"), \
         patch("app.notifications.telegram.send_admin_alert", new=send_mock):
        await jobs.job_scraper_watchdog()

    send_mock.assert_awaited_once()
    msg = send_mock.await_args.args[0]
    assert "ryanair_direct" in msg
    assert "vueling_direct" not in msg


@pytest.mark.asyncio
async def test_watchdog_silent_when_too_few_runs():
    """If a scraper logged < 3 runs, we don't alert — could just be
    the start of an outage being recovered."""
    from app.scheduler import jobs
    jobs._watchdog_last_alert.clear()

    db_mock = _build_db_mock(
        rows_per_source={"ryanair_direct": 0, "vueling_direct": 0, "travelpayouts": 1000, "one_way": 0},
        runs_per_actor={"tier1": 2, "flights": 12, "flights_oneway": 1},
    )
    send_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs.settings, "TELEGRAM_ADMIN_CHAT_ID", "12345"), \
         patch("app.notifications.telegram.send_admin_alert", new=send_mock):
        await jobs.job_scraper_watchdog()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_watchdog_cooldown_prevents_repeat_alerts():
    """A second run within the cooldown window must NOT re-alert."""
    from app.scheduler import jobs
    jobs._watchdog_last_alert.clear()

    db_mock = _build_db_mock(
        rows_per_source={"ryanair_direct": 0, "vueling_direct": 200, "travelpayouts": 1000, "one_way": 100},
        runs_per_actor={"tier1": 50, "flights": 12, "flights_oneway": 6},
    )
    send_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs.settings, "TELEGRAM_ADMIN_CHAT_ID", "12345"), \
         patch("app.notifications.telegram.send_admin_alert", new=send_mock):
        await jobs.job_scraper_watchdog()
        await jobs.job_scraper_watchdog()
        await jobs.job_scraper_watchdog()
    # Should have alerted only on the first call.
    assert send_mock.await_count == 1


@pytest.mark.asyncio
async def test_watchdog_alerts_again_after_cooldown_expires():
    """Past the 6h cooldown, the watchdog re-alerts if the scraper is
    still broken."""
    from app.scheduler import jobs
    jobs._watchdog_last_alert.clear()
    # Pretend we already alerted 7h ago.
    jobs._watchdog_last_alert["ryanair_direct"] = (
        datetime.now(timezone.utc) - timedelta(hours=7)
    )

    db_mock = _build_db_mock(
        rows_per_source={"ryanair_direct": 0, "vueling_direct": 200, "travelpayouts": 1000, "one_way": 100},
        runs_per_actor={"tier1": 50, "flights": 12, "flights_oneway": 6},
    )
    send_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs.settings, "TELEGRAM_ADMIN_CHAT_ID", "12345"), \
         patch("app.notifications.telegram.send_admin_alert", new=send_mock):
        await jobs.job_scraper_watchdog()

    send_mock.assert_awaited_once()
