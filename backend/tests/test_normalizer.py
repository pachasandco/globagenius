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


# ─── V5: one-way flights ───

def test_compute_flight_hash_round_trip_legacy_format():
    # Round-trip default (no trip_type / direction passed) must keep the
    # legacy 6-field format so existing raw_flights.hash rows stay stable.
    h_default = compute_flight_hash("CDG", "LIS", "2026-05-10", "2026-05-17", 89.0, "skyscanner")
    h_explicit = compute_flight_hash(
        "CDG", "LIS", "2026-05-10", "2026-05-17", 89.0, "skyscanner",
        trip_type="round_trip", direction=None,
    )
    legacy = hashlib.sha256("CDG|LIS|2026-05-10|2026-05-17|89.0|skyscanner".encode()).hexdigest()
    assert h_default == legacy
    assert h_explicit == legacy


def test_compute_flight_hash_oneway_distinct_from_round_trip():
    h_rt = compute_flight_hash("CDG", "LIS", "2026-05-10", "2026-05-17", 89.0, "tp")
    h_ow = compute_flight_hash(
        "CDG", "LIS", "2026-05-10", None, 89.0, "tp",
        trip_type="one_way", direction="outbound",
    )
    assert h_rt != h_ow


def test_compute_flight_hash_oneway_outbound_vs_inbound_distinct():
    h_out = compute_flight_hash(
        "CDG", "LIS", "2026-05-10", None, 89.0, "tp",
        trip_type="one_way", direction="outbound",
    )
    h_in = compute_flight_hash(
        "CDG", "LIS", "2026-05-10", None, 89.0, "tp",
        trip_type="one_way", direction="inbound",
    )
    assert h_out != h_in


def test_normalize_flight_one_way_outbound():
    raw = {
        "origin": "CDG",
        "destination": "JFK",
        "departureDate": "2026-06-01",
        "returnDate": None,
        "price": 220.0,
        "currency": "EUR",
        "airline": "FB",
        "stops": 0,
        "tripType": "one_way",
        "direction": "outbound",
    }
    result = normalize_flight(raw, source="travelpayouts")
    assert result["trip_type"] == "one_way"
    assert result["direction"] == "outbound"
    assert result["return_date"] is None
    assert result["price"] == 220.0


def test_normalize_flight_one_way_requires_direction():
    raw = {
        "origin": "CDG",
        "destination": "JFK",
        "departureDate": "2026-06-01",
        "returnDate": None,
        "price": 220.0,
        "currency": "EUR",
        "tripType": "one_way",
        # direction missing
    }
    try:
        normalize_flight(raw, source="travelpayouts")
    except ValueError:
        return
    raise AssertionError("normalize_flight should reject one_way without direction")


def test_normalize_flight_round_trip_default(sample_flight_raw):
    # Without tripType/direction, behaviour must stay identical to pre-V5.
    result = normalize_flight(sample_flight_raw, source="skyscanner")
    assert result["trip_type"] == "round_trip"
    assert result["direction"] is None
    assert result["return_date"] is not None
