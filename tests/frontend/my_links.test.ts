import { describe, expect, it } from "vitest";
import { bestMyLink, cleanOpenAction, showWatchLive } from "../../frontend/lib/myLinks";
import type { MyLink } from "../../frontend/types";

function link(overrides: Partial<MyLink> = {}): MyLink {
  return {
    id: 1,
    game_id: 1,
    url: "https://www.nfl.com/watch",
    source_name: "My link",
    notes: "",
    priority: 3,
    enabled: true,
    status: "ONLINE",
    final_url: "https://www.nfl.com/watch",
    final_destination_domain: "www.nfl.com",
    last_checked: null,
    last_successful_check: null,
    last_failure: null,
    successful_check_count: 1,
    failure_count: 0,
    average_response_time: 0.2,
    redirect_count: 0,
    last_opened_at: null,
    reliability_score: 90,
    ...overrides,
  };
}

describe("My Links selection and clean open", () => {
  it("prefers enabled online links with the highest reliability", () => {
    const selected = bestMyLink([
      link({ id: 1, reliability_score: 99, enabled: false }),
      link({ id: 2, status: "WARNING", reliability_score: 100 }),
      link({ id: 3, reliability_score: 80 }),
    ]);
    expect(selected?.id).toBe(3);
  });

  it("requires confirmation for warnings and prevents blocked links", () => {
    expect(cleanOpenAction(link({ status: "WARNING" }))).toBe("confirm");
    expect(cleanOpenAction(link({ status: "BLOCKED" }))).toBe("blocked");
    expect(cleanOpenAction(link({ status: "OFFLINE" }))).toBe("blocked");
    expect(cleanOpenAction(link())).toBe("navigate");
  });

  it("only shows WATCH LIVE for live games with enabled My Links", () => {
    expect(showWatchLive({ status: "LIVE", my_links: [link()] })).toBe(true);
    expect(showWatchLive({ status: "FINAL", my_links: [link()] })).toBe(false);
    expect(showWatchLive({ status: "LIVE", my_links: [link({ enabled: false })] })).toBe(false);
  });
});
