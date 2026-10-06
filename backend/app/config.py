from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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

    ip_hash_secret: SecretStr = SecretStr("local-only-development-key-rotate-before-release")
    property_turns_per_minute: int | None = Field(default=None, ge=1, le=100000)
    demo_ip_limit_override: int | None = Field(default=None, ge=1, le=100000)

    @model_validator(mode="after")
    def release_settings(self):
        if self.app_env != "local":
            secret = self.ip_hash_secret.get_secret_value()
            if secret.startswith("local-only") or len(secret) < 32:
                raise ValueError(
                    "Non-local releases require an explicit IP_HASH_SECRET of at least 32 characters"
                )
            if self.property_turns_per_minute is None:
                raise ValueError(
                    "Set PROPERTY_TURNS_PER_MINUTE from measured model capacity before release"
                )
        if self.demo_ip_limit_override is not None and self.app_env != "demo":
            raise ValueError("DEMO_IP_LIMIT_OVERRIDE is allowed only in a private demo deployment")
        return self

    @property
    def property_limit(self):
        return self.property_turns_per_minute or 300

    @property
    def origins(self) -> set[str]:
        return {item.strip() for item in self.public_origins.split(",") if item.strip()}
