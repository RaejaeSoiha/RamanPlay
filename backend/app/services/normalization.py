"""Provider-independent canonical team, phase, status and timestamp mappings."""

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CANONICAL_TEAMS = set(
    "ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS".split()
)
ALIASES = {
    "LA": "LAR",
    "JAC": "JAX",
    "WSH": "WAS",
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LAR",
}
PHASES = {
    1: "REGULAR",
    2: "PRESEASON",
    3: "POSTSEASON",
    "REG": "REGULAR",
    "PRE": "PRESEASON",
    "POST": "POSTSEASON",
}


def normalize_team(value):
    value = str(value or "").strip().upper()
    value = ALIASES.get(value, value)
    if value not in CANONICAL_TEAMS:
        raise ValueError("Unrecognized NFL team")
    return value


def normalize_status(value, quarter=None):
    key = str(value or "Scheduled").replace(" ", "").replace("_", "").lower()
    status = {
        "scheduled": "SCHEDULED",
        "pregame": "PRE_GAME",
        "inprogress": "LIVE",
        "live": "LIVE",
        "halftime": "HALFTIME",
        "final": "FINAL",
        "f/ot": "FINAL",
        "final/ot": "FINAL",
        "final/2ot": "FINAL",
        "suspended": "POSTPONED",
        "postponed": "POSTPONED",
        "canceled": "CANCELLED",
        "cancelled": "CANCELLED",
    }.get(key)
    if status is None:
        # Never log arbitrary provider strings, which could contain credentials.
        logging.warning("Unknown provider status; using SCHEDULED")
        status = "SCHEDULED"
    return (
        "HALFTIME"
        if status == "LIVE" and str(quarter).upper() in ("HALF", "HALFTIME")
        else status
    )


def normalize_kickoff(row):
    value = row.get("DateTimeUTC") or row.get("Date")
    if not value:
        return None
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc
            if row.get("DateTimeUTC")
            else ZoneInfo("America/New_York")
        )
    return result.astimezone(timezone.utc)


def normalize_network(value):
    if (
        not value
        or not str(value).strip()
        or str(value).strip().upper() in ("TBA", "TBD", "UNKNOWN")
    ):
        return None
    value = str(value).strip()
    names = {
        "cbs": "CBS",
        "fox": "FOX",
        "nbc": "NBC",
        "abc": "ABC",
        "espn": "ESPN",
        "espn+": "ESPN+",
        "amazon": "Prime Video",
        "amazon prime": "Prime Video",
        "amazon prime video": "Prime Video",
        "prime video": "Prime Video",
        "nfln": "NFL Network",
        "nfl network": "NFL Network",
        "peacock": "Peacock",
    }
    return names.get(value.lower(), value)
