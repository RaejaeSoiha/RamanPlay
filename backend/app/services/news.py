"""Small, cached adapter for public ESPN headline feeds.

The API exposes provider-supplied metadata and links only. It never fetches or
stores article bodies.
"""

import time
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.schemas.news import NewsStory


SUPPORTED_NEWS_SPORTS = {"NFL", "NBA", "UFC"}
NEWS_CACHE_SECONDS = 300


class NewsProviderError(RuntimeError):
    """Raised when a provider has neither a fresh nor stale usable feed."""


class NewsProvider(Protocol):
    def fetch_news(self, sport: str, limit: int) -> list[NewsStory]: ...


class ESPNNewsProvider:
    """Public ESPN headline feed adapter shared by NFL, NBA, and UFC."""

    _cache: dict[str, tuple[float, list[NewsStory]]] = {}
    endpoints = {
        "NFL": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news",
        "NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news",
        "UFC": "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/news",
    }
    sport_names = {"NFL": "FOOTBALL", "NBA": "BASKETBALL", "UFC": "MIXED MARTIAL ARTS"}

    def __init__(self, client: httpx.Client | None = None):
        self.client = client

    def fetch_news(self, sport: str, limit: int) -> list[NewsStory]:
        sport = sport.upper()
        if sport not in SUPPORTED_NEWS_SPORTS:
            raise ValueError("Unknown sport")
        cached = type(self)._cache.get(sport)
        if cached and time.monotonic() - cached[0] < NEWS_CACHE_SECONDS:
            return list(cached[1][:limit])

        client = self.client or httpx.Client(
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )
        try:
            response = client.get(
                self.endpoints[sport],
                params={"limit": max(limit, 12)},
                headers={"User-Agent": settings.user_agent},
            )
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles") if isinstance(data, dict) else None
            if not isinstance(articles, list):
                raise ValueError("unexpected ESPN news response")
            stories = []
            for article in articles:
                try:
                    stories.append(self.normalize_story(article, sport))
                except (ValueError, TypeError, KeyError):
                    # Providers sometimes mix recap links without an HTTPS web
                    # URL into an otherwise valid feed. Never surface that row,
                    # but keep the usable headlines available.
                    continue
            if not stories:
                raise ValueError("ESPN news contained no safe story links")
            stories.sort(key=lambda story: story.published_at, reverse=True)
            type(self)._cache[sport] = (time.monotonic(), stories)
            return list(stories[:limit])
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            # A stale headline list is more useful than an empty Home page while
            # an upstream request is temporarily unavailable.
            if cached:
                return list(cached[1][:limit])
            raise NewsProviderError(f"{sport} news is currently unavailable.") from None
        finally:
            if self.client is None:
                client.close()

    @classmethod
    def normalize_story(cls, article: dict, sport: str) -> NewsStory:
        article_id = str(article["id"])
        source_url = ((article.get("links") or {}).get("web") or {}).get("href")
        parsed = urlparse(str(source_url or ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("ESPN story is missing a safe web URL")
        published_at = cls._timestamp(article.get("published"))
        updated_at = cls._timestamp(article.get("lastModified"), required=False)
        images = article.get("images") or []
        image_url = next(
            (image.get("url") for image in images if isinstance(image, dict) and cls._https_url(image.get("url"))),
            None,
        )
        team_ids: list[str] = []
        fighter_ids: list[str] = []
        event_id = None
        for category in article.get("categories") or []:
            if not isinstance(category, dict):
                continue
            kind = str(category.get("type") or "").lower()
            identifier = category.get("teamId") or category.get("athleteId") or category.get("eventId") or category.get("competitionId")
            if identifier is None:
                continue
            if kind == "team":
                team_ids.append(str(identifier))
            elif kind in {"athlete", "fighter"}:
                fighter_ids.append(str(identifier))
            elif kind in {"event", "competition"}:
                event_id = str(identifier)
        return NewsStory(
            id=f"espn-{sport.lower()}-{article_id}", sport=cls.sport_names[sport], league=sport,
            headline=str(article["headline"]), description=article.get("description") or None,
            source_name="ESPN", source_url=source_url, image_url=image_url,
            published_at=published_at, updated_at=updated_at, related_team_ids=team_ids,
            related_fighter_ids=fighter_ids, related_game_event_id=event_id, provider_id=article_id,
        )

    @staticmethod
    def _https_url(value: object) -> bool:
        parsed = urlparse(str(value or ""))
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password

    @staticmethod
    def _timestamp(value: object, required: bool = True) -> datetime | None:
        if not value:
            if required:
                raise ValueError("ESPN story is missing a publication time")
            return None
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)


def fetch_news(sport: str = "ALL", limit: int = 6, provider: NewsProvider | None = None) -> list[NewsStory]:
    """Return headline metadata, combining sport feeds when requested."""

    sport = sport.upper()
    if sport not in {"ALL", *SUPPORTED_NEWS_SPORTS}:
        raise ValueError("Unknown sport")
    provider = provider or ESPNNewsProvider()
    sports = sorted(SUPPORTED_NEWS_SPORTS) if sport == "ALL" else [sport]
    stories: list[NewsStory] = []
    failures = 0
    per_sport_limit = max(limit, 6) if sport == "ALL" else limit
    for league in sports:
        try:
            stories.extend(provider.fetch_news(league, per_sport_limit))
        except NewsProviderError:
            failures += 1
    if failures == len(sports):
        raise NewsProviderError("Sports news is currently unavailable.")
    return sorted(stories, key=lambda story: story.published_at, reverse=True)[:limit]
