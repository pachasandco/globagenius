from app.composer.package_builder import build_packages, match_accommodations


def test_match_accommodations_finds_compatible():
    flight = {
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.3,
            "total_price": 420.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
        {
            "id": "acc-2",
            "city": "Lisbon",
            "check_in": "2026-05-11",
            "check_out": "2026-05-17",
            "rating": 4.5,
            "total_price": 500.0,
            "source": "airbnb",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    matches = match_accommodations(flight, accommodations)
    assert len(matches) == 1
    assert matches[0]["id"] == "acc-1"


def test_match_accommodations_filters_low_rating():
    flight = {
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 3.5,
            "total_price": 300.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    matches = match_accommodations(flight, accommodations)
    assert len(matches) == 0


def test_build_packages_creates_qualified():
    flight = {
        "id": "flight-1",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "price": 89.0,
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.3,
            "total_price": 420.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    flight_baseline = {"avg_price": 198.0, "std_dev": 45.0}
    accommodation_baselines = {"lisbon-booking": {"avg_price": 780.0, "std_dev": 120.0}}

    packages = build_packages(
        flight=flight,
        accommodations=accommodations,
        flight_baseline=flight_baseline,
        accommodation_baselines=accommodation_baselines,
    )
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg["flight_id"] == "flight-1"
    assert pkg["accommodation_id"] == "acc-1"
    assert pkg["total_price"] == 509.0
    assert pkg["discount_pct"] >= 40.0
    assert pkg["score"] > 0


def test_build_packages_rejects_low_discount():
    flight = {
        "id": "flight-1",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "price": 180.0,
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.3,
            "total_price": 700.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    flight_baseline = {"avg_price": 198.0, "std_dev": 45.0}
    accommodation_baselines = {"lisbon-booking": {"avg_price": 780.0, "std_dev": 120.0}}

    packages = build_packages(
        flight=flight,
        accommodations=accommodations,
        flight_baseline=flight_baseline,
        accommodation_baselines=accommodation_baselines,
    )
    assert len(packages) == 0


def test_build_packages_limits_to_3():
    flight = {
        "id": "flight-1",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "price": 50.0,
    }
    accommodations = [
        {
            "id": f"acc-{i}",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.0 + i * 0.1,
            "total_price": 200.0 + i * 10,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        }
        for i in range(5)
    ]
    flight_baseline = {"avg_price": 198.0, "std_dev": 45.0}
    accommodation_baselines = {"lisbon-booking": {"avg_price": 780.0, "std_dev": 120.0}}

    packages = build_packages(
        flight=flight,
        accommodations=accommodations,
        flight_baseline=flight_baseline,
        accommodation_baselines=accommodation_baselines,
    )
    assert len(packages) <= 3
