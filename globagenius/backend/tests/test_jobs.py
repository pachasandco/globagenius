from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    assert "scrape_flights_02" in job_names
    assert "scrape_flights_22" in job_names
    assert "scrape_accommodations_03" in job_names
    assert "travelpayouts_enrichment" in job_names
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_flight_every_2h():
    jobs = get_scheduler_jobs()
    flight_jobs = [j for j in jobs if j["id"].startswith("scrape_flights")]
    assert len(flight_jobs) == 12
    hours = sorted([j["hour"] for j in flight_jobs])
    assert hours == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]


def test_get_scheduler_jobs_hotels_1x_daily():
    jobs = get_scheduler_jobs()
    hotel_jobs = [j for j in jobs if j["id"].startswith("scrape_accommodations")]
    assert len(hotel_jobs) == 1
    assert hotel_jobs[0]["hour"] == 3


import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_db_with_baseline():
    """Mock db with a single baseline returned for any query."""
    db_mock = MagicMock()
    baseline_row = {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": 50,
    }
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[baseline_row])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{}])
    db_mock.table.return_value = table_mock
    return db_mock, baseline_row


def _flight_for_analysis(price=120.0, trip_duration_days=7, stops=0,
                         duration_minutes=120, origin="CDG", destination="BCN"):
    return {
        "id": "test-id",
        "origin": origin,
        "destination": destination,
        "departure_date": "2026-05-12",
        "return_date": "2026-05-19",
        "price": price,
        "trip_duration_days": trip_duration_days,
        "stops": stops,
        "duration_minutes": duration_minutes,
        "airline": "AF",
    }


