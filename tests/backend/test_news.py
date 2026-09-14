from datetime import datetime, timezone

import httpx

from app.api import routes
from app.schemas.news import NewsStory
from app.services.news import ESPNNewsProvider, NewsProviderError, fetch_news


def article(**changes):
    data = {
        "id": "100",
        "headline": "A real headline",
        "description": "A short provider supplied description.",
        "published": "2026-09-14T10:00:00Z",
        "lastModified": "2026-09-14T10:15:00Z",
        "links": {"web": {"href": "https://www.espn.com/nfl/story/_/id/100/test"}},
        "images": [{"url": "https://a.espncdn.com/photo/test.jpg"}],
        "categories": [
            {"type": "team", "teamId": 7},
            {"type": "athlete", "athleteId": 23},
            {"type": "event", "eventId": 91},
        ],
    }
    data.update(changes)
    return data


def test_espn_news_normalizes_summary_metadata_and_caches():
    ESPNNewsProvider._cache.clear()
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"articles": [article()]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = ESPNNewsProvider(client)
        story = provider.fetch_news("NFL", 6)[0]
        assert provider.fetch_news("NFL", 1)[0].id == story.id

    assert story.league == "NFL" and story.source_name == "ESPN"
    assert str(story.source_url).startswith("https://www.espn.com/")
    assert story.related_team_ids == ["7"]
    assert story.related_fighter_ids == ["23"]
    assert story.related_game_event_id == "91"
    assert len(calls) == 1


def test_espn_news_uses_stale_cache_when_provider_fails():
    ESPNNewsProvider._cache.clear()
    story = ESPNNewsProvider.normalize_story(article(), "NBA")
    ESPNNewsProvider._cache["NBA"] = (0, [story])
    transport = httpx.MockTransport(lambda _: httpx.Response(503))
    with httpx.Client(transport=transport) as client:
        assert ESPNNewsProvider(client).fetch_news("NBA", 6) == [story]


def test_espn_news_skips_an_individual_unsafe_article_link():
    ESPNNewsProvider._cache.clear()
    unsafe = article(id="unsafe", links={"web": {"href": "http://www.espn.com/nfl/unsafe"}})
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"articles": [unsafe, article(id="safe")] }))
    with httpx.Client(transport=transport) as client:
        stories = ESPNNewsProvider(client).fetch_news("NFL", 6)
    assert [story.provider_id for story in stories] == ["safe"]


def test_news_combines_available_feeds_without_mixing_scoped_feed():
    class Provider:
        def fetch_news(self, sport, limit):
            if sport == "NBA":
                raise NewsProviderError("unavailable")
            return [
                NewsStory(
                    id=sport,
                    sport=sport,
                    league=sport,
                    headline=sport,
                    source_name="ESPN",
                    source_url="https://www.espn.com/",
                    published_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
                    provider_id=sport,
                )
            ]

    assert [story.league for story in fetch_news("UFC", 6, Provider())] == ["UFC"]
    assert set(story.league for story in fetch_news("ALL", 6, Provider())) == {"NFL", "UFC"}


def test_news_api_filters_validates_and_handles_provider_failure(client, monkeypatch):
    story = NewsStory(
        id="espn-nfl-100", sport="FOOTBALL", league="NFL", headline="NFL story",
        source_name="ESPN", source_url="https://www.espn.com/nfl/", provider_id="100",
        published_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
    )
    seen = []

    def fake_fetch(sport, limit):
        seen.append((sport, limit))
        return [story]

    monkeypatch.setattr(routes, "fetch_news", fake_fetch)
    response = client.get("/api/news?sport=NFL&limit=4")
    assert response.status_code == 200 and response.json()[0]["league"] == "NFL"
    assert seen == [("NFL", 4)]
    assert client.get("/api/news?sport=MLB").status_code == 422

    monkeypatch.setattr(routes, "fetch_news", lambda *_: (_ for _ in ()).throw(NewsProviderError("unavailable")))
    assert client.get("/api/news?sport=UFC").status_code == 503
