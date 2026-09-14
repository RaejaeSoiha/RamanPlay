import { describe, expect, it } from "vitest";
import { filterUfcWatchEvents } from "../../frontend/lib/ufcWatch";

const now = new Date("2026-09-14T15:00:00Z");
const events = [
  { event_time: "2026-09-14T20:00:00Z", status: "SCHEDULED" },
  { event_time: "2026-09-15T20:00:00Z", status: "LIVE" },
  { event_time: "2026-09-19T20:00:00Z", status: "SCHEDULED" },
  { event_time: "2026-09-26T20:00:00Z", status: "SCHEDULED" },
];

describe("UFC Watch filters", () => {
  it("keeps UFC live events isolated", () => {
    expect(filterUfcWatchEvents(events, "live", "UTC", now)).toEqual([events[1]]);
  });

  it("filters today, tomorrow, week, and weekend by local date", () => {
    expect(filterUfcWatchEvents(events, "today", "UTC", now)).toEqual([events[0]]);
    expect(filterUfcWatchEvents(events, "tomorrow", "UTC", now)).toEqual([events[1]]);
    expect(filterUfcWatchEvents(events, "week", "UTC", now)).toEqual(events.slice(0, 3));
    expect(filterUfcWatchEvents(events, "weekend", "UTC", now)).toEqual([events[2]]);
  });
});
