"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Award, Trophy, Calendar, BarChart2, TrendingUp, Star } from "lucide-react";

interface TeamDirectoryEntry {
  id: number;
  city: string;
  name: string;
}

interface NbaPlayerDetail {
  id: number;
  external_id: string;
  provider_id: string;
  league: string;
  team_id: number | null;
  full_name: string;
  first_name: string;
  last_name: string;
  display_name: string;
  short_name: string;
  jersey: string;
  position: string;
  position_name: string;
  position_abbreviation: string;
  height: string;
  weight: string;
  age: number | null;
  date_of_birth: string;
  birth_place: string;
  college: string;
  headshot_url: string;
  status: string;
  experience_years: number;
  draft_year: number | null;
  draft_round: number | null;
  draft_pick: number | null;
  career_stats: Record<string, { value: number | string; display: string }>;
  game_log: Array<{
    date: string;
    opponent: string;
    home_away: string;
    result: string;
    points: number | null;
    rebounds: number | null;
    assists: number | null;
    minutes: number | null;
    fg_made: number | null;
    fg_attempted: number | null;
    fg_pct: number | null;
    ft_made: number | null;
    ft_attempted: number | null;
    ft_pct: number | null;
    three_made: number | null;
    three_attempted: number | null;
    three_pct: number | null;
  }>;
  splits: Record<string, Array<{ name: string; value: number | string; display: string }>>;
  awards: Array<{ name: string; type: string; year: string; description: string }>;
}

