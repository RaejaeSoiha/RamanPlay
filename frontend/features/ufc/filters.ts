export type UfcWatchEvent = { event_time: string | null; status: string };
export type UfcWatchPeriod = "all" | "live" | "today" | "tomorrow" | "week" | "weekend";

function parts(value: Date, timezone: string) {
  return Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  }).formatToParts(value).filter(({ type }) => type !== "literal").map(({ type, value }) => [type, value]));
}

function dayKey(value: Date, timezone: string) {
  const current = parts(value, timezone);
  return `${current.year}-${current.month}-${current.day}`;
}

export function filterUfcWatchEvents<T extends UfcWatchEvent>(events: T[], period: UfcWatchPeriod, timezone: string, now = new Date()) {
  if (period === "all") return events;
  if (period === "live") return events.filter((event) => event.status === "LIVE");
  const today = dayKey(now, timezone);
  const tomorrow = dayKey(new Date(now.getTime() + 86_400_000), timezone);
  return events.filter((event) => {
    if (!event.event_time) return false;
    const eventTime = new Date(event.event_time);
    const date = dayKey(eventTime, timezone);
    if (period === "today") return date === today;
    if (period === "tomorrow") return date === tomorrow;
    const daysAway = Math.round((Date.parse(date + "T00:00:00Z") - Date.parse(today + "T00:00:00Z")) / 86_400_000);
    if (period === "week") return daysAway >= 0 && daysAway <= 6;
    return daysAway >= 0 && daysAway <= 6 && ["Sat", "Sun"].includes(parts(eventTime, timezone).weekday);
  });
}
