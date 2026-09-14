from sqlalchemy import select

from app.api import routes
from app.models.entities import Player, Team
from app.watch import links as personal_links
from app.services.nba import NBAESPNProvider, nba_key, seed_nba_teams, sync_nba_games


def nba_event(**changes):
    event = {
        "id": "401810326",
        "date": "2026-10-20T23:30:00Z",
        "season": {"year": 2026, "type": 2},
        "week": {"number": 1},
        "status": {"type": {"state": "in", "name": "STATUS_IN_PROGRESS"}},
        "competitions": [
            {
                "venue": {"fullName": "Toyota Center"},
                "broadcasts": [{"names": ["ESPN"]}],
                "competitors": [
                    {"homeAway": "away", "team": {"abbreviation": "BKN"}, "score": "101"},
                    {"homeAway": "home", "team": {"abbreviation": "HOU"}, "score": "105", "records": [{"name": "overall", "summary": "12-8"}]},
                ],
            }
        ],
    }
    event.update(changes)
    return event


def test_nba_normalizes_espn_event_and_internal_team_keys():
    game = NBAESPNProvider.normalize(nba_event())
    assert game.external_id == "espn-nba-401810326"
    assert (game.away, game.home) == ("NBA_BKN", "NBA_HOU")
    assert game.status == "LIVE"
    assert (game.away_score, game.home_score) == (101, 105)
    assert game.home_record == "12-8"
    assert game.venue == "Toyota Center" and game.broadcast_network == "ESPN"
    assert nba_key("GS") == "NBA_GSW"
    assert nba_key("WSH") == "NBA_WAS"


def test_nba_teams_games_search_and_league_filter(client, db):
    seed_nba_teams(db)
    game = NBAESPNProvider.normalize(nba_event())
    sync_nba_games(db, [game])

    teams = client.get("/api/teams?league=NBA").json()
    assert len(teams) == 30
    assert {team["name"] for team in teams} >= {"Nuggets", "Lakers", "Celtics", "Warriors", "Knicks"}
    nuggets = next(team for team in teams if team["name"] == "Nuggets")
    assert nuggets["abbreviation"] == "DEN" and nuggets["internal_abbreviation"] == "NBA_DEN"

    nba_games = client.get("/api/games?league=NBA").json()
    assert len(nba_games) == 1
    assert nba_games[0]["league"] == "NBA" and nba_games[0]["away_team"]["league"] == "NBA"
    assert client.get("/api/games?league=NFL").json()
    assert client.get("/api/search?league=NBA&q=Rockets").json()[0]["id"] == nba_games[0]["id"]


def test_nba_my_links_remain_attached_only_to_its_game(client, db, monkeypatch):
    seed_nba_teams(db)
    sync_nba_games(db, [NBAESPNProvider.normalize(nba_event())])
    nba_game = client.get("/api/games?league=NBA").json()[0]
    monkeypatch.setattr(routes, "validate_url", lambda url: url)

    class OnlineChecker:
        async def check_personal_details(self, url):
            return "ONLINE", 200, url, 0.1, None, 0

    monkeypatch.setattr(personal_links, "LinkChecker", OnlineChecker)
    created = client.post(
        f"/api/my-links/{nba_game['id']}",
        json={"url": "https://www.espn.com/watch", "source_name": "NBA watch"},
    )
    assert created.status_code == 201
    assert client.get(f"/api/games/{nba_game['id']}").json()["my_links"][0]["id"] == created.json()["id"]
    assert all(
        all(link["id"] != created.json()["id"] for link in row["my_links"])
        for row in client.get("/api/games?league=NFL").json()
    )


def test_nba_standings_are_grouped_and_safely_unavailable(client, db, monkeypatch):
    seed_nba_teams(db)
    rows = []
    for position, abbreviation in enumerate(("BOS", "NY", "BKN"), 1):
        rows.append(
            {
                "abbreviation": nba_key(abbreviation),
                "conference": "Eastern",
                "wins": 60 - position,
                "losses": 20 + position,
                "ties": 0,
                "win_percentage": f".{(750 - position):03d}",
                "games_back": str(position - 1),
                "division_record": "10-4",
                "conference_record": "35-17",
                "points_for": 0,
                "points_against": 0,
                "streak": "W2",
                "playoff_rank": position,
            }
        )
    rows.extend(
        [
            {**rows[0], "abbreviation": nba_key("DEN"), "conference": "Western", "playoff_rank": 1},
            {**rows[1], "abbreviation": nba_key("LAL"), "conference": "Western", "playoff_rank": 2},
        ]
    )
    monkeypatch.setattr(NBAESPNProvider, "get_standings", lambda _: rows)
    response = client.get("/api/standings?league=NBA")
    assert response.status_code == 200
    conferences = response.json()["conferences"]
    assert [conference["name"] for conference in conferences] == ["Eastern", "Western"]
    assert conferences[0]["divisions"][0]["teams"][0]["conference_leader"]

    from app.services.sportsdata import ProviderError

    monkeypatch.setattr(NBAESPNProvider, "get_standings", lambda _: (_ for _ in ()).throw(ProviderError("upstream")))
    assert client.get("/api/standings?league=NBA").status_code == 503


def test_nba_players_include_team_id_and_support_team_filter(client, db):
    team = db.scalar(select(Team).where(Team.league == "NBA", Team.abbreviation == nba_key("DEN")))
    assert team is not None
    player = Player(
        external_id="test-nba-player-team-grouping",
        provider_id="test-nba-player-team-grouping",
        league="NBA",
        team_id=team.id,
        full_name="Team Grouping Player",
        display_name="Team Grouping Player",
    )
    db.add(player)
    db.commit()

    response = client.get("/api/nba/players", params={"team": team.provider_id})

    assert response.status_code == 200
    row = next(row for row in response.json() if row["id"] == player.id)
    assert row["team_id"] == team.id
