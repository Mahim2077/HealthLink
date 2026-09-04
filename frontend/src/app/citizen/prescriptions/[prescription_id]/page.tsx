import { PrescriptionPage } from "@/components/prescriptions/prescription-page";

export default async function CitizenPrescriptionPage({
  params,
}: {
  params: Promise<{ prescription_id: string }>;
}) {
  const { prescription_id } = await params;
  return <PrescriptionPage portal="CITIZEN" prescriptionId={prescription_id} />;
}
