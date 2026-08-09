import type { Metadata } from "next";
import type { ReactNode } from "react";

import { CitizenShell } from "@/components/citizen/citizen-shell";

export const metadata: Metadata = {
  title: "Citizen Portal",
  description: "Secure citizen access to HealthLink.",
};

export default function CitizenLayout({ children }: { children: ReactNode }) {
  return <CitizenShell>{children}</CitizenShell>;
}
