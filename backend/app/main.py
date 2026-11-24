import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
        all_rows = _read_rows(data_store.read_text("activities.csv"))
        rows = sorted(
            all_rows.values(),
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
        form_summary = _read_form_summary()
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
        "stats": _dashboard_stats(list(all_rows.values())),
        "form_summary": form_summary,
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


def _read_form_summary() -> dict[str, object] | None:
    summary_text = data_store.read_text_optional("form_summary.json")
    if not summary_text:
        return None
    try:
        payload = json.loads(summary_text)
    except json.JSONDecodeError:
        return None
    result = payload.get("result") if isinstance(payload, dict) else None
    return result if isinstance(result, dict) else None


def _dashboard_stats(rows: list[dict[str, str]]) -> dict[str, object]:
    today = datetime.now(ZoneInfo(settings.timezone)).date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    running_rows = [
        row
        for row in rows
        if row.get("sport") in {"running", "treadmill_running", "track_running", "trail_running"}
    ]

    def row_date(row: dict[str, str]) -> date | None:
        try:
            return date.fromisoformat(row.get("start_date_local", ""))
        except ValueError:
            return None

    def distance(rows_to_sum: list[dict[str, str]]) -> float:
        return sum(float(row.get("distance_m") or 0) for row in rows_to_sum) / 1000

    weekly_volume: list[dict[str, object]] = []
    current_week = week_start - timedelta(days=11 * 7)
    for index in range(12):
        week_end = current_week + timedelta(days=7)
        volume = distance(
            [row for row in running_rows if (row_date(row) or date.min) >= current_week and (row_date(row) or date.min) < week_end]
        )
        weekly_volume.append({"label": f"T{index + 1}", "km": round(volume, 2)})
        current_week += timedelta(days=7)

    return {
        "week_distance_km": round(distance([row for row in running_rows if (row_date(row) or date.min) >= week_start]), 2),
        "month_distance_km": round(distance([row for row in running_rows if (row_date(row) or date.min) >= month_start]), 2),
        "run_count_week": sum(1 for row in running_rows if (row_date(row) or date.min) >= week_start),
        "weekly_volume": weekly_volume,
    }
