import { CitizenIdentityDetail } from "@/components/admin/citizen-identity-detail";

type Params = { user_id: string };

export default function AdminCitizenIdentityDetailPage({ params }: { params: Params }) {
  return <CitizenIdentityDetail userId={params.user_id} />;
}