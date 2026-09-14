"""Factual recap builders over RamanPlay's normalized stored sports data."""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.entities import CombatBout, CombatEvent, Game, Team
from app.schemas.recaps import Recap, RecapBout, RecapNextEvent, RecapParticipant
from app.services.sync import active_provider


SUPPORTED_RECAP_SPORTS = {"NFL", "NBA", "UFC"}


class RecapNotFoundError(LookupError):
    pass


def _team_participant(team: Team, score=None, record=None) -> RecapParticipant:
    return RecapParticipant(
        id=team.id,
        name=f"{team.city} {team.name}".strip(),
        abbreviation=team.provider_abbreviation or team.abbreviation,
        score=score,
        record=record or None,
    )


def _fighter_participant(fighter) -> RecapParticipant:
    return RecapParticipant(
        id=fighter.id,
        name=fighter.full_name,
        record=fighter.record or None,
        headshot_url=fighter.headshot_url or None,
    )


def _game_scope(db, sport: str):
    if sport == "NFL":
        return and_(
            Game.league == "NFL",
            Game.provider == active_provider(db),
            Game.season == settings.current_season,
        )
    if sport == "NBA":
        return Game.league == "NBA"
    return or_(
        and_(
            Game.league == "NFL",
            Game.provider == active_provider(db),
            Game.season == settings.current_season,
        ),
        Game.league == "NBA",
    )


def _next_game(db, game: Game, team: Team) -> RecapNextEvent | None:
    if not game.kickoff_time:
        return None
    next_game = db.scalar(
        select(Game)
        .where(
            Game.league == game.league,
            Game.provider == game.provider,
            Game.status.in_(("SCHEDULED", "PRE_GAME")),
            Game.kickoff_time > game.kickoff_time,
            or_(Game.away_team_id == team.id, Game.home_team_id == team.id),
        )
        .options(selectinload(Game.away_team), selectinload(Game.home_team))
        .order_by(Game.kickoff_time)
    )
    if not next_game:
        return None
    opponent = next_game.home_team if next_game.away_team_id == team.id else next_game.away_team
    return RecapNextEvent(
        participant_id=team.id,
        label=f"{team.city} {team.name} vs {opponent.city} {opponent.name}",
        event_id=next_game.id,
        event_time=next_game.kickoff_time,
        route=f"/game/{next_game.id}",
    )


def game_recap(db, game: Game) -> Recap:
    if game.status != "FINAL":
        raise RecapNotFoundError("A recap is available after a game is final.")
    away = _team_participant(game.away_team, game.away_score, game.away_record)
    home = _team_participant(game.home_team, game.home_score, game.home_record)
    winner = loser = None
    if game.away_score is not None and game.home_score is not None and game.away_score != game.home_score:
        winner, loser = (away, home) if game.away_score > game.home_score else (home, away)
    final_score = f"{away.abbreviation} {away.score} – {home.abbreviation} {home.score}" if away.score is not None and home.score is not None else None
    facts = [fact for fact in (
        final_score and f"Final score: {final_score}",
        away.record and f"{away.name} record: {away.record}",
        home.record and f"{home.name} record: {home.record}",
    ) if fact]
    next_related = [item for item in (_next_game(db, game, game.away_team), _next_game(db, game, game.home_team)) if item]
    return Recap(
        id=f"{game.league.lower()}-{game.id}",
        sport=game.sport,
        league=game.league,
        event_id=game.id,
        status=game.status,
        event_time=game.kickoff_time,
        title=f"{away.name} at {home.name}",
        final_score=final_score,
        winner=winner,
        loser=loser,
        summary_facts=facts,
        venue=game.venue or None,
        broadcast_network=game.broadcast_network,
        source_name="ESPN" if game.provider.startswith("espn") else game.provider,
        source_provider=game.provider,
        teams=[away, home],
        next_related=next_related,
    )


def _bout_recap(bout: CombatBout) -> RecapBout:
    winner = loser = None
    if bout.winner_id:
        winner = _fighter_participant(bout.fighter_a if bout.winner_id == bout.fighter_a_id else bout.fighter_b)
        loser = _fighter_participant(bout.fighter_b if bout.winner_id == bout.fighter_a_id else bout.fighter_a)
    return RecapBout(
        id=bout.id,
        card_section=bout.card_section,
        weight_class=bout.weight_class or None,
        winner=winner,
        loser=loser,
        result_method=bout.result_method or None,
        result_round=bout.result_round,
        finish_time=bout.finish_time or None,
    )


