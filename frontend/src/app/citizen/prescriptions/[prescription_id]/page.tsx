import { PrescriptionPage } from "@/components/prescriptions/prescription-page";

export default async function CitizenPrescriptionPage({
  params,
  searchParams,
}: {
  params: Promise<{ prescription_id: string }>;
  searchParams: Promise<{ returnTo?: string | string[] }>;
}) {
  const [{ prescription_id }, search] = await Promise.all([params, searchParams]);
  return <PrescriptionPage portal="CITIZEN" prescriptionId={prescription_id} returnTo={typeof search.returnTo === "string" ? search.returnTo : undefined} />;
}
