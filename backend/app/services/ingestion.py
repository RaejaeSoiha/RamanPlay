import json
from datetime import timezone
from sqlalchemy import select
from app.models.entities import Team, Game, WatchSource, MaintenanceState, now
from app.config import ROOT, settings
from app.services.providers import provider
from app.sources.official import OfficialSourceProvider


def seed_teams(db):
    for row in json.loads((ROOT.parent / "data/seeds/teams.json").read_text()):
        if not db.scalar(select(Team).where(Team.abbreviation == row["abbreviation"])):
            db.add(
                Team(
                    **row,
                    provider_abbreviation=row["abbreviation"],
                    sport="FOOTBALL",
                    league="NFL",
                )
            )
    db.commit()


def update_schedule(db, feed=None, provider_name=None):
    feed = provider().get_schedule() if feed is None else feed
    provider_name = provider_name or settings.selected_provider
    created = updated = 0
    teams = {t.abbreviation: t.id for t in db.scalars(select(Team))}
    # Validate the complete import before writing any records.
    records = []
    for row in feed:
        if row.away not in teams or row.home not in teams or row.away == row.home:
            raise ValueError("Unknown or identical teams")
        sources = OfficialSourceProvider().find_sources(row)
        records.append((row, sources))
    if len({r.external_id for r, _ in records}) != len(records):
        raise ValueError("Duplicate external game IDs")
    for row, sources in records:
        game = db.scalar(select(Game).where(Game.external_id == row.external_id))
        if not game:
            game = Game(external_id=row.external_id)
            db.add(game)
            created += 1
        else:
            updated += 1
        final = game.status == "FINAL"
        for key in (
            "season",
            "season_type",
            "week",
            "status",
            "venue",
            "broadcast_network",
            "away_score",
            "home_score",
            "development_data",
        ):
            if final and key == "status" and row.status != "FINAL":
                continue
            if key in ("away_score", "home_score"):
                if final and (row.status != "FINAL" or getattr(row, key) is None):
                    continue
                if row.status in ("SCHEDULED", "PRE_GAME"):
                    setattr(game, key, None)
                    continue
                if getattr(row, key) is None and getattr(game, key) is not None:
                    continue
            setattr(game, key, getattr(row, key))
        game.kickoff_time = (
            row.kickoff_time.astimezone(timezone.utc) if row.kickoff_time else None
        )
        game.game_date = (
            game.kickoff_time.date().isoformat() if game.kickoff_time else "TBD"
        )
        game.provider = provider_name
        game.sport = "FOOTBALL"
        game.league = "NFL"
        game.timezone = "UTC"
        game.away_team_id = teams[row.away]
        game.home_team_id = teams[row.home]
        db.flush()
        wanted = {s["url"] for s in sources}
        for old in list(game.sources):
            if old.url not in wanted:
                db.delete(old)
        for source in sources:
            # Filter out non-model fields
            model_fields = {k: v for k, v in source.items() if k != "deep_link" and k != "game_status"}
            old = db.scalar(
                select(WatchSource).where(
                    WatchSource.game_id == game.id, WatchSource.url == source["url"]
                )
            )
            if old:
                for key, value in model_fields.items():
                    setattr(old, key, value)
            else:
                db.add(WatchSource(game_id=game.id, **model_fields))
    db.merge(MaintenanceState(key="last_schedule_update", value=now().isoformat()))
    db.merge(MaintenanceState(key="games_received", value=str(len(records))))
    db.merge(MaintenanceState(key="games_created", value=str(created)))
    db.merge(MaintenanceState(key="games_updated", value=str(updated)))
    db.commit()
    db.expire_all()
    return len(records)
