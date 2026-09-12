"""Run maintenance locally; authentication is required for HTTP, not this local CLI."""

import argparse, asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.database.session import Base, engine, SessionLocal
from app.services.ingestion import seed_teams
from app.services.sync import sync_schedule
from app.database.migrations import migrate
from app.services.checker import LinkChecker

parser = argparse.ArgumentParser()
parser.add_argument(
    "action", choices=["update-schedule", "rebuild-sources", "check-links"]
)
args = parser.parse_args()
migrate(engine)
Base.metadata.create_all(engine)
with SessionLocal() as db:
    seed_teams(db)
    if args.action == "check-links":
        print({"checked": asyncio.run(LinkChecker().check_all(db))})
    else:
        result = sync_schedule(db)
        print(
            f"Provider: {result['active_provider']}\nGames fetched: {result['fetched']}\nGames created: {result['created']}\nGames updated: {result['updated']}\nErrors: {result['errors']}"
        )
        if result.get("error"):
            print(result["error"])
        if result["errors"]:
            sys.exit(1)