export default function NbaPlayerDetail({ playerId }: { playerId: string }) {
  const [player, setPlayer] = useState<NbaPlayerDetail | null>(null);
  const [teamName, setTeamName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"bio" | "career" | "gamelog" | "splits" | "awards">("bio");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`/api/nba/players/${playerId}`),
      fetch("/api/teams?league=NBA"),
    ])
      .then(async ([playerResponse, teamsResponse]) => {
        if (!playerResponse.ok) throw Error("Player not found.");
        const data: NbaPlayerDetail = await playerResponse.json();
        const teams: TeamDirectoryEntry[] = teamsResponse.ok ? await teamsResponse.json() : [];
        const team = teams.find((row) => row.id === data.team_id);
        setTeamName(team ? `${team.city} ${team.name}` : "");
        return data;
      })
      .then((data: NbaPlayerDetail) => {
        setPlayer(data);
        setError("");
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) {
    return <div className="empty">Loading player…</div>;
  }

  if (error || !player) {
    return <div className="error">{error || "Player not found"}</div>;
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const statRows = [
    ["PTS", "points"],
    ["REB", "rebounds"],
    ["AST", "assists"],
    ["FG%", "fieldGoalPct"],
    ["FT%", "freeThrowPct"],
    ["3P%", "threePointFieldGoalPct"],
    ["MIN", "minutes"],
  ] as const;

  return (
    <>
      <div className="page-heading">
        <div>
          <Link href="/sports/nba/players" className="back-link">
            <ArrowLeft size={16} /> Back to NBA teams
          </Link>
          <div className="eyebrow">NBA · BASKETBALL</div>
          <h1>{player.full_name || player.display_name}</h1>
          <p>
            {player.jersey && `#${player.jersey} · `}
            {player.position_name || player.position}{teamName && ` · ${teamName}`}
          </p>
        </div>
        {player.headshot_url && (
          <img src={player.headshot_url} alt="" className="player-headshot-large" onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} />
        )}
      </div>

      <div className="player-tabs">
        <button
          className={activeTab === "bio" ? "active" : ""}
          onClick={() => setActiveTab("bio")}
        >
          Bio
        </button>
        <button
          className={activeTab === "career" ? "active" : ""}
          onClick={() => setActiveTab("career")}
        >
          Career Stats
        </button>
        <button
          className={activeTab === "gamelog" ? "active" : ""}
          onClick={() => setActiveTab("gamelog")}
        >
          Game Log
        </button>
        <button
          className={activeTab === "splits" ? "active" : ""}
          onClick={() => setActiveTab("splits")}
        >
          Splits
        </button>
        <button
          className={activeTab === "awards" ? "active" : ""}
          onClick={() => setActiveTab("awards")}
        >
          Awards
        </button>
      </div>

      {activeTab === "bio" && (
        <div className="player-bio">
          <div className="bio-grid">
            <div className="bio-section">
              <h3>Personal</h3>
              <dl>
                <dt>Full Name</dt>
                <dd>{player.full_name}</dd>
                <dt>Born</dt>
                <dd>
                  {player.date_of_birth && formatDate(player.date_of_birth)}
                  {player.age !== null && ` (Age ${player.age})`}
                </dd>
                <dt>Birthplace</dt>
                <dd>{player.birth_place || "Unknown"}</dd>
                <dt>College</dt>
                <dd>{player.college || "None"}</dd>
                <dt>Height / Weight</dt>
                <dd>{player.height} / {player.weight}lbs</dd>
                <dt>Status</dt>
                <dd>{player.status || "Active"}</dd>
              </dl>
            </div>
            <div className="bio-section">
              <h3>Career</h3>
              <dl>
                <dt>Experience</dt>
                <dd>{player.experience_years > 0 ? `${player.experience_years} years` : "Rookie"}</dd>
                <dt>Draft</dt>
                <dd>
                  {player.draft_year
                    ? `${player.draft_year} · Round ${player.draft_round} · Pick ${player.draft_pick}`
                    : "Undrafted"}
                </dd>
                <dt>Jersey</dt>
                <dd>{player.jersey || "—"}</dd>
                <dt>Position</dt>
                <dd>{player.position_name || player.position}</dd>
              </dl>
            </div>
          </div>
        </div>
      )}

      {activeTab === "career" && (
        <div className="player-career">
          {Object.keys(player.career_stats).length === 0 ? (
            <div className="empty">No career statistics available.</div>
          ) : (
            <div className="stats-table">
              <h3>Career Totals</h3>
              <table>
                <thead>
                  <tr>
                    <th>Stat</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(player.career_stats).map(([key, stat]) => (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>{stat.display || stat.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "gamelog" && (
        <div className="player-gamelog">
          {player.game_log.length === 0 ? (
            <div className="empty">No game log available.</div>
          ) : (
            <div className="stats-table">
              <h3>Game Log ({player.game_log.length} games)</h3>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Opp</th>
                    <th>H/A</th>
                    <th>Result</th>
                    <th>MIN</th>
                    <th>PTS</th>
                    <th>REB</th>
                    <th>AST</th>
                    <th>FG%</th>
                    <th>3P%</th>
                    <th>FT%</th>
                  </tr>
                </thead>
                <tbody>
                  {player.game_log.map((game, idx) => (
                    <tr key={idx}>
                      <td>{game.date && formatDate(game.date)}</td>
                      <td>{game.opponent}</td>
                      <td>{game.home_away === "home" ? "vs" : "@"}</td>
                      <td className={game.result === "W" ? "win" : game.result === "L" ? "loss" : ""}>
                        {game.result}
                      </td>
                      <td>{game.minutes ?? "—"}</td>
                      <td>{game.points ?? "—"}</td>
                      <td>{game.rebounds ?? "—"}</td>
                      <td>{game.assists ?? "—"}</td>
                      <td>{game.fg_pct ? `${(game.fg_pct * 100).toFixed(1)}%` : "—"}</td>
                      <td>{game.three_pct ? `${(game.three_pct * 100).toFixed(1)}%` : "—"}</td>
                      <td>{game.ft_pct ? `${(game.ft_pct * 100).toFixed(1)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "splits" && (
        <div className="player-splits">
          {Object.keys(player.splits).length === 0 ? (
            <div className="empty">No situational splits available.</div>
          ) : (
            Object.entries(player.splits).map(([category, splits]) => (
              <div key={category} className="split-category">
                <h3>{category}</h3>
                <div className="stats-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Split</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {splits.map((split, idx) => (
                        <tr key={idx}>
                          <td>{split.name}</td>
                          <td>{split.display || split.value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "awards" && (
        <div className="player-awards">
          {player.awards.length === 0 ? (
            <div className="empty">No awards available.</div>
          ) : (
            <ul className="awards-list">
              {player.awards.map((award, idx) => (
                <li key={idx} className="award-item">
                  <Award className="award-icon" />
                  <div>
                    <strong>{award.name}</strong>
                    {award.year && <span className="award-year">{award.year}</span>}
                    {award.type && <span className="award-type">{award.type}</span>}
                    {award.description && <p className="award-desc">{award.description}</p>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}