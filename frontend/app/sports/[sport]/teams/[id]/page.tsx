import { notFound } from "next/navigation";

import Dashboard from "../../../../../components/layout/Dashboard";
import { sportFromSegment } from "../../../../../lib/sports/registry";

export default async function Page({ params }: { params: Promise<{ sport: string; id: string }> }) {
  const { sport: segment, id } = await params;
  const sport = sportFromSegment(segment);
  if (!sport || sport === "UFC") notFound();
  return <Dashboard initialLeague={sport} initialView="Teams" sportSection teamProfileId={id} />;
}
