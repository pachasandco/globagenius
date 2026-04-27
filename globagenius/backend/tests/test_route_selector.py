from app.analysis.route_selector import is_long_haul, LONG_HAUL_DESTINATIONS


def test_long_haul_set_contains_expected_destinations():
    expected = {"NRT", "JFK", "BKK", "YUL", "DXB", "MIA", "SYD",
                "CUN", "PUJ", "MLE", "MRU", "RUN", "GIG", "LAX",
                "HND", "ICN", "HKG", "SIN", "KUL", "DEL", "BOM",
                "BOG", "LIM", "EZE", "SCL", "JNB", "CPT", "ZNZ"}
    assert expected == LONG_HAUL_DESTINATIONS


def test_is_long_haul_returns_true_for_long_haul_codes():
    assert is_long_haul("JFK") is True
    assert is_long_haul("BKK") is True
    assert is_long_haul("SYD") is True


def test_is_long_haul_returns_false_for_short_haul_codes():
    assert is_long_haul("BCN") is False
    assert is_long_haul("LIS") is False
    assert is_long_haul("RAK") is False


def test_is_long_haul_handles_unknown_codes():
    assert is_long_haul("XXX") is False
