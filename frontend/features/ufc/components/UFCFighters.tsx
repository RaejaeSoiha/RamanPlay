"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, Star } from "lucide-react";

import type { Fighter } from "./UFCEvents";
import { toggleFavorite } from "../../../lib/helpers";

export default function UfcFighters({
  rankings = false,
  initialQuery,
  compact = false,
  favoritesOnly = false,
}: {
  rankings?: boolean;
  initialQuery?: string;
  compact?: boolean;
  favoritesOnly?: boolean;
}) {
  const [fighters, setFighters] = useState<Fighter[]>([]);
  const [query, setQuery] = useState(initialQuery || "");
  const [favorites, setFavorites] = useState<number[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    try { setFavorites(JSON.parse(localStorage.getItem("ramanplay-ufc-fighter-favorites") || "[]")); } catch {}
  }, []);
  useEffect(() => { if (initialQuery !== undefined) setQuery(initialQuery); }, [initialQuery]);
  useEffect(() => {
    const timer = setTimeout(() => {
      fetch(`/api/ufc/fighters?q=${encodeURIComponent(query)}`)
        .then(async (response) => {
          if (!response.ok) throw Error("UFC fighters are unavailable.");
          return response.json();
        })
        .then((rows: Fighter[]) => setFighters(rows.filter((fighter) => !rankings || fighter.ranking !== null || fighter.is_champion)))
        .catch((reason) => setError(reason.message));
    }, 200);
    return () => clearTimeout(timer);
  }, [query, rankings]);
  function toggle(id: number) {
    setFavorites((current) => {
      const next = toggleFavorite(current, id);
      localStorage.setItem("ramanplay-ufc-fighter-favorites", JSON.stringify(next));
      return next;
    });
  }
  const visible = fighters.filter((fighter) => !favoritesOnly || favorites.includes(fighter.id)).slice(compact ? 6 : undefined);
  return <>
    {compact && favoritesOnly && <div className="section-heading"><h2>Your UFC fighters</h2></div>}
    {!compact && <div className="page-heading"><div><div className="eyebrow">UFC · MMA</div><h1>{rankings ? "Rankings." : favoritesOnly ? "Your UFC fighters." : "Fighters."}</h1><p>{rankings ? "Rankings and champions appear only when supplied by the provider." : "Browse UFC fighters and keep your favorites close."}</p></div></div>}
    {!rankings && initialQuery === undefined && <div className="search-row"><div className="search-box"><Search size={19} /><input aria-label="Search UFC fighters" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search UFC fighters" /></div></div>}
    {error && <div className="error">{error}</div>}
    {rankings && !error && visible.length === 0 ? <div className="empty">Live UFC rankings are not available from the current provider feed.</div> : <div className="fighter-grid">
      {visible.map((fighter) => <article className="fighter-card" key={fighter.id}>
        {fighter.headshot_url && <img src={fighter.headshot_url} alt="" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />}
        <div><small>{fighter.is_champion ? "CHAMPION" : fighter.ranking ? `#${fighter.ranking}` : fighter.weight_class}</small><Link href={`/ufc/fighter/${fighter.id}`}><h2>{fighter.full_name}</h2></Link><p>{fighter.nickname && `“${fighter.nickname}” · `}{fighter.record || "Record unavailable"}</p></div>
        {!rankings && <button className={`icon-button ${favorites.includes(fighter.id) ? "selected" : ""}`} onClick={() => toggle(fighter.id)} aria-label={`Favorite ${fighter.full_name}`}><Star fill={favorites.includes(fighter.id) ? "currentColor" : "none"} /></button>}
      </article>)}
    </div>}
    {favoritesOnly && !error && visible.length === 0 && <div className="empty compact">No UFC fighter favorites yet.</div>}
  </>;
}