def _next_ufc_event(db, event: CombatEvent) -> RecapNextEvent | None:
    if not event.event_time:
        return None
    next_event = db.scalar(
        select(CombatEvent)
        .where(
            CombatEvent.league == "UFC",
            CombatEvent.status.in_(("SCHEDULED", "PRE_GAME")),
            CombatEvent.event_time > event.event_time,
        )
        .order_by(CombatEvent.event_time)
    )
    if not next_event:
        return None
    return RecapNextEvent(
        label=next_event.name,
        event_id=next_event.id,
        event_time=next_event.event_time,
        route=f"/ufc/event/{next_event.id}",
    )


def ufc_recap(db, event: CombatEvent) -> Recap:
    if event.status != "FINAL":
        raise RecapNotFoundError("A recap is available after an event is final.")
    completed_bouts = [_bout_recap(bout) for bout in event.bouts if bout.status == "FINAL"]
    main_bout = next((bout for bout in reversed(completed_bouts) if bout.card_section == "MAIN_EVENT"), completed_bouts[-1] if completed_bouts else None)
    final_score = f"{main_bout.winner.name} def. {main_bout.loser.name}" if main_bout and main_bout.winner and main_bout.loser else None
    facts = [fact for fact in (
        final_score and f"Main event: {final_score}",
        main_bout and main_bout.result_method,
        main_bout and main_bout.result_round and f"Round {main_bout.result_round}",
        main_bout and main_bout.finish_time,
    ) if fact]
    return Recap(
        id=f"ufc-{event.id}",
        sport=event.sport,
        league="UFC",
        event_id=event.id,
        status=event.status,
        event_time=event.event_time,
        title=event.name,
        final_score=final_score,
        winner=main_bout.winner if main_bout else None,
        loser=main_bout.loser if main_bout else None,
        summary_facts=facts,
        venue=event.venue or None,
        broadcast_network=event.broadcast_network,
        source_name="ESPN",
        source_provider=event.provider,
        bouts=completed_bouts,
        next_related=[item for item in (_next_ufc_event(db, event),) if item],
    )


def list_recaps(db, sport: str = "ALL", limit: int = 5) -> list[Recap]:
    sport = sport.upper()
    if sport not in {"ALL", *SUPPORTED_RECAP_SPORTS}:
        raise ValueError("Unknown sport")
    recaps: list[Recap] = []
    if sport in {"ALL", "NFL", "NBA"}:
        game_sport = sport if sport in {"NFL", "NBA"} else "ALL"
        games = db.scalars(
            select(Game)
            .where(_game_scope(db, game_sport), Game.status == "FINAL")
            .options(selectinload(Game.away_team), selectinload(Game.home_team))
            .order_by(Game.kickoff_time.desc())
            .limit(limit if sport != "ALL" else limit * 2)
        ).all()
        recaps.extend(game_recap(db, game) for game in games)
    if sport in {"ALL", "UFC"}:
        events = db.scalars(
            select(CombatEvent)
            .where(CombatEvent.league == "UFC", CombatEvent.status == "FINAL")
            .options(
                selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_a),
                selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_b),
            )
            .order_by(CombatEvent.event_time.desc())
            .limit(limit if sport != "ALL" else limit * 2)
        ).all()
        recaps.extend(ufc_recap(db, event) for event in events)
    return sorted(
        recaps,
        key=lambda recap: (recap.event_time or recap.completed_at).isoformat() if (recap.event_time or recap.completed_at) else "",
        reverse=True,
    )[:limit]


def recap_detail(db, sport: str, event_id: int) -> Recap:
    sport = sport.upper()
    if sport not in SUPPORTED_RECAP_SPORTS:
        raise ValueError("Unknown sport")
    if sport == "UFC":
        event = db.scalar(
            select(CombatEvent)
            .where(CombatEvent.id == event_id, CombatEvent.league == "UFC")
            .options(
                selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_a),
                selectinload(CombatEvent.bouts).selectinload(CombatBout.fighter_b),
            )
        )
        if not event:
            raise RecapNotFoundError("UFC event not found")
        return ufc_recap(db, event)
    game = db.scalar(
        select(Game)
        .where(Game.id == event_id, Game.league == sport, _game_scope(db, sport))
        .options(selectinload(Game.away_team), selectinload(Game.home_team))
    )
    if not game:
        raise RecapNotFoundError("Game not found")
    return game_recap(db, game)
