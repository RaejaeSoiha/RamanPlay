from app.services.sportsdata import SportsDataProvider
from app.config import settings
import httpx


def test_normalize_live():
    g = SportsDataProvider.normalize(
        {
            "ScoreID": 55,
            "Season": 2026,
            "Week": 1,
            "DateTimeUTC": "2026-09-14T00:15:00",
            "AwayTeam": "LA",
            "HomeTeam": "JAC",
            "Status": "InProgress",
            "Quarter": "HALF",
            "AwayScore": 7,
            "HomeScore": 10,
            "Channel": "NBC",
        }
    )
    assert g.away == "LAR" and g.home == "JAX" and g.status == "HALFTIME"
    assert g.kickoff_time.isoformat() == "2026-09-14T00:15:00+00:00"


def test_full_season_and_cache(monkeypatch):
    monkeypatch.setattr(settings, "nfl_data_api_key", "test-key")
    SportsDataProvider._cache.clear()
    calls = []

    def handler(request):
        calls.append(str(request.url))
        assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
        assert "test-key" not in str(request.url)
        return httpx.Response(
            200,
            json=[
                {
                    "ScoreID": len(calls),
                    "Season": 2026,
                    "Week": 1,
                    "AwayTeam": "DEN",
                    "HomeTeam": "KC",
                    "DateTimeUTC": "2026-09-13T20:00:00",
                    "Status": "Scheduled",
                }
            ],
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        p = SportsDataProvider(client)
        assert len(p.get_schedule()) == 3
        assert len(p.get_schedule()) == 3
    assert (
        len(calls) == 3
        and calls[0].endswith("2026PRE")
        and calls[-1].endswith("2026POST")
    )
    SportsDataProvider._cache.clear()


def test_unannounced_kickoff():
    assert (
        SportsDataProvider.normalize(
            {
                "ScoreID": 1,
                "Season": 2026,
                "Week": 18,
                "AwayTeam": "DEN",
                "HomeTeam": "KC",
            }
        ).kickoff_time
        is None
    )
