"""Shared factual recap representation for completed games and fight cards."""

from datetime import datetime

from pydantic import BaseModel


class RecapParticipant(BaseModel):
    id: int
    name: str
    abbreviation: str | None = None
    score: int | None = None
    record: str | None = None
    headshot_url: str | None = None


class RecapNextEvent(BaseModel):
    participant_id: int | None = None
    label: str
    event_id: int
    event_time: datetime | None = None
    route: str


class RecapBout(BaseModel):
    id: int
    card_section: str
    weight_class: str | None = None
    winner: RecapParticipant | None = None
    loser: RecapParticipant | None = None
    result_method: str | None = None
    result_round: int | None = None
    finish_time: str | None = None


class Recap(BaseModel):
    id: str
    sport: str
    league: str
    event_id: int
    status: str
    completed_at: datetime | None = None
    event_time: datetime | None = None
    title: str
    final_score: str | None = None
    winner: RecapParticipant | None = None
    loser: RecapParticipant | None = None
    summary_facts: list[str] = []
    top_performers: list[dict] = []
    notable_stats: list[dict] = []
    venue: str | None = None
    broadcast_network: str | None = None
    source_name: str
    source_provider: str
    teams: list[RecapParticipant] = []
    bouts: list[RecapBout] = []
    next_related: list[RecapNextEvent] = []
