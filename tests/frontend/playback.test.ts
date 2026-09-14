import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { directPlayableKind, directPlayableUrl, playbackSourceType } from "../../frontend/lib/playback";
import type { MyLink } from "../../frontend/types";

function link(overrides: Partial<MyLink> = {}): MyLink {
  return {
    id: 1,
    game_id: 1,
    url: "https://media.ramanplay.test/fixtures/authorized-stream.m3u8",
    source_name: "Authorized stream",
    notes: "",
    priority: 1,
    enabled: true,
    status: "ONLINE",
    playback_type: "DIRECT_MEDIA",
    trust_state: "VERIFIED",
    final_url: "https://media.ramanplay.test/fixtures/authorized-stream.m3u8",
    final_destination_domain: "media.ramanplay.test",
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

describe("inline playback source classification", () => {
  it("accepts only verified, checked direct media for inline playback", () => {
    const manifest = readFileSync(new URL("./fixtures/authorized-stream.m3u8", import.meta.url), "utf8");
    expect(manifest).toContain("#EXTM3U");
    const source = link();
    expect(playbackSourceType(source)).toBe("DIRECT_MEDIA");
    expect(directPlayableUrl(source)).toBe(source.final_url);
    expect(directPlayableKind(source)).toBe("hls");
  });

  it("allows a safely checked unverified direct URL without treating web pages as video", () => {
    expect(playbackSourceType(link({ trust_state: "UNVERIFIED" }))).toBe("DIRECT_MEDIA");
    expect(playbackSourceType(link({ playback_type: "EXTERNAL_PAGE", final_url: "https://www.nfl.com/watch" }))).toBe("EXTERNAL_PAGE");
    expect(playbackSourceType(link({ playback_type: "OFFICIAL_EMBED", final_url: "https://provider.example.test/watch" }))).toBe("EXTERNAL_PAGE");
  });

  it("never plays a blocked link", () => {
    expect(playbackSourceType(link({ status: "BLOCKED", trust_state: "BLOCKED" }))).toBe("BLOCKED");
    expect(directPlayableUrl(link({ status: "BLOCKED", trust_state: "BLOCKED" }))).toBeNull();
  });
});
