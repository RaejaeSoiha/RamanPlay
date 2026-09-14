import type { NewsStory } from "../types";

export type NewsSport = "ALL" | "NFL" | "NBA" | "UFC";

export function newsEndpoint(sport: NewsSport, limit = 6) {
  return `/api/news?sport=${sport}&limit=${limit}`;
}

export function relativeNewsTime(value: string, now = Date.now()) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return "Recently";
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 172800) return "Yesterday";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(timestamp);
}

export function storySportClass(story: Pick<NewsStory, "league">) {
  return `news-badge-${story.league.toLowerCase()}`;
}
