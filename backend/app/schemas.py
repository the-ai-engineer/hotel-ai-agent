import json
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_turn_id: UUID
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A message is required")
        return value


class Source(BaseModel):
    id: UUID
    title: str
    version: int
    url: str


class Villa(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=80)
    name: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    capacity: int = Field(ge=1, le=8)
    amenities: list[str] = Field(max_length=20)
    image: str = Field(pattern=r"^/assets/[a-z0-9-]+\.(png|jpg|webp)$")


class AvailabilitySummary(BaseModel):
    outcome: Literal["ok", "no_matches", "outside_demo_period"]
    check_in: date
    check_out: date
    guests: int
    checked_at: datetime
    horizon_start: date
    horizon_end: date
    more_available: bool = False


class Availability(AvailabilitySummary):
    villas: list[Villa] = Field(default_factory=list, max_length=6)


class Answer(BaseModel):
    answer: str = Field(max_length=16000)
    sources: list[Source] = Field(default_factory=list, max_length=5)
    cards: list[Villa] = Field(default_factory=list, max_length=6)
    availability: AvailabilitySummary | None = None
    usage: dict[str, int] = Field(default_factory=dict)


class TurnState(BaseModel):
    client_turn_id: UUID
    state: Literal["running", "completed", "failed", "interrupted"]
    deadline: str
    result: Answer | None = None
    error_code: str | None = None


def context_answer(result: dict) -> str:
    text = result["answer"]
    availability = result.get("availability")
    if availability:
        facts = {key: availability[key] for key in ["check_in", "check_out", "guests"]}
        facts["villa_slugs"] = [villa["slug"] for villa in result.get("cards", [])]
        text += "\nHistorical search context (must recheck): " + json.dumps(facts, sort_keys=True)
    return text
