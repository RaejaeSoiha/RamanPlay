"""Compatibility exports for NBA player services. Source: app.sports.nba.players."""
from app.sports.nba.players import NBAESPNPlayerProvider, sync_nba_players, sync_player_details

__all__ = ["NBAESPNPlayerProvider", "sync_nba_players", "sync_player_details"]
