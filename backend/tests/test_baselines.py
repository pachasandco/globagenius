from app.analysis.baselines import compute_weighted_average, compute_baseline


def test_compute_weighted_average_simple():
    prices = [100.0, 200.0, 300.0]
    ages_days = [1.0, 1.0, 1.0]
    avg, std = compute_weighted_average(prices, ages_days)
    assert avg == 200.0
    assert std > 0


def test_compute_weighted_average_recent_bias():
    prices = [100.0, 300.0]
    ages_days = [1.0, 30.0]
    avg, _ = compute_weighted_average(prices, ages_days)
    assert avg < 200.0


def test_compute_weighted_average_empty():
    avg, std = compute_weighted_average([], [])
    assert avg == 0.0
    assert std == 0.0


def test_compute_baseline_returns_dict():
    observations = [
        {"price": 150.0, "scraped_at": "2026-04-06T10:00:00+00:00"},
        {"price": 180.0, "scraped_at": "2026-04-05T10:00:00+00:00"},
        {"price": 200.0, "scraped_at": "2026-04-01T10:00:00+00:00"},
        {"price": 170.0, "scraped_at": "2026-03-30T10:00:00+00:00"},
        {"price": 190.0, "scraped_at": "2026-03-28T10:00:00+00:00"},
        {"price": 160.0, "scraped_at": "2026-03-25T10:00:00+00:00"},
        {"price": 210.0, "scraped_at": "2026-03-22T10:00:00+00:00"},
        {"price": 175.0, "scraped_at": "2026-03-20T10:00:00+00:00"},
        {"price": 195.0, "scraped_at": "2026-03-18T10:00:00+00:00"},
        {"price": 185.0, "scraped_at": "2026-03-15T10:00:00+00:00"},
    ]
    result = compute_baseline("CDG-LIS", "flight", observations)
    assert result["route_key"] == "CDG-LIS"
    assert result["type"] == "flight"
    assert result["avg_price"] > 0
    assert result["std_dev"] > 0
    assert result["sample_count"] == 10


def test_compute_baseline_insufficient_data():
    observations = [
        {"price": 150.0, "scraped_at": "2026-04-06T10:00:00+00:00"},
    ]
    result = compute_baseline("CDG-LIS", "flight", observations)
    assert result is None


from app.analysis.baselines import compute_baselines_by_bucket, MIN_SAMPLE_COUNT


def _obs(price, duration_days=7, stops=0, duration_minutes=120, scraped_days_ago=1):
    from datetime import datetime, timedelta, timezone
    return {
        "price": price,
        "trip_duration_days": duration_days,
        "stops": stops,
        "duration_minutes": duration_minutes,
        "scraped_at": (datetime.now(timezone.utc) - timedelta(days=scraped_days_ago)).isoformat(),
    }


def test_min_sample_count_constant():
    assert MIN_SAMPLE_COUNT == 30


def test_compute_baselines_by_bucket_groups_by_bucket():
    short_obs = [_obs(100, duration_days=2) for _ in range(30)]
    medium_obs = [_obs(200, duration_days=7) for _ in range(30)]
    long_obs = [_obs(400, duration_days=14) for _ in range(30)]

    result = compute_baselines_by_bucket("CDG-BCN", short_obs + medium_obs + long_obs)

    assert len(result) == 3
    keys = sorted(b["route_key"] for b in result)
    assert keys == ["CDG-BCN-bucket_long", "CDG-BCN-bucket_medium", "CDG-BCN-bucket_short"]
    by_key = {b["route_key"]: b for b in result}
    assert by_key["CDG-BCN-bucket_short"]["avg_price"] == 100
    assert by_key["CDG-BCN-bucket_medium"]["avg_price"] == 200
    assert by_key["CDG-BCN-bucket_long"]["avg_price"] == 400


def test_compute_baselines_by_bucket_uses_median_not_mean():
    # 30 observations at 100, 1 outlier at 1000 -> median = 100, mean would be ~129
    obs = [_obs(100, duration_days=7) for _ in range(30)] + [_obs(1000, duration_days=7)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    medium = next(b for b in result if b["route_key"] == "CDG-BCN-bucket_medium")
    assert medium["avg_price"] == 100  # median, not mean


def test_compute_baselines_by_bucket_excludes_short_haul_with_stops():
    # 30 valid direct flights + 5 stopover flights, all duration_minutes=120 (short-haul)
    direct = [_obs(100, stops=0, duration_minutes=120) for _ in range(30)]
    with_stops = [_obs(60, stops=1, duration_minutes=120) for _ in range(5)]
    result = compute_baselines_by_bucket("CDG-BCN", direct + with_stops)
    medium = next(b for b in result if b["route_key"] == "CDG-BCN-bucket_medium")
    assert medium["sample_count"] == 30
    assert medium["avg_price"] == 100  # outliers with stops excluded


def test_compute_baselines_by_bucket_excludes_long_haul_with_2_plus_stops():
    # Long-haul: duration_minutes=600 -> max 1 stop allowed
    valid = [_obs(500, stops=1, duration_minutes=600) for _ in range(30)]
    too_many_stops = [_obs(300, stops=2, duration_minutes=600) for _ in range(5)]
    result = compute_baselines_by_bucket("CDG-JFK", valid + too_many_stops)
    medium = next(b for b in result if b["route_key"] == "CDG-JFK-bucket_medium")
    assert medium["sample_count"] == 30


def test_compute_baselines_by_bucket_minimum_sample_count_not_met():
    obs = [_obs(100, duration_days=7) for _ in range(29)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    assert result == []  # no bucket gets 30 observations


def test_compute_baselines_by_bucket_minimum_sample_count_met_exactly():
    obs = [_obs(100, duration_days=7) for _ in range(30)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    assert len(result) == 1
    assert result[0]["sample_count"] == 30


def test_compute_baselines_by_bucket_ignores_observations_outside_buckets():
    # 30 valid medium + 5 with duration_days=30 (out of range)
    obs = [_obs(100, duration_days=7) for _ in range(30)] + [_obs(50, duration_days=30) for _ in range(5)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    medium = next(b for b in result if b["route_key"] == "CDG-BCN-bucket_medium")
    assert medium["sample_count"] == 30
    assert medium["avg_price"] == 100


def test_compute_baselines_by_bucket_returns_baselines_with_required_fields():
    obs = [_obs(100, duration_days=7) for _ in range(30)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    assert len(result) == 1
    b = result[0]
    assert "route_key" in b
    assert "type" in b
    assert b["type"] == "flight"
    assert "avg_price" in b
    assert "std_dev" in b
    assert "sample_count" in b
    assert "calculated_at" in b
