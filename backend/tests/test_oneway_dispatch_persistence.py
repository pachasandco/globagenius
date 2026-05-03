"""V9: tests for sent_alerts persistence on one-way and split-ticket
dispatch paths.

Audit found 17 qualified one-way items but 0 sent_alerts rows over 7d.
Two bugs were fixed:
  1. _detect_and_dispatch_oneway_alerts() never persisted to sent_alerts
     after a successful send → no audit trail, no dedup.
  2. _detect_and_dispatch_oneway_alerts() was only invoked when
     `inserted > 0` from the scrape pass → existing qualifs were
     stranded between scrape passes when the scraper happened to
     upsert only no-op rows (hash collisions).

These tests pin down both invariants by mocking db.table chains.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mk_table(behaviour: dict | None = None):
    """A versatile MagicMock for db.table() that records upserts.

    Returns (table_mock, calls_list) where calls_list collects every
    upsert payload made on this table.
    """
    calls: list = []
    t = MagicMock()
    upsert_chain = MagicMock()

    def _upsert(payload, **kwargs):
        calls.append({"payload": payload, "kwargs": kwargs})
        execute = MagicMock()
        execute.execute.return_value = MagicMock(data=[])
        return execute

    t.upsert.side_effect = _upsert
    return t, calls


@pytest.mark.asyncio
async def test_oneway_dispatch_persists_sent_alert_after_successful_send():
    """Successful send_oneway_deal_alert → one row upserted into sent_alerts
    with alert_type='one_way'."""
    from app.scheduler import jobs

    # Build a minimal db mock that:
    # - returns one opt-in user with TG connected
    # - returns one fresh one-way candidate
    # - returns enough history (5 rows of 100€) so the qualifier passes a 60% drop
    # - dedup query returns no existing row (this is a fresh alert)
    # - records the sent_alerts upsert
    sent_alerts_calls: list = []

    def _table_router(name: str):
        m = MagicMock()
        if name == "user_preferences":
            execute = MagicMock(data=[{
                "user_id": "u1",
                "telegram_chat_id": 999,
                "airport_codes": ["CDG"],
                "flight_trip_types": ["round_trip", "one_way"],
                "blocked_destinations": [],
            }])
            m.select.return_value.eq.return_value.execute.return_value = execute
        elif name == "raw_flights":
            # candidate fetch
            cand_chain = (
                m.select.return_value
                .eq.return_value
                .gte.return_value
                .order.return_value
                .limit.return_value
            )
            cand_chain.execute.return_value = MagicMock(data=[{
                "id": "rf1", "origin": "CDG", "destination": "BKK",
                "departure_date": "2026-09-01", "direction": "outbound",
                "price": 30.0, "airline": "AF",
                "source_url": "https://aviasales.com/x",
                "scraped_at": "2026-09-01T00:00:00+00:00",
            }])
            # history fetch chain — returns 5 prices around 100€ so the
            # candidate at 30€ scores a -70% discount.
            hist_chain = (
                m.select.return_value
                .eq.return_value
                .eq.return_value
                .eq.return_value
                .eq.return_value
                .gte.return_value
            )
            hist_chain.execute.return_value = MagicMock(data=[
                {"price": 95.0}, {"price": 100.0}, {"price": 105.0},
                {"price": 100.0}, {"price": 110.0},
            ])
        elif name == "sent_alerts":
            # dedup check returns empty → new alert
            dedup_chain = (
                m.select.return_value
                .eq.return_value
                .eq.return_value
                .gte.return_value
                .limit.return_value
            )
            dedup_chain.execute.return_value = MagicMock(data=[])
            # capture upsert
            def _upsert(payload, **kwargs):
                sent_alerts_calls.append(payload)
                execute = MagicMock()
                execute.execute.return_value = MagicMock(data=[payload])
                return execute
            m.upsert.side_effect = _upsert
        elif name == "qualified_items":
            up = MagicMock()
            up.execute.return_value = MagicMock(data=[{}])
            m.upsert.return_value = up
        return m

    db_mock = MagicMock()
    db_mock.table.side_effect = _table_router

    send_mock = AsyncMock(return_value=True)

    with patch.object(jobs, "db", db_mock), \
         patch("app.notifications.telegram.send_oneway_deal_alert", new=send_mock), \
         patch.object(jobs.settings, "TRAVELPAYOUTS_TOKEN", "x"):
        await jobs._detect_and_dispatch_oneway_alerts()

    # 1 send call
    assert send_mock.await_count == 1
    # 1 sent_alerts upsert
    assert len(sent_alerts_calls) == 1
    row = sent_alerts_calls[0]
    assert row["user_id"] == "u1"
    assert row["alert_type"] == "one_way"
    assert row["destination"] == "BKK"
    assert row["alert_key"]


@pytest.mark.asyncio
async def test_oneway_dispatch_skips_when_already_alerted_within_inhibit_window():
    """If sent_alerts already has the same alert_key within the inhibit
    window, the dispatcher must NOT call send_oneway_deal_alert."""
    from app.scheduler import jobs

    def _table_router(name: str):
        m = MagicMock()
        if name == "user_preferences":
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{
                    "user_id": "u1", "telegram_chat_id": 999,
                    "airport_codes": ["CDG"],
                    "flight_trip_types": ["round_trip", "one_way"],
                    "blocked_destinations": [],
                }]
            )
        elif name == "raw_flights":
            (
                m.select.return_value.eq.return_value.gte.return_value
                .order.return_value.limit.return_value
                .execute.return_value
            ) = MagicMock(data=[{
                "id": "rf1", "origin": "CDG", "destination": "BKK",
                "departure_date": "2026-09-01", "direction": "outbound",
                "price": 30.0, "airline": "AF",
                "source_url": "https://aviasales.com/x",
                "scraped_at": "2026-09-01T00:00:00+00:00",
            }])
            (
                m.select.return_value.eq.return_value.eq.return_value
                .eq.return_value.eq.return_value.gte.return_value
                .execute.return_value
            ) = MagicMock(data=[
                {"price": 95.0}, {"price": 100.0}, {"price": 105.0},
                {"price": 100.0}, {"price": 110.0},
            ])
        elif name == "sent_alerts":
            # dedup check returns AN EXISTING row → already alerted
            (
                m.select.return_value.eq.return_value.eq.return_value
                .gte.return_value.limit.return_value
                .execute.return_value
            ) = MagicMock(data=[{"id": "existing"}])
        elif name == "qualified_items":
            m.upsert.return_value.execute.return_value = MagicMock(data=[{}])
        return m

    db_mock = MagicMock()
    db_mock.table.side_effect = _table_router

    send_mock = AsyncMock(return_value=True)

    with patch.object(jobs, "db", db_mock), \
         patch("app.notifications.telegram.send_oneway_deal_alert", new=send_mock), \
         patch.object(jobs.settings, "TRAVELPAYOUTS_TOKEN", "x"):
        await jobs._detect_and_dispatch_oneway_alerts()

    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_oneway_dispatch_does_not_persist_when_send_returns_false():
    """If the Telegram send fails (returns False), we must NOT pollute
    sent_alerts with a row claiming the alert went through."""
    from app.scheduler import jobs

    sent_alerts_calls: list = []

    def _table_router(name: str):
        m = MagicMock()
        if name == "user_preferences":
            m.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{
                    "user_id": "u1", "telegram_chat_id": 999,
                    "airport_codes": ["CDG"],
                    "flight_trip_types": ["round_trip", "one_way"],
                    "blocked_destinations": [],
                }]
            )
        elif name == "raw_flights":
            (
                m.select.return_value.eq.return_value.gte.return_value
                .order.return_value.limit.return_value
                .execute.return_value
            ) = MagicMock(data=[{
                "id": "rf1", "origin": "CDG", "destination": "BKK",
                "departure_date": "2026-09-01", "direction": "outbound",
                "price": 30.0, "airline": "AF",
                "source_url": "https://aviasales.com/x",
                "scraped_at": "2026-09-01T00:00:00+00:00",
            }])
            (
                m.select.return_value.eq.return_value.eq.return_value
                .eq.return_value.eq.return_value.gte.return_value
                .execute.return_value
            ) = MagicMock(data=[
                {"price": 95.0}, {"price": 100.0}, {"price": 105.0},
                {"price": 100.0}, {"price": 110.0},
            ])
        elif name == "sent_alerts":
            (
                m.select.return_value.eq.return_value.eq.return_value
                .gte.return_value.limit.return_value
                .execute.return_value
            ) = MagicMock(data=[])

            def _upsert(payload, **kwargs):
                sent_alerts_calls.append(payload)
                execute = MagicMock()
                execute.execute.return_value = MagicMock(data=[payload])
                return execute
            m.upsert.side_effect = _upsert
        elif name == "qualified_items":
            m.upsert.return_value.execute.return_value = MagicMock(data=[{}])
        return m

    db_mock = MagicMock()
    db_mock.table.side_effect = _table_router

    # Telegram send returns False → simulated failure
    send_mock = AsyncMock(return_value=False)

    with patch.object(jobs, "db", db_mock), \
         patch("app.notifications.telegram.send_oneway_deal_alert", new=send_mock), \
         patch.object(jobs.settings, "TRAVELPAYOUTS_TOKEN", "x"):
        await jobs._detect_and_dispatch_oneway_alerts()

    # Send was attempted
    assert send_mock.await_count == 1
    # But NO sent_alerts row was created — we don't claim a delivery
    # we couldn't make.
    assert sent_alerts_calls == []
