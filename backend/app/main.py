import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.database.session import Base, engine, SessionLocal
from app.models.entities import Game, MaintenanceState
from app.services.ingestion import seed_teams
from app.sports.nba.games import seed_nba_teams
from app.sports.nba.players import sync_nba_players
from app.database.migrations import migrate
from app.services.jobs import refresh_schedule, refresh_active, check_links
from app.api.routes import router
from app.utils.logging import configure_logging

configure_logging()


def refresh_nba_players():
    try:
        with SessionLocal() as db:
            sync_nba_players(db)
    except Exception:
        logging.warning("nba_player_sync_failed")


@asynccontextmanager
async def lifespan(app):
    migrate(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        saved_hours = db.get(MaintenanceState, "link_check_hours")
        if saved_hours:
            settings.link_check_hours = max(1, min(168, int(saved_hours.value)))
        seed_teams(db)
        seed_nba_teams(db)
    # Provider requests can take longer than the web server startup budget.
    # Cached schedules remain available while the first refresh runs after bind.
    app.state.initial_sync_task = asyncio.create_task(asyncio.to_thread(refresh_schedule))
    app.state.nba_players_sync_task = asyncio.create_task(asyncio.to_thread(refresh_nba_players))
    scheduler = AsyncIOScheduler()
    app.state.scheduler = scheduler
    if settings.scheduler_enabled:
        scheduler.add_job(
            refresh_schedule,
            "interval",
            hours=max(settings.schedule_hours, 1),
            max_instances=1,
        )
        scheduler.add_job(
            refresh_active,
            "interval",
            seconds=max(settings.live_refresh_seconds, 60),
            max_instances=1,
        )
        scheduler.add_job(
            check_links,
            "interval",
            id="link-checks",
            hours=max(settings.link_check_hours, 1),
            max_instances=1,
        )
        scheduler.start()
    yield
    for task in (app.state.initial_sync_task, app.state.nba_players_sync_task):
        task.cancel()
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="RamanPlay", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
buckets = defaultdict(deque)


@app.middleware("http")
async def guard(request: Request, call_next):
    key = (
        request.client.host if request.client else "unknown",
        request.url.path.startswith("/api/admin"),
    )
    now = time.monotonic()
    bucket = buckets[key]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    # A dashboard route makes several independent read requests (account,
    # preferences, teams, games, and sport-specific data). Keep public reads
    # bounded without treating normal in-app navigation as abusive traffic.
    if len(bucket) >= (10 if key[1] else 600):
        return JSONResponse(
            {"detail": "Rate limit exceeded"},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    bucket.append(now)
    if len(buckets) > 10000:
        for k in list(buckets):
            if not buckets[k] or buckets[k][-1] < now - 60:
                del buckets[k]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(router)
