import { describe, it, expect } from "vitest";
import {
  kickoff,
  gameDate,
  toggleFavorite,
  favoriteFirst,
} from "../../frontend/lib/helpers";
import type { Game } from "../../frontend/types";
describe("local preferences and schedule", () => {
  it("adds and removes a favorite without mutation", () => {
    const ids = [1];
    expect(toggleFavorite(ids, 2)).toEqual([1, 2]);
    expect(toggleFavorite(ids, 1)).toEqual([]);
    expect(ids).toEqual([1]);
  });
  it("converts kickoff across midnight", () => {
    expect(gameDate("2026-09-14T01:00:00Z", "America/Denver")).toContain(
      "Sep 13",
    );
    expect(kickoff("2026-09-14T01:00:00Z", "America/Denver")).toContain("7:00");
  });
  it("handles daylight saving", () => {
    expect(kickoff("2026-12-01T02:00:00Z", "America/Denver")).toContain("7:00");
    expect(kickoff("2026-09-01T02:00:00Z", "America/Denver")).toContain("8:00");
  });
  it("pins favorite games then orders chronologically", () => {
    const a = {
      id: 1,
      away_team: { id: 1 },
      home_team: { id: 2 },
      kickoff_time: "2026-09-01",
    } as Game;
    const b = {
      id: 2,
      away_team: { id: 3 },
      home_team: { id: 4 },
      kickoff_time: "2026-09-02",
    } as Game;
    expect(favoriteFirst([a, b], [4]).map((g) => g.id)).toEqual([2, 1]);
  });
});

import { showScores, seasonLabel } from "../../frontend/lib/helpers";
it("never shows placeholder scores for upcoming games", () => {
  expect(
    showScores({ status: "SCHEDULED", away_score: 0, home_score: 0 }),
  ).toBe(false);
  expect(showScores({ status: "FINAL", away_score: 0, home_score: 17 })).toBe(
    true,
  );
  expect(showScores({ status: "LIVE", away_score: 0, home_score: null })).toBe(
    false,
  );
});
it.each(["PRESEASON", "REGULAR", "POSTSEASON"] as const)(
  "labels season phase %s",
  (phase) => {
    expect(
      seasonLabel({ season: 2027, season_type: phase, week: 1 }),
    ).toContain("2027");
    expect(
      seasonLabel({ season: 2027, season_type: phase, week: 1 }),
    ).toContain("Week 1");
  },
);
it.each([
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  Intl.DateTimeFormat().resolvedOptions().timeZone,
])("formats a UTC kickoff in %s", (tz) => {
  expect(kickoff("2026-09-14T01:00:00Z", tz)).not.toContain("Invalid");
  expect(gameDate("2026-09-14T01:00:00Z", tz)).toContain("Sep");
});
