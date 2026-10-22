import { CitizenIdentityDetail } from "@/components/admin/citizen-identity-detail";

type Params = { user_id: string };

export default async function AdminCitizenIdentityDetailPage({ params }: { params: Promise<Params> }) {
  const { user_id } = await params;
  return <CitizenIdentityDetail userId={user_id} />;
}
