export type RecapSport = "ALL" | "NFL" | "NBA" | "UFC";

export function recapsEndpoint(sport: RecapSport, limit = 5) {
  return `/api/recaps?sport=${sport}&limit=${limit}`;
}

export function recapEndpoint(sport: Exclude<RecapSport, "ALL">, eventId: number | string) {
  return `/api/recaps/${sport}/${eventId}`;
}

export function recapRoute(sport: Exclude<RecapSport, "ALL">, eventId: number) {
  return sport === "UFC" ? `/ufc/event/${eventId}` : `/game/${eventId}`;
}
