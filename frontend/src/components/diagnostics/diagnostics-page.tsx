"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { listCitizenDiagnostics, listProfessionalDiagnostics, transitionDiagnosticTest } from "@/lib/diagnostics/api";
import { loadProfessionalMe } from "@/lib/professional/api";
import type { ProfessionalMe } from "@/lib/professional/types";
import { CitizenDiagnosticTrends } from "./citizen-lab-reports";
import { DiagnosticList } from "./diagnostic-list";

function ProfessionalDiagnostics() {
  const [me, setMe] = useState<ProfessionalMe | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    void loadProfessionalMe().then(value => { if (active) { setMe(value); setError(""); } }, () => {
      if (active) setError("We could not verify your professional role.");
    });
    return () => { active = false; };
  }, [version]);
  if (error) return <ErrorState message={error} onAction={() => { setError(""); setVersion(v => v + 1); }} />;
  if (!me) return <LoadingState label="Loading diagnostics" />;
  if (me.verification_status !== "VERIFIED" || !["DOCTOR", "LAB_TECHNICIAN"].includes(me.role_code)) {
    return <EmptyState title="Diagnostics unavailable" message="A verified Doctor or Lab Technician role is required." />;
  }
  return <DiagnosticList loadAction={listProfessionalDiagnostics} role={me.role_code === "LAB_TECHNICIAN" ? "lab" : "doctor"} transitionAction={transitionDiagnosticTest} />;
}

function CitizenDiagnostics() {
  return <div className="space-y-12">
    <section aria-labelledby="diagnostic-requests-heading" className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-slate-950" id="diagnostic-requests-heading">Requests and results</h2>
        <p className="mt-2 text-sm text-slate-600">Follow each request from submission to completion and open finalized results directly from the completed test.</p>
      </div>
      <DiagnosticList loadAction={listCitizenDiagnostics} role="citizen" />
    </section>
    <CitizenDiagnosticTrends />
  </div>;
}

export function DiagnosticsPage({ portal }: { portal: "CITIZEN" | "PROFESSIONAL" }) {
  const auth = usePortalAuth(portal);
  const { status, refreshSession } = auth;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);
  const content = status !== "authenticated" ? (
    failed ? <EmptyState title="Sign in required" message="Sign in to view diagnostic tests." action={<Link href={`/${portal.toLowerCase()}/login`}>Sign in</Link>} /> : <LoadingState label="Checking session" />
  ) : !auth.isRequiredPortal ? <EmptyState title="Portal access required" message="This session belongs to another HealthLink portal." /> : portal === "CITIZEN" ? (
    <CitizenDiagnostics key={auth.claims?.sid} />
  ) : <ProfessionalDiagnostics key={auth.claims?.sid} />;
  return <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8" id="main-content">
    <header className="border-b border-slate-200 pb-7">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--portal-strong)]">Diagnostics</p>
      <h1 className="mt-3 text-3xl font-bold text-slate-950">Diagnostic tests</h1>
      <p className="mt-2 text-sm text-slate-600">{portal === "CITIZEN" ? "Track requests, open finalized results, and review numeric trends in one place." : "Track requests, assignments and progress."}</p>
    </header>
    <div className="mt-8">{content}</div>
  </main>;
}
