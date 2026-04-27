from app.analysis.anomaly_detector import detect_anomaly, QualifiedItem


def test_detect_anomaly_qualifies(sample_baseline_flight):
    # Price 89, baseline 198, std 45 → z=2.42, discount=55% → good_deal (z < 2.5)
    result = detect_anomaly(price=89.0, baseline=sample_baseline_flight)
    assert result is not None
    assert isinstance(result, QualifiedItem)
    assert result.discount_pct >= 40.0
    assert result.alert_level == "good_deal"


def test_detect_anomaly_good_deal():
    # Price 130, baseline 198, std 45 → z=1.51, discount=34% → good_deal
    baseline = {"avg_price": 198.0, "std_dev": 45.0, "sample_count": 25}
    result = detect_anomaly(price=130.0, baseline=baseline)
    assert result is not None
    assert result.alert_level == "good_deal"


def test_detect_anomaly_real_fare_mistake():
    # Price 50, baseline 300, std 60 → z=4.17, discount=83% → fare_mistake
    baseline = {"avg_price": 300.0, "std_dev": 60.0, "sample_count": 30}
    result = detect_anomaly(price=50.0, baseline=baseline)
    assert result is not None
    assert result.alert_level == "fare_mistake"
    assert result.discount_pct >= 60


def test_detect_anomaly_below_z_threshold(sample_baseline_flight):
    # Price 170, baseline 198, std 45 → z=0.62, discount=14% → no deal
    result = detect_anomaly(price=170.0, baseline=sample_baseline_flight)
    assert result is None


def test_detect_anomaly_below_minimum_threshold():
    baseline = {"avg_price": 198.0, "std_dev": 45.0, "sample_count": 25}
    result = detect_anomaly(price=170.0, baseline=baseline)
    assert result is None


def test_detect_anomaly_zero_std_dev():
    baseline = {"avg_price": 200.0, "std_dev": 0.0, "sample_count": 15}
    result = detect_anomaly(price=100.0, baseline=baseline)
    assert result is None


def test_detect_anomaly_price_higher_than_baseline():
    baseline = {"avg_price": 100.0, "std_dev": 20.0, "sample_count": 15}
    result = detect_anomaly(price=150.0, baseline=baseline)
    assert result is None
