import { CitizenAuthCard } from "@/components/citizen/auth-card";
import { CitizenLoginForm } from "@/components/citizen/login-form";

export default async function CitizenLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string }>;
}) {
  const { registered } = await searchParams;

  return (
    <CitizenAuthCard
      description="Return to your private HealthLink space. Your citizen session is isolated from professional and administrative portal access."
      eyebrow="Citizen access"
      title="Your health information, when you need it."
    >
      <CitizenLoginForm registrationComplete={registered === "1"} />
    </CitizenAuthCard>
  );
}
