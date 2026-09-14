import Dashboard from "../../../../../../components/layout/Dashboard";

export default async function Page({ params }: { params: Promise<{ team: string; id: string }> }) {
  const { team, id } = await params;
  return <Dashboard initialLeague="NFL" initialView="Players" sportSection nflPlayer={{ team, id }} />;
}
