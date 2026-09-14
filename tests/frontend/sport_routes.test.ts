import { describe, expect, it } from "vitest";
import { globalPath, isPrimaryNavActive, sportFromSegment, sportPath, sportView } from "../../frontend/lib/sportRoutes";

describe("sport routes", () => {
  it("maps each supported sport to an isolated route", () => {
    expect(sportPath("NFL", "Home")).toBe("/sports/nfl");
    expect(sportPath("NFL", "Live")).toBe("/sports/nfl/live");
    expect(sportPath("NFL", "Schedule")).toBe("/sports/nfl/schedule");
    expect(sportPath("NFL", "Standings")).toBe("/sports/nfl/standings");
    expect(sportPath("NFL", "Favorites")).toBe("/sports/nfl/favorites");
    expect(sportPath("NFL", "Watch")).toBe("/sports/nfl/watch");
    expect(sportPath("NFL", "Players")).toBe("/sports/nfl/players");
    expect(sportPath("NBA", "Live")).toBe("/sports/nba/live");
    expect(sportPath("NBA", "Schedule")).toBe("/sports/nba/schedule");
    expect(sportPath("NBA", "Standings")).toBe("/sports/nba/standings");
    expect(sportPath("NBA", "Favorites")).toBe("/sports/nba/favorites");
    expect(sportPath("NBA", "Watch")).toBe("/sports/nba/watch");
    expect(sportPath("NBA", "Players")).toBe("/sports/nba/players");
    expect(sportPath("UFC", "Live")).toBe("/sports/ufc/live");
    expect(sportPath("UFC", "Schedule")).toBe("/sports/ufc/schedule");
    expect(sportPath("UFC", "Fighters")).toBe("/sports/ufc/fighters");
    expect(sportPath("UFC", "Rankings")).toBe("/sports/ufc/rankings");
    expect(sportPath("UFC", "Favorites")).toBe("/sports/ufc/favorites");
    expect(sportPath("UFC", "Watch")).toBe("/sports/ufc/watch");
  });

  it("does not map unsupported route segments to a sport", () => {
    expect(sportFromSegment("nfl")).toBe("NFL");
    expect(sportFromSegment("mlb")).toBeNull();
    expect(sportView("UFC", "rankings")).toBe("Rankings");
    expect(sportView("NBA", "fighters")).toBe("Home");
  });

  it("keeps mixed-sport pages explicitly global", () => {
    expect(globalPath("Live")).toBe("/live");
    expect(globalPath("Schedule")).toBe("/schedule");
  });

  it("uses one primary active item inside a sport section", () => {
    expect(isPrimaryNavActive("Schedule", "Schedule", true)).toBe(false);
    expect(isPrimaryNavActive("Sports", "Schedule", true)).toBe(true);
    expect(isPrimaryNavActive("Schedule", "Schedule", false)).toBe(true);
  });
});
