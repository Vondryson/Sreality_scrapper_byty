import { notFound } from "next/navigation";
import { ListingDetailView } from "@/components/listing-detail-view";

export default async function ListingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const listingId = Number(id);
  if (!Number.isSafeInteger(listingId) || listingId <= 0) notFound();
  return <ListingDetailView listingId={listingId} />;
}
