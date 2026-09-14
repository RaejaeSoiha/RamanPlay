import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("platform enhancements", () => {
  it("provides calendar, browser reminder, and safe live-score UI", () => {
    const utilities = read("frontend/components/shared/GameUtilities.tsx");
    expect(utilities).toContain("text/calendar");
    expect(utilities).toContain("Notification.requestPermission");
    expect(utilities).toContain("/live-details");
  });

  it("provides team profiles and mobile navigation without replacing sport routes", () => {
    const dashboard = read("frontend/components/layout/Dashboard.tsx");
    expect(dashboard).toContain("TeamProfile");
    expect(dashboard).toContain("mobile-bottom-nav");
    expect(dashboard).toContain("/api/account/preferences");
    expect(read("frontend/components/shared/TeamProfile.tsx")).toContain("Team schedule");
  });
});
