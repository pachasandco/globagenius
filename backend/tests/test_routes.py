from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], count=0)

        response = client.get("/api/status")
        assert response.status_code == 200


def test_packages_list_free_enriches_with_flight_info():
    """/api/packages?plan=free returns qualified_items enriched with the
    underlying raw_flights row (origin, destination, dates, source_url...)."""
    fake_qi = [{
        "id": "qi-1",
        "item_id": "flight-1",
        "tier": "free",
        "price": 150.0,
        "baseline_price": 220.0,
        "discount_pct": 31.8,
        "score": 48,
        "created_at": "2026-04-14T08:00:00+00:00",
    }]
    fake_flights = [{
        "id": "flight-1",
        "origin": "CDG",
        "destination": "BCN",
        "departure_date": "2026-05-12",
        "return_date": "2026-05-17",
        "airline": "VY",
        "stops": 0,
        "source_url": "https://www.aviasales.com/search/CDG1205BCN17051",
        "trip_duration_days": 5,
        "duration_minutes": 105,
    }]

    qi_table = MagicMock()
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=fake_qi)

    rf_table = MagicMock()
    rf_table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=fake_flights)

    with patch("app.api.routes.db") as mock_db:
        mock_db.table.side_effect = lambda name: {
            "qualified_items": qi_table,
            "raw_flights": rf_table,
        }[name]
        response = client.get("/api/packages?plan=free")
        assert response.status_code == 200
        body = response.json()
        assert body["plan"] == "free"
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["origin"] == "CDG"
        assert item["destination"] == "BCN"
        assert item["airline"] == "VY"
        assert item["tier"] == "free"
        assert item["price"] == 150.0
        assert item["baseline_price"] == 220.0
        assert item["source_url"].startswith("https://www.aviasales.com")


def test_packages_list_premium_same_enrichment_path():
    """plan=premium uses the same enrichment path with a gte 40 filter."""
    fake_qi = [{
        "id": "qi-2",
        "item_id": "flight-2",
        "tier": "premium",
        "price": 90.0,
        "baseline_price": 180.0,
        "discount_pct": 50.0,
        "score": 59,
        "created_at": "2026-04-14T08:00:00+00:00",
    }]
    fake_flights = [{
        "id": "flight-2",
        "origin": "CDG",
        "destination": "TUN",
        "departure_date": "2026-06-01",
        "return_date": "2026-06-08",
        "airline": "AF",
        "stops": 0,
        "source_url": "https://www.aviasales.com/search/...",
        "trip_duration_days": 7,
        "duration_minutes": 150,
    }]

    qi_table = MagicMock()
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=fake_qi)

    rf_table = MagicMock()
    rf_table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=fake_flights)

    with patch("app.api.routes.db") as mock_db:
        mock_db.table.side_effect = lambda name: {
            "qualified_items": qi_table,
            "raw_flights": rf_table,
        }[name]
        response = client.get("/api/packages?plan=premium")
        assert response.status_code == 200
        body = response.json()
        assert body["plan"] == "premium"
        assert len(body["items"]) == 1
        assert body["items"][0]["tier"] == "premium"
        assert body["items"][0]["discount_pct"] == 50.0


def test_packages_list_empty_returns_no_items():
    qi_table = MagicMock()
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.routes.db") as mock_db:
        mock_db.table.side_effect = lambda name: {"qualified_items": qi_table}[name]
        response = client.get("/api/packages?plan=free")
        assert response.status_code == 200
        assert response.json() == {"items": [], "plan": "free"}


def test_packages_detail_not_found():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        response = client.get("/api/packages/nonexistent-id")
        assert response.status_code == 404
