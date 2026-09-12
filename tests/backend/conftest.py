import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.database.session import Base, get_db
from app.services.ingestion import seed_teams, update_schedule
from app.config import settings
from app.main import app, buckets


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        seed_teams(session)
        update_schedule(session)
        yield session
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(settings, "admin_secret", "test-maintenance-key")
    app.dependency_overrides[get_db] = lambda: db
    buckets.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolate_provider(monkeypatch):
    from app.services.espn import ESPNProvider
    from app.services.sportsdata import SportsDataProvider

    monkeypatch.setattr(settings, "nfl_data_api_key", "")
    monkeypatch.setattr(settings, "data_provider", "development")
    monkeypatch.setattr(settings, "nfl_season", 2026)
    monkeypatch.setattr(settings, "sportsdata_trial", False)
    SportsDataProvider._cache.clear()
    ESPNProvider._cache.clear()
    ESPNProvider._standings_cache.clear()
    yield
    SportsDataProvider._cache.clear()
    ESPNProvider._cache.clear()
    ESPNProvider._standings_cache.clear()
