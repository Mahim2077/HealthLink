"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AiAssistant } from "@/components/ai/ai-assistant";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, LoadingState } from "@/components/ui/async-state";

export default function CitizenAiAssistantPage() {
  const auth = usePortalAuth("CITIZEN"); const { status, refreshSession } = auth; const [failed, setFailed] = useState(false);
  useEffect(() => { if (status === "authenticated") return; let active = true; void refreshSession().catch(() => { if (active) setFailed(true); }); return () => { active = false; }; }, [refreshSession, status]);
  if (status === "unauthenticated" && !failed) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Checking for an active Citizen Portal session." label="Checking Citizen session" /></main>;
  if (status === "unauthenticated") return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-5 font-bold text-white" href="/citizen/login">Sign in to Citizen Portal</Link>} message="Sign in to use HealthLink AI." title="Citizen sign in required" /></main>;
  if (!auth.isRequiredPortal) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState message="This session belongs to another HealthLink portal." title="Citizen Portal access required" /></main>;
  return (
    <main className="flex min-h-0 min-w-0 flex-1 flex-col" id="main-content">
      <AiAssistant key={auth.claims?.sid} />
    </main>
  );
}
