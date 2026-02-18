from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "listings_count" in payload


def test_metrics_endpoint() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "count_scanned" in payload


def test_dashboard_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Autonomous Dublin Yield Scanner" in response.text
