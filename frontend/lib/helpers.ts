import type { Game } from "../types";
export function kickoff(value: string | null, tz: string) {
  if (!value) return "To be announced";
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
    timeZone: tz,
  }).format(new Date(value));
}
export function gameDate(value: string | null, tz: string) {
  if (!value) return "To be announced";
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
    timeZone: tz,
  }).format(new Date(value));
}
export function toggleFavorite(ids: number[], id: number) {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
}
export function favoriteFirst(games: Game[], ids: number[]) {
  return [...games].sort(
    (a, b) =>
      Number(ids.includes(b.away_team.id) || ids.includes(b.home_team.id)) -
        Number(ids.includes(a.away_team.id) || ids.includes(a.home_team.id)) ||
      (a.kickoff_time ? Date.parse(a.kickoff_time) : Infinity) -
        (b.kickoff_time ? Date.parse(b.kickoff_time) : Infinity),
  );
}
export const teamColors: Record<string, string> = {
  DEN: "#fb782f",
  KC: "#e84651",
  BUF: "#448ff8",
  BAL: "#aa81ed",
  GB: "#e9bb43",
  CHI: "#f58c43",
  DAL: "#91afcf",
  PHI: "#5cbfab",
  SF: "#e95858",
  SEA: "#80b751",
  CIN: "#ff793f",
  PIT: "#efc645",
  DET: "#49a9e9",
  LAR: "#f8c949",
};

export function showScores(
  game: Pick<Game, "status" | "away_score" | "home_score">,
) {
  return (
    ["LIVE", "HALFTIME", "FINAL", "POSTPONED"].includes(game.status) &&
    game.away_score !== null &&
    game.home_score !== null
  );
}
export function seasonLabel(
  game: Pick<Game, "season" | "season_type" | "week">,
) {
  const phase =
    {
      PRESEASON: "Preseason",
      REGULAR: "Regular season",
      POSTSEASON: "Postseason",
    }[game.season_type] || "Regular season";
  return `${game.season} · ${phase} · Week ${game.week}`;
}
