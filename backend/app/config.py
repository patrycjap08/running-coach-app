from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Running Coach API"
    environment: str = "development"
    garmin_personal_api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    github_data_token: str | None = None
    github_data_repo: str = "patrycjap08/running-coach-data"
    github_data_branch: str = "main"
    allowed_origins: str = "http://localhost:5173"
    timezone: str = "Europe/Warsaw"
    history_start: str = "2025-01-01"
    recent_run_count: int = 10
    sync_lookback_days: int = 7
    ai_max_input_tokens: int = 40000
    ai_max_output_tokens: int = 3500

    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
