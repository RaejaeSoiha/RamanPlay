import httpx
import pytest
from sqlalchemy import select, func, create_engine, inspect
from app.config import Settings, settings
from app.models.entities import Game
from app.services.sportsdata import SportsDataProvider, ProviderError
from app.services.normalization import (
    CANONICAL_TEAMS,
    normalize_team,
    normalize_status,
    normalize_network,
    normalize_kickoff,
)
from app.services.ingestion import update_schedule
from app.services.sync import sync_schedule, provider_status, active_provider
from app.database.migrations import migrate


def record(**changes):
    return (
        dict(
            ScoreID=100,
            Season=2026,
            SeasonType=1,
            Week=1,
            AwayTeam="DEN",
            HomeTeam="KC",
            DateTimeUTC="2026-09-14T00:15:00",
            Status="Scheduled",
            **changes,
        )
        if not changes
        else {**record(), **changes}
    )


def mock_provider(monkeypatch, handler):
    monkeypatch.setattr(settings, "nfl_data_api_key", "private-test-key")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    p = SportsDataProvider(client, sleep=lambda _: None)
    monkeypatch.setattr("app.services.ingestion.provider", lambda: p)
    return p


@pytest.mark.parametrize("team", sorted(CANONICAL_TEAMS))
def test_all_canonical_teams(team):
    assert normalize_team(team) == team


@pytest.mark.parametrize(
    "given,expected", [("LA", "LAR"), ("JAC", "JAX"), ("WSH", "WAS"), (" den ", "DEN")]
)
def test_aliases(given, expected):
    assert normalize_team(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        ("PreGame", "PRE_GAME"),
        ("InProgress", "LIVE"),
        ("Halftime", "HALFTIME"),
        ("Final", "FINAL"),
        ("F/OT", "FINAL"),
        ("Suspended", "POSTPONED"),
        ("Canceled", "CANCELLED"),
        ("unknown-value", "SCHEDULED"),
    ],
)
def test_statuses(given, expected):
    assert normalize_status(given) == expected


def test_unknown_status_safe_logging(caplog):
    assert normalize_status("SECRET-INPUT") == "SCHEDULED"
    assert (
        "Unknown provider status" in caplog.text and "SECRET-INPUT" not in caplog.text
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("TBA", None),
        ("amazon", "Prime Video"),
        ("NFLN", "NFL Network"),
        ("fox", "FOX"),
        ("ESPN+", "ESPN+"),
    ],
)
def test_broadcasts(value, expected):
    assert normalize_network(value) == expected


@pytest.mark.parametrize(
    "phase,expected", [(1, "REGULAR"), (2, "PRESEASON"), (3, "POSTSEASON")]
)
def test_phase_mapping(phase, expected):
    assert (
        SportsDataProvider.normalize(record(SeasonType=phase)).season_type == expected
    )


def test_scheduled_scores_removed_and_extra_fields_ignored():
    g = SportsDataProvider.normalize(
        record(AwayScore=99, HomeScore=99, Unexpected="ignored")
    )
    assert g.away_score is None and g.home_score is None and g.broadcast_network is None


def test_offset_preserved():
    assert (
        normalize_kickoff({"DateTimeUTC": "2026-09-13T20:15:00-04:00"}).isoformat()
        == "2026-09-14T00:15:00+00:00"
    )
    assert (
        normalize_kickoff({"Date": "2026-12-01T20:15:00"}).isoformat()
        == "2026-12-02T01:15:00+00:00"
    )


def test_composite_identity():
    a = SportsDataProvider.normalize(record(ScoreID=None))
    b = SportsDataProvider.normalize(record(ScoreID=None))
    assert a.external_id == b.external_id and "composite" in a.external_id


