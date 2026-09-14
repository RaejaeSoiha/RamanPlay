from app.models.entities import Game
from app.services.nba import NBAESPNProvider, sync_nba_games
from app.services.recaps import game_recap
from app.services.ufc import UFCESPNProvider, sync_ufc_events

from test_nba import nba_event
from test_ufc import ufc_event


def final_nba_event():
    row = nba_event()
    row["status"] = {"type": {"state": "post", "name": "STATUS_FINAL", "completed": True}}
    return row


def final_ufc_event():
    row = ufc_event()
    row["status"] = {"type": {"state": "post", "name": "STATUS_FINAL", "completed": True}}
    row["competitions"][0]["status"] = {"period": 1, "displayClock": "1:12", "type": {"state": "post", "name": "STATUS_FINAL", "completed": True}}
    row["competitions"][0]["competitors"][0]["winner"] = True
    return row


def test_nfl_completed_game_recap_uses_stored_final_data(client):
    response = client.get("/api/recaps?sport=NFL&limit=3")
    assert response.status_code == 200
    recap = response.json()[0]
    assert recap["league"] == "NFL" and recap["status"] == "FINAL"
    assert recap["final_score"] and recap["winner"] and recap["loser"]
    assert recap["top_performers"] == [] and recap["notable_stats"] == []
    assert client.get(f"/api/recaps/NFL/{recap['event_id']}").status_code == 200


def test_nba_completed_game_recap_and_sport_isolation(client, db):
    sync_nba_games(db, [NBAESPNProvider.normalize(final_nba_event())])
    response = client.get("/api/recaps?sport=NBA")
    assert response.status_code == 200
    recap = response.json()[0]
    assert recap["league"] == "NBA" and recap["final_score"] == "BKN 101 – HOU 105"
    assert recap["winner"]["name"] == "Houston Rockets"
    assert all(row["league"] == "NBA" for row in response.json())


def test_ufc_completed_event_recap_includes_provider_results(client, db):
    sync_ufc_events(db, [UFCESPNProvider.normalize(final_ufc_event())])
    response = client.get("/api/recaps?sport=UFC")
    assert response.status_code == 200
    recap = response.json()[0]
    assert recap["league"] == "UFC" and recap["winner"]["name"] == "Main Winner"
    assert len(recap["bouts"]) == 2
    assert recap["bouts"][-1]["result_round"] == 2
    assert recap["bouts"][-1]["result_method"] is None
    assert client.get(f"/api/recaps/UFC/{recap['event_id']}").status_code == 200


def test_recap_omits_missing_optional_score_data(db):
    game = db.query(Game).filter(Game.status == "FINAL").first()
    game.away_score = None
    game.home_score = None
    db.commit()
    recap = game_recap(db, game)
    assert recap.final_score is None and recap.winner is None and recap.loser is None


def test_recaps_validate_sport_and_hide_non_final_detail(client, db):
    scheduled = db.query(Game).filter(Game.status != "FINAL").first()
    assert client.get("/api/recaps?sport=MLB").status_code == 422
    assert client.get(f"/api/recaps/NFL/{scheduled.id}").status_code == 404
