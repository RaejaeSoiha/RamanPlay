"""Compatibility exports for NBA game services. Source: app.sports.nba.games."""
from app.sports.nba.games import NBAESPNProvider, nba_key, seed_nba_teams, sync_nba_games

__all__ = ["NBAESPNProvider", "nba_key", "seed_nba_teams", "sync_nba_games"]
