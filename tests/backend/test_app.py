import asyncio, socket
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from sqlalchemy import select, func
from app.models.entities import Game, WatchSource, LinkCheck
from app.services.ingestion import update_schedule
from app.services.security import validate_url
from app.services.checker import LinkChecker
from app.sources.official import OfficialSourceProvider
from app.services.providers import DevelopmentProvider
from app.schemas.feed import GameInput
from app.config import settings


def test_import_idempotent(db):
    update_schedule(db)
    assert db.scalar(select(func.count(Game.id))) == 16
    assert db.scalar(select(func.count(WatchSource.id))) == 17


def test_provider_interface():
    p = DevelopmentProvider()
    g = p.get_games()[0]
    assert p.get_game(g.external_id).external_id == g.external_id
    assert all(g.status in ("LIVE", "HALFTIME") for g in p.get_live_games())
    assert all(g.development_data for g in p.get_schedule())


@pytest.mark.parametrize(
    "url",
    [
        "http://nfl.com",
        "https://127.0.0.1",
        "https://localhost",
        "https://169.254.169.254/latest/meta-data",
        "https://nfl.com.evil.test",
        "https://evilnfl.com",
        "https://user:pass@nfl.com",
        "https://nfl.com:444",
        "https://0.0.0.0",
        "https://[::1]",
    ],
)
def test_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_url(url, False)


def test_subdomains():
    assert validate_url("https://www.nfl.com/ways-to-watch", False)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "100.64.0.1",
    ],
)
def test_private_dns(ip):
    with patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))],
    ):
        with pytest.raises(ValueError):
            validate_url("https://nfl.com")


def test_source_classification():
    p = OfficialSourceProvider()
    g = DevelopmentProvider().get_games()[0]
    s = next(s for s in p.find_sources(g) if s["access_type"] == "OFFICIAL")
    assert s["is_official"] and not s["is_free"] and s["access_type"] == "OFFICIAL"
    with pytest.raises(ValueError):
        p.classify_source(dict(s, access_type="FREE"))
    free = p.classify_source(
        dict(
            provider_name="NFL",
            source_name="Confirmed example",
            url="https://nfl.com/",
            source_type="FREE_LEGAL",
            access_type="FREE",
            notes="Explicit test-only evidence",
            region="US",
        )
    )
    assert free["is_free"] and not free["requires_subscription"]


@pytest.mark.parametrize(
    "code,state",
    [(200, "ONLINE"), (404, "NOT_FOUND"), (403, "BLOCKED"), (500, "ERROR")],
)
def test_checker_status(code, state, monkeypatch):
    monkeypatch.setattr(settings, "request_interval_seconds", 0)

    def request(url, method):
        if url.endswith("robots.txt"):
            return 404, {}, b""
        return code, {}, b""

    assert asyncio.run(LinkChecker(request).check("https://nfl.com"))[0] == state


def test_checker_fallback_redirect(monkeypatch):
    monkeypatch.setattr(settings, "request_interval_seconds", 0)
    calls = []

    def request(url, method):
        calls.append((url, method))
        if url.endswith("robots.txt"):
            return 404, {}, b""
        if url.endswith("/start"):
            return 302, {"location": "/watch"}, b""
        if method == "HEAD":
            return 405, {}, b""
        return 200, {}, b""

    result = asyncio.run(LinkChecker(request).check("https://nfl.com/start"))
    assert result[0] == "REDIRECT" and result[2] == "https://nfl.com/watch"
    assert ("https://nfl.com/watch", "GET") in calls


def test_reject_redirect_before_request(monkeypatch):
    monkeypatch.setattr(settings, "request_interval_seconds", 0)

    def request(url, method):
        assert "127.0.0.1" not in url
        if url.endswith("robots.txt"):
            return 404, {}, b""
        return 302, {"location": "https://127.0.0.1/private"}, b""

    assert asyncio.run(LinkChecker(request).check("https://nfl.com"))[0] == "ERROR"


def test_robots(monkeypatch):
    monkeypatch.setattr(settings, "request_interval_seconds", 0)

    def request(url, method):
        assert url.endswith("robots.txt")
        return 200, {}, b"User-agent: *\nDisallow: /"

    assert (
        asyncio.run(LinkChecker(request).check("https://nfl.com/watch"))[0] == "BLOCKED"
    )


