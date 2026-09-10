import type { ReactNode } from "react";

import { PortalShell } from "@/components/layout/portal-shell";

export function AdminShell({ children }: { children: ReactNode }) {
  return <PortalShell portal="ADMIN">{children}</PortalShell>;
}
