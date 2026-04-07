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
    result = detect_anomaly(price=130.0, baseline=sample_baseline_flight)
    assert result is None


def test_detect_anomaly_zero_std_dev():
    baseline = {"avg_price": 200.0, "std_dev": 0.0, "sample_count": 15}
    result = detect_anomaly(price=100.0, baseline=baseline)
    assert result is None


def test_detect_anomaly_price_higher_than_baseline():
    baseline = {"avg_price": 100.0, "std_dev": 20.0, "sample_count": 15}
    result = detect_anomaly(price=150.0, baseline=baseline)
    assert result is None
