#!/usr/bin/env python3
"""
Browser Automation Skeleton for Legal Stream Access

Uses YOUR logged-in browser session to navigate to live games.
Legal: Only automates YOUR browser with YOUR valid subscriptions.

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    # 1. Start Chrome with debug port (run once)
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
    
    # 2. Log into your services (YouTube TV, Fubo, Peacock, etc.) in that Chrome window
    
    # 3. Run this script
    python scripts/playwright_stream.py --game "DEN@KC" --network "NBC"
"""

import asyncio
import argparse
import json
import re
from dataclasses import dataclass
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page


@dataclass
class StreamResult:
    url: str
    title: str
    platform: str
    requires_action: bool = False  # True if user needs to click something
    error: Optional[str] = None


PLATFORM_CONFIG = {
    "youtube_tv": {
        "name": "YouTube TV",
        "base_url": "https://tv.youtube.com",
        "live_path": "/live",
        "guide_path": "/live/guide",
        "selectors": {
            "guide_channel": "[data-testid='guide-channel']",
            "live_button": "[aria-label*='Watch live']",
            "player": "video.html5-video-player",
        },
    },
    "fubo": {
        "name": "Fubo",
        "base_url": "https://www.fubo.tv",
        "live_path": "/live",
        "selectors": {
            "channel_card": ".ChannelCard",
            "watch_button": "button:has-text('Watch')",
            "player": "video",
        },
    },
    "peacock": {
        "name": "Peacock",
        "base_url": "https://www.peacocktv.com",
        "live_path": "/watch/nfl",
        "selectors": {
            "game_tile": "[data-testid='asset-tile']",
            "watch_button": "button:has-text('Watch')",
            "player": "video",
        },
    },
    "paramount_plus": {
        "name": "Paramount+",
        "base_url": "https://www.paramountplus.com",
        "live_path": "/shows/nfl-on-cbs/live",
        "selectors": {
            "live_tile": "[data-testid='live-tile']",
            "watch_button": "button:has-text('Watch Live')",
            "player": "video",
        },
    },
    "espn_plus": {
        "name": "ESPN+",
        "base_url": "https://www.espn.com",
        "live_path": "/watch/espnplus",
        "selectors": {
            "event_card": ".EventCard",
            "watch_button": "a:has-text('Watch')",
            "player": "video",
        },
    },
    "nfl_plus": {
        "name": "NFL+",
        "base_url": "https://www.nfl.com",
        "live_path": "/nflplus/live",
        "selectors": {
            "game_card": ".nfl-c-game-card",
            "watch_button": "a:has-text('Watch Live')",
            "player": "video",
        },
    },
    "prime_video": {
        "name": "Prime Video",
        "base_url": "https://www.primevideo.com",
        "live_path": "/nfl/live",
        "selectors": {
            "live_badge": "[data-automation-id='live-badge']",
            "watch_button": "button:has-text('Watch Live')",
            "player": "video",
        },
    },
}


