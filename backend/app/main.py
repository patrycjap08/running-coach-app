import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .data_store import GitHubDataStore
from .garmin import GarminIntegrationError, GarminPersonalApi, default_activity_window
from .sync import SyncError, _read_rows, sync_data


settings = get_settings()
garmin_api = GarminPersonalApi(settings)
data_store = GitHubDataStore(settings)
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {
        "status": "ok",
        "environment": settings.environment,
        "garmin_configured": garmin_api.configured,
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, object]:
    if not data_store.configured:
        return {
            "schema_version": 1,
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "status": "demo",
            "message": "Repozytorium danych nie jest jeszcze skonfigurowane.",
            "activities": [],
        }
    try:
        rows = sorted(
            _read_rows(data_store.read_text("activities.csv")).values(),
            key=lambda row: (row.get("start_at_utc", ""), row.get("activity_id", "")),
            reverse=True,
        )[: settings.recent_run_count]
        activities: list[dict[str, object]] = []
        for row in rows:
            activity_path_id = "".join(
                character if character.isalnum() or character in "-_" else "_"
                for character in row["activity_id"]
            )
            analysis_text = data_store.read_text_optional(
                f"analyses/{activity_path_id}/v1-{row['source_fingerprint'][:16]}.json"
            )
            analysis: dict[str, object] | None = None
            if analysis_text:
                try:
                    payload = json.loads(analysis_text)
                    analysis = payload.get("result") if isinstance(payload, dict) else None
                except json.JSONDecodeError:
                    analysis = None
            activities.append({"activity": row, "analysis": analysis})
    except Exception as exc:
        if isinstance(exc, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
            raise HTTPException(status_code=502, detail="Dane w repozytorium mają niepoprawny format.") from exc
        raise HTTPException(status_code=502, detail="Nie udało się odczytać danych treningowych.") from exc
    return {
        "schema_version": 1,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
        "status": "connected",
        "message": "Dane z prywatnego repozytorium.",
        "activities": activities,
    }


@app.get("/api/garmin/status")
def garmin_status() -> dict[str, object]:
    """Check the Garmin key without exposing credentials or Garmin profile data."""

    if not garmin_api.configured:
        return {"configured": False, "connected": False, "message": "Klucz Garmin nie jest jeszcze skonfigurowany."}

    try:
        connection = garmin_api.check_connection()
    except GarminIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"configured": True, **connection}


@app.post("/api/garmin/preview")
def garmin_preview() -> dict[str, object]:
    """Read the recent activity count as a safe first sync verification step."""

    start_date, end_date = default_activity_window(settings)
    try:
        activities = garmin_api.list_activities(start_date=start_date, end_date=end_date)
    except GarminIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "status": "ready",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "activity_count": len(activities),
        "message": "Połączenie z Garminem działa. To jest podgląd bez zapisu danych.",
    }


@app.post("/api/sync")
def sync() -> dict[str, object]:
    """Fetch and persist normalized Garmin summaries in the private data repo."""

    try:
        return sync_data(settings, garmin_api, data_store)
    except SyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
