from datetime import date

from app.config import Settings
from app.sync import GarminSync


class FakeGarmin:
    configured = True

    def list_activities(self, *, start_date: date, end_date: date) -> list[dict[str, object]]:
        return [
            {
                "activityId": 123,
                "startTimeGMT": "2026-11-22T08:00:00Z",
                "activityType": {"typeKey": "running"},
                "distance": 5000,
                "movingDuration": 1800,
                "averageHR": 145,
            }
        ]


class FakeStore:
    configured = True

    def __init__(self) -> None:
        self.committed: dict[str, str] = {}

    def read_json(self, path: str, default: dict[str, object]) -> dict[str, object]:
        return {}

    def read_text(self, path: str) -> str:
        return "activity_id,start_at_utc,start_date_local,sport,subsport,title,distance_m,moving_s,elapsed_s,avg_pace_s_km,avg_hr_bpm,max_hr_bpm,avg_power_w,avg_cadence_spm,elevation_gain_m,elevation_loss_m,calories,aerobic_te,anaerobic_te,training_load,device_source,details_status,analysis_status,source_fingerprint,imported_at,updated_at\n"

    def commit_files(self, files: dict[str, str], message: str) -> str:
        self.committed = files
        return "commit-test"


class FakeAnalyzer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def analyze_activity(self, activity: dict[str, str], context: list[dict[str, str]]) -> dict[str, object]:
        self.calls.append(activity["activity_id"])
        return {
            "summary": "Dobry bieg.",
            "classification": "easy",
            "confidence": "medium",
            "positives": [],
            "risks": [],
            "recommendation": "planned",
            "recommendation_text": "Kontynuuj plan.",
            "plan_alignment": "not_assessed",
            "uncertainty": [],
        }


def test_sync_analyzes_each_new_running_activity() -> None:
    store = FakeStore()
    analyzer = FakeAnalyzer()
    settings = Settings(
        garmin_personal_api_key="configured",
        github_data_token="configured",
        recent_run_count=10,
    )

    result = GarminSync(settings, FakeGarmin(), store, analyzer).run()

    assert result["analysis_count"] == 1
    assert analyzer.calls == ["123"]
    assert "analyses/123/" in "".join(store.committed)
