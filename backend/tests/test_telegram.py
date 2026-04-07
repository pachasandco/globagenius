from app.notifications.telegram import format_deal_alert, format_admin_report, format_digest


def test_format_deal_alert():
    package = {
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "flight_price": 89.0,
        "accommodation_price": 420.0,
        "total_price": 509.0,
        "discount_pct": 47.9,
        "score": 84,
    }
    flight = {"source_url": "https://flights.example.com", "airline": "TAP Portugal"}
    accommodation = {
        "name": "Hotel Lisboa Plaza",
        "rating": 4.3,
        "source_url": "https://hotel.example.com",
    }
    msg = format_deal_alert(package, flight, accommodation)
    assert "Lisbon" in msg or "CDG" in msg  # City name or IATA code
    assert "509" in msg
    assert "47.9" in msg
    assert "84" in msg
    assert "https://flights.example.com" in msg
    assert "https://hotel.example.com" in msg


def test_format_admin_report():
    stats = {
        "flight_scrapes": 12,
        "accommodation_scrapes": 6,
        "total_flights": 2340,
        "total_accommodations": 1890,
        "errors": 2,
        "packages_qualified": 47,
        "qualification_rate": 3.2,
        "alerts_sent": 12,
        "active_baselines": 186,
    }
    msg = format_admin_report(stats)
    assert "12" in msg
    assert "47" in msg
    assert "3.2" in msg


def test_format_digest():
    packages = [
        {
            "origin": "CDG",
            "destination": "LIS",
            "total_price": 509.0,
            "discount_pct": 47.9,
            "score": 84,
            "departure_date": "2026-05-10",
            "return_date": "2026-05-17",
        },
        {
            "origin": "LYS",
            "destination": "BCN",
            "total_price": 320.0,
            "discount_pct": 52.1,
            "score": 78,
            "departure_date": "2026-05-15",
            "return_date": "2026-05-20",
        },
    ]
    msg = format_digest(packages)
    assert "CDG" in msg
    assert "LYS" in msg
    assert "Top" in msg or "top" in msg or "DIGEST" in msg
