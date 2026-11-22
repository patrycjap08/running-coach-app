from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz_is_public() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["garmin_configured"], bool)


def test_dashboard_is_public() -> None:
    response = client.get("/api/dashboard")
    assert response.status_code in {200, 502}


def test_garmin_status_is_public() -> None:
    response = client.get("/api/garmin/status")
    assert response.status_code in {200, 502}


def test_garmin_status_does_not_expose_configuration_without_session() -> None:
    response = client.get("/api/garmin/status")
    assert "GARMIN_PERSONAL_API_KEY" not in response.text


def test_sync_is_public() -> None:
    response = client.post("/api/sync")
    assert response.status_code != 401
