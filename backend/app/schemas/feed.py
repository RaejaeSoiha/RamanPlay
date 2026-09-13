from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class SourceInput(BaseModel):
    provider_name: str
    source_name: str
    url: str
    source_type: Literal[
        "OFFICIAL_NFL",
        "OFFICIAL_NETWORK",
        "OFFICIAL_STREAMING_SERVICE",
        "FREE_LEGAL",
        "FREE_TRIAL",
        "PAID_STREAMING",
        "AUDIO",
        "GAME_TRACKER",
    ]
    access_type: Literal[
        "FREE", "FREE TRIAL", "SUBSCRIPTION", "OFFICIAL", "AUDIO ONLY", "UNAVAILABLE"
    ]
    region: str
    notes: str = Field(min_length=10)


class GameInput(BaseModel):
    external_id: str
    season_type: Literal["PRESEASON", "REGULAR", "POSTSEASON"] = "REGULAR"
    season: int
    week: int = Field(ge=0, le=30)
    kickoff_time: datetime | None
    away: str
    home: str
    status: Literal[
        "SCHEDULED", "PRE_GAME", "LIVE", "HALFTIME", "FINAL", "POSTPONED", "CANCELLED"
    ] = "SCHEDULED"
    venue: str = ""
    broadcast_network: str | None = None
    away_score: int | None = None
    home_score: int | None = None
    away_record: str | None = None
    home_record: str | None = None
    development_data: bool = False
    sources: list[SourceInput] = []

    @field_validator("kickoff_time")
    @classmethod
    def aware(cls, v):
        if v is not None and v.tzinfo is None:
            raise ValueError("Kickoff must include timezone offset")
        return v
