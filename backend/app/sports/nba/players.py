"""ESPN NBA player/roster adapter with player details and career statistics."""

import time
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.entities import Player, Team
from app.services.sportsdata import ProviderError


class NBAESPNPlayerProvider:
    """NBA player adapter using ESPN's public basketball endpoints."""

    _roster_cache = {}
    _player_cache = {}
    _stats_cache = {}

    def __init__(self, client=None):
        self.client = client

    def _get_client(self):
        return self.client or httpx.Client(
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def _request(self, endpoint: str, params: dict = None):
        client = self._get_client()
        try:
            response = client.get(endpoint, params=params, headers={"User-Agent": settings.user_agent})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"ESPN NBA player data could not be reached: {exc}") from None
        finally:
            if self.client is None:
                client.close()

    def get_team_roster(self, team_id: str, season: int = None) -> list[dict]:
        """Fetch roster for a specific NBA team."""
        if season is None:
            season = settings.current_season

        cache_key = f"{team_id}_{season}"
        cached = self._roster_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 60):
            return cached[1]

        endpoint = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
        data = self._request(endpoint, {"season": season})

        athletes = data.get("athletes") if isinstance(data, dict) else None
        if not isinstance(athletes, list):
            raise ProviderError("ESPN NBA roster returned an unexpected response.")

        roster = []
        for athlete in athletes:
            try:
                roster.append(self._normalize_roster_entry(athlete, team_id))
            except (KeyError, TypeError, ValueError):
                continue

        self._roster_cache.clear()
        self._roster_cache[cache_key] = (time.monotonic(), roster)
        return roster

    def get_player_details(self, player_id: str) -> dict:
        """Fetch detailed player profile including bio and career info."""
        cached = self._player_cache.get(player_id)
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 60):
            return cached[1]

        endpoint = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{player_id}"
        data = self._request(endpoint)

        if not isinstance(data, dict) or not data.get("id"):
            raise ProviderError("ESPN NBA player detail returned an unexpected response.")

        player = self._normalize_player_detail(data)
        self._player_cache.clear()
        self._player_cache[player_id] = (time.monotonic(), player)
        return player

    def get_player_career_stats(self, player_id: str) -> dict:
        """Fetch career statistics for a player."""
        cached = self._stats_cache.get(f"career_{player_id}")
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 60):
            return cached[1]

        endpoint = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{player_id}/statistics"
        data = self._request(endpoint)

        stats = self._normalize_career_stats(data)
        self._stats_cache.clear()
        self._stats_cache[f"career_{player_id}"] = (time.monotonic(), stats)
        return stats

    def get_player_game_log(self, player_id: str, season: int = None) -> list[dict]:
        """Fetch game-by-game log for a player."""
        if season is None:
            season = settings.current_season

        endpoint = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{player_id}/statisticslog"
        data = self._request(endpoint, {"season": season})

        splits = data.get("splits") if isinstance(data, dict) else None
        if not isinstance(splits, list):
            return []

        game_log = []
        for split in splits:
            category = split.get("category")
            if category != "gamelog":
                continue
            for stat in split.get("stats", []):
                game_log.append(self._normalize_game_log_entry(stat))
        return game_log

    def get_player_splits(self, player_id: str) -> dict:
        """Fetch situational splits for a player."""
        endpoint = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{player_id}/splits"
        data = self._request(endpoint)

        splits = data.get("splits") if isinstance(data, dict) else None
        if not isinstance(splits, list):
            return {}

        result = {}
        for split in splits:
            category = split.get("category", "unknown")
            result[category] = []
            for stat in split.get("stats", []):
                result[category].append(self._normalize_split_entry(stat))
        return result

    def get_player_awards(self, player_id: str) -> list[dict]:
        """Fetch awards history for a player."""
        endpoint = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{player_id}/awards"
        data = self._request(endpoint)

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []

        awards = []
        for item in items:
            awards.append({
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "year": item.get("year", ""),
                "description": item.get("description", ""),
            })
        return awards

    def _normalize_roster_entry(self, athlete: dict, team_id: str) -> dict:
        """Normalize a roster entry from ESPN team roster endpoint."""
        player_id = str(athlete.get("id") or athlete.get("uid") or "")
        if not player_id:
            raise ValueError("Missing player ID")

        return {
            "external_id": f"espn-nba-player-{player_id}",
            "provider_id": player_id,
            "full_name": str(athlete.get("fullName") or athlete.get("displayName") or ""),
            "first_name": str(athlete.get("firstName") or ""),
            "last_name": str(athlete.get("lastName") or ""),
            "display_name": str(athlete.get("displayName") or ""),
            "short_name": str(athlete.get("shortName") or ""),
            "jersey": str(athlete.get("jersey") or ""),
            "position": str(athlete.get("position", {}).get("abbreviation") or ""),
            "position_name": str(athlete.get("position", {}).get("name") or ""),
            "position_abbreviation": str(athlete.get("position", {}).get("abbreviation") or ""),
            "height": str(athlete.get("displayHeight") or ""),
            "weight": str(athlete.get("displayWeight") or ""),
            "age": athlete.get("age"),
            "date_of_birth": str(athlete.get("dateOfBirth") or ""),
            "birth_place": self._format_birth_place(athlete),
            "college": self._format_college(athlete),
            "headshot_url": f"https://a.espncdn.com/i/headshots/nba/players/full/{player_id}.png",
            "status": str(athlete.get("status", {}).get("name") or ""),
            "experience_years": athlete.get("experience", {}).get("years", 0) if isinstance(athlete.get("experience"), dict) else 0,
            "draft_year": athlete.get("draft", {}).get("year") if isinstance(athlete.get("draft"), dict) else None,
            "draft_round": athlete.get("draft", {}).get("round") if isinstance(athlete.get("draft"), dict) else None,
            "draft_pick": athlete.get("draft", {}).get("selection") if isinstance(athlete.get("draft"), dict) else None,
        }

    def _normalize_player_detail(self, data: dict) -> dict:
        """Normalize detailed player profile from ESPN core API."""
        player_id = str(data.get("id") or "")
        if not player_id:
            raise ValueError("Missing player ID")

        return {
            "external_id": f"espn-nba-player-{player_id}",
            "provider_id": player_id,
            "full_name": str(data.get("fullName") or data.get("displayName") or ""),
            "first_name": str(data.get("firstName") or ""),
            "last_name": str(data.get("lastName") or ""),
            "display_name": str(data.get("displayName") or ""),
            "short_name": str(data.get("shortName") or ""),
            "jersey": str(data.get("jersey") or ""),
            "position": str(data.get("position", {}).get("abbreviation") or ""),
            "position_name": str(data.get("position", {}).get("name") or ""),
            "position_abbreviation": str(data.get("position", {}).get("abbreviation") or ""),
            "height": str(data.get("displayHeight") or ""),
            "weight": str(data.get("displayWeight") or ""),
            "age": data.get("age"),
            "date_of_birth": str(data.get("dateOfBirth") or ""),
            "birth_place": self._format_birth_place(data),
            "college": self._format_college(data),
            "headshot_url": f"https://a.espncdn.com/i/headshots/nba/players/full/{player_id}.png",
            "status": str(data.get("status", {}).get("name") or ""),
            "experience_years": data.get("experience", {}).get("years", 0) if isinstance(data.get("experience"), dict) else 0,
            "draft_year": data.get("draft", {}).get("year") if isinstance(data.get("draft"), dict) else None,
            "draft_round": data.get("draft", {}).get("round") if isinstance(data.get("draft"), dict) else None,
            "draft_pick": data.get("draft", {}).get("selection") if isinstance(data.get("draft"), dict) else None,
        }

    def _normalize_career_stats(self, data: dict) -> dict:
        """Normalize career statistics from ESPN."""
        splits = data.get("splits") if isinstance(data, dict) else None
        if not isinstance(splits, list):
            return {}

        career = {}
        for split in splits:
            if split.get("category") != "career":
                continue
            for stat in split.get("stats", []):
                name = stat.get("name", "")
                value = stat.get("value")
                display_value = stat.get("displayValue", "")
                if name:
                    career[name] = {"value": value, "display": display_value}
        return career

    def _normalize_game_log_entry(self, stat: dict) -> dict:
        """Normalize a single game log entry."""
        return {
            "date": str(stat.get("eventDate") or ""),
            "opponent": str(stat.get("opponent", {}).get("displayName") or ""),
            "home_away": str(stat.get("homeAway") or ""),
            "result": str(stat.get("result") or ""),
            "minutes": stat.get("minutes"),
            "points": stat.get("points"),
            "rebounds": stat.get("rebounds"),
            "assists": stat.get("assists"),
            "steals": stat.get("steals"),
            "blocks": stat.get("blocks"),
            "turnovers": stat.get("turnovers"),
            "fg_made": stat.get("fieldGoalsMade"),
            "fg_attempted": stat.get("fieldGoalsAttempted"),
            "fg_pct": stat.get("fieldGoalPct"),
            "ft_made": stat.get("freeThrowsMade"),
            "ft_attempted": stat.get("freeThrowsAttempted"),
            "ft_pct": stat.get("freeThrowPct"),
            "three_made": stat.get("threePointFieldGoalsMade"),
            "three_attempted": stat.get("threePointFieldGoalsAttempted"),
            "three_pct": stat.get("threePointFieldGoalPct"),
        }

    def _normalize_split_entry(self, stat: dict) -> dict:
        """Normalize a split entry."""
        return {
            "name": stat.get("name", ""),
            "value": stat.get("value"),
            "display": stat.get("displayValue", ""),
            "abbreviation": stat.get("abbreviation", ""),
        }

    def _format_birth_place(self, data: dict) -> str:
        parts = []
        for key in ("birthPlaceCity", "birthPlaceState", "birthPlaceCountry"):
            val = data.get(key)
            if val:
                parts.append(str(val))
        return ", ".join(parts)

    def _format_college(self, data: dict) -> str:
        college = data.get("college") or {}
        if isinstance(college, dict):
            return str(college.get("name") or "")
        return ""


