from sqlalchemy import select

from app.models.entities import Team
from app.services.espn import ESPNProvider
from app.services.sportsdata import ProviderError


def rows_for(db):
    rows = []
    for team in db.scalars(select(Team).where(Team.league == "NFL")):
        rows.append(
            {
                "abbreviation": team.abbreviation,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "win_percentage": ".000",
                "division_record": "0-0",
                "conference_record": "0-0",
                "points_for": 0,
                "points_against": 0,
                "streak": "—",
                "playoff_rank": None,
            }
        )
    for row in rows:
        if row["abbreviation"] == "DEN":
            row.update(wins=3, win_percentage=".750", points_for=90, playoff_rank=2)
        if row["abbreviation"] == "KC":
            row.update(wins=2, losses=1, win_percentage=".667", points_for=75)
    return rows


def test_standings_groups_all_divisions_and_sorts_leader(client, db, monkeypatch):
    monkeypatch.setattr(ESPNProvider, "get_standings", lambda _: rows_for(db))

    response = client.get("/api/standings")
    assert response.status_code == 200
    payload = response.json()
    assert [conference["name"] for conference in payload["conferences"]] == ["AFC", "NFC"]
    assert [division["name"] for division in payload["conferences"][0]["divisions"]] == [
        "East",
        "North",
        "South",
        "West",
    ]
    west = payload["conferences"][0]["divisions"][3]["teams"]
    assert west[0]["abbreviation"] == "DEN" and west[0]["division_leader"]
    assert {team["abbreviation"] for team in west} == {"DEN", "KC", "LAC", "LV"}
    filtered = client.get("/api/standings/nfc/west")
    assert filtered.status_code == 200
    assert filtered.json()["conferences"][0]["name"] == "NFC"
    assert filtered.json()["conferences"][0]["divisions"][0]["name"] == "West"
    assert len(filtered.json()["conferences"][0]["divisions"][0]["teams"]) == 4


def test_standings_returns_safe_error_when_espn_is_unavailable(client, monkeypatch):
    def unavailable(_):
        raise ProviderError("upstream detail")

    monkeypatch.setattr(ESPNProvider, "get_standings", unavailable)
    response = client.get("/api/standings")
    assert response.status_code == 503
    assert response.json()["detail"] == "Live standings are currently unavailable."
