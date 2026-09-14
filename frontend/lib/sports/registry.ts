export const SPORT_REGISTRY = {
  NFL: {
    segment: "nfl",
    label: "Football",
    logo: "/images/sports/nfl-official.png",
    description: "Games, live scores, teams, standings, players, and watch options.",
    details: ["32 teams", "Live games", "Season coverage"],
    capabilities: { teams: true, standings: true, players: true, fighters: false, rankings: false },
    views: { Home: "", Games: "", Live: "live", Schedule: "schedule", Teams: "teams", Standings: "standings", Favorites: "favorites", Watch: "watch", Players: "players", Search: "search" },
  },
  NBA: {
    segment: "nba",
    label: "Basketball",
    logo: "/images/sports/nba-official.png",
    description: "Games, live scores, teams, standings, players, and watch options.",
    details: ["30 teams", "Live games", "Season coverage"],
    capabilities: { teams: true, standings: true, players: true, fighters: false, rankings: false },
    views: { Home: "", Games: "", Live: "live", Schedule: "schedule", Teams: "teams", Standings: "standings", Favorites: "favorites", Watch: "watch", Players: "players", Search: "search" },
  },
  UFC: {
    segment: "ufc",
    label: "Mixed martial arts",
    logo: "/images/sports/ufc-official.png",
    description: "Fight cards, live events, fighters, rankings, and watch options.",
    details: ["Fight cards", "Rankings", "Fighters"],
    capabilities: { teams: false, standings: false, players: false, fighters: true, rankings: true },
    views: { Home: "", Events: "", Live: "live", Schedule: "schedule", Fighters: "fighters", Rankings: "rankings", Favorites: "favorites", Watch: "watch", Search: "search" },
  },
} as const;

export type Sport = keyof typeof SPORT_REGISTRY;

export function sportPath(sport: Sport, view: string = "Home") {
  const entry = SPORT_REGISTRY[sport];
  const segment = (entry.views as Record<string, string>)[view] ?? "";
  return `/sports/${entry.segment}${segment ? `/${segment}` : ""}`;
}

export function sportFromSegment(segment: string): Sport | null {
  const matched = (Object.entries(SPORT_REGISTRY) as Array<[Sport, typeof SPORT_REGISTRY[Sport]]>)
    .find(([, entry]) => entry.segment === segment.toLowerCase());
  return matched?.[0] ?? null;
}

export function sportView(sport: Sport, segment?: string): string {
  const normalized = (segment || "").toLowerCase();
  const found = Object.entries(SPORT_REGISTRY[sport].views).find(([, path]) => path === normalized);
  return found?.[0] ?? "Home";
}

export function globalPath(view: string): string {
  return ({ Home: "/", Sports: "/sports", Live: "/live", Schedule: "/schedule", Favorites: "/favorites", Watch: "/watch", Search: "/search" } as Record<string, string>)[view] || "/";
}

export function isPrimaryNavActive(label: string, view: string, sportSection: boolean) {
  return sportSection ? label === "Sports" : label === view;
}
