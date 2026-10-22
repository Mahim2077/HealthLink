"use client";

import { PracticeScheduleEditor } from "@/components/professional/practice-schedule-editor";
import { EmptyState } from "@/components/ui/async-state";
import { useSettingsContext } from "./settings-layout";

export function PracticeSettings() {
  const { professional } = useSettingsContext();
  if (professional?.role_code !== "DOCTOR" || professional.verification_status !== "VERIFIED") return <EmptyState title="Verified doctor access required" message="Practice hours are available only for the verified doctor role selected at sign in." />;
  return <section aria-label="Practice hours"><PracticeScheduleEditor /></section>;
}
