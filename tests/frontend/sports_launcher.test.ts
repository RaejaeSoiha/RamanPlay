import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { SPORT_LAUNCHER_CARDS } from "../../frontend/components/sports/SportsLauncher";
import { sportPath } from "../../frontend/lib/sportRoutes";

const launcherSource = readFileSync(
  new URL("../../frontend/components/sports/SportsLauncher.tsx", import.meta.url),
  "utf8",
);
const styles = readFileSync(
  new URL("../../frontend/app/globals.css", import.meta.url),
  "utf8",
);
const registrySource = readFileSync(
  new URL("../../frontend/lib/sports/registry.ts", import.meta.url),
  "utf8",
);

describe("sports launcher", () => {
  it("shows exactly one dedicated dashboard card for each supported sport", () => {
    expect(SPORT_LAUNCHER_CARDS.map((card) => card.sport)).toEqual(["NFL", "NBA", "UFC"]);
    expect(SPORT_LAUNCHER_CARDS.map((card) => sportPath(card.sport, "Home"))).toEqual([
      "/sports/nfl",
      "/sports/nba",
      "/sports/ufc",
    ]);
  });

  it("uses a semantic whole-card link without nested card buttons", () => {
    expect(launcherSource).toContain("<Link");
    expect(launcherSource).toContain("aria-label={`Open ${sport} dashboard`}");
    expect(launcherSource).toContain("sports-launcher-brand");
    expect(launcherSource).toContain("SPORT_REGISTRY");
    expect(launcherSource).toContain("sports-launcher-details");
    expect(registrySource).toContain('/images/sports/nfl-official.png');
    expect(registrySource).toContain('/images/sports/nba-official.png');
    expect(registrySource).toContain('/images/sports/ufc-official.png');
    expect(launcherSource).not.toContain("<button");
    expect(styles).toContain(".sports-launcher-card:focus-visible");
  });

  it("uses responsive grid breakpoints with a single-column mobile layout", () => {
    expect(styles).toContain("grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(styles).toContain("@media (max-width: 680px)");
    expect(styles).toContain(".sports-launcher-grid { grid-template-columns: 1fr;");
    expect(styles).toContain('url("/images/sports/football-stadium.png")');
  });
});
