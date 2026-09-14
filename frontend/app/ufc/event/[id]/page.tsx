import UfcEventDetail from "../../../../features/ufc/components/UFCEventDetail";
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <UfcEventDetail eventId={id} />;
}