def sync_nba_players(db, team_id: str = None, season: int = None) -> int:
    """Sync NBA players for a team or all teams."""
    if season is None:
        season = settings.current_season

    provider = NBAESPNPlayerProvider()
    teams_query = select(Team).where(Team.league == "NBA")
    if team_id:
        teams_query = teams_query.where(Team.provider_id == team_id)

    teams = db.scalars(teams_query).all()
    total_synced = 0

    for team in teams:
        try:
            roster = provider.get_team_roster(team.provider_id, season)
        except ProviderError:
            continue

        for player_data in roster:
            provider_id = player_data["provider_id"]
            player = db.scalar(select(Player).where(Player.provider_id == provider_id, Player.league == "NBA"))
            if not player:
                player = Player(provider_id=provider_id, external_id=player_data["external_id"], league="NBA")
                db.add(player)

            for key, value in player_data.items():
                if key not in {"external_id", "provider_id"}:
                    setattr(player, key, value)
            player.team_id = team.id
            total_synced += 1

    db.commit()
    return total_synced


def sync_player_details(db, player_id: str) -> Optional[Player]:
    """Sync detailed player info including career stats."""
    provider = NBAESPNPlayerProvider()
    try:
        details = provider.get_player_details(player_id)
        career_stats = provider.get_player_career_stats(player_id)
        game_log = provider.get_player_game_log(player_id)
        splits = provider.get_player_splits(player_id)
        awards = provider.get_player_awards(player_id)
    except ProviderError:
        return None

    player = db.scalar(select(Player).where(Player.provider_id == player_id, Player.league == "NBA"))
    if not player:
        player = Player(provider_id=player_id, external_id=details["external_id"], league="NBA")
        db.add(player)

    for key, value in details.items():
        if key not in {"external_id", "provider_id"}:
            setattr(player, key, value)

    player.career_stats = career_stats
    player.game_log = game_log
    player.splits = splits
    player.awards = awards

    db.commit()
    db.refresh(player)
    return player