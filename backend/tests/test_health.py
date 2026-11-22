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


def test_private_garmin_status_requires_session() -> None:
    response = client.get("/api/garmin/status")
    assert response.status_code == 401


def test_garmin_status_does_not_expose_configuration_without_session() -> None:
    response = client.get("/api/garmin/status")
    assert "GARMIN_PERSONAL_API_KEY" not in response.text
