"""Safe access to the Garmin Connect Personal API.

The Garmin Personal API key stays in the backend environment.  This module
only exposes connection metadata and never returns the API key or bearer
token to an HTTP response.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator
from garmin_personal_api.errors import GarminPersonalApiError, HttpError

from .config import Settings


GARMIN_CACHE_FILE = Path("/tmp/running-coach-garmin-bearer-token.json")


class GarminIntegrationError(RuntimeError):
    """An expected, safe-to-display Garmin integration error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GarminPersonalApi:
    """Authenticate with Garmin and expose the first read-only API operations."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.garmin_personal_api_key and self.settings.garmin_personal_api_key.strip())

    def _get_client(self) -> GarminPersonalApiClient:
        api_key = self.settings.garmin_personal_api_key
        if not api_key or not api_key.strip():
            raise GarminIntegrationError("Klucz Garmin Personal API nie jest skonfigurowany.")

        try:
            with PersonalApiAuthenticator(
                timeout=20,
                bearer_token_cache_file=GARMIN_CACHE_FILE,
            ) as authenticator:
                token = authenticator.obtain_token(api_key.strip())
        except HttpError as exc:
            raise self._from_http_error(exc) from exc
        except GarminPersonalApiError as exc:
            raise GarminIntegrationError("Klucz Garmin Personal API jest niepoprawny lub wygasł.") from exc
        except Exception as exc:  # pragma: no cover - defensive protection for vendor SDK errors
            raise GarminIntegrationError("Nie udało się uwierzytelnić w Garmin Personal API.") from exc

        return GarminPersonalApiClient(token.access_token, timeout=20)

    def check_connection(self) -> dict[str, Any]:
        """Verify the key and one documented read-only API endpoint."""

        client = self._get_client()
        try:
            profile = client.get_user_profile_settings()
            return {
                "connected": True,
                "profile_available": profile is not None,
            }
        except HttpError as exc:
            raise self._from_http_error(exc) from exc
        except GarminPersonalApiError as exc:
            raise GarminIntegrationError("Garmin odrzucił żądanie odczytu danych.") from exc
        except Exception as exc:  # pragma: no cover - defensive protection for vendor SDK errors
            raise GarminIntegrationError("Nie udało się odczytać danych z Garmin Personal API.") from exc
        finally:
            client.close()

    def list_activities(self, *, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """Read summarized activities with pagination, without writing anything yet."""

        client = self._get_client()
        page_size = 100
        start = 0
        activities: list[dict[str, Any]] = []

        try:
            while True:
                payload = client.search_activities(
                    start=start,
                    limit=page_size,
                    start_date=start_date,
                    end_date=end_date,
                )
                page = self._activity_items(payload)
                activities.extend(item for item in page if isinstance(item, dict))
                if len(page) < page_size:
                    return activities
                start += page_size
        except HttpError as exc:
            raise self._from_http_error(exc) from exc
        except GarminPersonalApiError as exc:
            raise GarminIntegrationError("Garmin odrzucił żądanie listy aktywności.") from exc
        except Exception as exc:  # pragma: no cover - defensive protection for vendor SDK errors
            raise GarminIntegrationError("Nie udało się pobrać listy aktywności z Garmina.") from exc
        finally:
            client.close()

    @staticmethod
    def _activity_items(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("activityList", "activities", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    @staticmethod
    def _from_http_error(error: HttpError) -> GarminIntegrationError:
        if error.status_code in (401, 403):
            return GarminIntegrationError(
                "Garmin odrzucił klucz. Sprawdź, czy Personal API Key jest aktywny i nie wygasł.",
                status_code=error.status_code,
            )
        if error.status_code == 429:
            return GarminIntegrationError(
                "Garmin chwilowo ograniczył liczbę żądań. Spróbuj ponownie za chwilę.",
                status_code=error.status_code,
            )
        return GarminIntegrationError(
            "Garmin chwilowo nie odpowiada. Spróbuj ponownie później.",
            status_code=error.status_code,
        )


def default_activity_window(settings: Settings) -> tuple[date, date]:
    end_date = date.today()
    return end_date - timedelta(days=settings.sync_lookback_days), end_date