class StreamFinder:
    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.browser: Optional[Browser] = None
        self.context = None

    async def connect(self):
        """Connect to existing Chrome debug session"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.connect_over_cdp(
            f"http://localhost:{self.debug_port}"
        )
        # Use the first context (your logged-in profile)
        self.context = self.browser.contexts[0]
        print(f"Connected to browser with {len(self.context.pages)} open tabs")

    async def find_live_game(self, platform_key: str, home_team: str, away_team: str) -> StreamResult:
        """Navigate to platform and find the specific game"""
        config = PLATFORM_CONFIG.get(platform_key)
        if not config:
            return StreamResult("", "", "", error=f"Unknown platform: {platform_key}")

        page = await self._get_or_create_page(config["base_url"])
        
        # Navigate to live section
        live_url = config["base_url"] + config.get("live_path", "")
        await page.goto(live_url, wait_until="networkidle")
        await asyncio.sleep(2)

        # Platform-specific logic
        if platform_key == "youtube_tv":
            return await self._find_youtube_tv_game(page, config, home_team, away_team)
        elif platform_key == "peacock":
            return await self._find_peacock_game(page, config, home_team, away_team)
        elif platform_key == "paramount_plus":
            return await self._find_paramount_game(page, config, home_team, away_team)
        else:
            return await self._generic_find(page, config, home_team, away_team)

    async def _get_or_create_page(self, base_url: str) -> Page:
        """Get existing page for domain or create new"""
        for page in self.context.pages:
            if base_url in page.url:
                return page
        page = await self.context.new_page()
        return page

    async def _find_youtube_tv_game(self, page: Page, config: dict, home: str, away: str) -> StreamResult:
        """Find game on YouTube TV guide"""
        try:
            # Go to guide
            await page.goto(config["base_url"] + config["guide_path"], wait_until="networkidle")
            await asyncio.sleep(2)

            # Look for channel with game
            channels = await page.query_selector_all(config["selectors"]["guide_channel"])
            for ch in channels:
                text = await ch.inner_text()
                if self._match_teams(text, home, away):
                    # Click watch live
                    watch_btn = await ch.query_selector(config["selectors"]["live_button"])
                    if watch_btn:
                        await watch_btn.click()
                        await asyncio.sleep(3)
                        # Get player URL
                        player = await page.query_selector(config["selectors"]["player"])
                        if player:
                            src = await player.get_attribute("src")
                            return StreamResult(page.url, f"{away} @ {home}", config["name"])
            
            return StreamResult(page.url, "", config["name"], requires_action=True,
                              error="Game found but couldn't auto-play. Click 'Watch Live' manually.")
        except Exception as e:
            return StreamResult("", "", config["name"], error=str(e))

    async def _find_peacock_game(self, page: Page, config: dict, home: str, away: str) -> StreamResult:
        try:
            await page.goto(config["base_url"] + config["live_path"], wait_until="networkidle")
            await asyncio.sleep(2)

            tiles = await page.query_selector_all(config["selectors"]["game_tile"])
            for tile in tiles:
                text = await tile.inner_text()
                if self._match_teams(text, home, away):
                    watch_btn = await tile.query_selector(config["selectors"]["watch_button"])
                    if watch_btn:
                        await watch_btn.click()
                        await asyncio.sleep(3)
                        return StreamResult(page.url, f"{away} @ {home}", config["name"])
            
            return StreamResult(page.url, "", config["name"], requires_action=True,
                              error="Browse to the NFL section and click the game.")
        except Exception as e:
            return StreamResult("", "", config["name"], error=str(e))

    async def _find_paramount_game(self, page: Page, config: dict, home: str, away: str) -> StreamResult:
        try:
            await page.goto(config["base_url"] + config["live_path"], wait_until="networkidle")
            await asyncio.sleep(2)

            tiles = await page.query_selector_all(config["selectors"]["live_tile"])
            for tile in tiles:
                text = await tile.inner_text()
                if self._match_teams(text, home, away):
                    watch_btn = await tile.query_selector(config["selectors"]["watch_button"])
                    if watch_btn:
                        await watch_btn.click()
                        await asyncio.sleep(3)
                        return StreamResult(page.url, f"{away} @ {home}", config["name"])

            return StreamResult(page.url, "", config["name"], requires_action=True)
        except Exception as e:
            return StreamResult("", "", config["name"], error=str(e))

    async def _generic_find(self, page: Page, config: dict, home: str, away: str) -> StreamResult:
        """Generic fallback: look for team names on page"""
        try:
            content = await page.content()
            if self._match_teams(content, home, away):
                return StreamResult(page.url, f"{away} @ {home}", config["name"], requires_action=True)
            return StreamResult(page.url, "", config["name"], requires_action=True,
                              error="Game not found on current page. Navigate manually.")
        except Exception as e:
            return StreamResult("", "", config["name"], error=str(e))

    def _match_teams(self, text: str, home: str, away: str) -> bool:
        """Fuzzy match team names"""
        text_lower = text.lower()
        # Common abbreviations
        abbrev = {
            "buffalo": "buf", "miami": "mia", "new england": "ne", "nyj": "nyj",
            "baltimore": "bal", "cincinnati": "cin", "cleveland": "cle", "pittsburgh": "pit",
            "houston": "hou", "indianapolis": "ind", "jacksonville": "jax", "tennessee": "ten",
            "denver": "den", "kansas city": "kc", "la chargers": "lac", "las vegas": "lv",
            "dallas": "dal", "ny giants": "nyg", "philadelphia": "phi", "washington": "was",
            "chicago": "chi", "detroit": "det", "green bay": "gb", "minnesota": "min",
            "atlanta": "atl", "carolina": "car", "new orleans": "no", "tampa bay": "tb",
            "arizona": "ari", "la rams": "lar", "san francisco": "sf", "seattle": "sea",
        }
        
        home_kw = home.lower().split()[-1]  # Last word (team name)
        away_kw = away.lower().split()[-1]
        
        return (home_kw in text_lower or abbrev.get(home_kw, "") in text_lower) and \
               (away_kw in text_lower or abbrev.get(away_kw, "") in text_lower)

    async def close(self):
        if self.browser:
            await self.browser.close()


async def main():
    parser = argparse.ArgumentParser(description="Find live NFL stream in your browser")
    parser.add_argument("--game", required=True, help="Game format: AWAY@HOME (e.g., DEN@KC)")
    parser.add_argument("--network", required=True, help="Broadcast network: NBC, CBS, FOX, ESPN, PRIME, NFLN")
    parser.add_argument("--port", type=int, default=9222, help="Chrome debug port")
    args = parser.parse_args()

    # Parse game
    try:
        away, home = args.game.upper().split("@")
    except ValueError:
        print("Error: Game format must be AWAY@HOME (e.g., DEN@KC)")
        return

    # Map network to platform
    network_to_platform = {
        "NBC": ["peacock", "youtube_tv", "fubo"],
        "CBS": ["paramount_plus", "youtube_tv", "fubo"],
        "FOX": ["youtube_tv", "fubo"],
        "ESPN": ["espn_plus", "youtube_tv", "fubo"],
        "ABC": ["espn_plus", "youtube_tv", "fubo"],
        "PRIME": ["prime_video"],
        "NFLN": ["nfl_plus", "youtube_tv", "fubo"],
    }
    
    platforms = network_to_platform.get(args.network.upper(), ["youtube_tv", "fubo"])

    finder = StreamFinder(args.port)
    try:
        await finder.connect()
        
        results = []
        for platform in platforms:
            print(f"\nChecking {PLATFORM_CONFIG[platform]['name']}...")
            result = await finder.find_live_game(platform, home, away)
            results.append(result)
            
            if result.error:
                print(f"  Error: {result.error}")
            elif result.requires_action:
                print(f"  Found at {result.url} — manual click needed")
            else:
                print(f"  ✓ Playing at {result.url}")

        # Summary
        print("\n" + "="*50)
        print("SUMMARY")
        for r in results:
            status = "✓ AUTO" if not r.requires_action and not r.error else "⚠ MANUAL" if not r.error else "✗ ERROR"
            print(f"  {r.platform}: {status}")
            if r.url:
                print(f"    {r.url}")

    finally:
        await finder.close()


if __name__ == "__main__":
    asyncio.run(main())