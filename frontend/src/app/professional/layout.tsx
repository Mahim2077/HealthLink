import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ProfessionalShell } from "@/components/professional/professional-shell";

export const metadata: Metadata = {
  title: "Professional Registration",
  description: "Apply for a verified HealthLink professional role.",
};

export default function ProfessionalLayout({ children }: { children: ReactNode }) {
  return <ProfessionalShell>{children}</ProfessionalShell>;
}
