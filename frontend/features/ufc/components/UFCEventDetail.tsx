"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Play, Trophy } from "lucide-react";
import MyLinks from "../../../components/watch/MyLinks";
import { Badge } from "../../../components/shared/SportUI";
import { gameDate, kickoff } from "../../../lib/helpers";
import { showWatchLive } from "../../../lib/myLinks";
import type { Bout, UfcEvent } from "./UFCEvents";

const sections = ["MAIN_EVENT", "MAIN_CARD", "PRELIMINARY_CARD", "EARLY_PRELIMS"];

function FighterLine({ fighter, winner }: { fighter: Bout["fighter_a"]; winner: boolean }) {
  return <Link className={winner ? "fight-fighter winner" : "fight-fighter"} href={`/ufc/fighter/${fighter.id}`}>
    <img src={fighter.headshot_url} alt="" />
    <span><strong>{fighter.full_name}</strong><small>{fighter.record || "Record unavailable"}{fighter.ranking ? ` · #${fighter.ranking}` : ""}</small></span>
    {winner && <Trophy size={14} />}
  </Link>;
}

export default function UfcEventDetail({ eventId }: { eventId: string }) {
  const [event, setEvent] = useState<UfcEvent | null>(null);
  const [error, setError] = useState("");
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  useEffect(() => {
    fetch(`/api/ufc/events/${eventId}`).then(async (response) => {
      if (!response.ok) throw Error("UFC event is unavailable.");
      return response.json();
    }).then(setEvent).catch((reason) => setError(reason.message));
  }, [eventId]);
  if (error) return <div className="error">{error}</div>;
  if (!event) return <div className="empty">Loading UFC event…</div>;
  const live = event.status === "LIVE";
  return <>
    <Link className="back-link" href="/sports/ufc"><ArrowLeft size={16} /> Back to UFC</Link>
    <div className="page-heading"><div><div className="eyebrow">UFC · MMA EVENT</div><h1>{event.name}</h1><p>{gameDate(event.event_time, timezone)} · {kickoff(event.main_card_time || event.event_time, timezone)} · {event.venue}{event.location && `, ${event.location}`}</p></div><Badge kind={live ? "live" : ""}>{live ? "LIVE NOW" : event.status}</Badge></div>
    {event.broadcast_network && <p className="muted">Broadcast: {event.broadcast_network}</p>}
    {live && showWatchLive({ status: event.status, my_links: event.my_links }) && <Link className="primary-button" href="?watch=best"><Play size={15} /> WATCH LIVE</Link>}
    <MyLinks collectionPath={`/api/ufc/events/${event.id}/my-links`} links={event.my_links} officialSources={event.official_sources} live={live} />
    {sections.map((section) => {
      const bouts = event.bouts.filter((bout) => bout.card_section === section);
      if (!bouts.length) return null;
      return <section className="fight-section" key={section}>
        <div className="section-heading"><h2>{section.replaceAll("_", " ")}</h2></div>
        {bouts.map((bout) => <article className="fight-row" key={bout.id}>
          <div className="fight-title"><Badge>{bout.weight_class || "MMA"}</Badge>{bout.is_title_fight && <Badge kind="live">TITLE</Badge>}<span>{bout.status} · {bout.scheduled_rounds} rounds</span></div>
          <div className="fight-pair"><FighterLine fighter={bout.fighter_a} winner={bout.winner_id === bout.fighter_a.id} /><b>vs</b><FighterLine fighter={bout.fighter_b} winner={bout.winner_id === bout.fighter_b.id} /></div>
          {bout.status === "FINAL" && <small>{bout.result_method || "Result reported"}{bout.result_round && ` · Round ${bout.result_round}`}{bout.finish_time && ` · ${bout.finish_time}`}</small>}
        </article>)}
      </section>;
    })}
  </>;
}