@pytest.mark.asyncio
async def test_analyze_skips_flights_outside_duration_buckets(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    flight = _flight_for_analysis(trip_duration_days=30)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.assert_not_called()  # never even queried baseline


@pytest.mark.asyncio
async def test_analyze_skips_flights_violating_stops_rule(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # Short-haul (120 min), 1 stop -> rejected
    flight = _flight_for_analysis(stops=1, duration_minutes=120)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_uses_bucket_medium_for_7_day_flight(mock_db_with_baseline):
    db_mock, baseline_row = mock_db_with_baseline
    from app.scheduler import jobs
    flight = _flight_for_analysis(price=120.0, trip_duration_days=7)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()):
        await jobs._analyze_new_flights([flight])
    # Verify baseline was queried with the right key
    select_call = db_mock.table.return_value.select.return_value
    eq_calls = select_call.eq.call_args_list
    assert any(call.args == ("route_key", "CDG-BCN-bucket_medium") for call in eq_calls)


@pytest.mark.asyncio
async def test_analyze_skips_when_no_baseline_for_bucket():
    db_mock = MagicMock()
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    db_mock.table.return_value = table_mock

    from app.scheduler import jobs
    flight = _flight_for_analysis()
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_skips_when_baseline_sample_count_too_low():
    from app.analysis.baselines import MIN_SAMPLE_COUNT
    db_mock = MagicMock()
    baseline_row = {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": MIN_SAMPLE_COUNT - 1,  # below MIN_SAMPLE_COUNT
    }
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[baseline_row])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    db_mock.table.return_value = table_mock

    from app.scheduler import jobs
    flight = _flight_for_analysis(price=80.0)  # would be -60% otherwise
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_assigns_free_tier_for_25_pct_discount(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # baseline avg 200, price 148 -> -26%, z = (200-148)/25 = 2.08 (safely above 2.0 floor)
    # Under Phase D4 rules, 26% < 30% -> free tier.
    flight = _flight_for_analysis(price=148.0)
    compose_mock = AsyncMock()
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "_compose_packages_for_flight", new=compose_mock):
        await jobs._analyze_new_flights([flight])
    insert_calls = db_mock.table.return_value.insert.call_args_list
    inserted_payloads = [c.args[0] for c in insert_calls]
    qualified = [p for p in inserted_payloads if p.get("type") == "flight"]
    assert len(qualified) == 1
    assert qualified[0]["tier"] == "free"
    compose_mock.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_assigns_premium_tier_for_50_pct_discount(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # baseline avg 200, price 100 -> -50%, z = 4.0
    flight = _flight_for_analysis(price=100.0)
    compose_mock = AsyncMock()
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "_compose_packages_for_flight", new=compose_mock):
        await jobs._analyze_new_flights([flight])
    insert_calls = db_mock.table.return_value.insert.call_args_list
    inserted_payloads = [c.args[0] for c in insert_calls]
    qualified = [p for p in inserted_payloads if p.get("type") == "flight"]
    assert len(qualified) == 1
    assert qualified[0]["tier"] == "premium"
    compose_mock.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_skips_when_reverify_returns_false(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    flight = _flight_for_analysis(price=100.0)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=False)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_skips_when_discount_below_20_pct(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # baseline 200, price 175 -> -12.5%, below threshold
    flight = _flight_for_analysis(price=175.0)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_skips_when_z_score_below_2():
    """Even with discount >= 20%, the deal is rejected if the route is too volatile (z_score < 2)."""
    db_mock = MagicMock()
    # baseline avg 200, std_dev 100 (very volatile), price 150 -> -25%, z = 0.5
    baseline_row = {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 100.0,
        "sample_count": 50,
    }
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[baseline_row])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    db_mock.table.return_value = table_mock

    from app.scheduler import jobs
    flight = _flight_for_analysis(price=150.0)  # -25% but z = 0.5
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_travelpayouts_enrichment_builds_bucket_baselines():
    """The job should fetch flights via get_prices_for_dates, normalize them,
    and upsert one baseline per (route, bucket) that meets MIN_SAMPLE_COUNT."""
    from app.scheduler import jobs

    # Build a fake API response with 30 medium-bucket flights for one route
    fake_entries = []
    for i in range(30):
        day_dep = (i % 14) + 1
        day_ret = day_dep + 7
        fake_entries.append({
            "origin_airport": "CDG",
            "destination_airport": "BCN",
            "departure_at": f"2026-05-{day_dep:02d}T10:00:00+02:00",
            "return_at": f"2026-05-{day_ret:02d}T18:00:00+02:00",
            "price": 200 + i,
            "airline": "AF",
            "transfers": 0,
            "return_transfers": 0,
            "duration_to": 100,
            "duration_back": 110,
            "link": "/search/...",
        })

    db_mock = MagicMock()
    table_mock = MagicMock()
    upsert_mock = MagicMock()
    upsert_mock.execute.return_value = MagicMock(data=[{}])
    table_mock.upsert.return_value = upsert_mock
    db_mock.table.return_value = table_mock

    # Mock settings to limit to 1 airport
    fake_settings = MagicMock()
    fake_settings.MVP_AIRPORTS = ["CDG"]
    fake_settings.TRAVELPAYOUTS_TOKEN = "fake-token"

    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "settings", fake_settings), \
         patch("app.scheduler.jobs.get_prices_for_dates", return_value=fake_entries), \
         patch("app.scheduler.jobs.get_priority_destinations", return_value=["BCN"]):
        await jobs.job_travelpayouts_enrichment()

    upsert_calls = table_mock.upsert.call_args_list
    upserted_baselines = [c.args[0] for c in upsert_calls]
    bucket_baselines = [b for b in upserted_baselines if "bucket_" in b.get("route_key", "")]
    assert len(bucket_baselines) >= 1
    medium = next((b for b in bucket_baselines if b["route_key"] == "CDG-BCN-bucket_medium"), None)
    assert medium is not None
    assert medium["sample_count"] == 30
    assert medium["type"] == "flight"


