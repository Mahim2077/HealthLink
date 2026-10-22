"use client";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { listLabTrends, type LabTrendPoint } from "@/lib/diagnostics/report-api";

export function LabTrendTables({ points }: { points: LabTrendPoint[] }) {
  const groups = new Map<string, LabTrendPoint[]>();
  for (const point of points) {
    // Exact parameter and unit identity: never convert or combine incompatible units.
    const key = JSON.stringify([point.parameter_name, point.unit]);
    groups.set(key, [...(groups.get(key) ?? []), point]);
  }
  return <div className="space-y-4">{[...groups].map(([key, values]) => <section aria-label={`${values[0].parameter_name} trend table`} tabIndex={0} className="hl-card hl-scrollbar overflow-x-auto p-4" key={key}>
    <table className="w-full text-left text-sm">
      <caption className="mb-3 text-left font-bold">{values[0].parameter_name} — {values[0].unit ?? "Unit not recorded"}</caption>
      <thead><tr><th scope="col" className="p-2">Report date</th><th scope="col" className="p-2">Numeric result</th><th scope="col" className="p-2">Unit</th></tr></thead>
      <tbody>{values.map((point, index) => <tr className="border-t border-slate-200" key={`${point.report_id}-${index}`}><td className="p-2">{point.report_date}</td><td className="p-2">{point.value}</td><td className="p-2">{point.unit ?? "Not recorded"}</td></tr>)}</tbody>
    </table>
  </section>)}</div>;
}

export function CitizenDiagnosticTrends() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LabTrendPoint[] | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    void listLabTrends(page).then(value => {
      if (active) {
        setData(value);
        setError("");
      }
    }, reason => { if (active) setError(reason instanceof Error ? reason.message : "Results unavailable."); });
    return () => { active = false; };
  }, [page, version]);

  return <section aria-labelledby="result-trends-heading" className="space-y-5" id="result-trends">
    <div>
      <h2 className="text-2xl font-bold text-slate-950" id="result-trends-heading">Numeric result trends</h2>
      <p className="mt-2 text-sm text-slate-600">Finalized numeric results in chronological order, grouped by parameter and exact unit. These tables do not interpret results or establish a diagnosis.</p>
    </div>
    {error ? <ErrorState title="Result trends unavailable" message={error} onAction={() => { setData(null); setError(""); setVersion(v => v + 1); }} /> : !data ? <LoadingState label="Loading result trends" /> : <div className="space-y-5">
      {!data.length ? <EmptyState title="No numeric results" message="Finalized numeric diagnostic results will appear here." /> : <LabTrendTables points={data} />}
      <nav aria-label="Result trend pages" className="flex items-center gap-4">
      <button className="min-h-11 rounded-xl border px-4 disabled:opacity-50" disabled={page === 1} onClick={() => { setData(null); setPage(p => p - 1); }}>Previous</button>
      <span>Page {page}</span>
        <button className="min-h-11 rounded-xl border px-4 disabled:opacity-50" disabled={data.length < 100} onClick={() => { setData(null); setPage(p => p + 1); }}>Next</button>
      </nav>
    </div>}
  </section>;
}
