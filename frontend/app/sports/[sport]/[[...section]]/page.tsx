import { notFound } from "next/navigation";

import Dashboard from "../../../../components/layout/Dashboard";
import { sportFromSegment, sportView } from "../../../../lib/sports/registry";

export default async function SportPage({ params }: { params: Promise<{ sport: string; section?: string[] }> }) {
  const { sport: segment, section } = await params;
  const sport = sportFromSegment(segment);
  if (!sport || (section && section.length > 1)) notFound();
  return <Dashboard initialLeague={sport} initialView={sportView(sport, section?.[0])} sportSection />;
}
