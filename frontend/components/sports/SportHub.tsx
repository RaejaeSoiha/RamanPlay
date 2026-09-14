import Link from "next/link";
import { ArrowUpRight, Dumbbell, Radio, Shield, Trophy } from "lucide-react";

import { sportPath, type Sport } from "../../lib/sportRoutes";

type SportCard = {
  name: Sport;
  label: string;
  description: string;
  entry: string;
  links: { label: string; view: string }[];
};

const sports: SportCard[] = [
  {
    name: "NFL",
    label: "Football",
    description: "Games, live scores, teams, standings, players, and watch options.",
    entry: "Home",
    links: [
      { label: "Live", view: "Live" },
      { label: "Schedule", view: "Schedule" },
      { label: "Teams", view: "Teams" },
      { label: "Standings", view: "Standings" },
      { label: "Favorites", view: "Favorites" },
      { label: "Watch", view: "Watch" },
      { label: "Players", view: "Players" },
    ],
  },
  {
    name: "NBA",
    label: "Basketball",
    description: "Games, live scores, teams, standings, players, and watch options.",
    entry: "Home",
    links: [
      { label: "Live", view: "Live" },
      { label: "Schedule", view: "Schedule" },
      { label: "Teams", view: "Teams" },
      { label: "Standings", view: "Standings" },
      { label: "Favorites", view: "Favorites" },
      { label: "Watch", view: "Watch" },
      { label: "Players", view: "Players" },
    ],
  },
  {
    name: "UFC",
    label: "Mixed martial arts",
    description: "Fight cards, live events, fighters, rankings, and watch options.",
    entry: "Home",
    links: [
      { label: "Live", view: "Live" },
      { label: "Schedule", view: "Schedule" },
      { label: "Fighters", view: "Fighters" },
      { label: "Rankings", view: "Rankings" },
      { label: "Favorites", view: "Favorites" },
      { label: "Watch", view: "Watch" },
    ],
  },
];

const icons = { NFL: Shield, NBA: Trophy, UFC: Dumbbell };

export default function SportHub({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`sport-hub ${compact ? "sport-hub-compact" : ""}`} aria-label="Browse sports">
      <div className="sport-hub-heading">
        <div>
          <div className="eyebrow">SPORTS HUB</div>
          <h2>{compact ? "Pick your sport." : "Every sport has its place."}</h2>
          <p>{compact ? "Jump into NFL, NBA, or UFC without mixing schedules and player pages." : "Open a dedicated section for schedules, live action, standings, players or fighters, and watch options."}</p>
        </div>
        <Radio size={23} aria-hidden="true" />
      </div>
      <div className="sport-hub-grid">
        {sports.map(({ name, label, description, entry, links }) => {
          const Icon = icons[name];
          return (
            <article className={`sport-hub-card sport-hub-${name.toLowerCase()}`} key={name}>
              <Link className="sport-hub-main" href={sportPath(name, entry)}>
                <span className="sport-hub-icon"><Icon size={23} /></span>
                <span className="sport-hub-copy">
                  <small>{label}</small>
                  <strong>{name}</strong>
                  <span>{description}</span>
                </span>
                <ArrowUpRight size={18} aria-hidden="true" />
              </Link>
              <nav className="sport-hub-links" aria-label={`${name} destinations`}>
                {links.map(({ label: linkLabel, view }) => (
                  <Link href={sportPath(name, view)} key={linkLabel}>{linkLabel}</Link>
                ))}
              </nav>
            </article>
          );
        })}
      </div>
    </section>
  );
}
