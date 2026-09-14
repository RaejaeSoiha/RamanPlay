"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarDays, Play, Radio, Search, ShieldCheck, Star } from "lucide-react";

import { Badge } from "../../../components/shared/SportUI";
import InlineVideoPlayer from "../../../components/player/InlineVideoPlayer";
import { gameDate, kickoff, toggleFavorite } from "../../../lib/helpers";
import { bestMyLink, showWatchLive } from "../../../lib/myLinks";
import { directPlayableKind, directPlayableUrl } from "../../../lib/playback";
import { filterUfcWatchEvents, type UfcWatchPeriod } from "../filters";
import type { MyLink } from "../../../types";

export type Fighter = {
  id: number;
  full_name: string;
  nickname: string;
  record: string;
  weight_class: string;
  headshot_url: string;
  ranking: number | null;
  is_champion: boolean;
};
export type Bout = {
  id: number;
  fighter_a: Fighter;
  fighter_b: Fighter;
  weight_class: string;
  card_section: string;
  scheduled_rounds: number;
  status: string;
  winner_id: number | null;
  result_method: string;
  result_round: number | null;
  finish_time: string;
  is_title_fight: boolean;
  is_interim_title: boolean;
};
export type UfcEvent = {
  id: number;
  league: "UFC";
  name: string;
  event_time: string | null;
  main_card_time: string | null;
  preliminary_card_time: string | null;
  status: string;
  venue: string;
  location: string;
  broadcast_network: string | null;
  bouts: Bout[];
  main_event: Bout | null;
  my_links: MyLink[];
  official_sources?: Array<{ provider_name: string; source_name: string; url: string; access_type: string }>;
};

function FighterFace({ fighter }: { fighter: Fighter }) {
  return <img className="fighter-face" src={fighter.headshot_url} alt="" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />;
}

