"""ESPN NBA data adapter and NBA-specific schedule ingestion."""

import time
from datetime import timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.models.entities import Game, Team
from app.schemas.feed import GameInput
from app.services.espn import ESPNProvider
from app.services.normalization import normalize_network
from app.services.sportsdata import ProviderError


# ESPN's short codes are the provider identifiers. Namespaced internal keys
# keep NBA teams distinct from NFL teams with the same abbreviation.
NBA_TEAMS = (
    ("ATL", "1", "Atlanta", "Hawks", "Eastern", "Southeast"),
    ("BOS", "2", "Boston", "Celtics", "Eastern", "Atlantic"),
    ("BKN", "17", "Brooklyn", "Nets", "Eastern", "Atlantic"),
    ("CHA", "30", "Charlotte", "Hornets", "Eastern", "Southeast"),
    ("CHI", "4", "Chicago", "Bulls", "Eastern", "Central"),
    ("CLE", "5", "Cleveland", "Cavaliers", "Eastern", "Central"),
    ("DAL", "6", "Dallas", "Mavericks", "Western", "Southwest"),
    ("DEN", "7", "Denver", "Nuggets", "Western", "Northwest"),
    ("DET", "8", "Detroit", "Pistons", "Eastern", "Central"),
    ("GSW", "9", "Golden State", "Warriors", "Western", "Pacific"),
    ("HOU", "10", "Houston", "Rockets", "Western", "Southwest"),
    ("IND", "11", "Indiana", "Pacers", "Eastern", "Central"),
    ("LAC", "12", "Los Angeles", "Clippers", "Western", "Pacific"),
    ("LAL", "13", "Los Angeles", "Lakers", "Western", "Pacific"),
    ("MEM", "29", "Memphis", "Grizzlies", "Western", "Southwest"),
    ("MIA", "14", "Miami", "Heat", "Eastern", "Southeast"),
    ("MIL", "15", "Milwaukee", "Bucks", "Eastern", "Central"),
    ("MIN", "16", "Minnesota", "Timberwolves", "Western", "Northwest"),
    ("NOP", "3", "New Orleans", "Pelicans", "Western", "Southwest"),
    ("NYK", "18", "New York", "Knicks", "Eastern", "Atlantic"),
    ("OKC", "25", "Oklahoma City", "Thunder", "Western", "Northwest"),
    ("ORL", "19", "Orlando", "Magic", "Eastern", "Southeast"),
    ("PHI", "20", "Philadelphia", "76ers", "Eastern", "Atlantic"),
    ("PHX", "21", "Phoenix", "Suns", "Western", "Pacific"),
    ("POR", "22", "Portland", "Trail Blazers", "Western", "Northwest"),
    ("SAC", "23", "Sacramento", "Kings", "Western", "Pacific"),
    ("SAS", "24", "San Antonio", "Spurs", "Western", "Southwest"),
    ("TOR", "28", "Toronto", "Raptors", "Eastern", "Atlantic"),
    ("UTA", "26", "Utah", "Jazz", "Western", "Northwest"),
    ("WAS", "27", "Washington", "Wizards", "Eastern", "Southeast"),
)

NBA_ABBREVIATIONS = {
    **{code: code for code, *_ in NBA_TEAMS},
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
    "UTAH": "UTA",
    "WSH": "WAS",
}


def nba_key(abbreviation: str) -> str:
    code = NBA_ABBREVIATIONS.get(str(abbreviation or "").upper())
    if not code:
        raise ValueError("Unrecognized NBA team")
    return "NBA_" + code


def seed_nba_teams(db):
    for code, provider_id, city, name, conference, division in NBA_TEAMS:
        key = nba_key(code)
        if db.scalar(select(Team.id).where(Team.abbreviation == key)):
            continue
        db.add(
            Team(
                abbreviation=key,
                provider_abbreviation=code,
                provider_id=provider_id,
                sport="BASKETBALL",
                league="NBA",
                city=city,
                name=name,
                conference=conference,
                division=division,
                logo_url=f"https://a.espncdn.com/i/teamlogos/nba/500/{code.lower()}.png",
                official_url="https://www.nba.com/teams",
            )
        )
    db.commit()


