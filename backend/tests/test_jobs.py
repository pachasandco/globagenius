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


def test_get_scheduler_jobs_flight_every_4h():
    jobs = get_scheduler_jobs()
    flight_jobs = [j for j in jobs if j["id"].startswith("scrape_flights")]
    assert len(flight_jobs) == 6
    hours = sorted([j["hour"] for j in flight_jobs])
    assert hours == [2, 6, 10, 14, 18, 22]


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
    db_mock = MagicMock()
    baseline_row = {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": 25,  # below MIN_SAMPLE_COUNT
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
    # baseline avg 200, price 140 -> -30%, z = (200-140)/25 = 2.4 (safely above 2.0 floor)
    flight = _flight_for_analysis(price=140.0)
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
