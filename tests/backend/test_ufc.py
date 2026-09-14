from app.api import routes
from app.watch import links as personal_links
from app.services.ufc import UFCESPNProvider, fighter_key, sync_ufc_events


def ufc_event(**changes):
    event = {
        "id": "600000001",
        "name": "UFC 330: Alpha vs. Bravo",
        "date": "2026-10-10T22:00:00Z",
        "season": {"year": 2026, "type": 2},
        "status": {"type": {"state": "in", "name": "STATUS_IN_PROGRESS"}},
        "competitions": [
            {
                "id": "401000001",
                "date": "2026-10-10T22:00:00Z",
                "type": {"abbreviation": "Lightweight"},
                "venue": {"fullName": "Example Arena", "address": {"city": "Denver", "state": "CO"}},
                "broadcast": "ESPN+",
                "format": {"regulation": {"periods": 3}},
                "status": {"type": {"state": "pre", "name": "STATUS_SCHEDULED"}},
                "competitors": [
                    {"id": "10", "order": 1, "winner": False, "athlete": {"fullName": "Alpha Fighter", "flag": {"alt": "USA"}}, "records": [{"name": "overall", "summary": "10-1-0"}]},
                    {"id": "11", "order": 2, "winner": False, "athlete": {"fullName": "Bravo Fighter", "flag": {"alt": "Canada"}}, "records": [{"name": "overall", "summary": "11-2-0"}]},
                ],
            },
            {
                "id": "401000002",
                "date": "2026-10-11T02:00:00Z",
                "type": {"abbreviation": "Heavyweight"},
                "venue": {"fullName": "Example Arena", "address": {"city": "Denver", "state": "CO"}},
                "broadcast": "ESPN+",
                "format": {"regulation": {"periods": 5}},
                "status": {"period": 2, "displayClock": "3:42", "type": {"state": "post", "name": "STATUS_FINAL", "completed": True}},
                "competitors": [
                    {"id": "12", "order": 1, "winner": True, "athlete": {"fullName": "Main Winner"}, "records": [{"name": "overall", "summary": "20-1-0"}]},
                    {"id": "13", "order": 2, "winner": False, "athlete": {"fullName": "Main Opponent"}, "records": [{"name": "overall", "summary": "15-4-0"}]},
                ],
            },
        ],
    }
    event.update(changes)
    return event


def test_ufc_provider_normalizes_event_bouts_and_fighters():
    event = UFCESPNProvider.normalize(ufc_event())
    assert event["external_id"] == "espn-ufc-600000001"
    assert event["status"] == "LIVE" and event["broadcast_network"] == "ESPN+"
    assert event["location"] == "Denver, CO"
    assert event["bouts"][-1]["card_section"] == "MAIN_EVENT"
    assert event["bouts"][-1]["winner_external_id"] == "espn-ufc-fighter-12"
    assert event["bouts"][-1]["result_round"] == 2
    assert fighter_key("Jon Jones", "1") == "UFC_JON_JONES_1"


def test_ufc_event_search_card_and_my_links(client, db, monkeypatch):
    sync_ufc_events(db, [UFCESPNProvider.normalize(ufc_event())])
    events = client.get("/api/ufc/events?q=Alpha").json()
    assert len(events) == 1 and events[0]["main_event"]["fighter_a"]["full_name"] == "Main Winner"
    event = events[0]
    detail = client.get(f"/api/ufc/events/{event['id']}").json()
    assert len(detail["bouts"]) == 2
    assert client.get("/api/search?league=UFC&q=Heavyweight").json()[0]["id"] == event["id"]
    fighter = client.get("/api/ufc/fighters?q=Alpha").json()[0]
    assert client.get(f"/api/ufc/fighters/{fighter['id']}").json()["full_name"] == "Alpha Fighter"

    monkeypatch.setattr(routes, "validate_url", lambda url: url)
    class OnlineChecker:
        async def check_personal_details(self, url):
            return "ONLINE", 200, url, 0.1, None, 0
    monkeypatch.setattr(personal_links, "LinkChecker", OnlineChecker)
    created = client.post(f"/api/ufc/events/{event['id']}/my-links", json={"url": "https://www.espn.com/watch", "source_name": "UFC link"})
    assert created.status_code == 201
    assert created.json()["event_id"] == event["id"] and created.json()["game_id"] is None
    assert client.get(f"/api/ufc/events/{event['id']}/my-links").json()[0]["id"] == created.json()["id"]
