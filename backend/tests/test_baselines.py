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
