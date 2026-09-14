"""Normalized, summary-only sports news records."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class NewsStory(BaseModel):
    id: str
    sport: str
    league: str
    headline: str
    description: str | None = None
    source_name: str
    source_url: HttpUrl
    image_url: HttpUrl | None = None
    published_at: datetime
    updated_at: datetime | None = None
    related_team_ids: list[str] = []
    related_fighter_ids: list[str] = []
    related_game_event_id: str | None = None
    provider_id: str
