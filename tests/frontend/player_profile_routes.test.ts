import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("sport player profile routes", () => {
  it("links NFL roster players to a dedicated profile route", () => {
    expect(read("frontend/features/nfl/components/NFLPlayers.tsx"))
      .toContain("/sports/nfl/players/${player.team}/${player.id}");
    expect(read("frontend/features/nfl/components/NFLPlayerDetail.tsx"))
      .toContain("/api/nfl/players/${encodeURIComponent(team)}/${encodeURIComponent(playerId)}");
  });

  it("keeps NBA profiles inside the NBA sport section", () => {
    expect(read("frontend/features/nba/components/NBAPlayers.tsx"))
      .toContain("/sports/nba/players/${player.id}");
    expect(read("frontend/features/nba/components/NBAPlayerDetail.tsx"))
      .toContain('href="/sports/nba/players"');
    expect(read("frontend/app/nba/player/[id]/page.tsx"))
      .toContain("redirect(`/sports/nba/players/${id}`)");
  });
});
