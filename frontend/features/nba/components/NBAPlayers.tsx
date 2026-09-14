"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";

interface TeamDirectoryEntry {
  id: number;
  provider_id: string | null;
  abbreviation: string;
  city: string;
  name: string;
  logo_url: string;
}

interface NbaPlayer {
  id: number;
  external_id: string;
  provider_id: string;
  team_id: number | null;
  full_name: string;
  display_name: string;
  jersey: string;
  position: string;
  position_name: string;
  height: string;
  weight: string;
  age: number | null;
  headshot_url: string;
  status: string;
  experience_years: number;
  college: string;
}

const teamLabel = (team: TeamDirectoryEntry) => `${team.city} ${team.name}`;

export default function NbaPlayers({
  teamId,
  teamName,
  initialQuery,
}: {
  teamId?: string;
  teamName?: string;
  initialQuery?: string;
}) {
  const [players, setPlayers] = useState<NbaPlayer[]>([]);
  const [teams, setTeams] = useState<TeamDirectoryEntry[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState(teamId || "");
  const [query, setQuery] = useState(initialQuery || "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialQuery !== undefined) setQuery(initialQuery);
  }, [initialQuery]);
  useEffect(() => {
    setSelectedTeamId(teamId || "");
  }, [teamId]);
  useEffect(() => {
    fetch("/api/teams?league=NBA")
      .then((response) => response.ok ? response.json() : [])
      .then((rows: TeamDirectoryEntry[]) => setTeams(rows))
      .catch(() => setTeams([]));
  }, []);

  useEffect(() => {
    if (!selectedTeamId && !query.trim()) {
      setPlayers([]);
      setError("");
      setLoading(false);
      return;
    }
    const timer = setTimeout(() => {
      setLoading(true);
      const params = new URLSearchParams();
      if (selectedTeamId) params.set("team", selectedTeamId);
      if (query.trim()) params.set("q", query.trim());
      fetch(`/api/nba/players?${params}`)
        .then(async (response) => {
          if (!response.ok) throw Error("NBA players are unavailable.");
          return response.json();
        })
        .then((rows: NbaPlayer[]) => { setPlayers(rows); setError(""); })
        .catch((reason) => setError(reason.message))
        .finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(timer);
  }, [query, selectedTeamId]);

  const selectedTeam = teams.find((team) => team.provider_id === selectedTeamId);
  const matchingTeams = useMemo(() => {
    const phrase = query.trim().toLowerCase();
    return teams.filter((team) => !phrase || [team.city, team.name, team.abbreviation]
      .some((value) => value.toLowerCase().includes(phrase)));
  }, [query, teams]);
  const teamsById = useMemo(() => new Map(teams.map((team) => [team.id, team])), [teams]);
  const playerGroups = useMemo(() => {
    const groups = new Map<number | null, NbaPlayer[]>();
    for (const player of players) {
      const roster = groups.get(player.team_id) || [];
      roster.push(player);
      groups.set(player.team_id, roster);
    }
    return [...groups.entries()]
      .map(([id, roster]) => ({
        id,
        team: id === null ? undefined : teamsById.get(id),
        roster: [...roster].sort((a, b) => (a.full_name || a.display_name).localeCompare(b.full_name || b.display_name)),
      }))
      .sort((a, b) => (a.team ? teamLabel(a.team) : "Unassigned players")
        .localeCompare(b.team ? teamLabel(b.team) : "Unassigned players"));
  }, [players, teamsById]);

  const selectTeam = (team: TeamDirectoryEntry) => {
    setSelectedTeamId(team.provider_id || "");
    setQuery("");
  };
  const activeTeamName = selectedTeam ? teamLabel(selectedTeam) : teamName;
  const showingDirectory = !selectedTeamId;
  const hasSearch = query.trim().length > 0;

  return <>
    <div className="page-heading"><div><div className="eyebrow">NBA · BASKETBALL</div><h1>NBA Players</h1><p>{activeTeamName ? `Browse the ${activeTeamName} roster and view player profiles.` : "Choose a team to view its roster, or search for a team or player."}</p></div></div>
    <div className="search-row"><div className="search-box"><Search size={19} /><input aria-label="Search NBA teams or players" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search NBA teams or players" /></div></div>
    {selectedTeamId && <button className="team-directory-back" type="button" onClick={() => setSelectedTeamId("")}>← All NBA teams</button>}
    {showingDirectory && <section className="team-directory" aria-label="NBA teams">
      <div className="team-directory-title"><h2>{hasSearch ? "Matching teams" : "Choose a team"}</h2><p>{hasSearch ? "Select a team to view its roster." : "Select a team to see all players."}</p></div>
      {matchingTeams.length > 0 ? <div className="team-selection-grid">
        {matchingTeams.map((team) => <button className="team-selection-card" type="button" key={team.id} onClick={() => selectTeam(team)}>
          {team.logo_url ? <img src={team.logo_url} alt="" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <span>{team.abbreviation}</span>}
          <strong>{teamLabel(team)}</strong><small>{team.abbreviation} · View roster</small>
        </button>)}
      </div> : <div className="empty">No NBA teams match that search.</div>}
    </section>}
    {loading ? <div className="empty">Loading NBA players…</div> : error ? <div className="error">{error}</div> : playerGroups.length > 0 && <section className="player-search-results" aria-label={activeTeamName ? `${activeTeamName} players` : "Matching NBA players"}>
      {!selectedTeamId && <div className="team-directory-title"><h2>Matching players</h2><p>Player results appear below matching teams.</p></div>}
      <div className="player-team-groups">
        {playerGroups.map(({ id, team, roster }) => <section className="player-team-group" key={id ?? "unassigned"}>
          {!selectedTeamId && <header className="player-team-heading"><span className="player-team-fallback">{team?.abbreviation || "NBA"}</span><div><h2>{team ? teamLabel(team) : "Unassigned players"}</h2><p>{roster.length} {roster.length === 1 ? "player" : "players"}</p></div></header>}
          <div className="player-grid">
            {roster.map((player) => <article className="player-card" key={player.id}>
              {player.headshot_url && <img src={player.headshot_url} alt="" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />}
              <div className="player-info"><small>{player.jersey && `#${player.jersey} · `}{player.position_name || player.position}{player.height && ` · ${player.height}`}{player.weight && ` · ${player.weight}lbs`}</small><Link href={`/sports/nba/players/${player.id}`}><h2>{player.full_name || player.display_name}</h2></Link><p>{player.college && `${player.college} · `}{player.age !== null && player.age !== undefined ? `${player.age} yrs · ` : ""}{player.experience_years > 0 ? `${player.experience_years} yr exp` : "Rookie"}</p></div>
            </article>)}
          </div>
        </section>)}
      </div>
    </section>}
    {!loading && !error && hasSearch && playerGroups.length === 0 && !selectedTeamId && <div className="empty">No players match that search.</div>}
    {!loading && !error && selectedTeamId && playerGroups.length === 0 && <div className="empty">No players found for {activeTeamName || "this team"}.</div>}
  </>;
}
