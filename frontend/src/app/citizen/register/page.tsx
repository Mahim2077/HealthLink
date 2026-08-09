import { CitizenAuthCard } from "@/components/citizen/auth-card";
import { CitizenRegisterForm } from "@/components/citizen/register-form";

export default function CitizenRegisterPage() {
  return (
    <CitizenAuthCard
      description="Create one secure account for your identity and future healthcare journey. Citizens can begin with either an NID or a Birth Certificate Number."
      eyebrow="Citizen registration"
      title="Your care story starts with you."
    >
      <CitizenRegisterForm />
    </CitizenAuthCard>
  );
}