@pytest.mark.asyncio
async def test_travelpayouts_enrichment_skips_routes_without_enough_samples():
    """If a route returns fewer than MIN_SAMPLE_COUNT usable observations,
    no baseline is published for that route."""
    from app.scheduler import jobs

    # Only 5 flights — below MIN_SAMPLE_COUNT
    fake_entries = []
    for i in range(5):
        day_dep = i + 1
        day_ret = day_dep + 7
        fake_entries.append({
            "origin_airport": "CDG",
            "destination_airport": "BCN",
            "departure_at": f"2026-05-{day_dep:02d}T10:00:00+02:00",
            "return_at": f"2026-05-{day_ret:02d}T18:00:00+02:00",
            "price": 200 + i,
            "airline": "AF",
            "transfers": 0,
            "return_transfers": 0,
            "duration_to": 100,
            "duration_back": 110,
            "link": "/search/...",
        })

    db_mock = MagicMock()
    table_mock = MagicMock()
    upsert_mock = MagicMock()
    upsert_mock.execute.return_value = MagicMock(data=[{}])
    table_mock.upsert.return_value = upsert_mock
    db_mock.table.return_value = table_mock

    fake_settings = MagicMock()
    fake_settings.MVP_AIRPORTS = ["CDG"]
    fake_settings.TRAVELPAYOUTS_TOKEN = "fake-token"

    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "settings", fake_settings), \
         patch("app.scheduler.jobs.get_prices_for_dates", return_value=fake_entries), \
         patch("app.scheduler.jobs.get_priority_destinations", return_value=["BCN"]):
        await jobs.job_travelpayouts_enrichment()

    upsert_calls = table_mock.upsert.call_args_list
    upserted_baselines = [c.args[0] for c in upsert_calls]
    bucket_baselines = [b for b in upserted_baselines if "bucket_" in b.get("route_key", "")]
    assert bucket_baselines == []


@pytest.mark.asyncio
async def test_recalculate_baselines_builds_bucket_baselines_from_history():
    """job_recalculate_baselines should read raw_flights for the last 30 days,
    group by route, and produce per-bucket baselines via compute_baselines_by_bucket."""
    from app.scheduler import jobs
    from datetime import datetime, timezone

    # 30 medium-bucket flights for CDG-BCN, all valid
    fake_flights = []
    for i in range(30):
        fake_flights.append({
            "origin": "CDG",
            "destination": "BCN",
            "price": 200 + i,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "trip_duration_days": 7,
            "stops": 0,
            "duration_minutes": 120,
        })

    pb_table = MagicMock()
    pb_table.upsert.return_value.execute.return_value = MagicMock(data=[{}])

    # raw_flights chain: select().gte().not_.is_().order().range().execute()
    # First page returns fake_flights, subsequent pages return empty (breaks loop)
    rf_table = MagicMock()
    rf_chain = rf_table.select.return_value.gte.return_value
    rf_chain.not_.is_.return_value.order.return_value.range.return_value.execute.side_effect = [
        MagicMock(data=fake_flights),
        MagicMock(data=[]),
    ]

    # raw_accommodations chain: select().gte().execute()
    ra_table = MagicMock()
    ra_table.select.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

    db_mock = MagicMock()

    def fake_table(name):
        return {
            "raw_flights": rf_table,
            "raw_accommodations": ra_table,
            "price_baselines": pb_table,
        }[name]

    db_mock.table.side_effect = fake_table

    with patch.object(jobs, "db", db_mock):
        await jobs.job_recalculate_baselines()

    upsert_payloads = [c.args[0] for c in pb_table.upsert.call_args_list]
    bucket_baselines = [b for b in upsert_payloads if "bucket_" in b.get("route_key", "")]
    assert len(bucket_baselines) >= 1
    medium = next((b for b in bucket_baselines if b["route_key"] == "CDG-BCN-bucket_medium"), None)
    assert medium is not None
    assert medium["sample_count"] == 30
    assert medium["type"] == "flight"


