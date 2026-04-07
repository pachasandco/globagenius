from app.analysis.anomaly_detector import detect_anomaly, QualifiedItem


def test_detect_anomaly_qualifies(sample_baseline_flight):
    result = detect_anomaly(price=89.0, baseline=sample_baseline_flight)
    assert result is not None
    assert isinstance(result, QualifiedItem)
    assert result.discount_pct >= 40.0
    assert result.z_score > 2.0


def test_detect_anomaly_below_z_threshold(sample_baseline_flight):
    result = detect_anomaly(price=170.0, baseline=sample_baseline_flight)
    assert result is None


def test_detect_anomaly_below_discount_threshold(sample_baseline_flight):
    # Price 130, baseline 198 → 34% discount, z=1.51 → qualifies now (>= 20%, z >= 1.0)
    result = detect_anomaly(price=130.0, baseline=sample_baseline_flight)
    assert result is not None
    assert result.discount_pct >= 20.0


def test_detect_anomaly_below_minimum_threshold():
    # Price 170, baseline 198, std 45 → 14% discount, below 20% minimum
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
