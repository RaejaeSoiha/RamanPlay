"""ESPN UFC adapter with dedicated event, bout, and fighter persistence."""

import re
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.entities import CombatBout, CombatEvent, Fighter
from app.services.espn import ESPNProvider
from app.services.normalization import normalize_network
from app.services.sportsdata import ProviderError


def fighter_key(name: str, provider_id: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", str(name).upper()).strip("_")
    return f"UFC_{slug}_{provider_id}"


class UFCESPNProvider:
    _cache = {}
    endpoint = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"

    def __init__(self, client=None):
        self.client = client

    def get_events(self):
        season = settings.current_season
        cached = self._cache.get(season)
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 60):
            return cached[1]
        client = self.client or httpx.Client(
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )
        try:
            response = client.get(
                self.endpoint,
                params={"dates": season, "limit": 1000},
                headers={"User-Agent": settings.user_agent},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise ProviderError("ESPN UFC events could not be reached or returned invalid data.") from None
        finally:
            if self.client is None:
                client.close()
        events = data.get("events") if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ProviderError("ESPN UFC scoreboard returned an unexpected response.")
        try:
            rows = [self.normalize(event) for event in events if event.get("season", {}).get("year") == season]
        except (KeyError, TypeError, ValueError):
            raise ProviderError("ESPN UFC scoreboard returned an invalid event.") from None
        if len({row["external_id"] for row in rows}) != len(rows):
            raise ProviderError("ESPN UFC scoreboard returned duplicate event IDs.")
        self._cache.clear()
        self._cache[season] = (time.monotonic(), rows)
        return rows

    @staticmethod
    def normalize(event):
        competitions = event.get("competitions") or []
        if not competitions:
            raise ValueError("Event has no bouts")
        status = ESPNProvider.normalize_status(event.get("status") or {})
        normalized_bouts = [UFCESPNProvider.normalize_bout(bout, index) for index, bout in enumerate(competitions)]
        times = [bout["start_time"] for bout in normalized_bouts if bout["start_time"]]
        latest = max(times) if times else event.get("date")
        earliest = min(times) if times else event.get("date")
        for index, bout in enumerate(normalized_bouts):
            if index == len(normalized_bouts) - 1:
                bout["card_section"] = "MAIN_EVENT"
            elif bout["start_time"] == latest:
                bout["card_section"] = "MAIN_CARD"
            elif earliest != latest and bout["start_time"] == earliest:
                bout["card_section"] = "EARLY_PRELIMS"
            else:
                bout["card_section"] = "PRELIMINARY_CARD"
        venue = competitions[0].get("venue") or event.get("venues", [{}])[0] or {}
        address = venue.get("address") or {}
        location = ", ".join(part for part in (address.get("city"), address.get("state") or address.get("country")) if part)
        broadcast = competitions[-1].get("broadcast") or ""
        if not broadcast:
            broadcasts = competitions[-1].get("broadcasts") or []
            names = broadcasts[0].get("names") if broadcasts else []
            broadcast = names[0] if names else None
        return {
            "external_id": "espn-ufc-" + str(event["id"]),
            "name": str(event.get("name") or "UFC Event"),
            "event_time": event.get("date") or earliest,
            "main_card_time": latest,
            "preliminary_card_time": earliest if earliest != latest else None,
            "status": status,
            "venue": str(venue.get("fullName") or ""),
            "location": location,
            "broadcast_network": normalize_network(broadcast),
            "bouts": normalized_bouts,
        }

    @staticmethod
    def normalize_bout(competition, index):
        competitors = sorted(competition.get("competitors") or [], key=lambda entry: entry.get("order", 0))
        if len(competitors) != 2:
            raise ValueError("Bout must have two fighters")
        fighters = [UFCESPNProvider.normalize_fighter(entry, competition.get("type", {}).get("abbreviation") or "") for entry in competitors]
        status = ESPNProvider.normalize_status(competition.get("status") or {})
        winner = next((fighter["external_id"] for fighter, entry in zip(fighters, competitors) if entry.get("winner")), None)
        format_data = competition.get("format") or {}
        rounds = int((format_data.get("regulation") or {}).get("periods") or 3)
        raw_status = competition.get("status") or {}
        return {
            "external_id": "espn-ufc-bout-" + str(competition["id"]),
            "fighters": fighters,
            "start_time": competition.get("date"),
            "weight_class": str(competition.get("type", {}).get("abbreviation") or ""),
            "bout_order": index,
            "card_section": "PRELIMINARY_CARD",
            "scheduled_rounds": rounds,
            "status": status,
            "winner_external_id": winner,
            "result_method": "",
            "result_round": int(raw_status.get("period")) if status == "FINAL" and raw_status.get("period") else None,
            "finish_time": str(raw_status.get("displayClock") or "") if status == "FINAL" else "",
            "is_title_fight": False,
            "is_interim_title": False,
        }

    @staticmethod
    def normalize_fighter(competitor, weight_class):
        athlete = competitor.get("athlete") or {}
        provider_id = str(competitor.get("id") or athlete.get("id") or "")
        if not provider_id or not athlete.get("fullName"):
            raise ValueError("Bout fighter is incomplete")
        records = competitor.get("records") or []
        record = next((row.get("summary") for row in records if row.get("name") == "overall"), "") or ""
        flag = athlete.get("flag") or {}
        return {
            "external_id": "espn-ufc-fighter-" + provider_id,
            "internal_key": fighter_key(athlete["fullName"], provider_id),
            "full_name": str(athlete["fullName"]),
            "nickname": str(athlete.get("nickname") or ""),
            "country": str(flag.get("alt") or ""),
            "record": record,
            "weight_class": weight_class,
            "headshot_url": f"https://a.espncdn.com/i/headshots/mma/players/full/{provider_id}.png",
        }


def sync_ufc_events(db, feed=None):
    rows = UFCESPNProvider().get_events() if feed is None else feed
    for row in rows:
        event = db.scalar(select(CombatEvent).where(CombatEvent.external_id == row["external_id"]))
        if not event:
            event = CombatEvent(external_id=row["external_id"])
            db.add(event)
        for key in ("name", "status", "venue", "location", "broadcast_network"):
            setattr(event, key, row[key])
        for key in ("event_time", "main_card_time", "preliminary_card_time"):
            value = row[key]
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            setattr(event, key, value.astimezone(timezone.utc) if value else None)
        event.sport = "MMA"
        event.league = "UFC"
        event.provider = "espn-ufc"
        event.development_data = False
        db.flush()
        existing = {bout.external_id: bout for bout in event.bouts}
        wanted = set()
        for bout_row in row["bouts"]:
            wanted.add(bout_row["external_id"])
            fighters = []
            for fighter_row in bout_row["fighters"]:
                fighter = db.scalar(select(Fighter).where(Fighter.external_id == fighter_row["external_id"]))
                if not fighter:
                    fighter = Fighter(external_id=fighter_row["external_id"], internal_key=fighter_row["internal_key"], full_name=fighter_row["full_name"])
                    db.add(fighter)
                for key, value in fighter_row.items():
                    if key not in {"external_id", "internal_key"}:
                        setattr(fighter, key, value)
                fighters.append(fighter)
            db.flush()
            bout = existing.get(bout_row["external_id"])
            if not bout:
                bout = CombatBout(external_id=bout_row["external_id"], event_id=event.id, fighter_a_id=fighters[0].id, fighter_b_id=fighters[1].id)
                db.add(bout)
            bout.fighter_a_id, bout.fighter_b_id = fighters[0].id, fighters[1].id
            for key in ("weight_class", "bout_order", "card_section", "scheduled_rounds", "status", "result_method", "result_round", "finish_time", "is_title_fight", "is_interim_title"):
                setattr(bout, key, bout_row[key])
            bout.winner_id = next((fighter.id for fighter in fighters if fighter.external_id == bout_row["winner_external_id"]), None)
        for external_id, bout in existing.items():
            if external_id not in wanted:
                db.delete(bout)
    db.commit()
    db.expire_all()
    return len(rows)


def event_with_card(db, event_id):
    return db.scalar(
        select(CombatEvent)
        .where(CombatEvent.id == event_id)
        .options(
            selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_a),
            selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_b),
            selectinload(CombatEvent.my_links),
        )
    )
