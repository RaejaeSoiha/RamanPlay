import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");
const nflPlayers = readFileSync(resolve(root, "frontend/features/nfl/components/NFLPlayers.tsx"), "utf8");
const nbaPlayers = readFileSync(resolve(root, "frontend/features/nba/components/NBAPlayers.tsx"), "utf8");

describe("team-grouped player directories", () => {
  it("groups the NFL directory by the player team and shows team roster headings", () => {
    expect(nflPlayers).toContain('fetch("/api/teams?league=NFL")');
    expect(nflPlayers).toContain("selectedTeam");
    expect(nflPlayers).toContain("Search NFL teams or players");
    expect(nflPlayers).toContain('className="team-selection-card"');
    expect(nflPlayers).toContain('className="player-team-group"');
    expect(nflPlayers).toContain('className="player-team-heading"');
  });

  it("groups NBA players by their persisted team ID", () => {
    expect(nbaPlayers).toContain('fetch("/api/teams?league=NBA")');
    expect(nbaPlayers).toContain("team_id: number | null");
    expect(nbaPlayers).toContain("selectedTeamId");
    expect(nbaPlayers).toContain("Search NBA teams or players");
    expect(nbaPlayers).toContain('className="team-selection-card"');
    expect(nbaPlayers).toContain('className="player-team-group"');
    expect(nbaPlayers).toContain("/sports/nba/players/${player.id}");
  });
});
