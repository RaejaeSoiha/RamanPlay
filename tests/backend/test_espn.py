import httpx
import pytest

from app.config import settings
from app.services.espn import ESPNProvider
from app.services.sportsdata import ProviderError


def event(**changes):
    data = {
        "id": "123",
        "date": "2025-09-07T20:25:00Z",
        "season": {"year": 2025, "type": 2},
        "week": {"number": 1},
        "status": {"type": {"state": "pre", "name": "STATUS_SCHEDULED"}},
        "competitions": [
            {
                "venue": {"fullName": "Arrowhead Stadium"},
                "broadcasts": [{"names": ["NBC"]}],
                "competitors": [
                    {"homeAway": "away", "team": {"abbreviation": "DEN"}},
                    {"homeAway": "home", "team": {"abbreviation": "KC"}},
                ],
            }
        ],
    }
    data.update(changes)
    return data


def test_espn_provider_normalizes_schedule_scores_and_cache(monkeypatch):
    monkeypatch.setattr(settings, "nfl_season", 2025)
    calls = []
    live = event()
    live["status"] = {"type": {"state": "in", "name": "STATUS_IN_PROGRESS"}}
    live["competitions"][0]["competitors"][0]["score"] = "17"
    live["competitions"][0]["competitors"][1]["score"] = "14"

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"events": [live]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = ESPNProvider(client)
        games = provider.get_schedule()
        assert provider.get_schedule()[0].external_id == "espn-123"

    game = games[0]
    assert game.away == "DEN" and game.home == "KC"
    assert game.status == "LIVE" and game.away_score == 17 and game.home_score == 14
    assert game.broadcast_network == "NBC" and game.development_data is False
    assert len(calls) == 1
    assert "dates=2025" in str(calls[0].url) and "limit=1000" in str(calls[0].url)


def test_espn_provider_rejects_an_empty_season(monkeypatch):
    monkeypatch.setattr(settings, "nfl_season", 2025)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"events": []}))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(ProviderError, match="no games"):
            ESPNProvider(client).get_schedule()


def test_auto_provider_uses_espn_without_a_paid_key(monkeypatch):
    monkeypatch.setattr(settings, "nfl_data_api_key", "")
    monkeypatch.setattr(settings, "data_provider", "auto")
    assert settings.selected_provider == "espn"


def test_espn_normalizes_standing_stats():
    entry = {
        "team": {"abbreviation": "DEN"},
        "stats": [
            {"name": "wins", "value": 3},
            {"name": "losses", "value": 1},
            {"name": "ties", "value": 0},
            {"name": "winPercent", "displayValue": ".750"},
            {"name": "pointsFor", "value": 110},
            {"name": "pointsAgainst", "value": 85},
            {"name": "streak", "displayValue": "W3"},
            {"name": "playoffSeed", "value": 2},
            {"type": "vsdiv", "summary": "2-0"},
            {"type": "vsconf", "summary": "3-1"},
        ],
    }

    assert ESPNProvider.normalize_standing(entry) == {
        "abbreviation": "DEN",
        "wins": 3,
        "losses": 1,
        "ties": 0,
        "win_percentage": ".750",
        "division_record": "2-0",
        "conference_record": "3-1",
        "points_for": 110,
        "points_against": 85,
        "streak": "W3",
        "playoff_rank": 2,
    }
