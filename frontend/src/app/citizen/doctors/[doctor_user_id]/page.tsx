import { DoctorProfileView } from "@/components/citizen/doctor-profile";

export default async function CitizenDoctorDetailPage({
  params,
}: {
  params: Promise<{ doctor_user_id: string }>;
}) {
  const { doctor_user_id } = await params;
  return <DoctorProfileView doctorUserId={doctor_user_id} />;
}