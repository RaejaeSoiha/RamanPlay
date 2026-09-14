from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def now():
    return datetime.now(timezone.utc)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    # `abbreviation` is the stable internal key. NBA keys are namespaced so
    # shared abbreviations such as DEN never collide with NFL teams.
    abbreviation: Mapped[str] = mapped_column(String(16), unique=True)
    provider_abbreviation: Mapped[str | None] = mapped_column(String(8), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sport: Mapped[str] = mapped_column(String(32), default="FOOTBALL", server_default="FOOTBALL")
    league: Mapped[str] = mapped_column(String(16), default="NFL", server_default="NFL", index=True)
    name: Mapped[str]
    city: Mapped[str]
    conference: Mapped[str]
    division: Mapped[str]
    logo_url: Mapped[str] = mapped_column(default="")
    official_url: Mapped[str] = mapped_column(default="https://www.nfl.com/teams/")


class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(unique=True)
    season: Mapped[int]
    week: Mapped[int]
    season_type: Mapped[str] = mapped_column(
        default="REGULAR", server_default="REGULAR"
    )
    provider: Mapped[str] = mapped_column(default="development", index=True)
    sport: Mapped[str] = mapped_column(String(32), default="FOOTBALL", server_default="FOOTBALL")
    league: Mapped[str] = mapped_column(String(16), default="NFL", server_default="NFL", index=True)
    game_date: Mapped[str]
    kickoff_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    timezone: Mapped[str] = mapped_column(default="UTC")
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    status: Mapped[str] = mapped_column(default="SCHEDULED")
    venue: Mapped[str] = mapped_column(default="")
    broadcast_network: Mapped[str | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None]
    home_score: Mapped[int | None]
    away_record: Mapped[str | None] = mapped_column(String(32), nullable=True)
    home_record: Mapped[str | None] = mapped_column(String(32), nullable=True)
    development_data: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)
    sources: Mapped[list["WatchSource"]] = relationship(cascade="all, delete-orphan")
    my_links: Mapped[list["PersonalLink"]] = relationship(cascade="all, delete-orphan")


class WatchSource(Base):
    __tablename__ = "watch_sources"
    __table_args__ = (UniqueConstraint("game_id", "url"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    provider_name: Mapped[str]
    source_name: Mapped[str]
    url: Mapped[str]
    live_url: Mapped[str | None] = mapped_column(nullable=True)
    source_type: Mapped[str]
    access_type: Mapped[str]
    is_official: Mapped[bool] = mapped_column(default=True)
    is_free: Mapped[bool] = mapped_column(default=False)
    requires_subscription: Mapped[bool] = mapped_column(default=False)
    requires_trial: Mapped[bool] = mapped_column(default=False)
    region: Mapped[str] = mapped_column(default="See provider")
    last_checked: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(default="UNCHECKED")
    notes: Mapped[str] = mapped_column(default="")
    final_url: Mapped[str | None]
    checks: Mapped[list["LinkCheck"]] = relationship(cascade="all, delete-orphan")


class PersonalLink(Base):
    __tablename__ = "personal_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id"), index=True, nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("combat_events.id"), index=True, nullable=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.id"), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048))
    source_name: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, default=3)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    playback_preference: Mapped[str] = mapped_column(
        String(32), default="AUTO", server_default="AUTO"
    )
    playback_type: Mapped[str] = mapped_column(
        String(32), default="EXTERNAL_PAGE", server_default="EXTERNAL_PAGE"
    )
    final_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_successful_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    successful_check_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    average_response_time: Mapped[float] = mapped_column(Float, default=0.0)
    redirect_count: Mapped[int] = mapped_column(Integer, default=0)
    final_destination_domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    last_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shared_with_household: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), unique=True)


class CombatEvent(Base):
    __tablename__ = "combat_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    sport: Mapped[str] = mapped_column(String(32), default="MMA")
    league: Mapped[str] = mapped_column(String(16), default="UFC", index=True)
    name: Mapped[str] = mapped_column(String(255))
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    main_card_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preliminary_card_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED")
    venue: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    broadcast_network: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="espn-ufc", index=True)
    development_data: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)
    bouts: Mapped[list["CombatBout"]] = relationship(cascade="all, delete-orphan", order_by="CombatBout.bout_order")
    my_links: Mapped[list["PersonalLink"]] = relationship(cascade="all, delete-orphan", foreign_keys="PersonalLink.event_id")


