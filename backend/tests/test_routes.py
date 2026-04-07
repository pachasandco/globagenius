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


def test_packages_list():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "pkg-1", "score": 80}]
        )
        response = client.get("/api/packages")
        assert response.status_code == 200


def test_packages_detail_not_found():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        response = client.get("/api/packages/nonexistent-id")
        assert response.status_code == 404
