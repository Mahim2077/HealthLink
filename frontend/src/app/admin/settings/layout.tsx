import type { ReactNode } from "react";
import { SettingsLayout } from "@/components/settings/settings-layout";

export default function Layout({ children }: { children: ReactNode }) {
  return <SettingsLayout portal="ADMIN">{children}</SettingsLayout>;
}