@pytest.mark.asyncio
async def test_recalculate_baselines_skips_routes_without_enough_history():
    """If a route has fewer than MIN_SAMPLE_COUNT observations per bucket,
    no baseline is upserted for that route."""
    from app.scheduler import jobs
    from datetime import datetime, timezone

    # Only 5 flights for CDG-BCN — under MIN_SAMPLE_COUNT
    fake_flights = []
    for i in range(5):
        fake_flights.append({
            "origin": "CDG",
            "destination": "BCN",
            "price": 200 + i,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "trip_duration_days": 7,
            "stops": 0,
            "duration_minutes": 120,
        })

    pb_table = MagicMock()
    pb_table.upsert.return_value.execute.return_value = MagicMock(data=[{}])

    rf_table = MagicMock()
    rf_chain = rf_table.select.return_value.gte.return_value
    rf_chain.not_.is_.return_value.order.return_value.range.return_value.execute.side_effect = [
        MagicMock(data=fake_flights),
        MagicMock(data=[]),
    ]

    ra_table = MagicMock()
    ra_table.select.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

    db_mock = MagicMock()

    def fake_table(name):
        return {
            "raw_flights": rf_table,
            "raw_accommodations": ra_table,
            "price_baselines": pb_table,
        }[name]

    db_mock.table.side_effect = fake_table

    with patch.object(jobs, "db", db_mock):
        await jobs.job_recalculate_baselines()

    pb_table.upsert.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Telegram alert filtering by user_preferences.min_discount
# ─────────────────────────────────────────────────────────────────────────────


def _build_alert_db_mock(
    baseline_row: dict,
    subscribers: list[dict],
    user_prefs: list[dict] | Exception | None = None,
    already_sent_keys: list[str] | None = None,
    sent_alerts_upsert_spy: MagicMock | None = None,
):
    """Build a db mock that routes table() calls by name:
    - price_baselines: returns baseline_row for .select().eq().eq().execute()
    - qualified_items: .insert().execute() returns data=[{}]
    - telegram_subscribers: .select().in_("airport_code",...).execute() returns `subscribers`
    - user_preferences: .select().in_().execute() returns `user_prefs`
                       (or raises if user_prefs is an Exception)
    - raw_accommodations: .select() chain returns data=[] (skip _compose_packages)
    - sent_alerts:
        .select("alert_key").eq("user_id",...).in_("alert_key",...).execute()
            → [{"alert_key": k} for k in already_sent_keys if k in queried]
        .select("id").eq("user_id",...).eq("alert_key",...).limit(1).execute()
            → [{"id": "x"}] if queried alert_key in already_sent_keys, else []
        .upsert(rows, on_conflict=...).execute()
            → records call on sent_alerts_upsert_spy when provided
    """
    already_sent_keys = already_sent_keys or []

    # price_baselines chain
    pb_table = MagicMock()
    pb_eq2 = MagicMock()
    pb_eq2.execute.return_value = MagicMock(data=[baseline_row])
    pb_table.select.return_value.eq.return_value.eq.return_value = pb_eq2

    # qualified_items chain (insert)
    qi_table = MagicMock()
    qi_table.insert.return_value.execute.return_value = MagicMock(data=[{}])

    # telegram_subscribers chain — new grouped dispatch uses
    #   .select("chat_id,user_id,airport_code").in_("airport_code", origins).execute()
    ts_table = MagicMock()
    ts_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=subscribers
    )

    # user_preferences chain
    up_table = MagicMock()
    up_chain = up_table.select.return_value.in_.return_value
    if isinstance(user_prefs, Exception):
        up_chain.execute.side_effect = user_prefs
    else:
        up_chain.execute.return_value = MagicMock(data=user_prefs or [])

    # raw_accommodations chain: skip packages composition (return no hotels)
    ra_table = MagicMock()
    ra_chain = (
        ra_table.select.return_value
        .eq.return_value
        .eq.return_value
        .eq.return_value
        .gte.return_value
        .gte.return_value
    )
    ra_chain.execute.return_value = MagicMock(data=[])

    # sent_alerts chain
    sa_table = MagicMock()

    # .select("alert_key").eq("user_id",...).in_("alert_key", keys).execute()
    def _sa_bulk_execute(*args, **kwargs):
        # We can't easily inspect which keys were requested through MagicMock
        # chaining side_effects, so just return rows for every already_sent key.
        return MagicMock(data=[{"alert_key": k} for k in already_sent_keys])

    (
        sa_table.select.return_value
        .eq.return_value
        .in_.return_value
        .execute.side_effect
    ) = _sa_bulk_execute

    # .select("id").eq("user_id",...).eq("alert_key", k).limit(1).execute()
    # Build a side_effect on the .eq.return_value.eq to capture the alert_key
    # being queried, then return data accordingly at .limit(1).execute().
    _pkg_last_key = {"value": None}

    def _pkg_eq_alert_key(column, value):
        if column == "alert_key":
            _pkg_last_key["value"] = value
        m = MagicMock()
        limit_mock = MagicMock()

        def _pkg_limit_execute():
            if _pkg_last_key["value"] in already_sent_keys:
                return MagicMock(data=[{"id": "existing-id"}])
            return MagicMock(data=[])

        limit_mock.execute.side_effect = _pkg_limit_execute
        m.limit.return_value = limit_mock
        return m

    sa_table.select.return_value.eq.return_value.eq.side_effect = _pkg_eq_alert_key

    # .upsert(rows, on_conflict=...).execute()
    if sent_alerts_upsert_spy is not None:
        def _sa_upsert(*args, **kwargs):
            sent_alerts_upsert_spy(*args, **kwargs)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[])
            return m
        sa_table.upsert.side_effect = _sa_upsert
    else:
        sa_table.upsert.return_value.execute.return_value = MagicMock(data=[])

    db_mock = MagicMock()

    def fake_table(name):
        return {
            "price_baselines": pb_table,
            "qualified_items": qi_table,
            "telegram_subscribers": ts_table,
            "user_preferences": up_table,
            "raw_accommodations": ra_table,
            "sent_alerts": sa_table,
        }.get(name, MagicMock())

    db_mock.table.side_effect = fake_table
    return db_mock


