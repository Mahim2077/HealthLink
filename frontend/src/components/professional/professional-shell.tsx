import type { ReactNode } from "react";

import { PortalShell } from "@/components/layout/portal-shell";

export function ProfessionalShell({ children }: { children: ReactNode }) {
  return <PortalShell portal="PROFESSIONAL">{children}</PortalShell>;
}
