"""Incremental Garmin summary sync into the private data repository."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo

from .config import Settings
from .data_store import DataStoreError, GitHubDataStore
from .garmin import GarminIntegrationError, GarminPersonalApi


ACTIVITY_COLUMNS = [
    "activity_id",
    "start_at_utc",
    "start_date_local",
    "sport",
    "subsport",
    "title",
    "distance_m",
    "moving_s",
    "elapsed_s",
    "avg_pace_s_km",
    "avg_hr_bpm",
    "max_hr_bpm",
    "avg_power_w",
    "avg_cadence_spm",
    "elevation_gain_m",
    "elevation_loss_m",
    "calories",
    "aerobic_te",
    "anaerobic_te",
    "training_load",
    "device_source",
    "details_status",
    "analysis_status",
    "source_fingerprint",
    "imported_at",
    "updated_at",
]

sync_lock = Lock()


class SyncError(RuntimeError):
    """A safe-to-display synchronization error."""


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _first(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return None


def _activity_type(raw: dict[str, Any]) -> tuple[str, str]:
    nested = raw.get("activityType")
    if isinstance(nested, dict):
        return (
            str(_first(nested, "typeKey", "parentTypeKey") or "unknown"),
            str(_first(nested, "typeKey", "subTypeKey") or "unknown"),
        )
    sport = _first(raw, "activityTypeKey", "sportType", "sport")
    subsport = _first(raw, "activitySubTypeKey", "subSportType", "subsport")
    return str(sport or "unknown"), str(subsport or "unknown")


def _parse_datetime(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_activity(raw: dict[str, Any], *, imported_at: str, timezone_name: str = "Europe/Warsaw") -> dict[str, str]:
    activity_id = str(_first(raw, "activityId", "activity_id", "id") or "")
    sport, subsport = _activity_type(raw)
    started = _parse_datetime(_first(raw, "startTimeGMT", "startTimeUtc", "start_at_utc", "startTimeLocal"))
    start_at_utc = started.isoformat().replace("+00:00", "Z") if started else ""
    distance = _number(_first(raw, "distance", "distance_m"))
    moving_s = _number(_first(raw, "movingDuration", "moving_s", "timerDuration"))
    elapsed_s = _number(_first(raw, "elapsedDuration", "elapsed_s", "duration"))
    distance_m = float(distance) if distance is not None else None
    moving_seconds = float(moving_s) if moving_s is not None else None
    is_running = sport in {"running", "treadmill_running", "track_running", "trail_running"}
    pace = None
    if is_running and distance_m and distance_m > 0 and moving_seconds and moving_seconds > 0:
        pace = moving_seconds / (distance_m / 1000)
    normalized = {
        "activity_id": activity_id,
        "start_at_utc": start_at_utc,
        "start_date_local": (started.astimezone(ZoneInfo(timezone_name)).date().isoformat() if started else ""),
        "sport": sport,
        "subsport": subsport,
        "title": "Bieg" if is_running else "Aktywność",
        "distance_m": _text(distance),
        "moving_s": _text(moving_s),
        "elapsed_s": _text(elapsed_s),
        "avg_pace_s_km": _text(pace),
        "avg_hr_bpm": _text(_first(raw, "averageHR", "avg_hr_bpm")),
        "max_hr_bpm": _text(_first(raw, "maxHR", "max_hr_bpm")),
        "avg_power_w": _text(_first(raw, "avgPower", "averagePower", "avg_power_w")),
        "avg_cadence_spm": _text(_first(raw, "averageRunningCadenceInStepsPerMinute", "avg_cadence_spm")),
        "elevation_gain_m": _text(_first(raw, "elevationGain", "elevation_gain_m")),
        "elevation_loss_m": _text(_first(raw, "elevationLoss", "elevation_loss_m")),
        "calories": _text(_first(raw, "calories")),
        "aerobic_te": _text(_first(raw, "aerobicTrainingEffect", "aerobic_te")),
        "anaerobic_te": _text(_first(raw, "anaerobicTrainingEffect", "anaerobic_te")),
        "training_load": _text(_first(raw, "trainingLoad", "training_load")),
        "device_source": "garmin",
        "details_status": "not_requested",
        "analysis_status": "pending",
        "source_fingerprint": _fingerprint(raw),
        "imported_at": imported_at,
        "updated_at": imported_at,
    }
    return normalized


def _text(value: Any) -> str:
    number = _number(value)
    if number is None:
        return ""
    return str(number).removesuffix(".0")


def _fingerprint(raw: dict[str, Any]) -> str:
    allowlist = {
        key: raw.get(key)
        for key in (
            "activityId",
            "startTimeGMT",
            "startTimeLocal",
            "activityType",
            "distance",
            "movingDuration",
            "elapsedDuration",
            "averageHR",
            "maxHR",
            "averagePower",
            "elevationGain",
            "elevationLoss",
            "calories",
        )
    }
    payload = json.dumps(allowlist, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_rows(content: str) -> dict[str, dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content))
    return {str(row.get("activity_id", "")): {key: row.get(key, "") or "" for key in ACTIVITY_COLUMNS} for row in reader if row.get("activity_id")}


def _csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=ACTIVITY_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class GarminSync:
    def __init__(self, settings: Settings, garmin: GarminPersonalApi, data_store: GitHubDataStore) -> None:
        self.settings = settings
        self.garmin = garmin
        self.data_store = data_store

    def run(self) -> dict[str, Any]:
        if not sync_lock.acquire(blocking=False):
            raise SyncError("Synchronizacja już trwa. Poczekaj na jej zakończenie.")
        try:
            return self._run_locked()
        finally:
            sync_lock.release()

    def _run_locked(self) -> dict[str, Any]:
        if not self.garmin.configured:
            raise SyncError("Klucz Garmin Personal API nie jest skonfigurowany.")
        if not self.data_store.configured:
            raise SyncError("Token GitHub do prywatnego repozytorium danych nie jest skonfigurowany.")

        started = datetime.now(timezone.utc)
        state = self.data_store.read_json("sync_state.json", {})
        start_date = self._start_date(state, started)
        end_date = started.astimezone(ZoneInfo(self.settings.timezone)).date()
        raw_activities = self.garmin.list_activities(start_date=start_date, end_date=end_date)
        imported_at = started.isoformat().replace("+00:00", "Z")
        incoming = [
            normalize_activity(raw, imported_at=imported_at, timezone_name=self.settings.timezone)
            for raw in raw_activities
        ]
        incoming = [row for row in incoming if row["activity_id"]]

        existing = _read_rows(self.data_store.read_text("activities.csv"))
        new_count = 0
        changed_count = 0
        for row in incoming:
            old = existing.get(row["activity_id"])
            if old is None:
                new_count += 1
                existing[row["activity_id"]] = row
            elif old.get("source_fingerprint") != row["source_fingerprint"]:
                changed_count += 1
                row["imported_at"] = old.get("imported_at", imported_at)
                existing[row["activity_id"]] = row

        rows = sorted(existing.values(), key=lambda item: (item.get("start_at_utc", ""), item["activity_id"]))
        latest = rows[-1] if rows else {}
        next_state = {
            **state,
            "schema_version": 1,
            "last_successful_sync_at": imported_at,
            "download_watermark": imported_at,
            "latest_activity_id": latest.get("activity_id"),
            "latest_activity_start_at": latest.get("start_at_utc"),
            "sync_revision": int(state.get("sync_revision", 0) or 0) + 1,
            "last_job": {
                "status": "completed",
                "started_at": imported_at,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "new_count": new_count,
                "changed_count": changed_count,
            },
        }
        commit_sha = self.data_store.commit_files(
            {
                "activities.csv": _csv(rows),
                "sync_state.json": json.dumps(next_state, ensure_ascii=False, indent=2) + "\n",
            },
            f"sync Garmin activities {end_date.isoformat()}",
        )
        return {
            "status": "completed",
            "new_count": new_count,
            "changed_count": changed_count,
            "activity_count": len(incoming),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "commit_sha": commit_sha,
        }

    def _start_date(self, state: dict[str, Any], started: datetime) -> date:
        history_start = date.fromisoformat(self.settings.history_start)
        last_success = _parse_datetime(state.get("last_successful_sync_at"))
        if last_success is None:
            return history_start
        lookback_start = last_success.astimezone(ZoneInfo(self.settings.timezone)).date() - timedelta(
            days=self.settings.sync_lookback_days
        )
        return max(history_start, lookback_start)


def sync_data(settings: Settings, garmin: GarminPersonalApi, data_store: GitHubDataStore) -> dict[str, Any]:
    try:
        return GarminSync(settings, garmin, data_store).run()
    except (DataStoreError, GarminIntegrationError) as exc:
        raise SyncError(str(exc)) from exc


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
