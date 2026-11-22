from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz_is_public() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_private_dashboard_requires_session() -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 401

