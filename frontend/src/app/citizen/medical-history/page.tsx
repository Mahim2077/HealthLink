"use client";

import { ArrowLeftIcon } from "@heroicons/react/24/outline";
import Link from "next/link";
import { useEffect, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { MedicalHistoryTimeline } from "@/components/medical-records/medical-history-timeline";
import { EmptyState, LoadingState } from "@/components/ui/async-state";
import { listCitizenMedicalHistory } from "@/lib/medical-records/api";

export default function CitizenMedicalHistoryPage() {
  const auth = usePortalAuth("CITIZEN");
  const status = auth.status;
  const refreshSession = auth.refreshSession;
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => {
      if (active) setFailed(true);
    });
    return () => {
      active = false;
    };
  }, [refreshSession, status]);

  if (status === "unauthenticated" && !failed) {
    return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Checking for an active Citizen Portal session." label="Checking Citizen session" /></main>;
  }
  if (status === "unauthenticated") {
    return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-5 font-bold text-white" href="/citizen/login">Sign in to Citizen Portal</Link>} message="Sign in to view your longitudinal health record." title="Citizen sign in required" /></main>;
  }
  if (!auth.isRequiredPortal) {
    return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState message="This session belongs to another HealthLink portal." title="Citizen Portal access required" /></main>;
  }

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
      <header className="border-b border-slate-200 pb-7">
        <Link className="inline-flex items-center gap-2 text-sm font-bold text-teal-700 hover:text-teal-900" href="/citizen/dashboard"><ArrowLeftIcon aria-hidden="true" className="size-4" />Citizen Dashboard</Link>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Health record</p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">My medical history</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">Review your finalized clinical timeline across HealthLink facilities. Use the filters to find visits and prescriptions by date.</p>
      </header>
      <div className="mt-8"><MedicalHistoryTimeline loadAction={listCitizenMedicalHistory} portal="citizen" /></div>
    </main>
  );
}
