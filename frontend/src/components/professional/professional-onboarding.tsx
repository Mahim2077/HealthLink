"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { ProfessionalApplicationForm } from "@/components/professional/professional-application-form";
import { EmptyState, LoadingState } from "@/components/ui/async-state";

export function ProfessionalOnboarding() {
  const auth = usePortalAuth("CITIZEN");
  const authStatus = auth.status;
  const isCitizen = auth.isRequiredPortal;
  const refreshSession = auth.refreshSession;
  const [hydrationFailed, setHydrationFailed] = useState(false);

  useEffect(() => {
    if (authStatus === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setHydrationFailed(true); });
    return () => { active = false; };
  }, [authStatus, refreshSession]);

  if (authStatus === "unauthenticated" && !hydrationFailed) {
    return <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content"><LoadingState description="Checking for an existing Citizen session." label="Checking your HealthLink identity" /></main>;
  }
  if (authStatus === "unauthenticated") {
    return <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" href="/citizen/login">Sign in as a citizen</Link>} message="Existing HealthLink citizens must authenticate before adding a professional role." title="Sign in before onboarding" /></main>;
  }
  if (!isCitizen) {
    return <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content"><EmptyState message="Use an authenticated Citizen Portal session for existing-account onboarding." title="Citizen session required" /></main>;
  }
  return <ProfessionalApplicationForm mode="onboard" />;
}