def _baseline_row_cdg_bcn():
    return {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": 50,
    }


def _baseline_row(route_key: str):
    return {
        "route_key": route_key,
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": 50,
    }


@pytest.mark.asyncio
async def test_flight_alert_filtered_by_user_min_discount():
    """User min_discount=50 blocks a 30% discount flight alert.

    After the grouped-dispatch refactor, filtering happens before send_grouped_flight_alerts
    is called. With a single filtered offer, no grouped call is emitted at all.
    """
    from app.scheduler import jobs

    baseline_row = _baseline_row_cdg_bcn()
    # price 140 -> -30% discount, z = 2.4 (passes 20% floor)
    flight = _flight_for_analysis(price=140.0)

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 50}],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    send_grouped_mock.assert_not_called()


@pytest.mark.asyncio
async def test_flight_alert_sent_when_discount_meets_threshold():
    """Premium user min_discount=30 allows a 45% discount flight alert via grouped dispatch."""
    from app.scheduler import jobs

    baseline_row = _baseline_row_cdg_bcn()
    # price 110 -> -45% discount, z = 3.6
    flight = _flight_for_analysis(price=110.0)

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 30}],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs, "_get_user_tier", return_value="premium"), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    assert send_grouped_mock.call_count == 1
    kwargs = send_grouped_mock.call_args.kwargs
    assert len(kwargs["offers"]) >= 1


