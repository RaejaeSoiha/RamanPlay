import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { SPORT_REGISTRY, sportPath, type Sport } from "../../lib/sports/registry";

export const SPORT_LAUNCHER_CARDS = (Object.entries(SPORT_REGISTRY) as Array<[Sport, typeof SPORT_REGISTRY[Sport]]>)
  .map(([sport, entry]) => ({
    sport,
    category: entry.label,
    description: entry.description,
    details: [...entry.details],
    logo: entry.logo,
  }));


export default function SportsLauncher() {
  return (
    <section className="sports-launcher" aria-labelledby="sports-launcher-title">
      <header className="sports-launcher-heading">
        <div className="eyebrow">SPORTS</div>
        <h1 id="sports-launcher-title">Choose your sport.</h1>
        <p>Open a dedicated dashboard for live action, schedules, standings, people, and watch options.</p>
      </header>
      <div className="sports-launcher-grid">
        {SPORT_LAUNCHER_CARDS.map(({ sport, category, description, details, logo }) => {
          return (
            <Link
              aria-label={`Open ${sport} dashboard`}
              className={`sports-launcher-card sports-launcher-${sport.toLowerCase()}`}
              href={sportPath(sport, "Home")}
              key={sport}
            >
              <span className="sports-launcher-brand" aria-hidden="true">
                <span className="sports-launcher-rp">RP</span>
                <span>{sport}</span>
              </span>
              <span className="sports-launcher-icon" aria-hidden="true">
                <img src={logo} alt="" />
              </span>
              <span className="sports-launcher-copy">
                <span className="sports-launcher-category">{category}</span>
                <strong>{sport}</strong>
                <span className="sports-launcher-description">{description}</span>
              </span>
              <span className="sports-launcher-footer">
                <span className="sports-launcher-cta">Open {sport} <ArrowRight size={18} aria-hidden="true" /></span>
                <span className="sports-launcher-details" aria-hidden="true">
                  {details.map((detail) => <span key={detail}>{detail}</span>)}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
