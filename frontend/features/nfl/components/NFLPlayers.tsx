"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";

type NflPlayer = {
  id: string;
  full_name: string;
  team: string;
  jersey: string;
  position: string;
  position_name: string;
  height: string;
  weight: string;
  age: number | null;
  college: string;
  headshot_url: string;
  status: string;
};

type TeamDirectoryEntry = {
  id: number;
  abbreviation: string;
  city: string;
  name: string;
  logo_url: string;
};

const teamLabel = (team: TeamDirectoryEntry) => `${team.city} ${team.name}`;

export default function NflPlayers() {
  const [players, setPlayers] = useState<NflPlayer[]>([]);
  const [teams, setTeams] = useState<TeamDirectoryEntry[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<TeamDirectoryEntry | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/teams?league=NFL")
      .then((response) => response.ok ? response.json() : [])
      .then((rows: TeamDirectoryEntry[]) => setTeams(rows))
      .catch(() => setTeams([]));
  }, []);

  useEffect(() => {
    const playerQuery = [selectedTeam?.abbreviation, query.trim()].filter(Boolean).join(" ");
    if (!playerQuery) {
      setPlayers([]);
      setError("");
      setLoading(false);
      return;
    }
    const timer = window.setTimeout(() => {
      setLoading(true);
      fetch(`/api/nfl/players?q=${encodeURIComponent(playerQuery)}`)
        .then(async (response) => {
          if (!response.ok) throw Error("NFL players are unavailable.");
          return response.json();
        })
        .then((rows: NflPlayer[]) => { setPlayers(rows); setError(""); })
        .catch((reason) => setError(reason.message))
        .finally(() => setLoading(false));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [query, selectedTeam]);

  const matchingTeams = useMemo(() => {
    const phrase = query.trim().toLowerCase();
    return teams.filter((team) => !phrase || [team.city, team.name, team.abbreviation]
      .some((value) => value.toLowerCase().includes(phrase)));
  }, [query, teams]);

  const playerGroups = useMemo(() => {
    const groups = new Map<string, NflPlayer[]>();
    for (const player of players) {
      const roster = groups.get(player.team) || [];
      roster.push(player);
      groups.set(player.team, roster);
    }
    return [...groups.entries()]
      .map(([abbreviation, roster]) => ({
        abbreviation,
        roster: [...roster].sort((a, b) => a.full_name.localeCompare(b.full_name)),
      }))
      .sort((a, b) => a.abbreviation.localeCompare(b.abbreviation));
  }, [players]);

  const selectTeam = (team: TeamDirectoryEntry) => {
    setSelectedTeam(team);
    setQuery("");
  };
  const showingDirectory = !selectedTeam;
  const hasSearch = query.trim().length > 0;

  return <>
    <div className="page-heading"><div><div className="eyebrow">NFL · FOOTBALL</div><h1>NFL Players</h1><p>{selectedTeam ? `Browse the ${teamLabel(selectedTeam)} roster.` : "Choose a team to view its roster, or search for a team or player."}</p></div></div>
    <div className="search-row"><div className="search-box"><Search size={19} /><input aria-label="Search NFL teams or players" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search NFL teams or players" /></div></div>
    {selectedTeam && <button className="team-directory-back" type="button" onClick={() => setSelectedTeam(null)}>← All NFL teams</button>}
    {showingDirectory && <section className="team-directory" aria-label="NFL teams">
      <div className="team-directory-title"><h2>{hasSearch ? "Matching teams" : "Choose a team"}</h2><p>{hasSearch ? "Select a team to view its roster." : "Select a team to see all players."}</p></div>
      {matchingTeams.length > 0 ? <div className="team-selection-grid">
        {matchingTeams.map((team) => <button className="team-selection-card" type="button" key={team.id} onClick={() => selectTeam(team)}>
          {team.logo_url ? <img src={team.logo_url} alt="" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <span>{team.abbreviation}</span>}
          <strong>{teamLabel(team)}</strong><small>{team.abbreviation} · View roster</small>
        </button>)}
      </div> : <div className="empty">No NFL teams match that search.</div>}
    </section>}
    {loading ? <div className="empty">Loading NFL players…</div> : error ? <div className="error">{error}</div> : playerGroups.length > 0 && <section className="player-search-results" aria-label={selectedTeam ? `${teamLabel(selectedTeam)} players` : "Matching NFL players"}>
      {!selectedTeam && <div className="team-directory-title"><h2>Matching players</h2><p>Choose a player result by team.</p></div>}
      <div className="player-team-groups">
        {playerGroups.map(({ abbreviation, roster }) => <section className="player-team-group" key={abbreviation}>
          {!selectedTeam && <header className="player-team-heading"><span className="player-team-fallback">{abbreviation}</span><div><h2>{abbreviation}</h2><p>{roster.length} {roster.length === 1 ? "player" : "players"}</p></div></header>}
          <div className="player-grid">
            {roster.map((player) => <article className="player-card" key={`${player.team}-${player.id}`}>
              {player.headshot_url && <img src={player.headshot_url} alt="" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />}
              <div className="player-info"><small>{player.jersey && `#${player.jersey}`} {player.position && `· ${player.position}`}</small><Link href={`/sports/nfl/players/${player.team}/${player.id}`}><h2>{player.full_name}</h2></Link><p>{player.position_name}{player.height && ` · ${player.height}`}{player.weight && ` · ${player.weight}`}</p><p>{player.college || "College unavailable"}{player.age !== null && ` · ${player.age} yrs`}</p></div>
            </article>)}
          </div>
        </section>)}
      </div>
    </section>}
    {!loading && !error && hasSearch && playerGroups.length === 0 && !selectedTeam && <div className="empty">No players match that search.</div>}
    {!loading && !error && selectedTeam && playerGroups.length === 0 && <div className="empty">No players found for {teamLabel(selectedTeam)}.</div>}
  </>;
}