class NBAESPNProvider:
    """NBA adapter using ESPN's public basketball endpoints."""

    _cache = {}
    _standings_cache = {}
    endpoint = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    standings_endpoint = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

    def __init__(self, client=None):
        self.client = client

    def _request(self, endpoint, params):
        client = self.client or httpx.Client(
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )
        try:
            response = client.get(endpoint, params=params, headers={"User-Agent": settings.user_agent})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ProviderError("ESPN NBA data could not be reached or returned invalid data.") from None
        finally:
            if self.client is None:
                client.close()

    def get_schedule(self):
        season = settings.current_season
        cached = self._cache.get(season)
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 60):
            return [game.model_copy(deep=True) for game in cached[1]]
        data = self._request(self.endpoint, {"dates": season, "limit": 1000})
        events = data.get("events") if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ProviderError("ESPN NBA scoreboard returned an unexpected response.")
        games = []
        for event in events:
            if event.get("season", {}).get("year") != season:
                continue
            try:
                games.append(self.normalize(event))
            except ValueError:
                # ESPN may include international exhibition opponents in the
                # NBA feed. They are not NBA teams and have no RamanPlay team.
                continue
            except (KeyError, TypeError):
                raise ProviderError("ESPN NBA scoreboard returned an invalid game record.") from None
        if len({game.external_id for game in games}) != len(games):
            raise ProviderError("ESPN NBA scoreboard returned duplicate game IDs.")
        self._cache.clear()
        self._cache[season] = (time.monotonic(), games)
        return [game.model_copy(deep=True) for game in games]

    @staticmethod
    def normalize(event):
        competition = event["competitions"][0]
        sides = {entry["homeAway"]: entry for entry in competition["competitors"]}
        status = ESPNProvider.normalize_status(competition.get("status") or event.get("status") or {})
        broadcasts = competition.get("broadcasts") or []
        names = broadcasts[0].get("names") if broadcasts else []
        return GameInput(
            external_id="espn-nba-" + str(event["id"]),
            season=int(event["season"]["year"]),
            season_type={1: "PRESEASON", 2: "REGULAR", 3: "POSTSEASON"}.get(event["season"].get("type"), "REGULAR"),
            week=int(event.get("week", {}).get("number") or 0),
            kickoff_time=event.get("date"),
            away=nba_key(sides["away"]["team"]["abbreviation"]),
            home=nba_key(sides["home"]["team"]["abbreviation"]),
            status=status,
            venue=str((competition.get("venue") or {}).get("fullName") or ""),
            broadcast_network=normalize_network(names[0] if names else None),
            away_score=ESPNProvider.score(sides["away"]) if status in ("LIVE", "HALFTIME", "FINAL") else None,
            home_score=ESPNProvider.score(sides["home"]) if status in ("LIVE", "HALFTIME", "FINAL") else None,
            away_record=NBAESPNProvider.team_record(sides["away"]),
            home_record=NBAESPNProvider.team_record(sides["home"]),
        )

    @staticmethod
    def team_record(competitor):
        records = competitor.get("records") or []
        overall = next((record for record in records if record.get("name") == "overall"), {})
        return overall.get("summary") or None

    def get_standings(self):
        season = settings.current_season
        cached = self._standings_cache.get(season)
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 60):
            return [dict(row) for row in cached[1]]
        data = self._request(self.standings_endpoint, {"season": season, "seasontype": 2})
        conferences = data.get("children") if isinstance(data, dict) else None
        if not isinstance(conferences, list):
            raise ProviderError("ESPN NBA standings returned an unexpected response.")
        try:
            rows = [
                self.normalize_standing(entry, conference.get("name") or conference.get("abbreviation") or "")
                for conference in conferences
                for entry in conference["standings"]["entries"]
            ]
        except (KeyError, TypeError, ValueError):
            raise ProviderError("ESPN NBA standings returned an invalid team record.") from None
        if len(rows) != 30 or len({row["abbreviation"] for row in rows}) != 30:
            raise ProviderError("ESPN NBA standings did not include every NBA team.")
        self._standings_cache.clear()
        self._standings_cache[season] = (time.monotonic(), rows)
        return [dict(row) for row in rows]

    @staticmethod
    def normalize_standing(entry, conference=""):
        stats = {stat.get("name"): stat for stat in entry["stats"]}

        def value(name, default=0):
            return stats.get(name, {}).get("value", default)

        def display(name, default="—"):
            return stats.get(name, {}).get("displayValue", default)

        def record(kind):
            stat = next((stat for stat in entry["stats"] if stat.get("type") == kind), {})
            return stat.get("summary") or stat.get("displayValue") or "—"

        seed = value("playoffSeed", 0)
        return {
            "abbreviation": nba_key(entry["team"]["abbreviation"]),
            "conference": "Eastern" if str(conference).lower().startswith("east") else "Western",
            "wins": int(value("wins")),
            "losses": int(value("losses")),
            "ties": 0,
            "win_percentage": display("winPercent", ".000"),
            "games_back": display("gamesBehind", "—"),
            "division_record": record("vsdiv"),
            "conference_record": record("vsconf"),
            "points_for": int(value("pointsFor")),
            "points_against": int(value("pointsAgainst")),
            "streak": display("streak"),
            "playoff_rank": int(seed) if seed and int(seed) > 0 else None,
        }


def sync_nba_games(db, feed=None):
    """Upsert NBA games only after validating the full ESPN response."""
    feed = NBAESPNProvider().get_schedule() if feed is None else feed
    teams = {team.abbreviation: team.id for team in db.scalars(select(Team).where(Team.league == "NBA"))}
    records = list(feed)
    if len({row.external_id for row in records}) != len(records):
        raise ValueError("Duplicate NBA game IDs")
    if any(row.away not in teams or row.home not in teams or row.away == row.home for row in records):
        raise ValueError("Unknown or identical NBA teams")
    for row in records:
        game = db.scalar(select(Game).where(Game.external_id == row.external_id))
        if not game:
            game = Game(external_id=row.external_id)
            db.add(game)
        final = game.status == "FINAL"
        for key in ("season", "season_type", "week", "status", "venue", "broadcast_network", "away_score", "home_score", "away_record", "home_record", "development_data"):
            if final and key == "status" and row.status != "FINAL":
                continue
            if key in ("away_score", "home_score") and final and (row.status != "FINAL" or getattr(row, key) is None):
                continue
            setattr(game, key, getattr(row, key))
        game.kickoff_time = row.kickoff_time.astimezone(timezone.utc) if row.kickoff_time else None
        game.game_date = game.kickoff_time.date().isoformat() if game.kickoff_time else "TBD"
        game.provider = "espn-nba"
        game.sport = "BASKETBALL"
        game.league = "NBA"
        game.timezone = "UTC"
        game.away_team_id = teams[row.away]
        game.home_team_id = teams[row.home]
    db.commit()
    db.expire_all()
    return len(records)
