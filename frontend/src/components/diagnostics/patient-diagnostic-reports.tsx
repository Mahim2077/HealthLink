"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { sharedRecords, type SharedRecord } from "@/lib/access/api";

export function PatientDiagnosticReports({ citizenId }: { citizenId: string }) {
  const [open, setOpen] = useState(false);
  return <details className="hl-card space-y-3 p-5" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="min-h-11 cursor-pointer font-semibold">Patient diagnostic reports</summary>
    {open && <ReportList citizenId={citizenId} />}
  </details>;
}

function ReportList({ citizenId }: { citizenId: string }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ records: SharedRecord[]; has_next: boolean } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void sharedRecords(citizenId, "LAB_REPORT", page).then(result => { if (active) setData(result); }, reason => {
      if (active) setError(reason instanceof Error ? reason.message : "Could not load diagnostic reports.");
    });
    return () => { active = false; };
  }, [citizenId, page]);
  const move = (next: number) => { setData(null); setError(""); setPage(next); };
  if (error) return <p role="alert" className="text-sm text-rose-700">{error}</p>;
  if (!data) return <p role="status">Loading diagnostic reports…</p>;
  return <div className="space-y-3">
    {data.records.length === 0 && <p className="text-sm">No diagnostic reports on this page.</p>}
    <ul className="space-y-2">
      {data.records.map(report => <li key={report.id} className="rounded-xl bg-slate-50 p-3">
        <p className="font-semibold">{report.title}</p>
        <p className="text-sm">{new Date(report.occurred_at).toLocaleDateString()}</p>
        {report.detail_url && <Link href={report.detail_url} className="inline-flex min-h-11 items-center text-sm text-sky-800 underline">Open report</Link>}
      </li>)}
    </ul>
    {(page > 1 || data.has_next) && <div className="flex gap-3">
      <button type="button" disabled={page === 1} onClick={() => move(page - 1)} className="min-h-11 px-3 disabled:opacity-50">Previous reports</button>
      <button type="button" disabled={!data.has_next} onClick={() => move(page + 1)} className="min-h-11 px-3 disabled:opacity-50">Next reports</button>
    </div>}
  </div>;
}
