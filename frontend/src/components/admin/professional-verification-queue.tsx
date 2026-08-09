"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminPortalGuard } from "@/components/admin/admin-portal-guard";
import { AdminSectionHeader } from "@/components/admin/admin-section-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadProfessionalRegistrations } from "@/lib/admin/api";
import type { ProfessionalRegistrationSummary, VerificationStatus } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";


const filters: Array<{ label: string; value: VerificationStatus | undefined }> = [
  { label: "All", value: undefined }, { label: "Pending", value: "PENDING" },
  { label: "Verified", value: "VERIFIED" }, { label: "Rejected", value: "REJECTED" },
];
const statusStyle: Record<VerificationStatus, string> = {
  PENDING: "bg-amber-50 text-amber-800", VERIFIED: "bg-emerald-50 text-emerald-700", REJECTED: "bg-rose-50 text-rose-700",
};

function ProfessionalVerificationQueueContent() {
  const [filter, setFilter] = useState<VerificationStatus | undefined>("PENDING");
  const [rows, setRows] = useState<ProfessionalRegistrationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try { const result = await loadProfessionalRegistrations(filter); setError(null); setRows(result); }
    catch (reason) { setError(citizenErrorMessage(reason, "We could not load the verification queue.")); }
  }, [filter]);
  useEffect(() => {
    let active = true;
    void loadProfessionalRegistrations(filter).then(
      (result) => { if (active) { setError(null); setRows(result); } },
      (reason: unknown) => { if (active) setError(citizenErrorMessage(reason, "We could not load the verification queue.")); },
    );
    return () => { active = false; };
  }, [filter]);

  return <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
    <AdminSectionHeader eyebrow="Professional verification" title="Application review queue" description="Review each requested role independently, inspect role-specific evidence, and record one audited decision." />
    <div aria-label="Filter applications" className="mt-7 flex flex-wrap gap-2">{filters.map((item) => <button aria-pressed={filter === item.value} className={`min-h-11 rounded-xl px-4 text-sm font-bold ${filter === item.value ? "bg-indigo-700 text-white" : "border border-slate-300 bg-white text-slate-700"}`} key={item.label} onClick={() => setFilter(item.value)} type="button">{item.label}</button>)}</div>
    <section className="mt-6">
      {rows === null && !error ? <LoadingState description="Loading professional applications." label="Loading verification queue" /> : null}
      {error ? <ErrorState message={error} onAction={() => { setError(null); setRows(null); void load(); }} title="Verification queue unavailable" /> : null}
      {rows?.length === 0 ? <EmptyState message="There are no applications in this view." title="Queue is clear" /> : null}
      <div className="grid gap-4">{rows?.map((row) => <article className="rounded-[1.4rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-6" key={row.id}><div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold text-slate-950">{row.first_name} {row.last_name}</h2><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${statusStyle[row.verification_status]}`}>{row.verification_status}</span></div><p className="mt-2 text-sm font-semibold text-indigo-800">{row.role_name} · {row.designation}</p><p className="mt-2 text-sm text-slate-600">Submitted facility: {row.facility_name_submitted}</p><p className="mt-1 text-xs text-slate-500">Submitted {new Date(row.submitted_at).toLocaleString()}</p></div><Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white" href={`/admin/professional-registrations/${row.id}`}>Review application</Link></div></article>)}</div>
    </section>
  </main>;
}

export function ProfessionalVerificationQueue() {
  return <AdminPortalGuard><ProfessionalVerificationQueueContent /></AdminPortalGuard>;
}
