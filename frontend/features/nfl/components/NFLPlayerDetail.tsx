"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

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

type TeamDirectoryEntry = { abbreviation: string; city: string; name: string };

export default function NflPlayerDetail({ team, playerId }: { team: string; playerId: string }) {
  const [player, setPlayer] = useState<NflPlayer | null>(null);
  const [teamName, setTeamName] = useState(team);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`/api/nfl/players/${encodeURIComponent(team)}/${encodeURIComponent(playerId)}`),
      fetch("/api/teams?league=NFL"),
    ])
      .then(async ([playerResponse, teamsResponse]) => {
        if (!playerResponse.ok) throw Error("Player not found.");
        const rows: TeamDirectoryEntry[] = teamsResponse.ok ? await teamsResponse.json() : [];
        const matchingTeam = rows.find((row) => row.abbreviation === team.toUpperCase());
        if (matchingTeam) setTeamName(`${matchingTeam.city} ${matchingTeam.name}`);
        return playerResponse.json();
      })
      .then((data: NflPlayer) => { setPlayer(data); setError(""); })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [playerId, team]);

  if (loading) return <div className="empty">Loading player…</div>;
  if (error || !player) return <div className="error">{error || "Player not found."}</div>;

  return <>
    <div className="page-heading player-profile-heading">
      <div>
        <Link href="/sports/nfl/players" className="back-link"><ArrowLeft size={16} /> Back to NFL teams</Link>
        <div className="eyebrow">NFL · {teamName.toUpperCase()}</div>
        <h1>{player.full_name}</h1>
        <p>{player.jersey && `#${player.jersey} · `}{player.position_name || player.position} · {teamName}</p>
      </div>
      {player.headshot_url && <img src={player.headshot_url} alt="" className="player-headshot-large" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />}
    </div>
    <div className="player-bio"><div className="bio-grid">
      <section className="bio-section"><h3>Player details</h3><dl>
        <dt>Team</dt><dd>{teamName}</dd>
        <dt>Position</dt><dd>{player.position_name || player.position || "—"}</dd>
        <dt>Jersey</dt><dd>{player.jersey ? `#${player.jersey}` : "—"}</dd>
        <dt>Status</dt><dd>{player.status || "Active"}</dd>
      </dl></section>
      <section className="bio-section"><h3>Background</h3><dl>
        <dt>Height / Weight</dt><dd>{player.height || "—"} {player.weight && `/ ${player.weight}`}</dd>
        <dt>Age</dt><dd>{player.age ?? "—"}</dd>
        <dt>College</dt><dd>{player.college || "Not available"}</dd>
      </dl></section>
    </div></div>
  </>;
}
