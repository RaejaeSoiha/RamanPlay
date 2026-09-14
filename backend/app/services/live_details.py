"""Small, cached ESPN live-score summary adapter."""

import time

import httpx

from app.config import settings
from app.services.sportsdata import ProviderError


class ESPNLiveDetailsProvider:
    _cache: dict[str, tuple[float, dict]] = {}

    def get(self, game) -> dict:
        if game.league not in {"NFL", "NBA"}:
            return {}
        cache_key = game.external_id
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < max(settings.live_refresh_seconds, 30):
            return dict(cached[1])
        sport, league = ("football", "nfl") if game.league == "NFL" else ("basketball", "nba")
        event_id = game.external_id.removeprefix("espn-nba-").removeprefix("espn-")
        endpoint = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary"
        try:
            with httpx.Client(
                timeout=settings.provider_timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = client.get(endpoint, params={"event": event_id}, headers={"User-Agent": settings.user_agent})
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            raise ProviderError("ESPN live score details are unavailable.") from None
        result = self.normalize(data)
        self._cache[cache_key] = (time.monotonic(), result)
        return dict(result)

    @staticmethod
    def normalize(data: dict) -> dict:
        header = data.get("header") or {}
        competition = next(iter(header.get("competitions") or []), {})
        status = competition.get("status") or {}
        status_type = status.get("type") or {}
        situation = data.get("situation") or {}
        competitors = competition.get("competitors") or []
        team_names = {str(item.get("id")): (item.get("team") or {}).get("abbreviation") for item in competitors}
        possession_id = str(situation.get("possession") or "")
        last_play = situation.get("lastPlay") or {}
        if not last_play and data.get("plays"):
            last_play = data["plays"][-1] or {}
        return {
            "status_detail": str(status_type.get("detail") or status.get("displayClock") or ""),
            "period": int(status.get("period") or 0) or None,
            "clock": str(status.get("displayClock") or ""),
            "possession": team_names.get(possession_id) or "",
            "down_distance": str(situation.get("downDistanceText") or ""),
            "last_play": str(last_play.get("text") or ""),
        }
