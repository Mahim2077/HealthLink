import { PrescriptionPage } from "@/components/prescriptions/prescription-page";

export default async function ProfessionalPrescriptionPage({
  params,
}: {
  params: Promise<{ prescription_id: string }>;
}) {
  const { prescription_id } = await params;
  return (
    <PrescriptionPage
      portal="PROFESSIONAL"
      prescriptionId={prescription_id}
    />
  );
}
