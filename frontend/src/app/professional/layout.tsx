import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ProfessionalShell } from "@/components/professional/professional-shell";

export const metadata: Metadata = {
  title: "Professional Portal",
  description: "Verified professional access to HealthLink clinical workflows.",
};

export default function ProfessionalLayout({ children }: { children: ReactNode }) {
  return <ProfessionalShell>{children}</ProfessionalShell>;
}
