"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, CalendarDays, Users } from "lucide-react";

import type { Game, Team } from "../../types";
import { gameDate, kickoff } from "../../lib/helpers";
import { sportPath } from "../../lib/sportRoutes";

export default function TeamProfile({ teamId, timezone }: { teamId: string; timezone: string }) {
  const [team, setTeam] = useState<Team | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`/api/teams/${teamId}`)
      .then(async (response) => {
        if (!response.ok) throw Error("Team not found.");
        return response.json();
      })
      .then(async (data: Team) => {
        if (!active) return;
        setTeam(data);
        const response = await fetch(`/api/games?league=${data.league}&team=${encodeURIComponent(data.abbreviation)}`);
        if (response.ok && active) setGames(await response.json());
      })
      .catch((reason) => active && setError(reason.message));
    return () => { active = false; };
  }, [teamId]);

  if (error) return <div className="error">{error}</div>;
  if (!team) return <div className="empty">Loading team…</div>;
  const teamName = `${team.city} ${team.name}`;
  const playerLabel = team.league === "NBA" ? "Players" : "Players";

  return <>
    <section className="team-profile-hero">
      <Link href={sportPath(team.league, "Teams")} className="back-link"><ArrowLeft size={16} /> Back to teams</Link>
      <div>{team.logo_url && <img src={team.logo_url} alt="" onError={(event) => { event.currentTarget.style.display = "none"; }} />}<div><div className="eyebrow">{team.league} · {team.conference} {team.division}</div><h1>{teamName}</h1><p>Schedule, roster, standings, and game-day information.</p></div></div>
      <div className="team-profile-actions"><Link className="secondary-button" href={`${sportPath(team.league, "Schedule")}?team=${encodeURIComponent(team.abbreviation)}`}><CalendarDays size={16} /> Schedule</Link><Link className="secondary-button" href={sportPath(team.league, playerLabel)}><Users size={16} /> {playerLabel}</Link><Link className="primary-button" href={sportPath(team.league, "Standings")}>Standings <ArrowRight size={16} /></Link></div>
    </section>
    <section><div className="section-heading"><h2>Team schedule</h2><span>{games.length} games</span></div>{games.length ? <div className="team-profile-games">{games.slice(0, 8).map((game) => <Link href={`/game/${game.id}`} key={game.id}><span>{game.away_team.abbreviation} at {game.home_team.abbreviation}</span><strong>{game.status === "LIVE" ? "LIVE" : game.status === "FINAL" ? `${game.away_score} – ${game.home_score}` : kickoff(game.kickoff_time, timezone)}</strong><small>{gameDate(game.kickoff_time, timezone)}</small></Link>)}</div> : <div className="empty compact">No scheduled games are available right now.</div>}</section>
  </>;
}
