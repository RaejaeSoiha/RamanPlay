from pydantic import BaseModel, Field, field_validator


class MyLinkInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    source_name: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=1000)
    priority: int = Field(default=3, ge=1, le=5)
    enabled: bool = True
    shared_with_household: bool = False

    @field_validator("url", "source_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str) -> str:
        return value.strip()


class MyLinkUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    source_name: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)
    priority: int | None = Field(default=None, ge=1, le=5)
    enabled: bool | None = None
    shared_with_household: bool | None = None

    @field_validator("url", "source_name")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value
