from app.config import Settings

def test_settings_defaults():
    s = Settings()
    assert s.MIN_DISCOUNT_PCT == 40
    assert s.MIN_SCORE_ALERT == 70
    assert s.MIN_SCORE_DIGEST == 50
    assert s.DATA_FRESHNESS_HOURS == 2
    assert s.MVP_AIRPORTS == ["CDG", "ORY", "LYS", "MRS", "NCE", "BOD", "NTE", "TLS"]

def test_iata_to_city_has_major_destinations():
    from app.config import IATA_TO_CITY
    assert "LIS" in IATA_TO_CITY
    assert "BCN" in IATA_TO_CITY
    assert "FCO" in IATA_TO_CITY

def test_destination_popularity_scores():
    from app.config import DESTINATION_POPULARITY
    assert all(0 <= v <= 100 for v in DESTINATION_POPULARITY.values())
    assert "BCN" in DESTINATION_POPULARITY
