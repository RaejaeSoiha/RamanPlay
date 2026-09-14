import Link from "next/link";
import { ArrowRight, CalendarDays, Radio, ShieldCheck } from "lucide-react";

import { SPORT_REGISTRY, sportPath, type Sport } from "../../lib/sports/registry";

const sports = (Object.entries(SPORT_REGISTRY) as Array<[Sport, typeof SPORT_REGISTRY[Sport]]>)
  .map(([sport, entry]) => ({ sport, label: entry.label, logo: entry.logo }));

export default function HomeHero({
  liveCount,
  upcomingCount,
  freeCount,
  lastUpdated,
}: {
  liveCount: number;
  upcomingCount: number;
  freeCount: number;
  lastUpdated: string;
}) {
  return (
    <section className="home-hero" aria-labelledby="home-hero-title">
      <div className="home-hero-copy">
        <div className="eyebrow">RAMANPLAY</div>
        <h1 id="home-hero-title">All your games.<br />One place.</h1>
        <p>Follow live action, find your teams, and choose where to watch across NFL, NBA, and UFC.</p>
        <div className="home-hero-actions">
          <Link className="primary-button" href="/sports">Browse sports <ArrowRight size={16} /></Link>
          <Link className="secondary-button" href="/live"><Radio size={16} /> Live now</Link>
        </div>
      </div>
      <div className="home-hero-stats" aria-label="Game overview">
        <Link href="/live"><Radio size={18} /><strong>{liveCount}</strong><span>live now</span></Link>
        <Link href="/schedule"><CalendarDays size={18} /><strong>{upcomingCount}</strong><span>upcoming</span></Link>
        <Link href="/watch"><ShieldCheck size={18} /><strong>{freeCount}</strong><span>free options</span></Link>
        <small>Updated {lastUpdated || "—"}</small>
      </div>
      <nav className="home-sport-launcher" aria-label="Open a sport">
        {sports.map(({ sport, label, logo }) => (
          <Link href={sportPath(sport, "Home")} key={sport} className={`home-sport-card home-sport-${sport.toLowerCase()}`}>
            <img src={logo} alt="" />
            <span><small>{label}</small><strong>{sport}</strong></span>
            <ArrowRight size={17} aria-hidden="true" />
          </Link>
        ))}
      </nav>
    </section>
  );
}