@pytest.mark.asyncio
async def test_flight_alert_default_min_when_user_prefs_missing():
    """Legacy subscribers with no user_id fall back to default min_discount=20."""
    from app.scheduler import jobs

    baseline_row = _baseline_row_cdg_bcn()
    # price 150 -> -25% discount, z = 2.0 (passes 20% floor, above default 20)
    flight = _flight_for_analysis(price=150.0)

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": None, "airport_code": "CDG"}],
        user_prefs=[],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    assert send_grouped_mock.call_count == 1
    kwargs = send_grouped_mock.call_args.kwargs
    assert len(kwargs["offers"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Grouped flight alerts + sent_alerts dedup
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dedup_skips_already_sent_flight():
    """If the alert_key for a flight already exists in sent_alerts, no grouped
    alert is dispatched for that flight."""
    from app.scheduler import jobs
    from app.notifications.dedup import compute_alert_key

    baseline_row = _baseline_row_cdg_bcn()
    flight = _flight_for_analysis(price=110.0)  # -45%

    expected_key = compute_alert_key(
        "u1",
        flight["origin"],
        flight["destination"],
        flight["departure_date"],
        flight["return_date"],
        flight["price"],
    )

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 20}],
        already_sent_keys=[expected_key],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    send_grouped_mock.assert_not_called()


@pytest.mark.asyncio
async def test_dedup_stores_alert_keys_after_send():
    """After a successful grouped send, the alert_key(s) are upserted into sent_alerts."""
    from app.scheduler import jobs
    from app.notifications.dedup import compute_alert_key

    baseline_row = _baseline_row_cdg_bcn()
    flight = _flight_for_analysis(price=110.0)  # -45%

    expected_key = compute_alert_key(
        "u1",
        flight["origin"],
        flight["destination"],
        flight["departure_date"],
        flight["return_date"],
        flight["price"],
    )

    upsert_spy = MagicMock()
    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 20}],
        sent_alerts_upsert_spy=upsert_spy,
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs, "_get_user_tier", return_value="premium"), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    assert upsert_spy.call_count >= 1
    # Spy signature: _sa_upsert(rows, on_conflict=...)
    stored_rows = upsert_spy.call_args.args[0]
    assert isinstance(stored_rows, list)
    assert any(r.get("alert_key") == expected_key for r in stored_rows)


@pytest.mark.asyncio
async def test_grouped_flight_alert_respects_min_discount():
    """With user min=40, a 30% offer is filtered out and not in the offers payload."""
    from app.scheduler import jobs

    baseline_row = _baseline_row_cdg_bcn()
    flight = _flight_for_analysis(price=140.0)  # -30%

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 40}],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    # Only offer was filtered: no send.
    send_grouped_mock.assert_not_called()


@pytest.mark.asyncio
async def test_grouped_flight_alert_two_offers_same_destination():
    """Two qualified flights CDG->LIS on different dates for same user group
    into a single send with 2 offers."""
    from app.scheduler import jobs

    baseline_row = _baseline_row("CDG-LIS-bucket_medium")

    f1 = _flight_for_analysis(price=110.0, destination="LIS")
    f1["id"] = "lis-1"
    f1["departure_date"] = "2026-05-12"
    f1["return_date"] = "2026-05-19"

    f2 = _flight_for_analysis(price=115.0, destination="LIS")
    f2["id"] = "lis-2"
    f2["departure_date"] = "2026-06-02"
    f2["return_date"] = "2026-06-09"

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 20}],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs, "_get_user_tier", return_value="premium"), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([f1, f2])

    assert send_grouped_mock.call_count == 1
    kwargs = send_grouped_mock.call_args.kwargs
    assert len(kwargs["offers"]) == 2
    assert kwargs["destination_iata"] == "LIS"


@pytest.mark.asyncio
async def test_grouped_flight_alert_different_destinations_separate_sends():
    """A CDG->LIS and a CDG->BCN flight produce 2 distinct grouped sends."""
    from app.scheduler import jobs

    # Baseline mock returns the same row for both routes — good enough since
    # the anomaly detector only compares avg/std to the incoming price.
    baseline_row = _baseline_row_cdg_bcn()

    f1 = _flight_for_analysis(price=110.0, destination="LIS")
    f1["id"] = "lis-1"
    f2 = _flight_for_analysis(price=110.0, destination="BCN")
    f2["id"] = "bcn-1"

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u1", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u1", "min_discount": 20}],
    )

    send_grouped_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs, "_get_user_tier", return_value="premium"), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([f1, f2])

    assert send_grouped_mock.call_count == 2
    destinations_sent = {
        call.kwargs["destination_iata"] for call in send_grouped_mock.call_args_list
    }
    assert destinations_sent == {"LIS", "BCN"}


