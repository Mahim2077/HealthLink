"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadProfessionalMe } from "@/lib/professional/api";
import type { ProfessionalMe } from "@/lib/professional/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

function ProfessionalGuard({ children }: { children: ReactNode }) {
  const auth = usePortalAuth("PROFESSIONAL"); const [failed, setFailed] = useState(false);
  const status = auth.status; const refresh = auth.refreshSession;
  useEffect(() => { if (status === "authenticated") return; let active=true; void refresh().catch(()=>{if(active)setFailed(true)}); return()=>{active=false}; }, [refresh,status]);
  if (status === "unauthenticated" && !failed) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Checking for a Professional session." label="Checking Professional session" /></main>;
  if (status === "unauthenticated") return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" href="/professional/login">Professional sign in</Link>} message="Sign in with your NID and selected role." title="Professional sign in required" /></main>;
  if (!auth.isRequiredPortal) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState message="This session belongs to another HealthLink portal." title="Professional Portal access required" /></main>;
  return children;
}

function ProfessionalPortalContent({ mode }: { mode: "dashboard" | "status" }) {
  const auth = usePortalAuth("PROFESSIONAL"); const router = useRouter();
  const [record, setRecord] = useState<ProfessionalMe | null>(null); const [error,setError]=useState<string|null>(null); const [version,setVersion]=useState(0); const [loggingOut,setLoggingOut]=useState(false);
  useEffect(()=>{let active=true; void loadProfessionalMe().then(value=>{if(active){setRecord(value);setError(null)}},reason=>{if(active)setError(citizenErrorMessage(reason,"We could not load this professional role."))});return()=>{active=false}},[version]);
  const retry=useCallback(()=>{setRecord(null);setError(null);setVersion(value=>value+1)},[]);
  const signOut=async()=>{setLoggingOut(true);try{await auth.logout()}finally{router.replace("/professional/login");setLoggingOut(false)}};
  if (!record && !error) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Loading the selected professional role." label="Loading Professional Portal" /></main>;
  if (error) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><ErrorState message={error} onAction={retry} title="Professional Portal unavailable" /></main>;
  if (!record) return null;
  const verified=record.verification_status === "VERIFIED";
  if (mode === "dashboard" && !verified) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" href="/professional/status">View verification status</Link>} message="Clinical workspace access begins only after this selected role is verified." title={`${record.verification_status} role is restricted`} /></main>;
  return <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content"><header className="flex flex-col gap-5 border-b border-slate-200 pb-7 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">Active role · {record.role_name}</p><h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">Welcome, {record.first_name}.</h1><p className="mt-2 text-sm text-slate-600">This session is isolated to your selected {record.role_name} role.</p></div><button className="min-h-11 rounded-xl border border-slate-300 bg-white px-5 text-sm font-bold disabled:opacity-60" disabled={loggingOut} onClick={signOut} type="button">{loggingOut?"Signing out…":"Sign out"}</button></header>{mode === "status" ? <section className="mt-8 max-w-3xl rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">Verification status</p><div className="mt-4 flex flex-wrap items-center gap-3"><h2 className="text-2xl font-bold text-slate-950">{record.role_name}</h2><span className={`rounded-full px-3 py-1.5 text-xs font-bold ${verified?"bg-emerald-50 text-emerald-700":record.verification_status==="PENDING"?"bg-amber-50 text-amber-800":"bg-rose-50 text-rose-700"}`}>{record.verification_status}</span></div><p className="mt-4 text-sm leading-6 text-slate-600">Designation: {record.designation}</p>{record.rejection_reason?<div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4"><p className="text-xs font-bold uppercase text-rose-700">Reason</p><p className="mt-2 text-sm text-rose-900">{record.rejection_reason}</p></div>:null}{verified?<Link className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" href="/professional/dashboard">Enter role dashboard</Link>:<p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">This restricted session can display verification status only.</p>}</section> : <div className="mt-8 grid gap-6 lg:grid-cols-2"><section className="rounded-[1.75rem] bg-sky-950 p-7 text-white"><p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-300">Verified role context</p><h2 className="mt-3 text-2xl font-bold">{record.role_name}</h2><p className="mt-3 text-sm leading-6 text-sky-100/80">Backend authorization checks this exact role registration for every professional capability.</p><span className="mt-6 inline-flex rounded-full bg-emerald-300/15 px-3 py-1.5 text-xs font-bold text-emerald-200">VERIFIED</span></section><section className="rounded-[1.75rem] border border-slate-200 bg-white p-7 shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">Primary facility</p><h2 className="mt-3 text-xl font-bold text-slate-950">{record.facility?.name ?? "No facility linked"}</h2><p className="mt-2 text-sm text-slate-600">{record.facility?.address ?? "Contact an administrator if this verified assignment is incomplete."}</p><Link className="mt-6 inline-flex min-h-11 items-center text-sm font-bold text-sky-700" href="/professional/status">View verification details →</Link></section></div>}</main>;
}

export function ProfessionalPortal({ mode }: { mode: "dashboard" | "status" }) { return <ProfessionalGuard><ProfessionalPortalContent mode={mode} /></ProfessionalGuard>; }
