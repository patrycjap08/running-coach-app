from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .auth import create_session_token, require_session, verify_app_password
from .config import get_settings


settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
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

