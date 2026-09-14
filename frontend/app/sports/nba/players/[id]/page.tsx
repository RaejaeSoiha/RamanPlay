import Dashboard from "../../../../../components/layout/Dashboard";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <Dashboard initialLeague="NBA" initialView="Players" sportSection nbaPlayerId={id} />;
}