@pytest.mark.asyncio
async def test_package_alert_filtered_by_user_min_discount():
    """User min_discount=50 blocks a 30% discount package alert in _compose_packages_for_flight."""
    from app.scheduler import jobs

    pkg = {
        "origin": "CDG",
        "destination": "BCN",
        "score": 80,
        "discount_pct": 30,
        "flight_id": "f-1",
        "accommodation_id": "a-1",
    }
    flight = _flight_for_analysis()
    flight_baseline = {"avg_price": 200.0, "sample_count": 50}

    # Build a db mock tailored to _compose_packages_for_flight
    acc_row = {
        "id": "a-1",
        "city": "Barcelona",
        "source": "booking",
        "check_in": flight["departure_date"],
        "check_out": flight["return_date"],
        "rating": 4.5,
        "name": "Test Hotel",
        "source_url": "http://example.com",
    }

    ra_table = MagicMock()
    ra_chain = (
        ra_table.select.return_value
        .eq.return_value
        .eq.return_value
        .eq.return_value
        .gte.return_value
        .gte.return_value
    )
    ra_chain.execute.return_value = MagicMock(data=[acc_row])
    # Also handle the raw_accommodations lookup by id: select().eq().execute()
    ra_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"name": "Test Hotel", "rating": 4.5, "source_url": "http://example.com"}]
    )

    pb_table = MagicMock()
    pb_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    pkg_table = MagicMock()
    pkg_table.insert.return_value.execute.return_value = MagicMock(data=[{}])

    rf_table = MagicMock()
    rf_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"source_url": "http://af.com", "airline": "AF"}]
    )

    ts_table = MagicMock()
    ts_table.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
        data=[{"chat_id": 123, "user_id": "u1"}]
    )

    up_table = MagicMock()
    up_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"user_id": "u1", "min_discount": 50}]
    )

    db_mock = MagicMock()

    def fake_table(name):
        return {
            "raw_accommodations": ra_table,
            "price_baselines": pb_table,
            "packages": pkg_table,
            "raw_flights": rf_table,
            "telegram_subscribers": ts_table,
            "user_preferences": up_table,
        }.get(name, MagicMock())

    db_mock.table.side_effect = fake_table

    # Build packages should return one package
    send_alert_mock = AsyncMock()
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "build_packages", return_value=[pkg]), \
         patch.object(jobs, "send_deal_alert", new=send_alert_mock), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._compose_packages_for_flight(flight, flight_baseline)

    send_alert_mock.assert_not_called()


