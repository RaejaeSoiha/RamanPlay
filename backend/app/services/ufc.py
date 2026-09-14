"""Compatibility exports for UFC event services. Source: app.sports.ufc.events."""
from app.sports.ufc.events import UFCESPNProvider, event_with_card, fighter_key, sync_ufc_events

__all__ = ["UFCESPNProvider", "event_with_card", "fighter_key", "sync_ufc_events"]
