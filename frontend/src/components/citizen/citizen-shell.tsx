import type { ReactNode } from "react";

import { PortalShell } from "@/components/layout/portal-shell";

export function CitizenShell({ children }: { children: ReactNode }) {
  return <PortalShell portal="CITIZEN">{children}</PortalShell>;
}
