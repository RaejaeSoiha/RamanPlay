"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, CalendarDays, Trophy } from "lucide-react";

import { recapEndpoint, recapRoute, recapsEndpoint, type RecapSport } from "../../lib/recaps";
import type { Recap } from "../../types";

function RecapCard({ recap }: { recap: Recap }) {
  const route = recapRoute(recap.league, recap.event_id);
  return (
    <Link href={route} className="recap-card" aria-label={`View recap for ${recap.title}`}>
      <span className="recap-card-top"><span className={`news-sport-badge news-badge-${recap.league.toLowerCase()}`}>{recap.league}</span><span>FINAL</span></span>
      <strong>{recap.final_score || recap.title}</strong>
      {recap.winner && recap.loser ? <span className="recap-result"><Trophy size={14} /> {recap.winner.name} def. {recap.loser.name}</span> : null}
      {recap.summary_facts.filter((fact) => fact !== recap.final_score && !fact.startsWith("Final score:")).slice(0, 2).map((fact) => <span className="recap-fact" key={fact}>{fact}</span>)}
      <span className="recap-card-link">View recap <ArrowUpRight size={15} aria-hidden="true" /></span>
    </Link>
  );
}

function RecapDetail({ recap }: { recap: Recap }) {
  const hasResult = recap.winner && recap.loser;
  return <section className="recap-detail" aria-labelledby="recap-detail-title">
    <div className="section-heading"><h2 id="recap-detail-title">Final recap</h2><span>{recap.source_name} provider data</span></div>
    <div className="recap-detail-grid">
      <div className="recap-detail-result">
        <span className="news-sport-badge">FINAL</span>
        <strong>{recap.final_score || recap.title}</strong>
        {hasResult ? <span><Trophy size={15} /> {recap.winner!.name} def. {recap.loser!.name}</span> : null}
        {recap.venue ? <small>{recap.venue}{recap.broadcast_network ? ` · ${recap.broadcast_network}` : ""}</small> : null}
      </div>
      {recap.bouts.length ? <div className="recap-bouts">
        <strong>Completed bouts</strong>
        {recap.bouts.map((bout) => <span key={bout.id}><b>{bout.winner && bout.loser ? `${bout.winner.name} def. ${bout.loser.name}` : bout.weight_class || "Result reported"}</b>{[bout.weight_class, bout.result_method, bout.result_round ? `Round ${bout.result_round}` : "", bout.finish_time].filter(Boolean).join(" · ")}</span>)}
      </div> : null}
      {recap.next_related.length ? <div className="recap-next">
        <strong>What’s next</strong>
        {recap.next_related.map((next) => <Link href={next.route} key={`${next.participant_id || "event"}-${next.event_id}`}><CalendarDays size={14} /> {next.label}</Link>)}
      </div> : null}
    </div>
  </section>;
}

export default function RecapSection({ sport = "ALL", limit = 5, detailId }: { sport?: RecapSport; limit?: number; detailId?: number }) {
  const [recaps, setRecaps] = useState<Recap[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    const endpoint = detailId ? recapEndpoint(sport as Exclude<RecapSport, "ALL">, detailId) : recapsEndpoint(sport, limit);
    fetch(endpoint)
      .then(async (response) => {
        if (response.status === 404 && detailId) return null;
        if (!response.ok) throw Error("Recaps are unavailable.");
        return response.json();
      })
      .then((data) => {
        if (!active) return;
        const rows = detailId ? (data ? [data] : []) : data as Recap[];
        setRecaps(rows);
        setState(rows.length ? "ready" : "empty");
      })
      .catch(() => active && setState("error"));
    return () => { active = false; };
  }, [sport, limit, detailId]);

  if (detailId) {
    if (state === "loading") return <section className="recap-detail recap-loading" aria-label="Loading final recap" />;
    if (state !== "ready") return null;
    return <RecapDetail recap={recaps[0]} />;
  }
  const title = sport === "ALL" ? "Recent results" : `${sport} results`;
  return <section className="recap-section" aria-labelledby={`recap-section-${sport.toLowerCase()}`}>
    <div className="section-heading"><h2 id={`recap-section-${sport.toLowerCase()}`}>{title}</h2><span>Completed games and events</span></div>
    {state === "loading" ? <div className="recap-grid recap-skeletons" aria-label="Loading recent results">{Array.from({ length: Math.min(limit, 3) }, (_, index) => <span className="recap-skeleton" key={index} />)}</div> : null}
    {state === "ready" ? <div className="recap-grid">{recaps.map((recap) => <RecapCard recap={recap} key={recap.id} />)}</div> : null}
    {state === "empty" ? <div className="empty compact">No completed {sport === "ALL" ? "games or events" : sport + " results"} are available yet.</div> : null}
    {state === "error" ? <div className="notice recap-unavailable">Recent results are temporarily unavailable. Schedules and live scores are still available.</div> : null}
  </section>;
}
