import pytest


@pytest.fixture
def sample_flight_raw():
    """Raw flight data as returned by Apify actor."""
    return {
        "price": 89.0,
        "currency": "EUR",
        "origin": "CDG",
        "destination": "LIS",
        "departureDate": "2026-05-10",
        "returnDate": "2026-05-17",
        "airline": "TAP Portugal",
        "stops": 0,
        "url": "https://www.skyscanner.fr/transport/flights/cdg/lis/260510/260517",
    }


@pytest.fixture
def sample_accommodation_raw():
    """Raw accommodation data as returned by Apify actor."""
    return {
        "name": "Hotel Lisboa Plaza",
        "city": "Lisbon",
        "pricePerNight": 60.0,
        "totalPrice": 420.0,
        "currency": "EUR",
        "rating": 4.3,
        "checkIn": "2026-05-10",
        "checkOut": "2026-05-17",
        "url": "https://www.booking.com/hotel/pt/lisboa-plaza.html",
        "source": "booking",
    }


@pytest.fixture
def sample_baseline_flight():
    """Baseline for CDG-LIS route."""
    return {
        "route_key": "CDG-LIS",
        "type": "flight",
        "avg_price": 198.0,
        "std_dev": 45.0,
        "sample_count": 25,
    }


@pytest.fixture
def sample_baseline_accommodation():
    """Baseline for Lisbon-booking accommodations."""
    return {
        "route_key": "lisbon-booking",
        "type": "accommodation",
        "avg_price": 780.0,
        "std_dev": 120.0,
        "sample_count": 30,
    }
