from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str
    gemini_model: str = "gemini-3.8-flash"
    google_cloud_project: str = "personal-infrastructure-505708"
    google_cloud_location: str = "global"
    public_origin: str = "http://127.0.0.1:8773"
    secure_cookie: bool = False
    active_agent_limit: int = Field(default=4, ge=1)
    turn_timeout_seconds: float = Field(default=90, gt=0, le=90)
    session_turns_per_minute: int = Field(default=10, ge=1)
    ip_turns_per_minute: int = Field(default=30, ge=1)
    property_turns_per_minute: int = Field(default=60, ge=1)
    property_turns_per_day: int = Field(default=10000, ge=1)
    sessions_per_ip_minute: int = Field(default=10, ge=1)
    conversations_per_session_minute: int = Field(default=10, ge=1)
