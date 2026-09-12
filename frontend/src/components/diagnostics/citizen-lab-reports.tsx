"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { listLabReports, listLabTrends, type LabReport, type LabTrendPoint } from "@/lib/diagnostics/report-api";
import { LabPortalGate } from "./lab-report-page";

export function LabTrendTables({ points }: { points: LabTrendPoint[] }) {
  const groups = new Map<string, LabTrendPoint[]>();
  for (const point of points) {
    // Exact parameter and unit identity: never convert or combine incompatible units.
    const key = JSON.stringify([point.parameter_name, point.unit]);
    groups.set(key, [...(groups.get(key) ?? []), point]);
  }
  return <div className="space-y-4">{[...groups].map(([key, values]) => <section className="hl-card overflow-x-auto p-4" key={key}>
    <table className="w-full text-left text-sm">
      <caption className="mb-3 text-left font-bold">{values[0].parameter_name} — {values[0].unit ?? "Unit not recorded"}</caption>
      <thead><tr><th scope="col" className="p-2">Report date</th><th scope="col" className="p-2">Numeric result</th><th scope="col" className="p-2">Unit</th></tr></thead>
      <tbody>{values.map((point, index) => <tr className="border-t border-slate-200" key={`${point.report_id}-${index}`}><td className="p-2">{point.report_date}</td><td className="p-2">{point.value}</td><td className="p-2">{point.unit ?? "Not recorded"}</td></tr>)}</tbody>
    </table>
  </section>)}</div>;
}

function ReportCollection({ trends }: { trends: boolean }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LabReport[] | LabTrendPoint[] | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    void (trends ? listLabTrends(page) : listLabReports(page)).then(value => { if (active) setData(value); }, reason => { if (active) setError(reason instanceof Error ? reason.message : "Results unavailable."); });
    return () => { active = false; };
  }, [trends, page, version]);
  if (error) return <ErrorState message={error} onAction={() => { setError(""); setVersion(v => v + 1); }} />;
  if (!data) return <LoadingState label="Loading lab results" />;
  return <div className="space-y-5">
    {!data.length ? <EmptyState title="No lab results" message="There are no finalized results on this page." /> : trends ? <LabTrendTables points={data as LabTrendPoint[]} /> : <div className="space-y-4">{(data as LabReport[]).map(report => <article key={report.id} className="hl-card p-5">
      <h2 className="text-lg font-bold"><Link className="text-sky-800 underline" href={`/citizen/lab-reports/${report.diagnostic_test_id}`}>{report.test_name}</Link></h2>
      <p className="mt-2 text-sm text-slate-600">{report.report_date} · {report.facility_name ?? "Facility not recorded"} · Finalized</p>
    </article>)}</div>}
    <nav aria-label="Result pages" className="flex items-center gap-4">
      <button className="min-h-11 rounded-xl border px-4 disabled:opacity-50" disabled={page === 1} onClick={() => { setData(null); setPage(p => p - 1); }}>Previous</button>
      <span>Page {page}</span>
      <button className="min-h-11 rounded-xl border px-4 disabled:opacity-50" disabled={data.length < (trends ? 100 : 20)} onClick={() => { setData(null); setPage(p => p + 1); }}>Next</button>
    </nav>
  </div>;
}

export function CitizenLabReports({ trends = false }: { trends?: boolean }) {
  return <main id="main-content" className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-5 py-10 sm:px-8">
    <h1 className="text-3xl font-bold">{trends ? "Lab result trends" : "My lab reports"}</h1>
    <p className="text-sm text-slate-600">{trends ? "Finalized numeric results in chronological order, grouped by parameter and exact unit. These tables do not interpret results or establish a diagnosis." : "Your finalized reports. Draft reports remain private to the assigned lab technician."}</p>
    <Link className="inline-block min-h-11 text-sm font-semibold text-sky-800 underline" href={trends ? "/citizen/lab-reports" : "/citizen/lab-trends"}>{trends ? "View reports" : "View numeric trends"}</Link>
    <LabPortalGate portal="CITIZEN"><ReportCollection key={String(trends)} trends={trends} /></LabPortalGate>
  </main>;
}
