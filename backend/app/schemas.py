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


class Answer(BaseModel):
    answer: str = Field(max_length=16000)
    sources: list[Source] = Field(default_factory=list, max_length=5)
    cards: list[dict] = Field(default_factory=list, max_length=6)
    usage: dict[str, int] = Field(default_factory=dict)


class TurnState(BaseModel):
    client_turn_id: UUID
    state: Literal["running", "completed", "failed", "interrupted"]
    deadline: str
    result: Answer | None = None
    error_code: str | None = None
