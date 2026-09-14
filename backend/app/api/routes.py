import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.session import get_db
from app.models.entities import (
    AppUser,
    CombatBout,
    CombatEvent,
    Fighter,
    Favorite,
    Game,
    LinkCheck,
    MaintenanceState,
    PersonalLink,
    HouseholdInvite,
    HouseholdPreference,
    ProviderAccount,
    Team,
    Player,
    UserSubscription,
    WatchTogetherParticipant,
    WatchTogetherRoom,
    WatchSource,
    now,
)
from app.schemas.links import MyLinkInput, MyLinkUpdate
from app.schemas.household import InviteInput, JoinHouseholdInput, WatchRoomInput
from app.schemas.preferences import HouseholdPreferencesInput
from app.services.accounts import current_user, require_csrf, session_payload
from app.watch.links import (
    check_personal_link,
    serialize_personal_link,
    serialize_personal_links,
)
from app.watch.security import validate_public_url, validate_url
from app.services.sync import active_provider, provider_status, sync_schedule
from app.services.espn import ESPNProvider
from app.sports.nba.games import NBAESPNProvider
from app.sports.ufc.events import event_with_card
from app.sports.nba.players import NBAESPNPlayerProvider, sync_nba_players, sync_player_details
from app.sports.nfl.players import NFLPlayerProvider
from app.services.live_details import ESPNLiveDetailsProvider
from app.services.providers import ADAPTERS

router = APIRouter(prefix="/api")


def code_hash(code: str):
    return hashlib.sha256(code.encode()).hexdigest()


def team_dict(t):
    result = {
        k: getattr(t, k)
        for k in (
            "id",
            "abbreviation",
            "provider_id",
            "sport",
            "league",
            "name",
            "city",
            "conference",
            "division",
            "logo_url",
            "official_url",
        )
    }
    result["internal_abbreviation"] = result["abbreviation"]
    result["abbreviation"] = t.provider_abbreviation or t.abbreviation
    return result


def source_dict(s, subs_map=None):
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    if subs_map:
        key = (s.provider_name, s.source_name)
        sub = subs_map.get(key)
        if sub:
            d["user_has_subscription"] = sub.has_subscription
            d["user_has_free_trial"] = sub.has_free_trial
    return d


def game_dict(g, subs_map=None, user=None):
    result = {c.name: getattr(g, c.name) for c in g.__table__.columns}
    result["kickoff_time"] = (
        None
        if g.kickoff_time is None
        else g.kickoff_time.replace(tzinfo=timezone.utc).isoformat()
        if g.kickoff_time is None or g.kickoff_time.tzinfo is None
        else g.kickoff_time.isoformat()
    )
    result.update(
        away_team=team_dict(g.away_team),
        home_team=team_dict(g.home_team),
        sources=sorted(
            [source_dict(s, subs_map) for s in g.sources],
            key=lambda s: (
                0 if s.get("user_has_subscription") else 1,
                {"FREE": 0, "OFFICIAL": 1, "FREE TRIAL": 2, "SUBSCRIPTION": 3, "AUDIO ONLY": 4}.get(s["access_type"], 5),
            ),
        ),
        my_links=serialize_personal_links(
            [
                link
                for link in g.my_links
                if user is None
                or link.owner_id == user.id
                or link.shared_with_household
            ]
        ),
    )
    return result


def fighter_dict(fighter):
    return {
        "id": fighter.id,
        "external_id": fighter.external_id,
        "internal_key": fighter.internal_key,
        "league": fighter.league,
        "full_name": fighter.full_name,
        "nickname": fighter.nickname,
        "country": fighter.country,
        "record": fighter.record,
        "weight_class": fighter.weight_class,
        "headshot_url": fighter.headshot_url,
        "ranking": fighter.ranking,
        "is_champion": fighter.is_champion,
    }


def player_dict(player):
    return {
        "id": player.id,
        "external_id": player.external_id,
        "provider_id": player.provider_id,
        "league": player.league,
        "team_id": player.team_id,
        "full_name": player.full_name,
        "first_name": player.first_name,
        "last_name": player.last_name,
        "display_name": player.display_name,
        "short_name": player.short_name,
        "jersey": player.jersey,
        "position": player.position,
        "position_name": player.position_name,
        "position_abbreviation": player.position_abbreviation,
        "height": player.height,
        "weight": player.weight,
        "age": player.age,
        "date_of_birth": player.date_of_birth,
        "birth_place": player.birth_place,
        "college": player.college,
        "headshot_url": player.headshot_url,
        "status": player.status,
        "experience_years": player.experience_years,
        "draft_year": player.draft_year,
        "draft_round": player.draft_round,
        "draft_pick": player.draft_pick,
        "career_stats": player.career_stats,
        "game_log": player.game_log,
        "splits": player.splits,
        "awards": player.awards,
    }


