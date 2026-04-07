import hashlib
from app.scraper.normalizer import (
    normalize_flight,
    normalize_accommodation,
    compute_flight_hash,
    compute_accommodation_hash,
)


def test_normalize_flight(sample_flight_raw):
    result = normalize_flight(sample_flight_raw, source="skyscanner")
    assert result["origin"] == "CDG"
    assert result["destination"] == "LIS"
    assert result["price"] == 89.0
    assert result["source"] == "skyscanner"
    assert result["hash"] is not None
    assert result["expires_at"] is not None


def test_normalize_flight_converts_currency(sample_flight_raw):
    sample_flight_raw["currency"] = "USD"
    sample_flight_raw["price"] = 100.0
    result = normalize_flight(sample_flight_raw, source="skyscanner")
    assert result["price"] != 100.0
    assert result["price"] > 0


def test_normalize_accommodation(sample_accommodation_raw):
    result = normalize_accommodation(sample_accommodation_raw)
    assert result["city"] == "Lisbon"
    assert result["name"] == "Hotel Lisboa Plaza"
    assert result["total_price"] == 420.0
    assert result["rating"] == 4.3
    assert result["source"] == "booking"
    assert result["hash"] is not None


def test_normalize_accommodation_lowercases_city():
    raw = {
        "name": "Test Hotel",
        "city": "LISBON",
        "pricePerNight": 50.0,
        "totalPrice": 350.0,
        "currency": "EUR",
        "rating": 4.0,
        "checkIn": "2026-05-10",
        "checkOut": "2026-05-17",
        "url": "https://example.com",
        "source": "airbnb",
    }
    result = normalize_accommodation(raw)
    assert result["city"] == "Lisbon"


def test_compute_flight_hash():
    h = compute_flight_hash("CDG", "LIS", "2026-05-10", "2026-05-17", 89.0, "skyscanner")
    expected = hashlib.sha256("CDG|LIS|2026-05-10|2026-05-17|89.0|skyscanner".encode()).hexdigest()
    assert h == expected


def test_compute_accommodation_hash():
    h = compute_accommodation_hash("Lisbon", "Hotel Lisboa Plaza", "2026-05-10", "2026-05-17", 420.0, "booking")
    expected = hashlib.sha256("Lisbon|Hotel Lisboa Plaza|2026-05-10|2026-05-17|420.0|booking".encode()).hexdigest()
    assert h == expected
