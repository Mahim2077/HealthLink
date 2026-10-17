"use client";

import { ArrowLeftIcon } from "@heroicons/react/24/outline";
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
    <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
      <header className="border-b border-slate-200 pb-7">
        <Link className="inline-flex items-center gap-2 text-sm font-bold text-teal-700 hover:text-teal-900" href="/citizen/dashboard"><ArrowLeftIcon aria-hidden="true" className="size-4" />Citizen Dashboard</Link>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Informational support</p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">HealthLink AI assistant</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">Ask general health questions, request record-aware guidance with your consent, or review symptoms for safe next-step information. HealthLink AI does not diagnose.</p>
      </header>
      <div className="mt-8"><AiAssistant key={auth.claims?.sid} /></div>
    </main>
  );
}
