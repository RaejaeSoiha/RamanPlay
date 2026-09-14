import UfcFighterDetail from "../../../../features/ufc/components/UFCFighterDetail";
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <UfcFighterDetail fighterId={id} />;
}
