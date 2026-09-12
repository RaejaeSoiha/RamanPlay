"""SportsDataIO Scores-by-Season; only normalized GameInput objects leave here."""

import hashlib
import time
import httpx
from app.config import settings
from app.schemas.feed import GameInput
from app.services.providers import GameDataProvider
from app.services.normalization import (
    normalize_team,
    normalize_status,
    normalize_kickoff,
    normalize_network,
    PHASES,
)


class ProviderError(Exception):
    """Safe operator-facing message; never contains raw responses or credentials."""


class SportsDataProvider(GameDataProvider):
    _cache = {}

    def __init__(self, client=None, sleep=time.sleep):
        self.client = client
        self.sleep = sleep

    def get_schedule(self):
        if not settings.nfl_data_api_key.strip():
            raise ProviderError(
                "SportsDataIO is not configured. Set SPORTSDATAIO_API_KEY."
            )
        key = (
            settings.current_season,
            settings.sportsdata_trial,
            hashlib.sha256(settings.nfl_data_api_key.encode()).hexdigest(),
        )
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < max(
            settings.live_refresh_seconds, 60
        ):
            return [g.model_copy(deep=True) for g in cached[1]]
        client = self.client or httpx.Client(
            timeout=settings.provider_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )
        games = []
        try:
            for phase in ("PRE", "REG", "POST"):
                rows = self._request(client, phase)
                try:
                    games.extend(self.normalize(row, phase) for row in rows)
                except (ValueError, KeyError, TypeError, AttributeError):
                    raise ProviderError(
                        "SportsDataIO returned an invalid game record. Stored games were preserved."
                    ) from None
        finally:
            if self.client is None:
                client.close()
        if not games:
            raise ProviderError(
                "SportsDataIO returned an empty season. Check NFL_SEASON and feed access; stored games were preserved."
            )
        if len({g.external_id for g in games}) != len(games):
            raise ProviderError(
                "SportsDataIO returned duplicate game IDs; stored games were preserved."
            )
        self._cache.clear()
        self._cache[key] = (time.monotonic(), games)
        return [g.model_copy(deep=True) for g in games]

    def _request(self, client, phase):
        for attempt in range(settings.provider_retries + 1):
            try:
                response = client.get(
                    f"https://api.sportsdata.io/v3/nfl/scores/json/Scores/{settings.current_season}{phase}",
                    headers={
                        "Ocp-Apim-Subscription-Key": settings.nfl_data_api_key,
                        "User-Agent": settings.user_agent,
                    },
                )
            except httpx.RequestError:
                if attempt < settings.provider_retries:
                    self.sleep(2**attempt)
                    continue
                raise ProviderError(
                    "SportsDataIO could not be reached or timed out. Stored games remain available."
                ) from None
            if response.status_code in (401, 403):
                raise ProviderError(
                    "SportsDataIO rejected the key or NFL feed access. Check SPORTSDATAIO_API_KEY and account permissions."
                )
            if response.status_code == 429:
                # Respect long Retry-After values by ending this sync, not retrying early.
                raise ProviderError(
                    "SportsDataIO rate limit reached. Wait until the next scheduled sync or your account retry window."
                )
            if response.status_code >= 500 and attempt < settings.provider_retries:
                self.sleep(2**attempt)
                continue
            if response.status_code != 200:
                raise ProviderError(
                    f"SportsDataIO request failed (HTTP {response.status_code}). Check season and feed access."
                )
            try:
                rows = response.json()
            except ValueError:
                raise ProviderError(
                    "SportsDataIO returned invalid JSON. Stored games were preserved."
                ) from None
            if not isinstance(rows, list):
                raise ProviderError(
                    "SportsDataIO returned an unexpected response format. Stored games were preserved."
                )
            return rows

    @staticmethod
    def normalize(row, phase="REG"):
        if not isinstance(row, dict):
            raise ValueError("Invalid record")
        away = normalize_team(row.get("AwayTeam"))
        home = normalize_team(row.get("HomeTeam"))
        if away == home:
            raise ValueError("Identical teams")
        kickoff = normalize_kickoff(row)
        season = int(row["Season"])
        season_type = PHASES.get(row.get("SeasonType"), PHASES[phase])
        status = normalize_status(row.get("Status"), row.get("Quarter"))
        stable = row.get("ScoreID") or row.get("GameID")
        if stable is None:
            if kickoff is None:
                raise ValueError("Missing identity and kickoff")
            identity = f"{season}|{season_type}|{row.get('Week') or 0}|{away}|{home}|{kickoff.isoformat()}"
            stable = "composite-" + hashlib.sha256(identity.encode()).hexdigest()
        scored = status in ("LIVE", "HALFTIME", "FINAL", "POSTPONED")
        return GameInput(
            external_id="sportsdataio-" + str(stable),
            season=season,
            season_type=season_type,
            week=row.get("Week") or 0,
            kickoff_time=kickoff,
            away=away,
            home=home,
            status=status,
            venue=str((row.get("StadiumDetails") or {}).get("Name") or ""),
            broadcast_network=normalize_network(row.get("Channel")),
            away_score=row.get("AwayScore") if scored else None,
            home_score=row.get("HomeScore") if scored else None,
            development_data=settings.sportsdata_trial,
        )
