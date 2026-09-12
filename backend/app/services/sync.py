"""Database-first sync orchestration with durable status and a safe fallback."""

import threading
from sqlalchemy import select
from app.config import settings
from app.models.entities import Game, MaintenanceState, now
from app.services.providers import DevelopmentProvider
from app.services.ingestion import update_schedule
from app.services.sportsdata import ProviderError

_lock = threading.RLock()


def state(db):
    return {s.key: s.value for s in db.scalars(select(MaintenanceState))}


def save(db, **values):
    for key, value in values.items():
        db.merge(MaintenanceState(key=key, value=str(value)))
    db.commit()


def active_provider(db):
    selected = settings.selected_provider
    if db.scalar(
        select(Game.id)
        .where(Game.provider == selected, Game.season == settings.current_season)
        .limit(1)
    ):
        return selected
    return "development"


def provider_status(db):
    values = state(db)
    active = active_provider(db)
    demo = active == "development" or bool(
        db.scalar(
            select(Game.id)
            .where(
                Game.provider == active,
                Game.season == settings.current_season,
                Game.development_data.is_(True),
            )
            .limit(1)
        )
    )
    return dict(
        provider={
            "sportsdataio": "SportsDataIO",
            "espn": "ESPN",
            "development": "Development",
            "json": "JSON",
        }[active],
        configured_provider={
            "sportsdataio": "SportsDataIO",
            "espn": "ESPN",
            "development": "Development",
            "json": "JSON",
        }[settings.selected_provider],
        provider_status=values.get("provider_status", "Not configured"),
        last_successful_sync=values.get("last_successful_sync", ""),
        last_attempted_sync=values.get("last_attempted_sync", ""),
        games_received=int(values.get("games_received", 0)),
        games_created=int(values.get("games_created", 0)),
        games_updated=int(values.get("games_updated", 0)),
        last_provider_error=values.get("last_provider_error", ""),
        development_data=demo,
        season=settings.current_season,
    )


def sync_schedule(db):
    with _lock:
        save(db, last_attempted_sync=now().isoformat())
        try:
            count = update_schedule(db)
        except Exception as exc:
            db.rollback()
            message = (
                str(exc)
                if isinstance(exc, ProviderError)
                else "Schedule validation or storage failed. Check the configured feed; existing data was preserved."
            )
            # Seed fallback only if there is no usable cache for the selected season.
            if active_provider(db) == "development" and not db.scalar(
                select(Game.id)
                .where(
                    Game.provider == "development",
                    Game.season == settings.current_season,
                )
                .limit(1)
            ):
                update_schedule(
                    db,
                    feed=DevelopmentProvider().get_schedule(),
                    provider_name="development",
                )
            save(
                db,
                provider_status="Error",
                last_provider_error=message,
                games_received=0,
                games_created=0,
                games_updated=0,
            )
            return dict(
                fetched=0,
                created=0,
                updated=0,
                errors=1,
                error=message,
                **{"active_provider": active_provider(db)},
            )
        save(
            db,
            provider_status="Not configured"
            if settings.selected_provider == "development"
            else "Connected",
            last_successful_sync=now().isoformat(),
            last_provider_error="",
        )
        counts = state(db)
        return dict(
            fetched=count,
            created=int(counts["games_created"]),
            updated=int(counts["games_updated"]),
            errors=0,
            active_provider=active_provider(db),
        )