def player_summary_dict(player):
    """Lightweight player dict for roster listings."""
    return {
        "id": player.id,
        "external_id": player.external_id,
        "provider_id": player.provider_id,
        "team_id": player.team_id,
        "full_name": player.full_name,
        "display_name": player.display_name,
        "jersey": player.jersey,
        "position": player.position,
        "position_name": player.position_name,
        "height": player.height,
        "weight": player.weight,
        "age": player.age,
        "headshot_url": player.headshot_url,
        "status": player.status,
        "experience_years": player.experience_years,
        "college": player.college,
    }


def bout_dict(bout):
    return {
        "id": bout.id,
        "external_id": bout.external_id,
        "fighter_a": fighter_dict(bout.fighter_a),
        "fighter_b": fighter_dict(bout.fighter_b),
        "weight_class": bout.weight_class,
        "bout_order": bout.bout_order,
        "card_section": bout.card_section,
        "scheduled_rounds": bout.scheduled_rounds,
        "status": bout.status,
        "winner_id": bout.winner_id,
        "result_method": bout.result_method,
        "result_round": bout.result_round,
        "finish_time": bout.finish_time,
        "is_title_fight": bout.is_title_fight,
        "is_interim_title": bout.is_interim_title,
    }


def combat_event_dict(event, user=None, include_card=True):
    result = {column.name: getattr(event, column.name) for column in event.__table__.columns}
    for key in ("event_time", "main_card_time", "preliminary_card_time"):
        value = result[key]
        result[key] = value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None
    links = [link for link in event.my_links if user is None or link.owner_id == user.id or link.shared_with_household]
    result["my_links"] = serialize_personal_links(links)
    result["official_sources"] = [
        {
            "provider_name": "UFC",
            "source_name": "Official UFC Watch",
            "url": "https://www.ufc.com/watch",
            "access_type": "OFFICIAL",
        }
    ]
    bouts = [bout_dict(bout) for bout in event.bouts] if include_card else []
    result["bouts"] = bouts
    result["main_event"] = next((bout for bout in reversed(bouts) if bout["card_section"] == "MAIN_EVENT"), bouts[-1] if bouts else None)
    return result


def ufc_event_rows(db, q="", user=None):
    rows = db.scalars(
        select(CombatEvent)
        .where(CombatEvent.league == "UFC")
        .options(
            selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_a),
            selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_b),
            selectinload(CombatEvent.my_links),
        )
        .order_by(CombatEvent.event_time)
    ).all()
    words = q.lower().split()
    if not words:
        return [combat_event_dict(event, user) for event in rows]
    result = []
    for event in rows:
        text = " ".join(
            [event.name, event.league, event.broadcast_network or ""]
            + [bout.weight_class + " " + bout.fighter_a.full_name + " " + bout.fighter_b.full_name for bout in event.bouts]
        ).lower()
        if all(word in text for word in words):
            result.append(combat_event_dict(event, user))
    return result


@router.get("/ufc/events")
def ufc_events(q: str = Query("", max_length=150), user: AppUser = Depends(current_user), db=Depends(get_db)):
    return ufc_event_rows(db, q, user)


