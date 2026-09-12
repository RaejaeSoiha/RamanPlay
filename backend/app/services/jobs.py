import asyncio, logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.entities import Game, WatchSource
from app.services.sync import sync_schedule, active_provider, state
from app.config import settings
from app.services.checker import LinkChecker

lock = asyncio.Lock()


async def check_links():
    if lock.locked():
        return {"status": "already_running"}
    async with lock:
        with SessionLocal() as db:
            return {"checked": await LinkChecker().check_all(db)}


async def check_live_sources():
    """Check official sources for games that are currently live."""
    with SessionLocal() as db:
        current = datetime.now(timezone.utc)
        games = list(
            db.scalars(
                select(Game).where(
                    Game.provider == active_provider(db),
                    Game.season == settings.current_season,
                    Game.status.in_(["LIVE", "HALFTIME"]),
                )
            )
        )
        if not games:
            return {"checked": 0, "message": "No live games"}

        sources_to_check = []
        for game in games:
            for source in game.sources:
                check_url = source.live_url or source.url
                sources_to_check.append((source, check_url))

        checker = LinkChecker()
        checked = 0
        for source, url in sources_to_check:
            status, code, final, elapsed, error = await checker.check(url)
            source.status = status
            source.last_checked = datetime.now(timezone.utc)
            source.final_url = final
            db.add(source)
            checked += 1

        db.commit()
        return {"checked": checked, "games": len(games)}


def refresh_schedule():
    try:
        with SessionLocal() as db:
            result = sync_schedule(db)
        logging.info(
            "schedule_sync fetched=%d errors=%d", result["fetched"], result["errors"]
        )
    except Exception:
        logging.error("schedule_update_failed")


async def refresh_active():
    with SessionLocal() as db:
        current = datetime.now(timezone.utc)
        games = list(
            db.scalars(
                select(Game).where(
                    Game.provider == active_provider(db),
                    Game.season == settings.current_season,
                )
            )
        )

        def utc(value):
            return (
                value.replace(tzinfo=timezone.utc)
                if value and value.tzinfo is None
                else value
            )

        live = any(g.status in ("LIVE", "HALFTIME") for g in games)
        await LinkChecker().check_near_kickoff_links(db, current)
        near = any(
            g.kickoff_time
            and abs((utc(g.kickoff_time) - current).total_seconds()) <= 86400
            for g in games
        )
        interval = (
            max(settings.live_refresh_seconds, 60)
            if live
            else max(settings.game_day_refresh_seconds, 300)
            if near
            else max(settings.schedule_hours, 1) * 3600
        )
        values = state(db)
        if values.get("provider_status") == "Error":
            interval = max(interval, 900)
        attempted = values.get("last_attempted_sync")
        if (
            attempted
            and (current - datetime.fromisoformat(attempted)).total_seconds() < interval
        ):
            return
    refresh_schedule()
