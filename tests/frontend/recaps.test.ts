import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { recapEndpoint, recapRoute, recapsEndpoint } from "../../frontend/lib/recaps";

const section = readFileSync(new URL("../../frontend/components/recaps/RecapSection.tsx", import.meta.url), "utf8");
const dashboard = readFileSync(new URL("../../frontend/components/layout/Dashboard.tsx", import.meta.url), "utf8");
const ufcDetail = readFileSync(new URL("../../frontend/features/ufc/components/UFCEventDetail.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../../frontend/app/globals.css", import.meta.url), "utf8");

describe("factual post-game recaps", () => {
  it("uses shared list and detail endpoints with sport-specific routes", () => {
    expect(recapsEndpoint("NFL", 3)).toBe("/api/recaps?sport=NFL&limit=3");
    expect(recapEndpoint("NBA", 42)).toBe("/api/recaps/NBA/42");
    expect(recapRoute("UFC", 42)).toBe("/ufc/event/42");
    expect(recapRoute("NFL", 42)).toBe("/game/42");
  });

  it("renders factual scores/results with loading and empty states", () => {
    expect(section).toContain("final_score");
    expect(section).toContain("Completed bouts");
    expect(section).toContain('state === "loading"');
    expect(section).toContain('state === "empty"');
    expect(section).toContain("recap-unavailable");
  });

  it("keeps sport homes isolated and adds final detail panels", () => {
    expect(dashboard).toContain('<RecapSection sport={prefs.league} />');
    expect(dashboard).toContain('<RecapSection sport="UFC" />');
    expect(dashboard).toContain('detail.status === "FINAL"');
    expect(ufcDetail).toContain('event.status === "FINAL"');
  });

  it("uses a responsive, mobile-safe recap grid", () => {
    expect(styles).toContain(".recap-grid");
    expect(styles).toContain(".recap-detail-grid");
    expect(styles).toContain(".recap-grid, .recap-detail-grid { grid-template-columns: 1fr;");
  });
});
