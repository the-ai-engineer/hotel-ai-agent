from pathlib import Path

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
