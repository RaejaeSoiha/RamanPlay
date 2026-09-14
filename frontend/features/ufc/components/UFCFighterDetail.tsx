"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Star } from "lucide-react";

import type { Fighter } from "./UFCEvents";

export default function UfcFighterDetail({ fighterId }: { fighterId: string }) {
  const [fighter, setFighter] = useState<(Fighter & { country: string; bouts: Array<{ id: number; weight_class: string; status: string; fighter_a: Fighter; fighter_b: Fighter; winner_id: number | null }> }) | null>(null);
  const [favorite, setFavorite] = useState(false);
  useEffect(() => {
    fetch(`/api/ufc/fighters/${fighterId}`).then((response) => response.ok ? response.json() : Promise.reject()).then(setFighter).catch(() => setFighter(null));
    try { setFavorite(JSON.parse(localStorage.getItem("ramanplay-ufc-fighter-favorites") || "[]").includes(Number(fighterId))); } catch {}
  }, [fighterId]);
  if (!fighter) return <div className="app-shell"><div className="main-shell"><main><div className="empty">Loading fighter…</div></main></div></div>;
  function toggle() {
    const current = JSON.parse(localStorage.getItem("ramanplay-ufc-fighter-favorites") || "[]") as number[];
    const next = favorite ? current.filter((id) => id !== fighter.id) : [...current, fighter.id];
    localStorage.setItem("ramanplay-ufc-fighter-favorites", JSON.stringify(next));
    setFavorite(!favorite);
  }
  return <div className="app-shell"><div className="main-shell"><main><Link className="back-link" href="/?league=UFC"><ArrowLeft size={16} /> Back to UFC</Link><section className="fighter-profile"><img src={fighter.headshot_url} alt="" /><div><div className="eyebrow">UFC FIGHTER</div><h1>{fighter.full_name}</h1><p>{fighter.nickname && `“${fighter.nickname}” · `}{fighter.weight_class} · {fighter.country || "Country unavailable"}</p><strong>{fighter.record || "Record unavailable"}</strong>{fighter.ranking && <span> · Ranked #{fighter.ranking}</span>}<button className="text-button" onClick={toggle}><Star size={16} fill={favorite ? "currentColor" : "none"} /> {favorite ? "Following" : "Follow fighter"}</button></div></section><div className="section-heading"><h2>Recent fights</h2></div><div className="fight-section">{fighter.bouts.map((bout) => <div className="fight-row" key={bout.id}><strong>{bout.fighter_a.full_name} vs {bout.fighter_b.full_name}</strong><small>{bout.weight_class} · {bout.status}</small></div>)}</div></main></div></div>;
}
