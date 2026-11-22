from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from .config import Settings


password_hasher = PasswordHasher()


def verify_app_password(password: str, settings: Settings) -> bool:
    if not settings.app_password_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uwierzytelnianie nie jest jeszcze skonfigurowane.",
        )
    try:
        return password_hasher.verify(settings.app_password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_session_token(settings: Settings, hours: int = 12) -> tuple[str, datetime]:
    if not settings.app_session_signing_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sekret sesji nie jest jeszcze skonfigurowany.",
        )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    token = jwt.encode(
        {"sub": "owner", "exp": expires_at},
        settings.app_session_signing_secret,
        algorithm="HS256",
    )
    return token, expires_at


def require_session(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> dict[str, str]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wymagana sesja.")
    if not settings.app_session_signing_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sesja nie jest skonfigurowana.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.app_session_signing_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesja wygasła lub jest niepoprawna.") from exc
    return {"subject": str(payload.get("sub", "owner"))}