@pytest.mark.asyncio
async def test_package_alert_dedup_skips_duplicate():
    """If a package's alert_key already exists in sent_alerts, send_deal_alert is skipped."""
    from app.scheduler import jobs
    from app.notifications.dedup import compute_alert_key

    flight = _flight_for_analysis()
    flight_baseline = {"avg_price": 200.0, "sample_count": 50}

    pkg = {
        "origin": "CDG",
        "destination": "BCN",
        "departure_date": flight["departure_date"],
        "return_date": flight["return_date"],
        "score": 80,
        "discount_pct": 45,
        "total_price": 500,
        "flight_id": "f-1",
        "accommodation_id": "a-1",
    }

    already_key = compute_alert_key(
        "u1",
        pkg["origin"],
        pkg["destination"],
        pkg["departure_date"],
        pkg["return_date"],
        pkg["total_price"],
    )

    acc_row = {
        "id": "a-1",
        "city": "Barcelona",
        "source": "booking",
        "check_in": flight["departure_date"],
        "check_out": flight["return_date"],
        "rating": 4.5,
        "name": "Test Hotel",
        "source_url": "http://example.com",
    }

    ra_table = MagicMock()
    ra_chain = (
        ra_table.select.return_value
        .eq.return_value
        .eq.return_value
        .eq.return_value
        .gte.return_value
        .gte.return_value
    )
    ra_chain.execute.return_value = MagicMock(data=[acc_row])
    ra_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"name": "Test Hotel", "rating": 4.5, "source_url": "http://example.com"}]
    )

    pb_table = MagicMock()
    pb_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    pkg_table = MagicMock()
    pkg_table.insert.return_value.execute.return_value = MagicMock(data=[{}])

    rf_table = MagicMock()
    rf_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"source_url": "http://af.com", "airline": "AF"}]
    )

    ts_table = MagicMock()
    ts_table.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
        data=[{"chat_id": 123, "user_id": "u1"}]
    )

    up_table = MagicMock()
    up_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"user_id": "u1", "min_discount": 20}]
    )

    # sent_alerts: .select("id").eq().eq().limit(1).execute() → already present
    sa_table = MagicMock()
    _pkg_last_key = {"value": None}

    def _pkg_eq_alert_key(column, value):
        if column == "alert_key":
            _pkg_last_key["value"] = value
        m = MagicMock()
        limit_mock = MagicMock()

        def _pkg_limit_execute():
            if _pkg_last_key["value"] == already_key:
                return MagicMock(data=[{"id": "existing"}])
            return MagicMock(data=[])

        limit_mock.execute.side_effect = _pkg_limit_execute
        m.limit.return_value = limit_mock
        return m

    sa_table.select.return_value.eq.return_value.eq.side_effect = _pkg_eq_alert_key
    sa_table.upsert.return_value.execute.return_value = MagicMock(data=[])

    db_mock = MagicMock()

    def fake_table(name):
        return {
            "raw_accommodations": ra_table,
            "price_baselines": pb_table,
            "packages": pkg_table,
            "raw_flights": rf_table,
            "telegram_subscribers": ts_table,
            "user_preferences": up_table,
            "sent_alerts": sa_table,
        }.get(name, MagicMock())

    db_mock.table.side_effect = fake_table

    send_alert_mock = AsyncMock(return_value=True)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "build_packages", return_value=[pkg]), \
         patch.object(jobs, "send_deal_alert", new=send_alert_mock), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._compose_packages_for_flight(flight, flight_baseline)

    send_alert_mock.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Phase D4 — Free tier strict <30% in dispatch
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_jobs_free_user_does_not_receive_30pct_grouped_alert():
    """A free-tier subscriber must NOT receive an offer with discount_pct >= 30.
    Even if their min_discount is 20, the tier-aware filter blocks it."""
    from app.scheduler import jobs

    baseline_row = _baseline_row_cdg_bcn()
    # price 130 -> (200-130)/200 = 35%, z = 70/25 = 2.8
    flight = _flight_for_analysis(price=130.0)

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 123, "user_id": "u_free", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u_free", "min_discount": 20}],
    )
    send_grouped_mock = AsyncMock(return_value=True)

    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs, "_get_user_tier", return_value="free"), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    send_grouped_mock.assert_not_called()


@pytest.mark.asyncio
async def test_jobs_premium_user_receives_30pct_grouped_alert():
    """A premium-tier subscriber receives a 35% offer normally."""
    from app.scheduler import jobs

    baseline_row = _baseline_row_cdg_bcn()
    flight = _flight_for_analysis(price=130.0)  # -35%

    db_mock = _build_alert_db_mock(
        baseline_row=baseline_row,
        subscribers=[{"chat_id": 456, "user_id": "u_prem", "airport_code": "CDG"}],
        user_prefs=[{"user_id": "u_prem", "min_discount": 20}],
    )
    send_grouped_mock = AsyncMock(return_value=True)

    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "send_grouped_flight_alerts", new=send_grouped_mock), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()), \
         patch.object(jobs, "_get_user_tier", return_value="premium"), \
         patch.object(jobs.settings, "MIN_SCORE_ALERT", 0):
        await jobs._analyze_new_flights([flight])

    send_grouped_mock.assert_called_once()
