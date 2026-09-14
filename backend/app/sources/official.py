from abc import ABC, abstractmethod
from app.watch.security import validate_url


class WatchSourceProvider(ABC):
    @abstractmethod
    def find_sources(self, game): ...

    def validate_source(self, source):
        return validate_url(source["url"], resolve=False)

    def classify_source(self, source):
        self.validate_source(source)
        access = source["access_type"]
        kind = source["source_type"]
        if access == "FREE" and kind != "FREE_LEGAL":
            raise ValueError("Free video requires explicit FREE_LEGAL evidence")
        if kind == "FREE_LEGAL" and access != "FREE":
            raise ValueError("Inconsistent free source")
        return dict(
            source,
            is_official=True,
            is_free=access == "FREE",
            requires_subscription=access == "SUBSCRIPTION",
            requires_trial=access == "FREE TRIAL",
        )


DEEP_LINK_PATTERNS = {
    "Peacock": "https://www.peacocktv.com/watch/nfl",
    "Peacock Premium": "https://www.peacocktv.com/watch/nfl",
    "NBC Sports App": "https://www.nbcsports.com/nfl/live",
    "Paramount+ Essential": "https://www.paramountplus.com/shows/nfl-on-cbs/live/",
    "CBS Sports App": "https://www.cbssports.com/nfl/live/",
    "FOX Sports App": "https://www.foxsports.com/nfl/live",
    "ESPN+": "https://www.espn.com/watch/espnplus",
    "ESPN App": "https://www.espn.com/watch",
    "ESPN+ (ABC simulcast)": "https://www.espn.com/watch/espnplus",
    "Prime Video": "https://www.primevideo.com/nfl/live",
    "NFL+": "https://www.nfl.com/nflplus/live",
}

FREE_TIER_INFO = {
    "Peacock": "Free tier with ads for select games; Premium required for all games",
    "Peacock Premium": "Full access; free tier has limited games with ads",
    "Paramount+ Essential": "Live CBS games; 7-day free trial available",
    "ESPN+": "Select exclusive games; no free tier (free trial sometimes available)",
    "NFL+": "Live local & primetime on mobile; 7-day free trial",
    "Prime Video": "TNF exclusive; 30-day Prime free trial",
}

NETWORK_STREAMING = {
    "NBC": [
        {
            "provider_name": "Peacock",
            "source_name": "Peacock Premium",
            "url": "https://www.peacocktv.com/sports/nfl",
            "deep_link": "https://www.peacocktv.com/watch/nfl",
            "source_type": "STREAMING",
            "access_type": "SUBSCRIPTION",
            "region": "US",
            "notes": "Select games free with ads; full access requires Peacock Premium",
        },
        {
            "provider_name": "NBC Sports",
            "source_name": "NBC Sports App",
            "url": "https://www.nbcsports.com/nfl",
            "deep_link": "https://www.nbcsports.com/nfl/live",
            "source_type": "STREAMING",
            "access_type": "FREE TRIAL",
            "region": "US",
            "notes": "Requires TV provider login; some games free on NBC.com",
        },
    ],
    "CBS": [
        {
            "provider_name": "Paramount+",
            "source_name": "Paramount+ Essential",
            "url": "https://www.paramountplus.com/shows/nfl-on-cbs/",
            "deep_link": "https://www.paramountplus.com/shows/nfl-on-cbs/live/",
            "source_type": "STREAMING",
            "access_type": "SUBSCRIPTION",
            "region": "US",
            "notes": "Live CBS games with Paramount+ Essential plan; 7-day free trial",
        },
        {
            "provider_name": "CBS Sports",
            "source_name": "CBS Sports App",
            "url": "https://www.cbssports.com/nfl/",
            "deep_link": "https://www.cbssports.com/nfl/live/",
            "source_type": "STREAMING",
            "access_type": "FREE TRIAL",
            "region": "US",
            "notes": "Requires TV provider login for live games",
        },
    ],
    "FOX": [
        {
            "provider_name": "FOX Sports",
            "source_name": "FOX Sports App",
            "url": "https://www.foxsports.com/nfl",
            "deep_link": "https://www.foxsports.com/nfl/live",
            "source_type": "STREAMING",
            "access_type": "FREE TRIAL",
            "region": "US",
            "notes": "Requires TV provider login for live games; some free clips",
        },
    ],
    "ESPN": [
        {
            "provider_name": "ESPN+",
            "source_name": "ESPN+",
            "url": "https://www.espn.com/espnplus/nfl",
            "deep_link": "https://www.espn.com/watch/espnplus",
            "source_type": "STREAMING",
            "access_type": "SUBSCRIPTION",
            "region": "US",
            "notes": "Select games exclusive to ESPN+; requires subscription",
        },
        {
            "provider_name": "ESPN",
            "source_name": "ESPN App",
            "url": "https://www.espn.com/nfl/",
            "deep_link": "https://www.espn.com/watch",
            "source_type": "STREAMING",
            "access_type": "FREE TRIAL",
            "region": "US",
            "notes": "Requires TV provider login for live ESPN games",
        },
    ],
    "ABC": [
        {
            "provider_name": "ESPN+",
            "source_name": "ESPN+ (ABC simulcast)",
            "url": "https://www.espn.com/espnplus/nfl",
            "deep_link": "https://www.espn.com/watch/espnplus",
            "source_type": "STREAMING",
            "access_type": "SUBSCRIPTION",
            "region": "US",
            "notes": "ABC games also stream on ESPN+",
        },
        {
            "provider_name": "ESPN",
            "source_name": "ESPN App",
            "url": "https://www.espn.com/nfl/",
            "deep_link": "https://www.espn.com/watch",
            "source_type": "STREAMING",
            "access_type": "FREE TRIAL",
            "region": "US",
            "notes": "Requires TV provider login for live ABC games",
        },
    ],
    "Prime Video": [
        {
            "provider_name": "Amazon Prime Video",
            "source_name": "Prime Video",
            "url": "https://www.primevideo.com/nfl",
            "deep_link": "https://www.primevideo.com/nfl/live",
            "source_type": "STREAMING",
            "access_type": "SUBSCRIPTION",
            "region": "US",
            "notes": "Thursday Night Football exclusive; 30-day Prime free trial",
        },
    ],
    "NFL Network": [
        {
            "provider_name": "NFL+",
            "source_name": "NFL+",
            "url": "https://www.nfl.com/nflplus/",
            "deep_link": "https://www.nfl.com/nflplus/live",
            "source_type": "STREAMING",
            "access_type": "SUBSCRIPTION",
            "region": "US",
            "notes": "Live local & primetime games on mobile; 7-day free trial",
        },
    ],
}

