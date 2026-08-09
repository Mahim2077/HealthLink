"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadAdminMe } from "@/lib/admin/api";
import type { AdminMe } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

type State = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; admin: AdminMe };

export function AdminDashboard({ loadAction = loadAdminMe }: { loadAction?: () => Promise<AdminMe> }) {
  const auth = usePortalAuth("ADMIN");
  const router = useRouter();
  const authStatus = auth.status;
  const isAdminPortal = auth.isRequiredPortal;
  const refreshSession = auth.refreshSession;
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const [state, setState] = useState<State>({ status: "loading" });
  const [version, setVersion] = useState(0);
  const [loggingOut, setLoggingOut] = useState(false);
  const [manualLogout, setManualLogout] = useState(false);

  useEffect(() => {
    if (authStatus === "authenticated" || manualLogout) return;
    let active = true;
    void refreshSession().catch(() => { if (active) setHydrationFailed(true); });
    return () => { active = false; };
  }, [authStatus, manualLogout, refreshSession]);

  useEffect(() => {
    if (authStatus !== "authenticated" || !isAdminPortal) return;
    let active = true;
    void loadAction().then(
      (admin) => { if (active) setState({ admin, status: "ready" }); },
      (reason: unknown) => { if (active) setState({ message: citizenErrorMessage(reason, "We could not load this admin account."), status: "error" }); },
    );
    return () => { active = false; };
  }, [authStatus, isAdminPortal, loadAction, version]);

  if (authStatus === "unauthenticated" && !hydrationFailed && !manualLogout) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Checking for a trusted Admin session." label="Checking Admin session" /></main>;
  if (authStatus === "unauthenticated") return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white" href="/admin/login">Sign in to Admin Portal</Link>} message="A trusted administrator account is required." title="Admin sign in required" /></main>;
  if (!isAdminPortal) return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState message="This session belongs to another HealthLink portal." title="Admin Portal access required" /></main>;
  if (state.status === "loading") return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Loading your trusted operational account." label="Loading Admin Dashboard" /></main>;
  if (state.status === "error") return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><ErrorState message={state.message} onAction={() => { setState({ status: "loading" }); setVersion((value) => value + 1); }} title="Admin Dashboard unavailable" /></main>;

  const admin = state.admin;
  const signOut = async () => {
    setManualLogout(true);
    setLoggingOut(true);
    try { await auth.logout(); } finally { router.replace("/admin/login"); setLoggingOut(false); }
  };
  return (
    <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 sm:py-14 lg:px-10" id="main-content">
      <div className="flex flex-col gap-5 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-700">Trusted account</p><h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">Welcome, {admin.first_name}.</h1><p className="mt-2 text-sm text-slate-600">Your Admin Portal identity is active and isolated from other portal contexts.</p></div>
        <button className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-5 text-sm font-bold text-slate-700 disabled:opacity-60" disabled={loggingOut} onClick={signOut} type="button">{loggingOut ? "Signing out…" : "Sign out"}</button>
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="rounded-[1.75rem] bg-indigo-950 p-6 text-white shadow-xl shadow-indigo-950/10 sm:p-8"><p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-300">Access level</p><h2 className="mt-3 text-2xl font-bold">{admin.is_super_admin ? "Super administrator" : "Administrator"}</h2><p className="mt-3 text-sm leading-6 text-indigo-100/75">Trusted operational capability is active. Every protected action remains subject to backend authorization and audit requirements.</p><span className="mt-6 inline-flex rounded-full bg-emerald-300/15 px-3 py-1.5 text-xs font-bold text-emerald-200">ACTIVE</span></section>
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-700">Admin identity</p><h2 className="mt-3 text-xl font-bold text-slate-950">{admin.first_name} {admin.last_name}</h2><dl className="mt-6 grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs font-bold text-slate-500">Email</dt><dd className="mt-1 break-words text-sm font-semibold text-slate-900">{admin.email}</dd></div><div className="rounded-xl bg-slate-50 p-4"><dt className="text-xs font-bold text-slate-500">Account type</dt><dd className="mt-1 text-sm font-semibold text-slate-900">Trusted operational account</dd></div></dl><div className="mt-6 grid gap-3 sm:grid-cols-2"><Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-indigo-700 px-4 text-center text-sm font-bold text-white" href="/admin/professional-registrations">Review professionals</Link><Link className="inline-flex min-h-11 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 px-4 text-center text-sm font-bold text-indigo-800" href="/admin/facilities">Manage facilities</Link></div></section>
      </div>
    </main>
  );
}
