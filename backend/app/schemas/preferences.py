from pydantic import BaseModel, Field


class HouseholdPreferencesInput(BaseModel):
    favorites: list[int] = Field(default_factory=list, max_length=128)
    preferences: dict[str, object] = Field(default_factory=dict)
