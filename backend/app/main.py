from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .auth import create_session_token, require_session, verify_app_password
from .config import get_settings
from .garmin import GarminIntegrationError, GarminPersonalApi, default_activity_window


settings = get_settings()
garmin_api = GarminPersonalApi(settings)
bearer_scheme = HTTPBearer(auto_error=False)
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


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    if not verify_app_password(payload.password, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Niepoprawne hasło.")
    token, expires_at = create_session_token(settings)
    return LoginResponse(access_token=token, expires_at=expires_at)


@app.get("/api/dashboard")
def dashboard(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, object]:
    require_session(credentials, settings)
    return {
        "schema_version": 1,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
        "status": "demo",
        "message": "Backend jest gotowy na podłączenie synchronizacji Garmin.",
        "activities": [],
    }


@app.get("/api/garmin/status")
def garmin_status(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, object]:
    """Check the Garmin key without exposing credentials or Garmin profile data."""

    require_session(credentials, settings)
    if not garmin_api.configured:
        return {"configured": False, "connected": False, "message": "Klucz Garmin nie jest jeszcze skonfigurowany."}

    try:
        connection = garmin_api.check_connection()
    except GarminIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"configured": True, **connection}


@app.post("/api/garmin/preview")
def garmin_preview(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, object]:
    """Read the recent activity count as a safe first sync verification step."""

    require_session(credentials, settings)
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
        "message": "Połączenie z Garminem działa. Zapis znormalizowanych danych będzie kolejnym krokiem synchronizacji.",
    }
