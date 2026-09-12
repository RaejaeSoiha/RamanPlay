"""Public ESPN scoreboard provider for real NFL schedules and scores."""

import time

import httpx

from app.config import settings
from app.schemas.feed import GameInput
from app.services.normalization import normalize_network, normalize_team
from app.services.providers import GameDataProvider
from app.services.sportsdata import ProviderError


class ESPNProvider(GameDataProvider):
    _cache = {}
    _standings_cache = {}
    endpoint = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    standings_endpoint = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"

    def __init__(self, client=None):
        self.client = client

    def get_schedule(self):
        season = settings.current_season
        cached = self._cache.get(season)
        if cached and time.monotonic() - cached[0] < max(
            settings.live_refresh_seconds, 60
        ):
            return [game.model_copy(deep=True) for game in cached[1]]

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
            raise ProviderError(
                "ESPN scoreboard could not be reached or returned invalid data. "
                "Stored games were preserved."
            ) from None
        finally:
            if self.client is None:
                client.close()

        events = data.get("events") if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ProviderError(
                "ESPN scoreboard returned an unexpected response. "
                "Stored games were preserved."
            )
        try:
            games = [
                self.normalize(event)
                for event in events
                if event.get("season", {}).get("year") == season
            ]
        except (KeyError, TypeError, ValueError):
            raise ProviderError(
                "ESPN scoreboard returned an invalid game record. "
                "Stored games were preserved."
            ) from None
        if not games:
            raise ProviderError(
                "ESPN scoreboard returned no games for this season. "
                "Stored games were preserved."
            )
        if len({game.external_id for game in games}) != len(games):
            raise ProviderError(
                "ESPN scoreboard returned duplicate game IDs. "
                "Stored games were preserved."
            )
        self._cache.clear()
        self._cache[season] = (time.monotonic(), games)
        return [game.model_copy(deep=True) for game in games]

    def get_standings(self):
        season = settings.current_season
        cached = self._standings_cache.get(season)
        if cached and time.monotonic() - cached[0] < max(
            settings.live_refresh_seconds, 60
        ):
            return [dict(team) for team in cached[1]]

        client = self.client or httpx.Client(
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )
        try:
            response = client.get(
                self.standings_endpoint,
                params={"season": season, "seasontype": 2},
                headers={"User-Agent": settings.user_agent},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise ProviderError(
                "ESPN standings could not be reached or returned invalid data."
            ) from None
        finally:
            if self.client is None:
                client.close()

        conferences = data.get("children") if isinstance(data, dict) else None
        if not isinstance(conferences, list):
            raise ProviderError("ESPN standings returned an unexpected response.")
        try:
            teams = [
                self.normalize_standing(entry)
                for conference in conferences
                for entry in conference["standings"]["entries"]
            ]
        except (KeyError, TypeError, ValueError):
            raise ProviderError("ESPN standings returned an invalid team record.") from None
        if len(teams) != 32 or len({team["abbreviation"] for team in teams}) != 32:
            raise ProviderError("ESPN standings did not include every NFL team.")
        self._standings_cache.clear()
        self._standings_cache[season] = (time.monotonic(), teams)
        return [dict(team) for team in teams]

    @staticmethod
    def normalize(event):
        competition = event["competitions"][0]
        teams = {team["homeAway"]: team for team in competition["competitors"]}
        status = ESPNProvider.normalize_status(
            competition.get("status") or event.get("status") or {}
        )
        away = teams["away"]
        home = teams["home"]
        broadcasts = competition.get("broadcasts") or []
        names = broadcasts[0].get("names") if broadcasts else []
        return GameInput(
            external_id="espn-" + str(event["id"]),
            season=int(event["season"]["year"]),
            season_type={1: "PRESEASON", 2: "REGULAR", 3: "POSTSEASON"}.get(
                event["season"].get("type"), "REGULAR"
            ),
            week=int(event.get("week", {}).get("number") or 0),
            kickoff_time=event.get("date"),
            away=normalize_team(away["team"]["abbreviation"]),
            home=normalize_team(home["team"]["abbreviation"]),
            status=status,
            venue=str((competition.get("venue") or {}).get("fullName") or ""),
            broadcast_network=normalize_network(names[0] if names else None),
            away_score=ESPNProvider.score(away)
            if status in ("LIVE", "HALFTIME", "FINAL")
            else None,
            home_score=ESPNProvider.score(home)
            if status in ("LIVE", "HALFTIME", "FINAL")
            else None,
        )

    @staticmethod
    def score(team):
        value = team.get("score")
        return int(value) if value not in (None, "") else None

    @staticmethod
    def normalize_status(status):
        kind = status.get("type") or {}
        name = str(kind.get("name") or "").upper()
        state = str(kind.get("state") or "").lower()
        if "CANCEL" in name:
            return "CANCELLED"
        if "POSTPON" in name or "SUSPEND" in name:
            return "POSTPONED"
        if state == "post" or kind.get("completed"):
            return "FINAL"
        if "HALFTIME" in name or "HALF" in str(kind.get("detail") or "").upper():
            return "HALFTIME"
        if state == "in":
            return "LIVE"
        return "SCHEDULED"

    @staticmethod
    def normalize_standing(entry):
        team = entry["team"]
        stats = {stat.get("name"): stat for stat in entry["stats"]}

        def value(name, default=0):
            return stats.get(name, {}).get("value", default)

        def display(name, default="—"):
            return stats.get(name, {}).get("displayValue", default)

        def record(kind):
            stat = next((s for s in entry["stats"] if s.get("type") == kind), {})
            return stat.get("summary") or stat.get("displayValue") or "—"

        seed = value("playoffSeed", 0)
        return {
            "abbreviation": normalize_team(team["abbreviation"]),
            "wins": int(value("wins")),
            "losses": int(value("losses")),
            "ties": int(value("ties")),
            "win_percentage": display("winPercent", ".000"),
            "division_record": record("vsdiv"),
            "conference_record": record("vsconf"),
            "points_for": int(value("pointsFor")),
            "points_against": int(value("pointsAgainst")),
            "streak": display("streak"),
            "playoff_rank": int(seed) if seed and int(seed) > 0 else None,
        }
