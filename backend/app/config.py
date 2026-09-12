from pathlib import Path
from pydantic import field_validator, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


def season_for_date(day):
    """January and February belong to the season that began the previous year."""
    return day.year - (day.month < 3)


class Settings(BaseSettings):
    database_url: str = "sqlite:///" + str(ROOT / "watch.db")
    admin_secret: str = ""
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    data_provider: str = "auto"
    nfl_data_api_key: str = Field(
        default="",
        repr=False,
        validation_alias=AliasChoices(
            "SPORTSDATAIO_API_KEY", "NFL_DATA_API_KEY", "nfl_data_api_key"
        ),
    )
    nfl_season: int | None = None
    sportsdata_trial: bool = False
    schedule_file: str = str(ROOT.parent / "data/seeds/schedule.json")
    trusted_domains: str = "nfl.com,nbc.com,nbcsports.com,foxsports.com,cbs.com,cbssports.com,espn.com,abc.com,amazon.com,primevideo.com,peacocktv.com,paramountplus.com,tv.youtube.com,netflix.com"
    blocked_domains: str = "doubleclick.net,googlesyndication.com,google-analytics.com,adservice.google.com,taboola.com,outbrain.com,scorecardresearch.com,pornhub.com,xvideos.com,xnxx.com,redtube.com"
    session_secret: str = ""
    session_secure_cookie: bool = False
    provider_token_encryption_key: str = Field(default="", repr=False)
    user_agent: str = "RamanPlay/1.0 (personal link checker)"
    schedule_hours: int = 6
    game_day_refresh_seconds: int = 900
    provider_timeout_seconds: float = 15
    provider_retries: int = Field(default=2, ge=0, le=4)
    live_refresh_seconds: int = 120
    link_check_hours: int = 6
    request_interval_seconds: float = 2
    scheduler_enabled: bool = True

    @field_validator("nfl_season", mode="before")
    @classmethod
    def optional_season(cls, value):
        return None if value in ("", None) else value

    @property
    def current_season(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        today = datetime.now(ZoneInfo("America/New_York"))
        return self.nfl_season or season_for_date(today)

    @property
    def selected_provider(self):
        # A configured SportsDataIO key remains the preferred paid provider.
        if self.nfl_data_api_key.strip():
            return "sportsdataio"
        if self.data_provider in ("auto", "espn"):
            return "espn"
        return "json" if self.data_provider == "json" else "development"

    @field_validator("database_url")
    @classmethod
    def normalize_database(cls, value):
        if not value:
            return "sqlite:///" + str(ROOT / "watch.db")
        if (
            value.startswith("sqlite:///")
            and not value.startswith("sqlite:////")
            and value != "sqlite:///:memory:"
        ):
            return "sqlite:///" + str((ROOT / value[len("sqlite:///") :]).resolve())
        return value

    model_config = SettingsConfigDict(
        env_file=(str(ROOT.parent / ".env"), ".env"), extra="ignore"
    )


settings = Settings()
