import NbaPlayers from "../../../../../features/nba/components/NBAPlayers";
import { Team } from "../../../../../types";

interface Props {
  params: Promise<{ teamId: string }>;
}

export default async function Page({ params }: Props) {
  const { teamId } = await params;
  const team = await fetchTeam(teamId);
  const teamName = team ? `${team.city} ${team.name}` : teamId.toUpperCase();
  return <NbaPlayers teamId={teamId} teamName={teamName} />;
}

async function fetchTeam(teamId: string): Promise<Team | null> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/teams?league=NBA`, {
      cache: "no-store",
    });
    if (!response.ok) return null;
    const teams: Team[] = await response.json();
    return teams.find((t) => t.provider_id === teamId) || null;
  } catch {
    return null;
  }
}