def test_link_results_persist_and_deduplicate(db, monkeypatch):
    monkeypatch.setattr(settings, "request_interval_seconds", 0)
    calls = []

    def request(url, method):
        calls.append(url)
        return (404, {}, b"") if url.endswith("robots.txt") else (200, {}, b"")

    asyncio.run(LinkChecker(request).check_all(db))
    assert len(calls) == 4
    assert db.scalar(select(func.count(LinkCheck.id))) == 17
    assert db.scalars(select(WatchSource)).first().status == "ONLINE"


@pytest.mark.parametrize(
    "path",
    [
        "/api/games",
        "/api/games/today",
        "/api/games/live",
        "/api/games/upcoming",
        "/api/teams",
        "/api/teams/1",
        "/api/games/1",
        "/api/sources/1",
        "/api/favorites",
        "/api/health",
    ],
)
def test_endpoints(client, path):
    assert client.get(path).status_code == 200


def test_search_match_and_filters(client):
    data = client.get("/api/search?q=Broncos%20Chiefs").json()
    assert len(data) == 1 and data[0]["away_team"]["abbreviation"] == "DEN"
    assert client.get("/api/search?q=Free%20games").json() == []
    assert len(client.get("/api/games?team=DEN").json()) == 1
    assert client.get("/api/games?tz=NotReal").status_code == 422
    assert client.get("/api/games/999").status_code == 404
    assert all(
        g["status"] in ("LIVE", "HALFTIME")
        for g in client.get("/api/games/live").json()
    )


def test_admin_protection_and_update(client):
    for action in ["update-schedule", "check-links", "rebuild-sources"]:
        assert client.post("/api/admin/" + action).status_code == 401
    assert client.get("/api/admin/status").status_code == 401
    headers = {"Authorization": "Bearer test-maintenance-key"}
    assert (
        client.post("/api/admin/update-schedule", headers=headers).json()["updated"]
        == 16
    )
    assert client.get("/api/admin/status", headers=headers).json()["games"] == 16


def test_headers(client):
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"


def test_timezone_filter_boundary(client, db):
    g = db.get(Game, 1)
    g.kickoff_time = datetime.now(timezone.utc).replace(hour=1, minute=0)
    db.commit()
    from zoneinfo import ZoneInfo

    expected = (
        g.kickoff_time.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
    )
    result = client.get(
        "/api/games", params={"date": expected, "tz": "America/Los_Angeles"}
    ).json()
    assert any(row["id"] == 1 for row in result)


def test_unknown_team_import_atomic(db, monkeypatch):
    import app.services.ingestion as ingestion

    rows = DevelopmentProvider().get_games()
    rows[0].away = "ZZZ"

    class BadProvider:
        def get_schedule(self):
            return rows

    monkeypatch.setattr(ingestion, "provider", lambda: BadProvider())
    with pytest.raises(ValueError):
        update_schedule(db)
    assert db.scalar(select(func.count(Game.id))) == 16


def test_reject_naive_datetime():
    with pytest.raises(ValueError):
        GameInput(
            external_id="x",
            season=2026,
            week=1,
            kickoff_time="2026-09-01T20:00:00",
            away="DEN",
            home="KC",
        )


def test_tbd_games_stay_in_full_schedule(client, db):
    g = db.get(Game, 1)
    g.kickoff_time = None
    g.game_date = "TBD"
    db.commit()
    assert client.get("/api/games/1").json()["kickoff_time"] is None
    assert any(g["id"] == 1 for g in client.get("/api/games").json())
    assert all(g["id"] != 1 for g in client.get("/api/games/today").json())


def test_link_frequency_authenticated_and_bounded(client):
    assert client.post("/api/admin/settings", json={"hours": 2}).status_code == 401
    h = {"Authorization": "Bearer test-maintenance-key"}
    assert (
        client.post("/api/admin/settings", json={"hours": 0}, headers=h).status_code
        == 422
    )
    assert (
        client.post("/api/admin/settings", json={"hours": 12}, headers=h).json()[
            "link_check_hours"
        ]
        == 12
    )
