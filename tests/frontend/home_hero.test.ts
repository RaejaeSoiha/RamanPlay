import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");
const hero = readFileSync(resolve(root, "frontend/components/home/HomeHero.tsx"), "utf8");
const dashboard = readFileSync(resolve(root, "frontend/components/layout/Dashboard.tsx"), "utf8");
const styles = readFileSync(resolve(root, "frontend/app/globals.css"), "utf8");
const registry = readFileSync(resolve(root, "frontend/lib/sports/registry.ts"), "utf8");

describe("RamanPlay home overview", () => {
  it("provides direct entry points to every supported sport", () => {
    expect(hero).toContain("SPORT_REGISTRY");
    expect(registry).toContain("NFL:");
    expect(registry).toContain("NBA:");
    expect(registry).toContain("UFC:");
    expect(hero).toContain('href="/sports"');
    expect(hero).toContain('href="/live"');
  });

  it("uses the upgraded overview only for the global home page", () => {
    expect(dashboard).toContain('<HomeHero');
    expect(dashboard).toContain('view === "Home" && prefs.league === "ALL"');
    expect(styles).toContain(".home-sport-launcher");
    expect(styles).toContain("@media (max-width: 580px)");
  });
});

it("keeps the global Home page to a balanced NFL/NBA overview", () => {
  const dashboard = readFileSync(resolve(root, "frontend/components/layout/Dashboard.tsx"), "utf8");
  expect(dashboard).toContain("const homeHighlights");
  expect(dashboard).toContain("const homeUpcoming = homeHighlights(next)");
  expect(dashboard).toContain("{homeUpcoming.map(card)}");
  expect(dashboard).toContain("{homeFree.map(card)}");
});


it("shows a compact personalized Home section for followed teams", () => {
  expect(dashboard).toContain("const homeFavoriteGames");
  expect(dashboard).toContain('id="home-team-tracker-title"');
  expect(dashboard).toContain("Your next games");
  expect(dashboard).toContain('go("Favorites")');
  expect(styles).toContain(".home-team-list");
});


it("keeps a dedicated sport route in its URL-selected league", () => {
  expect(dashboard).toContain("storedPreferences");
  expect(dashboard).toContain("...(initialLeague ? { league: initialLeague } : {})");
  expect(dashboard).toContain("`${prefs.league} game center.`");
});
