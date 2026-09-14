"""Cached ESPN NFL roster adapter for the NFL player directory."""

import time

import httpx

from app.config import settings
from app.services.sportsdata import ProviderError


class NFLPlayerProvider:
    _cache: tuple[float, list[dict]] | None = None
    endpoint = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team}/roster"
    # RamanPlay's persisted NFL team abbreviation is WAS, while ESPN's roster
    # endpoint still uses WSH. Keep the public response keyed by RamanPlay's
    # established abbreviation.
    espn_team_ids = {"WAS": "wsh"}

    def get_players(self, teams: list[str]) -> list[dict]:
        cached = type(self)._cache
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 300):
            return [dict(player) for player in cached[1]]

        players: list[dict] = []
        try:
            with httpx.Client(
                timeout=settings.provider_timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                for team in teams:
                    espn_team = self.espn_team_ids.get(team, team.lower())
                    response = client.get(
                        self.endpoint.format(team=espn_team),
                        params={"season": settings.current_season},
                        headers={"User-Agent": settings.user_agent},
                    )
                    response.raise_for_status()
                    for group in response.json().get("athletes") or []:
                        for athlete in group.get("items") or []:
                            player = self.normalize(athlete, team)
                            if player:
                                players.append(player)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(f"ESPN NFL player data could not be reached: {exc}") from None

        if not players:
            raise ProviderError("ESPN NFL player data returned no roster entries.")
        type(self)._cache = (time.monotonic(), players)
        return [dict(player) for player in players]

    @staticmethod
    def normalize(athlete: dict, team: str) -> dict | None:
        player_id = str(athlete.get("id") or "")
        name = str(athlete.get("fullName") or athlete.get("displayName") or "")
        if not player_id or not name:
            return None
        position = athlete.get("position") or {}
        headshot = athlete.get("headshot") or {}
        return {
            "id": player_id,
            "full_name": name,
            "team": team,
            "jersey": str(athlete.get("jersey") or ""),
            "position": str(position.get("abbreviation") or ""),
            "position_name": str(position.get("displayName") or position.get("name") or ""),
            "height": str(athlete.get("displayHeight") or ""),
            "weight": str(athlete.get("displayWeight") or ""),
            "age": athlete.get("age"),
            "college": str((athlete.get("college") or {}).get("name") or ""),
            "headshot_url": str(headshot.get("href") or ""),
            "status": str((athlete.get("status") or {}).get("name") or ""),
        }
