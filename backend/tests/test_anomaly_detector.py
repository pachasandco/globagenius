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


# ── Filtre de dispersion : creux ponctuel vs prix plancher généralisé ───────
# Un deal légitime bat ses dates de départ voisines (±3j). Si le prix
# candidat est ~identique à la médiane de ses voisins, ce n'est pas une
# opportunité — c'est le prix normal de la période, faussement affiché en
# -X% à cause d'une baseline historique décalée. Mesuré 2026-07-22 :
# 12-22% des deals tranchables étaient ces faux plancher.

from app.analysis.anomaly_detector import is_generalized_floor


def test_generalized_floor_rejects_when_price_matches_neighbors():
    # 56€ vs voisins tous à 56€ → plancher généralisé (faux deal)
    assert is_generalized_floor(56.0, [56.0, 56.0, 55.0, 57.0]) is True


def test_generalized_floor_accepts_real_dip():
    # 16€ vs voisins médiane 25€ → ratio 0.64, vrai creux
    assert is_generalized_floor(16.0, [24.0, 25.0, 26.0, 25.0]) is False


def test_generalized_floor_indecisive_when_too_few_neighbors():
    # < 3 voisins → on ne tranche pas (ne jamais rejeter faute de données)
    assert is_generalized_floor(56.0, [56.0, 56.0]) is False
    assert is_generalized_floor(56.0, []) is False


def test_generalized_floor_boundary_ratio():
    # Ratio exactement au seuil 0.90 → rejeté (>= seuil)
    # candidat 90 vs médiane 100 → ratio 0.90
    assert is_generalized_floor(90.0, [100.0, 100.0, 100.0]) is True
    # candidat 89 vs médiane 100 → ratio 0.89 < 0.90 → vrai deal
    assert is_generalized_floor(89.0, [100.0, 100.0, 100.0]) is False


def test_generalized_floor_custom_thresholds():
    # Seuil plus strict configurable
    assert is_generalized_floor(80.0, [100.0, 100.0, 100.0], ratio_threshold=0.75) is True
    assert is_generalized_floor(80.0, [100.0, 100.0, 100.0], ratio_threshold=0.85) is False
    # min_neighbors configurable
    assert is_generalized_floor(100.0, [100.0, 100.0], min_neighbors=2) is True
