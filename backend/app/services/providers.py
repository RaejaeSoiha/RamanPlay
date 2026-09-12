"""Schedule providers plus account adapters that only expose official hand-offs."""

from dataclasses import dataclass
import json

from app.config import settings
from app.schemas.feed import GameInput


class GameDataProvider:
    def get_schedule(self):
        raise NotImplementedError

    def get_games(self):
        return self.get_schedule()

    def get_game(self, external_id):
        return next(game for game in self.get_schedule() if game.external_id == external_id)

    def get_live_games(self):
        return [game for game in self.get_schedule() if game.status in ("LIVE", "HALFTIME")]


class DevelopmentProvider(GameDataProvider):
    def get_schedule(self):
        rows = json.loads(open(settings.schedule_file).read())
        return [GameInput.model_validate(row) for row in rows]


def provider():
    if settings.selected_provider == "sportsdataio":
        from app.services.sportsdata import SportsDataProvider
        return SportsDataProvider()
    if settings.selected_provider == "espn":
        from app.services.espn import ESPNProvider
        return ESPNProvider()
    return DevelopmentProvider()


@dataclass(frozen=True)
class ProviderAdapter:
    key: str
    name: str
    official_url: str
    network_terms: tuple[str, ...]
    supports_casting: bool = True
    supports_embedded_playback: bool = False

    def get_watch_url(self, game):
        network = (game.broadcast_network or "").upper()
        return self.official_url if not self.network_terms or any(term in network for term in self.network_terms) else None

    def connect(self):
        # No OAuth client IDs are bundled in the app. Hand off to the provider.
        return {"mode": "official-deep-link", "url": self.official_url}

    def disconnect(self):
        return None

    def get_auth_status(self, account):
        return account.status if account else "NOT_CONNECTED"


ADAPTERS = {
    adapter.key: adapter
    for adapter in (
        ProviderAdapter("espn", "ESPN", "https://www.espn.com/watch/", ("ESPN", "ABC")),
        ProviderAdapter("youtube-tv", "YouTube TV", "https://tv.youtube.com/", ()),
        ProviderAdapter("hulu-live", "Hulu + Live TV", "https://www.hulu.com/live-tv", ()),
        ProviderAdapter("fubo", "Fubo", "https://www.fubo.tv/", ()),
        ProviderAdapter("sling", "Sling", "https://www.sling.com/", ()),
        ProviderAdapter("prime-video", "Prime Video", "https://www.primevideo.com/", ("PRIME", "AMAZON")),
        ProviderAdapter("nfl", "NFL", "https://www.nfl.com/ways-to-watch", ()),
    )
}
