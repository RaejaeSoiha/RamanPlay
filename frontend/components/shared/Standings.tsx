"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Trophy } from "lucide-react";

import type { StandingTeam, Standings as StandingsData } from "../../types";
import { Crest } from "./SportUI";

const nflColumns = [
  ["W", "wins"],
  ["L", "losses"],
  ["T", "ties"],
  ["PCT", "win_percentage"],
  ["DIV", "division_record"],
  ["CONF", "conference_record"],
  ["PF", "points_for"],
  ["PA", "points_against"],
  ["STRK", "streak"],
  ["POS", "playoff_rank"],
] as const;

const nbaColumns = [
  ["W", "wins"],
  ["L", "losses"],
  ["PCT", "win_percentage"],
  ["GB", "games_back"],
  ["CONF", "conference_record"],
  ["DIV", "division_record"],
  ["STRK", "streak"],
  ["POS", "playoff_rank"],
] as const;

export default function Standings({ league = "NFL", sportRoot }: { league?: "NFL" | "NBA" | "ALL"; sportRoot?: string }) {
  const [data, setData] = useState<StandingsData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    setData(null);
    fetch(`/api/standings?league=${league === "ALL" ? "NFL" : league}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw Error(body?.detail || "Live standings are currently unavailable.");
        }
        return response.json();
      })
      .then(setData)
      .catch((err) => setError(err.message));
  }, [league]);

  if (error) return <div className="empty">{error}</div>;
  if (!data) return <div className="empty">Loading standings…</div>;
  const columns: readonly (readonly [string, keyof StandingTeam])[] =
    data.league === "NBA" ? nbaColumns : nflColumns;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">{data.season} {data.league} SEASON</div>
          <h1>League standings.</h1>
          <p>{data.league === "NBA" ? "Conference leaders are highlighted." : "Division leaders are highlighted."} Positions reflect ESPN’s playoff seed when available.</p>
        </div>
      </div>
      <div className="standings-conferences">
        {data.conferences.map((conference) => (
          <section className="standings-conference" key={conference.name}>
            <div className="section-heading">
              <h2>{conference.name}</h2>
              <span>{data.league === "NBA" ? `${conference.name} Conference` : conference.name === "AFC" ? "American Football Conference" : "National Football Conference"}</span>
            </div>
            <div className="standings-divisions">
              {conference.divisions.map((division) => (
                <article className="standings-division" key={division.name}>
                  <h3>{data.league === "NBA" ? `${conference.name} Conference` : `${conference.name} ${division.name}`}</h3>
                  <div className="standings-header">
                    <span>Team</span>
                    {columns.map(([label]) => <span key={label}>{label}</span>)}
                  </div>
                  <div>
                    {division.teams.map((team) => (
                      <Link
                        className={`standing-row${team.division_leader || team.conference_leader ? " division-leader" : ""}`}
                        href={sportRoot ? `${sportRoot}/schedule?team=${team.id}` : `/?view=Schedule&league=${data.league}&team=${team.id}`}
                        key={team.id}
                      >
                        <span className="standing-team">
                          <Crest small team={team} />
                          <span>
                            <strong>{team.city} {team.name}</strong>
                            <small>{team.abbreviation}{(team.division_leader || team.conference_leader) && <><Trophy size={12} /> {data.league === "NBA" ? "Conference leader" : "Division leader"}</>}</small>
                          </span>
                          <ChevronRight size={15} />
                        </span>
                        {columns.map(([label, key]) => (
                          <span data-label={label} key={key}>
                            {key === "playoff_rank" ? team[key] || "—" : team[key]}
                          </span>
                        ))}
                      </Link>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
