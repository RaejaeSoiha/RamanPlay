from pydantic import BaseModel, Field


class InviteInput(BaseModel):
    expires_hours: int = Field(default=24, ge=1, le=168)


class JoinHouseholdInput(BaseModel):
    code: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class WatchRoomInput(BaseModel):
    game_id: int
    selected_link_id: int | None = None
