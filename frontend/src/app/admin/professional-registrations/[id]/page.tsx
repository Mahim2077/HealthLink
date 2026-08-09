import { ProfessionalVerificationDetail } from "@/components/admin/professional-verification-detail";

export default async function ProfessionalRegistrationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProfessionalVerificationDetail registrationId={id} />;
}
