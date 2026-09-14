import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { newsEndpoint, relativeNewsTime, storySportClass } from "../../frontend/lib/news";

const section = readFileSync(new URL("../../frontend/components/news/NewsSection.tsx", import.meta.url), "utf8");
const dashboard = readFileSync(new URL("../../frontend/components/layout/Dashboard.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../../frontend/app/globals.css", import.meta.url), "utf8");

describe("sports news", () => {
  it("builds bounded, sport-scoped API requests", () => {
    expect(newsEndpoint("NFL", 6)).toBe("/api/news?sport=NFL&limit=6");
    expect(newsEndpoint("UFC", 4)).toContain("sport=UFC");
  });

  it("shows readable publication times and sport accents", () => {
    const now = Date.parse("2026-09-14T12:00:00Z");
    expect(relativeNewsTime("2026-09-14T10:00:00Z", now)).toBe("2h ago");
    expect(relativeNewsTime("2026-09-13T10:00:00Z", now)).toBe("Yesterday");
    expect(storySportClass({ league: "NBA" })).toBe("news-badge-nba");
  });

  it("uses safe external story links and includes loading, empty, and error states", () => {
    expect(section).toContain('target="_blank"');
    expect(section).toContain('rel="noopener noreferrer"');
    expect(section).toContain('state === "loading"');
    expect(section).toContain('state === "empty"');
    expect(section).toContain("news-unavailable");
  });

  it("keeps global and sport homes isolated", () => {
    expect(dashboard).toContain('<NewsSection sport="UFC" />');
    expect(dashboard).toContain("<NewsSection sport={prefs.league} />");
    expect(styles).toContain(".news-grid");
    expect(styles).toContain("@media (max-width: 580px)");
  });
});