@router.get("/ufc/events/{id}")
def ufc_event(id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    event = event_with_card(db, id)
    if not event:
        raise HTTPException(404, "UFC event not found")
    return combat_event_dict(event, user)


@router.get("/ufc/fighters")
def ufc_fighters(q: str = Query("", max_length=150), db=Depends(get_db)):
    query = select(Fighter).where(Fighter.league == "UFC").order_by(Fighter.full_name)
    if q.strip():
        phrase = "%" + q.strip().lower() + "%"
        query = query.where(func.lower(Fighter.full_name).like(phrase))
    return [fighter_dict(fighter) for fighter in db.scalars(query)]


@router.get("/ufc/fighters/{id}")
def ufc_fighter(id: int, db=Depends(get_db)):
    fighter = db.get(Fighter, id)
    if not fighter or fighter.league != "UFC":
        raise HTTPException(404, "UFC fighter not found")
    bouts = db.scalars(
        select(CombatBout)
        .where((CombatBout.fighter_a_id == id) | (CombatBout.fighter_b_id == id))
        .options(selectinload(CombatBout.fighter_a), selectinload(CombatBout.fighter_b))
        .order_by(CombatBout.id.desc())
    ).all()
    return {**fighter_dict(fighter), "bouts": [bout_dict(bout) for bout in bouts]}


@router.get("/nba/teams/{team_id}/players")
def nba_team_players(team_id: str, db=Depends(get_db)):
    team = db.scalar(select(Team).where(Team.provider_id == team_id, Team.league == "NBA"))
    if not team:
        raise HTTPException(404, "NBA team not found")
    players = db.scalars(
        select(Player).where(Player.team_id == team.id, Player.league == "NBA").order_by(Player.jersey)
    ).all()
    return [player_summary_dict(p) for p in players]


@router.get("/nba/players")
def nba_players(
    q: str = Query("", max_length=150),
    team: str = Query("", max_length=32),
    db=Depends(get_db),
):
    query = select(Player).where(Player.league == "NBA")
    if team.strip():
        team_row = db.scalar(
            select(Team).where(Team.provider_id == team.strip(), Team.league == "NBA")
        )
        if not team_row:
            return []
        query = query.where(Player.team_id == team_row.id)
    if q.strip():
        phrase = "%" + q.strip().lower() + "%"
        query = query.where(func.lower(Player.full_name).like(phrase))
    return [player_summary_dict(p) for p in db.scalars(query.order_by(Player.full_name))]


@router.get("/nba/players/{id}")
def nba_player(id: int, db=Depends(get_db)):
    player = db.get(Player, id)
    if not player or player.league != "NBA":
        raise HTTPException(404, "NBA player not found")
    return player_dict(player)


@router.get("/nfl/players/{team}/{player_id}")
def nfl_player(team: str, player_id: str, db=Depends(get_db)):
    team = team.upper()
    teams = list(db.scalars(select(Team.abbreviation).where(Team.league == "NFL").order_by(Team.abbreviation)))
    if team not in teams:
        raise HTTPException(404, "NFL team not found")
    try:
        players = NFLPlayerProvider().get_players(teams)
    except Exception as exc:
        from app.services.sportsdata import ProviderError
        if isinstance(exc, ProviderError):
            raise HTTPException(503, "NFL player details are unavailable from ESPN.") from None
        raise
    player = next((row for row in players if row["id"] == player_id and row["team"] == team), None)
    if not player:
        raise HTTPException(404, "NFL player not found")
    return player


@router.get("/nfl/players")
def nfl_players(q: str = Query("", max_length=150), db=Depends(get_db)):
    teams = list(db.scalars(select(Team.abbreviation).where(Team.league == "NFL").order_by(Team.abbreviation)))
    try:
        players = NFLPlayerProvider().get_players(teams)
    except Exception as exc:
        from app.services.sportsdata import ProviderError
        if isinstance(exc, ProviderError):
            raise HTTPException(503, "NFL players are unavailable from ESPN.") from None
        raise
    words = q.lower().split()
    return [
        player for player in players
        if not words or all(word in " ".join((player["full_name"], player["team"], player["position"], player["position_name"])).lower() for word in words)
    ]


@router.post("/nba/players/{id}/refresh")
def refresh_nba_player(id: int, db=Depends(get_db)):
    player = db.get(Player, id)
    if not player or player.league != "NBA":
        raise HTTPException(404, "NBA player not found")
    updated = sync_player_details(db, player.provider_id)
    if not updated:
        raise HTTPException(503, "Could not refresh player data")
    return player_dict(updated)


@router.get("/games")
@router.get("/search")
def games(
    q: str = Query("", max_length=150),
    period: str = "all",
    tz: str = "UTC",
    team: str = "",
    conference: str = "",
    division: str = "",
    network: str = "",
    access: str = "",
    status: str = "",
    date: str = "",
    league: str = "ALL",
    user: AppUser = Depends(current_user),
    db=Depends(get_db),
):
    try:
        zone = ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(422, "Unknown timezone")
    today = datetime.now(zone).date()
    
    # Fetch user subscriptions
    subs = db.scalars(select(UserSubscription)).all()
    subs_map = {(s.provider_name, s.source_name): s for s in subs}
    
    league = league.upper()
    if league not in {"ALL", "NFL", "NBA", "UFC"}:
        raise HTTPException(422, "Unknown league")
    if league == "UFC":
        return ufc_event_rows(db, q, user)
    nfl_scope = and_(
        Game.league == "NFL",
        Game.provider == active_provider(db),
        Game.season == settings.current_season,
    )
    scope = (
        nfl_scope
        if league == "NFL"
        else Game.league == "NBA"
        if league == "NBA"
        else or_(nfl_scope, Game.league == "NBA")
    )
    rows = db.scalars(
        select(Game)
        .where(scope)
        .options(
            selectinload(Game.away_team),
            selectinload(Game.home_team),
            selectinload(Game.sources),
            selectinload(Game.my_links),
        )
        .order_by(Game.kickoff_time)
    ).all()
    words = q.lower().split()
    if "sunday" in words:
        period = "sunday"
    if "tonight" in words:
        period = "today"
    if "free" in words:
        access = "FREE"
    words = [
        w for w in words if w not in ("sunday", "tonight", "free", "games", "game")
    ]
    result = []
    for g in rows:
        d = (
            None
            if g.kickoff_time is None
            else g.kickoff_time.replace(tzinfo=timezone.utc).astimezone(zone).date()
            if g.kickoff_time is None or g.kickoff_time.tzinfo is None
            else g.kickoff_time.astimezone(zone).date()
        )
        if period == "today" and d != today:
            continue
        if period == "tomorrow" and d != today + timedelta(days=1):
            continue
        monday = today - timedelta(days=today.weekday())
        if d is None and (period != "all" or date):
            continue
        if period == "week" and not monday <= d < monday + timedelta(days=7):
            continue
        if period == "weekend" and not monday + timedelta(
            days=5
        ) <= d < monday + timedelta(days=7):
            continue
        if period == "sunday" and (d.weekday() != 6 or d < today):
            continue
        if date and d.isoformat() != date:
            continue
        ts = (g.away_team, g.home_team)
        if team and not any(team in (t.abbreviation, t.provider_abbreviation, str(t.id)) for t in ts):
            continue
        if conference and not any(t.conference == conference for t in ts):
            continue
        if division and not any(t.division == division for t in ts):
            continue
        if network and network != g.broadcast_network:
            continue
        if status == "UPCOMING" and g.status not in ("SCHEDULED", "PRE_GAME"):
            continue
        if status == "LIVE" and g.status not in ("LIVE", "HALFTIME"):
            continue
        if status and status not in ("LIVE", "UPCOMING") and g.status != status:
            continue
        if access == "OFFICIAL" and not any(s.is_official for s in g.sources):
            continue
        if (
            access
            and access != "OFFICIAL"
            and not any(
                s.access_type == access
                and s.status not in ("NOT_FOUND", "BLOCKED", "ERROR")
                for s in g.sources
            )
        ):
            continue
        hay = " ".join(
            [t.city + " " + t.name + " " + (t.provider_abbreviation or t.abbreviation) + " " + t.league for t in ts]
            + [g.broadcast_network or ""]
            + [s.provider_name + " " + s.source_name for s in g.sources]
        ).lower()
        if not all(w in hay for w in words):
            continue
        result.append(game_dict(g, subs_map, user))
    return result


@router.get("/games/today")
def today(tz: str = "UTC", db=Depends(get_db)):
    return games(q="", period="today", tz=tz, db=db)


@router.get("/games/live")
def live(db=Depends(get_db)):
    return games(q="", status="LIVE", db=db)


@router.get("/games/upcoming")
def upcoming(db=Depends(get_db)):
    return games(q="", status="UPCOMING", db=db)


@router.get("/games/{id}/live-details")
def live_game_details(id: int, db=Depends(get_db)):
    game = db.get(Game, id)
    if not game:
        raise HTTPException(404, "Game not found")
    try:
        return ESPNLiveDetailsProvider().get(game)
    except Exception as exc:
        from app.services.sportsdata import ProviderError
        if isinstance(exc, ProviderError):
            raise HTTPException(503, "Live score details are currently unavailable.") from None
        raise


@router.get("/games/{id}")
def game(id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    g = db.get(Game, id)
    if not g:
        raise HTTPException(404, "Game not found")
    subs = db.scalars(select(UserSubscription)).all()
    subs_map = {(s.provider_name, s.source_name): s for s in subs}
    return game_dict(g, subs_map, user)


@router.get("/teams")
def teams(league: str = "ALL", db=Depends(get_db)):
    league = league.upper()
    if league not in {"ALL", "NFL", "NBA"}:
        raise HTTPException(422, "Unknown league")
    query = select(Team).order_by(Team.league, Team.city)
    if league != "ALL":
        query = query.where(Team.league == league)
    return [team_dict(t) for t in db.scalars(query)]


def standings_dict(db, conference=None, division=None):
    try:
        standings = ESPNProvider().get_standings()
    except Exception as exc:
        from app.services.sportsdata import ProviderError

        if isinstance(exc, ProviderError):
            raise HTTPException(503, "Live standings are currently unavailable.") from None
        raise
    teams_by_abbreviation = {
        team.abbreviation: team
        for team in db.scalars(select(Team).where(Team.league == "NFL"))
    }
    divisions = {"AFC": ["East", "North", "South", "West"], "NFC": ["East", "North", "South", "West"]}
    grouped = {name: {division: [] for division in names} for name, names in divisions.items()}
    for standing in standings:
        team = teams_by_abbreviation.get(standing["abbreviation"])
        if not team:
            raise HTTPException(503, "Live standings are currently unavailable.")
        grouped[team.conference][team.division].append({**team_dict(team), **standing})
    if conference:
        conference = conference.upper()
        if conference not in grouped:
            raise HTTPException(404, "Conference not found")
        grouped = {conference: grouped[conference]}
    if division:
        division = division.title()
        if not all(division in divisions[name] for name in grouped):
            raise HTTPException(404, "Division not found")
        grouped = {name: {division: grouped[name][division]} for name in grouped}

    def standing_order(team):
        return (
            -float(team["win_percentage"]),
            -team["wins"],
            team["losses"],
            -team["ties"],
            -(team["points_for"] - team["points_against"]),
            team["abbreviation"],
        )

    conferences = []
    for name, division_map in grouped.items():
        division_rows = []
        for division_name, rows in division_map.items():
            rows = sorted(rows, key=standing_order)
            for index, row in enumerate(rows):
                row["division_leader"] = index == 0
            division_rows.append({"name": division_name, "teams": rows})
        conferences.append({"name": name, "divisions": division_rows})
    return {"league": "NFL", "season": settings.current_season, "conferences": conferences}


def nba_standings_dict(db, conference=None):
    try:
        standings = NBAESPNProvider().get_standings()
    except Exception as exc:
        from app.services.sportsdata import ProviderError

        if isinstance(exc, ProviderError):
            raise HTTPException(503, "Live NBA standings are currently unavailable.") from None
        raise
    teams_by_abbreviation = {
        team.abbreviation: team
        for team in db.scalars(select(Team).where(Team.league == "NBA"))
    }
    grouped = {"Eastern": [], "Western": []}
    for standing in standings:
        team = teams_by_abbreviation.get(standing["abbreviation"])
        if not team:
            raise HTTPException(503, "Live NBA standings are currently unavailable.")
        grouped[standing.get("conference") or team.conference].append({**team_dict(team), **standing})
    if conference:
        name = conference.title()
        if name not in grouped:
            raise HTTPException(404, "Conference not found")
        grouped = {name: grouped[name]}

    conferences = []
    for name, rows in grouped.items():
        rows.sort(
            key=lambda row: (
                row["playoff_rank"] if row["playoff_rank"] is not None else 99,
                -float(row["win_percentage"]),
                -row["wins"],
                row["losses"],
                row["abbreviation"],
            )
        )
        for index, row in enumerate(rows):
            row["conference_leader"] = index == 0
        conferences.append({"name": name, "divisions": [{"name": name, "teams": rows}]})
    return {"league": "NBA", "season": settings.current_season, "conferences": conferences}


@router.get("/standings")
def standings(league: str = "NFL", db=Depends(get_db)):
    if league.upper() == "NBA":
        return nba_standings_dict(db)
    if league.upper() != "NFL":
        raise HTTPException(422, "Unknown league")
    return standings_dict(db)


@router.get("/standings/{conference}")
def conference_standings(conference: str, db=Depends(get_db)):
    if conference.lower() == "nba":
        return nba_standings_dict(db)
    return standings_dict(db, conference=conference)


@router.get("/standings/{conference}/{division}")
def division_standings(conference: str, division: str, db=Depends(get_db)):
    return standings_dict(db, conference=conference, division=division)


@router.get("/teams/{id}")
def team(id: int, db=Depends(get_db)):
    t = db.get(Team, id)
    if not t:
        raise HTTPException(404, "Team not found")
    return team_dict(t)


@router.get("/sources/{game_id}")
def sources(game_id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    return game(game_id, user, db)["sources"]


def personal_link_or_404(id: int, db, user: AppUser):
    link = db.get(PersonalLink, id)
    if not link or link.owner_id != user.id:
        raise HTTPException(404, "My Link not found")
    return link


def validate_personal_url(url: str):
    try:
        return validate_public_url(url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/account/me")
def account_me(user: AppUser = Depends(current_user), db=Depends(get_db)):
    return session_payload(user, db)


@router.get("/account/preferences")
def household_preferences(user: AppUser = Depends(current_user), db=Depends(get_db)):
    saved = db.scalar(select(HouseholdPreference).where(HouseholdPreference.household_id == user.household_id))
    return {
        "favorites": list(saved.favorites) if saved else [],
        "preferences": dict(saved.preferences) if saved else {},
        "updated_at": saved.updated_at if saved else None,
    }


@router.put("/account/preferences")
def update_household_preferences(
    body: HouseholdPreferencesInput,
    user: AppUser = Depends(require_csrf),
    db=Depends(get_db),
):
    saved = db.scalar(select(HouseholdPreference).where(HouseholdPreference.household_id == user.household_id))
    if not saved:
        saved = HouseholdPreference(household_id=user.household_id)
        db.add(saved)
    saved.favorites = sorted(set(body.favorites))
    saved.preferences = dict(body.preferences)
    db.commit()
    db.refresh(saved)
    return {"favorites": saved.favorites, "preferences": saved.preferences, "updated_at": saved.updated_at}


@router.get("/provider-accounts")
def provider_accounts(user: AppUser = Depends(current_user), db=Depends(get_db)):
    accounts = {account.provider: account for account in db.scalars(select(ProviderAccount).where(ProviderAccount.user_id == user.id))}
    return [
        {
            "provider": adapter.key,
            "name": adapter.name,
            "status": adapter.get_auth_status(accounts.get(adapter.key)),
            "official_url": adapter.official_url,
            "supports_casting": adapter.supports_casting,
            "supports_embedded_playback": adapter.supports_embedded_playback,
        }
        for adapter in ADAPTERS.values()
    ]


@router.post("/provider-accounts/{provider}/connect")
def connect_provider(provider: str, user: AppUser = Depends(require_csrf)):
    adapter = ADAPTERS.get(provider)
    if not adapter:
        raise HTTPException(404, "Provider not found")
    return adapter.connect()


@router.delete("/provider-accounts/{provider}", status_code=204)
def disconnect_provider(provider: str, user: AppUser = Depends(require_csrf), db=Depends(get_db)):
    account = db.scalar(select(ProviderAccount).where(ProviderAccount.user_id == user.id, ProviderAccount.provider == provider))
    if account:
        db.delete(account)
        db.commit()


@router.get("/provider-options/{game_id}")
def provider_options(game_id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    connected = {account.provider for account in db.scalars(select(ProviderAccount).where(ProviderAccount.user_id == user.id, ProviderAccount.status == "CONNECTED"))}
    return [
        {"provider": adapter.key, "name": adapter.name, "url": adapter.get_watch_url(game), "supports_casting": adapter.supports_casting}
        for adapter in ADAPTERS.values()
        if adapter.key in connected and adapter.get_watch_url(game)
    ]


@router.get("/household")
def household(user: AppUser = Depends(current_user), db=Depends(get_db)):
    members = list(db.scalars(select(AppUser).where(AppUser.household_id == user.household_id)))
    return {
        "name": session_payload(user, db)["household_name"],
        "role": user.role,
        "members": [{"id": member.id, "display_name": member.display_name, "role": member.role} for member in members],
    }


@router.post("/household/invites")
def create_household_invite(body: InviteInput, user: AppUser = Depends(require_csrf), db=Depends(get_db)):
    if user.role != "OWNER":
        raise HTTPException(403, "Only the household owner can invite members")
    code = secrets.token_urlsafe(18)
    invite = HouseholdInvite(
        household_id=user.household_id,
        code_hash=code_hash(code),
        expires_at=now() + timedelta(hours=body.expires_hours),
    )
    db.add(invite)
    db.commit()
    return {"code": code, "expires_at": invite.expires_at}


@router.post("/household/join")
def join_household(body: JoinHouseholdInput, user: AppUser = Depends(require_csrf), db=Depends(get_db)):
    invite = db.scalar(select(HouseholdInvite).where(HouseholdInvite.code_hash == code_hash(body.code)))
    if not invite or invite.used_at or invite.expires_at < now():
        raise HTTPException(404, "Invite is invalid or expired")
    user.display_name = body.display_name.strip()
    user.role = "FAMILY_MEMBER"
    user.household_id = invite.household_id
    invite.used_at = now()
    db.commit()
    return session_payload(user, db)


@router.post("/watch-together")
def create_watch_room(body: WatchRoomInput, user: AppUser = Depends(require_csrf), db=Depends(get_db)):
    if user.role != "OWNER" or not db.get(Game, body.game_id):
        raise HTTPException(403, "Only the household owner can create a room for a valid game")
    code = secrets.token_urlsafe(12)
    room = WatchTogetherRoom(
        game_id=body.game_id,
        household_id=user.household_id,
        owner_id=user.id,
        selected_link_id=body.selected_link_id,
        code_hash=code_hash(code),
        expires_at=now() + timedelta(hours=8),
    )
    db.add(room)
    db.flush()
    db.add(WatchTogetherParticipant(room_id=room.id, user_id=user.id))
    db.commit()
    return {"id": room.id, "code": code, "expires_at": room.expires_at}


@router.post("/watch-together/{code}/join")
def join_watch_room(code: str, user: AppUser = Depends(require_csrf), db=Depends(get_db)):
    room = db.scalar(select(WatchTogetherRoom).where(WatchTogetherRoom.code_hash == code_hash(code)))
    if not room or room.expires_at < now() or room.household_id != user.household_id:
        raise HTTPException(404, "Room is invalid, expired, or not available to this household")
    if not db.scalar(select(WatchTogetherParticipant).where(WatchTogetherParticipant.room_id == room.id, WatchTogetherParticipant.user_id == user.id)):
        db.add(WatchTogetherParticipant(room_id=room.id, user_id=user.id))
        db.commit()
    return {"id": room.id, "game_id": room.game_id, "selected_link_id": room.selected_link_id}


@router.get("/my-links/{game_id}")
def my_links(game_id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    if not db.get(Game, game_id):
        raise HTTPException(404, "Game not found")
    links = db.scalars(
        select(PersonalLink)
        .where(
            PersonalLink.game_id == game_id,
            (PersonalLink.owner_id == user.id) | PersonalLink.shared_with_household,
        )
        .order_by(PersonalLink.priority, PersonalLink.id)
    )
    return serialize_personal_links(list(links))


@router.get("/ufc/events/{event_id}/my-links")
def ufc_my_links(event_id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    if not db.get(CombatEvent, event_id):
        raise HTTPException(404, "UFC event not found")
    links = db.scalars(
        select(PersonalLink)
        .where(
            PersonalLink.event_id == event_id,
            (PersonalLink.owner_id == user.id) | PersonalLink.shared_with_household,
        )
        .order_by(PersonalLink.priority, PersonalLink.id)
    )
    return serialize_personal_links(list(links))


@router.post("/my-links/{game_id}", status_code=201)
async def create_my_link(game_id: int, body: MyLinkInput, user: AppUser = Depends(current_user), db=Depends(get_db)):
    if not db.get(Game, game_id):
        raise HTTPException(404, "Game not found")
    values = body.model_dump()
    playback_preference = values.pop("playback_preference")
    link = PersonalLink(game_id=game_id, owner_id=user.id, playback_preference=playback_preference, **values)
    link.url = validate_personal_url(link.url)
    db.add(link)
    db.commit()
    db.refresh(link)
    await check_personal_link(db, link, playback_preference)
    return serialize_personal_link(link)


@router.post("/ufc/events/{event_id}/my-links", status_code=201)
async def create_ufc_my_link(event_id: int, body: MyLinkInput, user: AppUser = Depends(current_user), db=Depends(get_db)):
    if not db.get(CombatEvent, event_id):
        raise HTTPException(404, "UFC event not found")
    values = body.model_dump()
    playback_preference = values.pop("playback_preference")
    link = PersonalLink(event_id=event_id, owner_id=user.id, playback_preference=playback_preference, **values)
    link.url = validate_personal_url(link.url)
    db.add(link)
    db.commit()
    db.refresh(link)
    await check_personal_link(db, link, playback_preference)
    return serialize_personal_link(link)


@router.patch("/my-links/{id}")
async def update_my_link(id: int, body: MyLinkUpdate, user: AppUser = Depends(current_user), db=Depends(get_db)):
    link = personal_link_or_404(id, db, user)
    changes = body.model_dump(exclude_unset=True)
    playback_preference = changes.pop("playback_preference", "AUTO")
    if "url" in changes:
        changes["url"] = validate_personal_url(changes["url"])
    for name, value in changes.items():
        setattr(link, name, value)
    db.commit()
    db.refresh(link)
    if "url" in changes or "enabled" in changes or "playback_preference" in body.model_fields_set:
        await check_personal_link(db, link, playback_preference)
    return serialize_personal_link(link)


@router.post("/my-links/{id}/check")
async def check_my_link(id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    link = personal_link_or_404(id, db, user)
    await check_personal_link(db, link)
    return serialize_personal_link(link)


@router.post("/my-links/{id}/opened")
def mark_my_link_opened(id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    link = personal_link_or_404(id, db, user)
    if (
        not link.enabled
        or link.status not in {"ONLINE", "REDIRECT", "WARNING"}
        or not link.final_url
    ):
        raise HTTPException(409, "This link is not safe to open")
    try:
        validate_public_url(link.final_url)
    except ValueError as exc:
        link.status = "BLOCKED"
        db.commit()
        raise HTTPException(409, "This link is not safe to open") from exc
    link.last_opened_at = now()
    db.commit()
    db.refresh(link)
    return serialize_personal_link(link)


@router.delete("/my-links/{id}", status_code=204)
def delete_my_link(id: int, user: AppUser = Depends(current_user), db=Depends(get_db)):
    db.delete(personal_link_or_404(id, db, user))
    db.commit()


@router.get("/favorites")
def favorites(db=Depends(get_db)):
    return list(db.scalars(select(Favorite.team_id)))


def admin(authorization: str = Header("")):
    if not settings.admin_secret or not secrets.compare_digest(
        authorization, "Bearer " + settings.admin_secret
    ):
        raise HTTPException(401, "Valid maintenance key required")


@router.get("/admin/status", dependencies=[Depends(admin)])
def admin_status(db=Depends(get_db)):
    states = {s.key: s.value for s in db.scalars(select(MaintenanceState))}
    states.setdefault("link_check_hours", settings.link_check_hours)
    return dict(
        games=db.scalar(select(func.count(Game.id))),
        sources=db.scalar(select(func.count(WatchSource.id))),
        online=db.scalar(
            select(func.count(WatchSource.id)).where(
                WatchSource.status.in_(["ONLINE", "REDIRECT"])
            )
        ),
        broken=db.scalar(
            select(func.count(WatchSource.id)).where(
                WatchSource.status.in_(["NOT_FOUND", "ERROR"])
            )
        ),
        failed_requests=db.scalar(
            select(func.count(LinkCheck.id)).where(LinkCheck.is_available == False)
        ),
        blocked=db.scalar(
            select(func.count(WatchSource.id)).where(WatchSource.status == "BLOCKED")
        ),
        unchecked=db.scalar(
            select(func.count(WatchSource.id)).where(WatchSource.status == "UNCHECKED")
        ),
        **{**states, **provider_status(db)},
    )


@router.post("/admin/update-schedule", dependencies=[Depends(admin)])
@router.post("/admin/rebuild-sources", dependencies=[Depends(admin)])
def update(db=Depends(get_db)):
    result = sync_schedule(db)
    return {
        **result,
        "updated": result["fetched"],
        "games_created": result["created"],
        "games_updated": result["updated"],
    }


@router.post("/admin/check-links", dependencies=[Depends(admin)])
async def check():
    from app.services.jobs import check_links

    return await check_links()


@router.post("/admin/sync-nba-players", dependencies=[Depends(admin)])
def admin_sync_nba_players(team_id: str = Query(""), db=Depends(get_db)):
    tid = team_id if team_id else None
    count = sync_nba_players(db, team_id=tid)
    return {"synced": count}


@router.get("/health")
def health(db=Depends(get_db)):
    info = provider_status(db)
    return {
        "status": "ok",
        "provider": info["provider"],
        "provider_status": info["provider_status"],
        "development_data": info["development_data"],
        "refresh_seconds": max(settings.live_refresh_seconds, 60),
        "season": settings.current_season,
    }


from pydantic import BaseModel, Field


class LinkSettings(BaseModel):
    hours: int = Field(ge=1, le=168)


class SubscriptionUpdate(BaseModel):
    has_subscription: bool | None = None
    has_free_trial: bool | None = None
    notes: str | None = None


@router.get("/subscriptions")
def get_subscriptions(db=Depends(get_db)):
    from app.models.entities import UserSubscription
    subs = db.scalars(select(UserSubscription).order_by(UserSubscription.provider_name)).all()
    return [
        {
            "id": s.id,
            "provider_name": s.provider_name,
            "source_name": s.source_name,
            "has_subscription": s.has_subscription,
            "has_free_trial": s.has_free_trial,
            "notes": s.notes,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in subs
    ]


@router.patch("/subscriptions/{provider_name}")
def update_subscription(provider_name: str, body: SubscriptionUpdate, db=Depends(get_db)):
    from app.models.entities import UserSubscription
    sub = db.scalar(select(UserSubscription).where(UserSubscription.provider_name == provider_name))
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if body.has_subscription is not None:
        sub.has_subscription = body.has_subscription
    if body.has_free_trial is not None:
        sub.has_free_trial = body.has_free_trial
    if body.notes is not None:
        sub.notes = body.notes
    sub.updated_at = now()
    db.commit()
    return {
        "id": sub.id,
        "provider_name": sub.provider_name,
        "source_name": sub.source_name,
        "has_subscription": sub.has_subscription,
        "has_free_trial": sub.has_free_trial,
        "notes": sub.notes,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


class LinkSettings(BaseModel):
    hours: int = Field(ge=1, le=168)


@router.post("/admin/settings", dependencies=[Depends(admin)])
def link_settings(body: LinkSettings, request: Request, db=Depends(get_db)):
    settings.link_check_hours = body.hours
    db.merge(MaintenanceState(key="link_check_hours", value=str(body.hours)))
    db.commit()
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler and scheduler.running:
        scheduler.reschedule_job("link-checks", trigger="interval", hours=body.hours)
    return {"link_check_hours": body.hours}