class Fighter(Base):
    __tablename__ = "fighters"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    internal_key: Mapped[str] = mapped_column(String(160), unique=True)
    league: Mapped[str] = mapped_column(String(16), default="UFC", index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    nickname: Mapped[str] = mapped_column(String(160), default="")
    country: Mapped[str] = mapped_column(String(96), default="")
    record: Mapped[str] = mapped_column(String(64), default="")
    weight_class: Mapped[str] = mapped_column(String(96), default="")
    headshot_url: Mapped[str] = mapped_column(String(2048), default="")
    ranking: Mapped[int | None] = mapped_column(nullable=True)
    is_champion: Mapped[bool] = mapped_column(default=False)


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    provider_id: Mapped[str] = mapped_column(String(32), index=True)
    league: Mapped[str] = mapped_column(String(16), default="NBA", index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    first_name: Mapped[str] = mapped_column(String(80), default="")
    last_name: Mapped[str] = mapped_column(String(80), default="")
    display_name: Mapped[str] = mapped_column(String(160), default="")
    short_name: Mapped[str] = mapped_column(String(64), default="")
    jersey: Mapped[str] = mapped_column(String(8), default="")
    position: Mapped[str] = mapped_column(String(32), default="")
    position_name: Mapped[str] = mapped_column(String(64), default="")
    position_abbreviation: Mapped[str] = mapped_column(String(8), default="")
    height: Mapped[str] = mapped_column(String(16), default="")
    weight: Mapped[str] = mapped_column(String(16), default="")
    age: Mapped[int | None] = mapped_column(nullable=True)
    date_of_birth: Mapped[str] = mapped_column(String(32), default="")
    birth_place: Mapped[str] = mapped_column(String(160), default="")
    college: Mapped[str] = mapped_column(String(160), default="")
    headshot_url: Mapped[str] = mapped_column(String(2048), default="")
    status: Mapped[str] = mapped_column(String(32), default="")
    experience_years: Mapped[int] = mapped_column(default=0)
    draft_year: Mapped[int | None] = mapped_column(nullable=True)
    draft_round: Mapped[int | None] = mapped_column(nullable=True)
    draft_pick: Mapped[int | None] = mapped_column(nullable=True)
    career_stats: Mapped[dict] = mapped_column(JSON, default={})
    game_log: Mapped[list] = mapped_column(JSON, default=[])
    splits: Mapped[dict] = mapped_column(JSON, default={})
    awards: Mapped[list] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)
    team: Mapped[Team | None] = relationship(foreign_keys=[team_id])


class CombatBout(Base):
    __tablename__ = "combat_bouts"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("combat_events.id"), index=True)
    fighter_a_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    fighter_b_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    fighter_a: Mapped[Fighter] = relationship(foreign_keys=[fighter_a_id])
    fighter_b: Mapped[Fighter] = relationship(foreign_keys=[fighter_b_id])
    weight_class: Mapped[str] = mapped_column(String(96), default="")
    bout_order: Mapped[int] = mapped_column(Integer, default=0)
    card_section: Mapped[str] = mapped_column(String(32), default="PRELIMINARY_CARD")
    scheduled_rounds: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED")
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("fighters.id"), nullable=True)
    result_method: Mapped[str] = mapped_column(String(128), default="")
    result_round: Mapped[int | None] = mapped_column(nullable=True)
    finish_time: Mapped[str] = mapped_column(String(32), default="")
    is_title_fight: Mapped[bool] = mapped_column(default=False)
    is_interim_title: Mapped[bool] = mapped_column(default=False)


class FavoriteCombatEvent(Base):
    __tablename__ = "favorite_combat_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("combat_events.id"), unique=True)


class FavoriteFighter(Base):
    __tablename__ = "favorite_fighters"
    id: Mapped[int] = mapped_column(primary_key=True)
    fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"), unique=True)


class Household(Base):
    __tablename__ = "households"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="My Household")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HouseholdPreference(Base):
    __tablename__ = "household_preferences"
    __table_args__ = (UniqueConstraint("household_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True)
    favorites: Mapped[list] = mapped_column(JSON, default=list)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AppUser(Base):
    __tablename__ = "app_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), default="Owner")
    role: Mapped[str] = mapped_column(String(20), default="OWNER")
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id"), nullable=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProviderAccount(Base):
    __tablename__ = "provider_accounts"
    __table_args__ = (UniqueConstraint("user_id", "provider"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="NOT_CONNECTED")
    encrypted_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class HouseholdInvite(Base):
    __tablename__ = "household_invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WatchTogetherRoom(Base):
    __tablename__ = "watch_together_rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"))
    code_hash: Mapped[str] = mapped_column(String(128), unique=True)
    selected_link_id: Mapped[int | None] = mapped_column(ForeignKey("personal_links.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WatchTogetherParticipant(Base):
    __tablename__ = "watch_together_participants"
    __table_args__ = (UniqueConstraint("room_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("watch_together_rooms.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(100), unique=True)
    source_name: Mapped[str] = mapped_column(String(100))
    has_subscription: Mapped[bool] = mapped_column(default=False)
    has_free_trial: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str] = mapped_column(default="")
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)


class LinkCheck(Base):
    __tablename__ = "link_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    watch_source_id: Mapped[int] = mapped_column(ForeignKey("watch_sources.id"))
    checked_at: Mapped[datetime] = mapped_column(default=now)
    http_status: Mapped[int | None]
    response_time: Mapped[float]
    is_available: Mapped[bool]
    error_message: Mapped[str | None]
    final_url: Mapped[str | None]


class MaintenanceState(Base):
    __tablename__ = "maintenance_state"
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]
