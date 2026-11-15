import { PortalLoginGate } from "@/components/auth/portal-login-gate";
import { ProfessionalLoginForm } from "@/components/professional/professional-login-form";

export default function ProfessionalLoginPage() {
  return (
    <PortalLoginGate portal="PROFESSIONAL">
      <ProfessionalLoginForm />
    </PortalLoginGate>
  );
}