export default function UfcEvents({ timezone, view = "Schedule", compact = false, initialQuery }: { timezone: string; view?: string; compact?: boolean; initialQuery?: string }) {
  const [events, setEvents] = useState<UfcEvent[]>([]);
  const [query, setQuery] = useState(initialQuery || "");
  const [favorites, setFavorites] = useState<number[]>([]);
  const [error, setError] = useState("");
  const [watchPeriod, setWatchPeriod] = useState<UfcWatchPeriod>("all");
  const [playingEventId, setPlayingEventId] = useState<number | null>(null);
  const watchMode = view === "Watch";

  useEffect(() => {
    try { setFavorites(JSON.parse(localStorage.getItem("ramanplay-ufc-event-favorites") || "[]")); } catch {}
  }, []);
  useEffect(() => { if (initialQuery !== undefined) setQuery(initialQuery); }, [initialQuery]);
  useEffect(() => {
    const timer = setTimeout(() => {
      fetch(`/api/ufc/events?q=${encodeURIComponent(query)}`)
        .then(async (response) => {
          if (!response.ok) throw Error((await response.json().catch(() => ({}))).detail || "UFC events are unavailable.");
          return response.json();
        })
        .then(setEvents)
        .catch((reason) => setError(reason.message));
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);
  function toggle(id: number) {
    setFavorites((current) => {
      const next = toggleFavorite(current, id);
      localStorage.setItem("ramanplay-ufc-event-favorites", JSON.stringify(next));
      return next;
    });
  }
  const viewEvents = events.filter((event) => {
    if (view === "Favorites") return favorites.includes(event.id);
    if (view === "Live") return event.status === "LIVE";
    if (view === "Home") return event.status === "LIVE" || ["SCHEDULED", "PRE_GAME"].includes(event.status);
    return true;
  });
  const visible = (watchMode ? filterUfcWatchEvents(viewEvents, watchPeriod, timezone) : viewEvents).slice(compact ? 6 : undefined);
  const liveCount = viewEvents.filter((event) => event.status === "LIVE").length;
  const upcomingCount = viewEvents.filter((event) => ["SCHEDULED", "PRE_GAME"].includes(event.status)).length;
  const watchOptionCount = viewEvents.filter((event) => event.my_links.some((link) => link.enabled) || Boolean(event.broadcast_network) || (event.official_sources?.length ?? 0) > 0).length;
  if (compact) return <section className="ufc-compact-section">
    <div className="section-heading"><h2>{view === "Favorites" ? "Your UFC favorites" : view === "Live" ? "UFC live now" : view === "Search" ? "UFC search results" : "UFC live & upcoming"}</h2><Link className="text-button" href={view === "Favorites" ? "/sports/ufc/favorites" : view === "Search" ? "/sports/ufc/search" : "/sports/ufc/schedule"}>{view === "Search" ? "UFC search" : "UFC schedule"}</Link></div>
    {error && <div className="error">{error}</div>}
    {!error && visible.length === 0 ? <div className="empty compact">{view === "Favorites" ? "No UFC favorites yet." : "No UFC events are live or upcoming."}</div> : <div className="ufc-event-grid">{visible.map((event) => <UfcCard event={event} favorites={favorites} timezone={timezone} toggle={toggle} playing={playingEventId === event.id} setPlaying={setPlayingEventId} key={event.id} />)}</div>}
  </section>;
  return (
    <>
      <div className="page-heading">
        <div><div className="eyebrow">UFC · MMA</div><h1>{watchMode ? "Watch UFC" : view === "Favorites" ? "Your UFC events." : "Fight night."}</h1><p>{watchMode ? "Find a UFC event and see your watch options." : "Cards, results, official provider details, and your personal watch links."}</p></div>
      </div>
      {watchMode && <>
        <div className="summary-strip ufc-watch-summary">
          <div><Radio size={19} /><strong>{liveCount}</strong><span>live events</span></div>
          <div><CalendarDays size={19} /><strong>{upcomingCount}</strong><span>upcoming events</span></div>
          <div><ShieldCheck size={19} /><strong>{watchOptionCount}</strong><span>available watch options</span></div>
        </div>
        <div className="filter-row ufc-watch-filters"><div className="tabs">{([['all', 'All events'], ['live', 'Live'], ['today', 'Today'], ['tomorrow', 'Tomorrow'], ['week', 'This week'], ['weekend', 'This weekend']] as const).map(([period, label]) => <button className={watchPeriod === period ? "active" : ""} key={period} onClick={() => setWatchPeriod(period)}>{label}</button>)}</div></div>
      </>}
      {initialQuery === undefined && <div className="search-row">
        <div className="search-box"><Search size={19} /><input aria-label="Search UFC" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={watchMode ? "Search UFC events or fighters" : "Search fighters, events, or weight class"} /></div>
      </div>}
      {error && <div className="error">{error}</div>}
      <div className="ufc-event-grid">
        {visible.map((event) => <UfcCard event={event} favorites={favorites} timezone={timezone} toggle={toggle} playing={playingEventId === event.id} setPlaying={setPlayingEventId} key={event.id} />)}
      </div>
      {!error && visible.length === 0 && <div className="empty"><Search size={30} /><h2>{watchMode ? "No UFC events found." : "No UFC events match this view."}</h2>{watchMode && <p>Try another date or view upcoming UFC events.</p>}</div>}
    </>
  );
}

function UfcCard({ event, favorites, timezone, toggle, playing, setPlaying }: { event: UfcEvent; favorites: number[]; timezone: string; toggle: (id: number) => void; playing: boolean; setPlaying: (id: number | null) => void }) {
  const main = event.main_event;
  const live = event.status === "LIVE";
  const playableUrl = directPlayableUrl(bestMyLink(event.my_links));
  return <article className={`ufc-event-card${live ? " active-game" : ""}`}>
    <div className="card-top"><span className={live ? "live-label" : "muted"}>{live ? "● LIVE NOW" : event.status === "FINAL" ? "FINAL" : kickoff(event.main_card_time || event.event_time, timezone)}</span><Badge>{event.league}</Badge></div>
    {playing && playableUrl ? <><InlineVideoPlayer sourceUrl={playableUrl} sourceType={directPlayableKind(bestMyLink(event.my_links))!} title={event.name} isLive={live} onClose={() => setPlaying(null)} onOpenWatchOptions={() => setPlaying(null)} /><div className="inline-player-summary"><span>{main ? `${main.fighter_a.full_name} vs ${main.fighter_b.full_name}` : event.name} · {event.status}</span><Link href={`/ufc/event/${event.id}`}>Fight card</Link></div></> : <><Link className="ufc-event-main" href={`/ufc/event/${event.id}`}><strong>{event.name}</strong>{main && <div className="ufc-matchup"><FighterFace fighter={main.fighter_a} /><span>{main.fighter_a.full_name}<b>vs</b>{main.fighter_b.full_name}</span><FighterFace fighter={main.fighter_b} /></div>}<small>{main ? `${main.card_section.replaceAll("_", " ")} · ${main.weight_class}` : "Fight card pending"}</small></Link><div className="card-meta"><span><CalendarDays size={14} /> {gameDate(event.event_time, timezone)}<br />{event.venue}{event.location && ` · ${event.location}`}</span><button className={`icon-button ${favorites.includes(event.id) ? "selected" : ""}`} onClick={() => toggle(event.id)} aria-label={`Favorite ${event.name}`}><Star size={17} fill={favorites.includes(event.id) ? "currentColor" : "none"} /></button></div><div className="card-bottom"><Badge kind={event.my_links.some((link) => link.enabled) ? "free" : "official"}>{event.my_links.some((link) => link.enabled) ? "MY LINK READY" : event.broadcast_network || "WATCH OPTIONS"}</Badge>{showWatchLive({ status: event.status, my_links: event.my_links }) && (playableUrl ? <button className="card-live-watch" onClick={() => setPlaying(event.id)}><Play size={13} /> WATCH LIVE</button> : <Link className="card-live-watch" href={`/ufc/event/${event.id}?watch=best`}><Play size={13} /> WATCH LIVE</Link>)}<Link href={`/ufc/event/${event.id}`}>Fight card</Link></div></>}
  </article>;
}