FREE_OVER_THE_AIR = {
    "NBC": "Check local NBC affiliate website for free live stream",
    "CBS": "Check local CBS affiliate website for free live stream",
    "FOX": "Check local FOX affiliate website for free live stream",
    "ABC": "Check local ABC affiliate website for free live stream",
}


class OfficialSourceProvider(WatchSourceProvider):
    def find_sources(self, game):
        sources = [s.model_dump() for s in game.sources]

        network = (game.broadcast_network or "").strip()
        away_abbr = getattr(game, "away", getattr(game, "away_team", "AWAY"))
        home_abbr = getattr(game, "home", getattr(game, "home_team", "HOME"))
        is_live = getattr(game, "status", "") in ("LIVE", "HALFTIME")

        if network in NETWORK_STREAMING:
            for src in NETWORK_STREAMING[network]:
                source_copy = dict(src)
                source_copy["notes"] = f"{away_abbr} @ {home_abbr}: {src['notes']}"
                source_copy["game_status"] = getattr(game, "status", "SCHEDULED")
                if src.get("deep_link"):
                    source_copy["live_url"] = src["deep_link"]
                if is_live:
                    source_copy["notes"] += " — LIVE NOW"
                sources.append(source_copy)

        if network in FREE_OVER_THE_AIR:
            sources.append(
                dict(
                    provider_name="Local Broadcast",
                    source_name=f"Local {network} Affiliate",
                    url="https://www.nfl.com/ways-to-watch",
                    live_url="https://www.nfl.com/ways-to-watch",
                    source_type="FREE_LEGAL",
                    access_type="FREE",
                    region="US (local market)",
                    notes=f"{FREE_OVER_THE_AIR[network]}. Use NFL.com to find your local station. {('LIVE NOW' if is_live else 'Check at kickoff')}",
                    game_status=getattr(game, "status", "SCHEDULED"),
                )
            )

        if not any(s["url"] == "https://www.nfl.com/ways-to-watch" for s in sources):
            sources.append(
                dict(
                    provider_name="NFL",
                    source_name="Official viewing guide",
                    url="https://www.nfl.com/ways-to-watch",
                    source_type="OFFICIAL_NFL",
                    access_type="OFFICIAL",
                    region="Location dependent",
                    notes="Find current broadcasters for your location. This directory is not a free live stream; provider access and game availability must be confirmed.",
                )
            )

        return [self.classify_source(s) for s in sources]