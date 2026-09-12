import type { Game, MyLink } from "../types";

const statusRank: Record<MyLink["status"], number> = {
  ONLINE: 0,
  REDIRECT: 1,
  WARNING: 2,
  UNKNOWN: 3,
  OFFLINE: 4,
  BLOCKED: 5,
};

export function sortMyLinks(links: MyLink[]) {
  return [...links].sort(
    (a, b) =>
      Number(!a.enabled) - Number(!b.enabled) ||
      statusRank[a.status] - statusRank[b.status] ||
      b.reliability_score - a.reliability_score ||
      a.priority - b.priority ||
      a.id - b.id,
  );
}

export function bestMyLink(links: MyLink[]) {
  return sortMyLinks(links.filter((link) => link.enabled))[0] ?? null;
}

export function cleanOpenAction(link: MyLink | null) {
  if (
    !link ||
    !link.enabled ||
    !["ONLINE", "REDIRECT", "WARNING"].includes(link.status) ||
    !link.final_url
  ) {
    return "blocked" as const;
  }
  return link.status === "WARNING" ? ("confirm" as const) : ("navigate" as const);
}

export function showWatchLive(game: Pick<Game, "status" | "my_links">) {
  return game.status === "LIVE" && game.my_links.some((link) => link.enabled);
}
