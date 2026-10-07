from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore"
    )
    app_env: Literal["local", "demo", "production"] = "local"
    public_origins: str = "http://127.0.0.1:8773,http://localhost:8773"
    database_url: str = "postgresql+asyncpg://hotel:hotel@127.0.0.1:55439/hotel"
    google_cloud_project: str = ""
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3.5-flash"
    hotel_timezone: str = "Asia/Makassar"
    hotel_contact_url: str = "mailto:stay@sanctuary.example"
    turn_timeout_seconds: float = Field(default=90, gt=0, le=90)

    @property
    def origins(self) -> set[str]:
        return {item.strip() for item in self.public_origins.split(",") if item.strip()}
