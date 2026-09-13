"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LabPortalGate } from "@/components/diagnostics/lab-report-page";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { apiClient } from "@/lib/api/client";

type HistoryPage = { page: number; has_next: boolean; items: {
  id: string; actor_name: string; role: string | null; facility: string | null;
  resource_type: string; action: string; access_source: string | null; created_at: string;
}[] };
const readable = (value: string) => value.toLowerCase().replaceAll("_", " ");

function History() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<HistoryPage | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    void apiClient.get<HistoryPage>(`citizens/me/access-history?page=${page}`).then(value => { if (active) setData(value); }, reason => { if (active) setError(reason instanceof Error ? reason.message : "Access history unavailable."); });
    return () => { active = false; };
  }, [page, retry]);
  if (error) return <ErrorState message={error} onAction={() => { setError(""); setRetry(v => v + 1); }} />;
  if (!data) return <LoadingState label="Loading access history" />;
  return <div className="space-y-4">
    {data.items.length ? data.items.map(item => <article key={item.id} className="hl-card p-5">
      <h2 className="font-bold text-slate-950">{item.actor_name}</h2>
      <p className="mt-1 text-sm text-slate-600">{item.role ?? "Account activity"}{item.facility ? ` · ${item.facility}` : ""}</p>
      <p className="mt-3 capitalize">{readable(item.action)} · {readable(item.resource_type)}</p>
      {item.access_source ? <p className="mt-1 text-sm">Access through {readable(item.access_source)}</p> : null}
      <time dateTime={item.created_at} className="mt-2 block text-sm text-slate-600">{new Date(item.created_at).toLocaleString("en-GB", { timeZone: "Asia/Dhaka" })} (Dhaka)</time>
    </article>) : <EmptyState title="No access activity" message="Recorded access to your medical information will appear here." />}
    <nav aria-label="Access history pages" className="flex items-center gap-4">
      <button className="min-h-11 rounded-xl border px-4 disabled:opacity-50" disabled={page === 1} onClick={() => { setData(null); setPage(p => p - 1); }}>Previous</button>
      <span>Page {page}</span>
      <button className="min-h-11 rounded-xl border px-4 disabled:opacity-50" disabled={!data.has_next} onClick={() => { setData(null); setPage(p => p + 1); }}>Next</button>
    </nav>
  </div>;
}

export function AccessHistoryPage() {
  return <main id="main-content" className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-5 py-10 sm:px-8">
    <h1 className="text-3xl font-bold">Privacy and access history</h1>
    <p className="text-sm text-slate-600">See who accessed your medical information and manage the access you have shared. Activity is recorded from the introduction of this feature.</p>
    <Link className="inline-block min-h-11 font-semibold text-sky-800 underline" href="/citizen/access-grants">Manage access grants</Link>
    <LabPortalGate portal="CITIZEN"><History /></LabPortalGate>
  </main>;
}
