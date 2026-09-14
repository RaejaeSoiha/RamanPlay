from app.api import routes
from app.services.nfl_players import NFLPlayerProvider


def athlete(**changes):
    row = {
        "id": "3918298",
        "fullName": "Josh Allen",
        "jersey": "17",
        "position": {"abbreviation": "QB", "displayName": "Quarterback"},
        "displayHeight": "6' 5\"",
        "displayWeight": "237 lbs",
        "age": 30,
        "college": {"name": "Wyoming"},
        "headshot": {"href": "https://a.espncdn.com/player.png"},
        "status": {"name": "Active"},
    }
    row.update(changes)
    return row


def test_nfl_roster_normalization_keeps_ramanplay_team_key():
    player = NFLPlayerProvider.normalize(athlete(), "BUF")

    assert player == {
        "id": "3918298",
        "full_name": "Josh Allen",
        "team": "BUF",
        "jersey": "17",
        "position": "QB",
        "position_name": "Quarterback",
        "height": "6' 5\"",
        "weight": "237 lbs",
        "age": 30,
        "college": "Wyoming",
        "headshot_url": "https://a.espncdn.com/player.png",
        "status": "Active",
    }
    assert NFLPlayerProvider.espn_team_ids["WAS"] == "wsh"


def test_nfl_players_api_filters_espn_roster(client, monkeypatch):
    rows = [
        NFLPlayerProvider.normalize(athlete(), "BUF"),
        NFLPlayerProvider.normalize(athlete(id="2", fullName="James Cook"), "BUF"),
    ]
    monkeypatch.setattr(routes.NFLPlayerProvider, "get_players", lambda _, __: rows)

    response = client.get("/api/nfl/players?q=Josh%20Allen")

    assert response.status_code == 200
    assert response.json() == [rows[0]]


def test_nfl_player_detail_api_returns_the_selected_roster_player(client, monkeypatch):
    row = NFLPlayerProvider.normalize(athlete(), "BUF")
    monkeypatch.setattr(routes.NFLPlayerProvider, "get_players", lambda _, __: [row])

    response = client.get("/api/nfl/players/BUF/3918298")

    assert response.status_code == 200
    assert response.json() == row
    assert client.get("/api/nfl/players/BUF/missing").status_code == 404