@pytest.mark.parametrize("code", [401, 403, 429, 500, 503])
def test_provider_http_failures_preserve_fallback(db, monkeypatch, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(code, text="SECRET-RESPONSE")

    mock_provider(monkeypatch, handler)
    result = sync_schedule(db)
    assert result["errors"] == 1 and active_provider(db) == "development"
    assert db.scalar(select(func.count(Game.id))) == 16
    info = provider_status(db)
    assert info["provider_status"] == "Error" and info["last_attempted_sync"]
    assert "SECRET" not in info[
        "last_provider_error"
    ] and "private-test-key" not in str(info)
    assert len(calls) == (3 if code >= 500 else 1)


@pytest.mark.parametrize(
    "kind", ["timeout", "network", "json", "format", "empty", "badteam"]
)
def test_provider_bad_responses(db, monkeypatch, kind):
    def handler(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("secret", request=request)
        if kind == "network":
            raise httpx.ConnectError("secret", request=request)
        if kind == "json":
            return httpx.Response(200, text="not JSON secret")
        if kind == "format":
            return httpx.Response(200, json={"unexpected": "secret"})
        if kind == "badteam":
            return httpx.Response(200, json=[record(AwayTeam="XYZ")])
        return httpx.Response(200, json=[])

    mock_provider(monkeypatch, handler)
    assert sync_schedule(db)["errors"] == 1
    assert len(db.scalars(select(Game)).all()) == 16
    assert "secret" not in provider_status(db)["last_provider_error"]


def test_missing_key_fallback(db):
    settings.data_provider = "sportsdataio"
    assert settings.selected_provider == "development"
    result = sync_schedule(db)
    assert result["errors"] == 0 and result["fetched"] == 16
    assert provider_status(db)["provider_status"] == "Not configured"
    assert provider_status(db)["development_data"]


def test_real_sync_updates_without_duplicates_and_preserves_final(db, monkeypatch):
    row = record(Status="InProgress", AwayScore=7, HomeScore=10)

    def handler(request):
        return httpx.Response(
            200, json=[row] if str(request.url).endswith("REG") else []
        )

    mock_provider(monkeypatch, handler)
    first = sync_schedule(db)
    assert first["created"] == 1 and first["updated"] == 0 and first["errors"] == 0
    assert not provider_status(db)["development_data"]
    second = sync_schedule(db)
    assert second["created"] == 0 and second["updated"] == 1
    row.update(Status="Final", AwayScore=24, HomeScore=21)
    SportsDataProvider._cache.clear()
    sync_schedule(db)
    g = db.scalar(select(Game).where(Game.external_id == "sportsdataio-100"))
    assert g.status == "FINAL" and g.away_score == 24 and g.home_score == 21
    row.update(Status="Scheduled", AwayScore=None, HomeScore=None)
    SportsDataProvider._cache.clear()
    sync_schedule(db)
    db.refresh(g)
    assert g.status == "FINAL" and g.away_score == 24
    assert (
        db.scalar(select(func.count(Game.id)).where(Game.provider == "sportsdataio"))
        == 1
    )


def test_outage_retains_real_cache(db, monkeypatch):
    mock_provider(
        monkeypatch,
        lambda req: httpx.Response(
            200, json=[record()] if str(req.url).endswith("REG") else []
        ),
    )
    sync_schedule(db)
    SportsDataProvider._cache.clear()
    mock_provider(monkeypatch, lambda req: httpx.Response(503))
    result = sync_schedule(db)
    assert result["errors"] == 1 and active_provider(db) == "sportsdataio"
    assert not provider_status(db)["development_data"]


def test_api_never_fetches_provider(client, db, monkeypatch):
    def fail():
        raise AssertionError("Browser request attempted provider fetch")

    monkeypatch.setattr("app.services.ingestion.provider", fail)
    assert client.get("/api/games").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_real_api_phase_null_network_and_banner(client, db, monkeypatch):
    mock_provider(
        monkeypatch,
        lambda req: httpx.Response(
            200, json=[record()] if str(req.url).endswith("REG") else []
        ),
    )
    sync_schedule(db)
    games = client.get("/api/games").json()
    assert (
        len(games) == 1
        and games[0]["season_type"] == "REGULAR"
        and games[0]["broadcast_network"] is None
    )
    assert client.get("/api/health").json()["development_data"] is False
    assert len(client.get("/api/search?q=Broncos").json()) == 1
    assert client.get("/api/games/" + str(games[0]["id"])).status_code == 200


@pytest.mark.parametrize(
    "zone",
    ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
)
def test_local_day_near_midnight(client, db, zone):
    from datetime import datetime, timezone

    g = db.get(Game, 1)
    g.kickoff_time = datetime(2026, 9, 14, 1, tzinfo=timezone.utc)
    db.commit()
    result = client.get("/api/games", params={"date": "2026-09-13", "tz": zone}).json()
    assert any(row["id"] == 1 for row in result)


def test_env_aliases_and_blank_season(monkeypatch):
    monkeypatch.setenv("SPORTSDATAIO_API_KEY", "canonical-test")
    monkeypatch.setenv("NFL_DATA_API_KEY", "old-test")
    config = Settings(_env_file=None, NFL_SEASON="")
    assert config.nfl_data_api_key == "canonical-test" and config.nfl_season is None
    assert "canonical-test" not in repr(config)
    monkeypatch.delenv("SPORTSDATAIO_API_KEY")
    assert Settings(_env_file=None).nfl_data_api_key == "old-test"


def test_schema_migration_preserves_data(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "old.db"))
    with engine.begin() as c:
        c.exec_driver_sql(
            "CREATE TABLE games (id INTEGER PRIMARY KEY, broadcast_network VARCHAR NOT NULL)"
        )
        c.exec_driver_sql("INSERT INTO games VALUES (1,'NBC'),(2,'TBA')")
    migrate(engine)
    migrate(engine)
    with engine.connect() as c:
        assert c.exec_driver_sql(
            "SELECT id,broadcast_network,season_type FROM games ORDER BY id"
        ).all() == [(1, "NBC", "REGULAR"), (2, None, "REGULAR")]
    assert next(
        c
        for c in inspect(engine).get_columns("games")
        if c["name"] == "broadcast_network"
    )["nullable"]


@pytest.mark.parametrize(
    "date,expected",
    [
        ("2027-01-01", 2026),
        ("2027-02-28", 2026),
        ("2027-03-01", 2027),
        ("2028-09-01", 2028),
    ],
)
def test_season_rollover(date, expected):
    from datetime import date as Date
    from app.config import season_for_date

    assert season_for_date(Date.fromisoformat(date)) == expected


def test_cold_start_provider_outage_does_not_crash(db, monkeypatch):
    import importlib

    main = importlib.import_module("app.main")
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient

    mock_provider(monkeypatch, lambda req: httpx.Response(401))
    monkeypatch.setattr(main, "engine", db.get_bind())
    monkeypatch.setattr(
        main, "SessionLocal", sessionmaker(db.get_bind(), expire_on_commit=False)
    )
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    from app.database.session import get_db

    main.app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(main.app) as client:
            assert client.get("/api/health").status_code == 200
            assert client.get("/api/health").json()["development_data"]
            assert len(client.get("/api/games").json()) == 16
    finally:
        main.app.dependency_overrides.clear()
