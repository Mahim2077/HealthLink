import { ProfessionalPortal } from "@/components/professional/professional-portal";
import { PracticeScheduleEditor } from "@/components/professional/practice-schedule-editor";

export default function ProfessionalDashboardPage() {
  return (
    <ProfessionalPortal
      mode="dashboard"
      verifiedDoctorSlot={<PracticeScheduleEditor />}
    />
  );
}
