"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import { loadProfessionalMe } from "@/lib/professional/api";
import { finalizeLabReport, readLabReport, saveLabReport, type LabDraft, type LabItem, type LabReport } from "@/lib/diagnostics/report-api";

const inputClass = "mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2";
const buttonClass = "min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold disabled:opacity-50";
const emptyItem = (): LabItem => ({ parameter_name: "", result_value_text: "", result_value_numeric: null, unit: null, reference_range: null, flag: null });

export function LabPortalGate({ portal, children }: { portal: "CITIZEN" | "PROFESSIONAL"; children: ReactNode }) {
  const auth = usePortalAuth(portal);
  const { status, refreshSession } = auth;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);
  if (status !== "authenticated") return failed ? <EmptyState title="Sign in required" message="Sign in to view lab reports." action={<Link href={`/${portal.toLowerCase()}/login`}>Sign in</Link>} /> : <LoadingState label="Checking session" />;
  if (!auth.isRequiredPortal) return <EmptyState title="Portal access required" message="This session belongs to another HealthLink portal." />;
  return <div key={auth.claims?.sid}>{children}</div>;
}

export function LabResults({ report }: { report: LabReport }) {
  return <section className="hl-card space-y-4 p-5">
    <h2 className="text-xl font-bold">{report.test_name}</h2>
    <p className="text-sm text-slate-600">{report.report_date} · {report.facility_name ?? "Facility not recorded"} · {report.status}</p>
    {report.summary ? <p className="whitespace-pre-wrap">{report.summary}</p> : null}
    <div className="overflow-x-auto"><table className="w-full text-left text-sm">
      <caption className="sr-only">Lab report results</caption>
      <thead><tr>{["Parameter", "Result", "Numeric result", "Unit", "Reference range", "Flag"].map(label => <th scope="col" className="p-3" key={label}>{label}</th>)}</tr></thead>
      <tbody>{report.items.map((item, index) => <tr className="border-t border-slate-200" key={index}>
        <th scope="row" className="p-3">{item.parameter_name}</th>
        {[item.result_value_text, item.result_value_numeric, item.unit, item.reference_range, item.flag].map((value, column) => <td className="p-3" key={column}>{value ?? "—"}</td>)}
      </tr>)}</tbody>
    </table></div>
  </section>;
}

export function LabReportEditor({ testId, initial }: { testId: string; initial: LabReport | null }) {
  const [report, setReport] = useState(initial);
  const [draft, setDraft] = useState<LabDraft>(() => initial ?? { report_date: "", summary: null, items: [emptyItem()] });
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const inFlight = useRef(false);
  useUnsavedChanges(dirty || pending);
  const update = (value: LabDraft) => { setDraft(value); setDirty(true); setNotice(""); };
  const perform = async (finalize: boolean) => {
    if (inFlight.current || (finalize && (dirty || !report))) return;
    if (finalize && !window.confirm("Finalize this lab report? Results will become visible to the citizen and cannot be edited. This also completes the diagnostic test.")) return;
    inFlight.current = true; setPending(true); setError(""); setNotice("");
    try {
      const saved = await (finalize ? finalizeLabReport(testId) : saveLabReport(testId, { report_date: draft.report_date, summary: draft.summary, items: draft.items }));
      setReport(saved); setDraft(saved); setDirty(false); setNotice(finalize ? "Report finalized. Diagnostic test completed." : "Draft saved. Review before finalizing.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The report could not be saved. Your changes are retained."); }
    finally { inFlight.current = false; setPending(false); }
  };
  if (report?.status === "FINALIZED") return <><p role="status" className="mb-4 text-emerald-800">Finalized report — read only.</p><LabResults report={report} /></>;
  return <form className="hl-card space-y-5 p-5" onSubmit={event => { event.preventDefault(); void perform(false); }}>
    <h2 className="text-xl font-bold">{report?.test_name ?? "New lab report"}</h2>
    <p className="text-sm text-slate-600">Save a draft, review all results, then finalize. Drafts are not visible to citizens.</p>
    <fieldset disabled={pending} className="space-y-5 disabled:opacity-60">
      <label className="block text-sm font-semibold">Report date<input className={inputClass} type="date" required value={draft.report_date} onChange={e => update({ ...draft, report_date: e.target.value })} /></label>
      <label className="block text-sm font-semibold">Summary<textarea className={inputClass} maxLength={10000} value={draft.summary ?? ""} onChange={e => update({ ...draft, summary: e.target.value || null })} /></label>
      {draft.items.map((item, index) => <fieldset className="rounded-xl border border-slate-200 p-4" key={index}>
        <legend className="px-2 font-semibold">Result {index + 1}</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {([
            ["parameter_name", "Parameter", 150], ["result_value_text", "Result", 500], ["result_value_numeric", "Numeric result (optional)", 30],
            ["unit", "Unit", 50], ["reference_range", "Reference range", 150], ["flag", "Flag", 50],
          ] as const).map(([field, label, maxLength]) => <label className="block text-sm font-semibold" key={field}>{label}<input
            className={inputClass} maxLength={maxLength} required={field === "parameter_name" || field === "result_value_text"}
            inputMode={field === "result_value_numeric" ? "decimal" : undefined} value={item[field] ?? ""}
            onChange={e => update({ ...draft, items: draft.items.map((row, rowIndex) => rowIndex === index ? { ...row, [field]: e.target.value || (field === "parameter_name" || field === "result_value_text" ? "" : null) } : row) })}
          /></label>)}
        </div>
        <button className={`${buttonClass} mt-4`} type="button" disabled={draft.items.length === 1} onClick={() => update({ ...draft, items: draft.items.filter((_, i) => i !== index) })}>Remove result {index + 1}</button>
      </fieldset>)}
      <button type="button" className={buttonClass} disabled={draft.items.length >= 100} onClick={() => update({ ...draft, items: [...draft.items, emptyItem()] })}>Add result</button>
      <div className="flex flex-wrap gap-3">
        <button className={`${buttonClass} bg-sky-700 text-white`} type="submit">{pending ? "Saving…" : "Save draft"}</button>
        <button className={`${buttonClass} bg-emerald-700 text-white`} type="button" disabled={dirty || !report} onClick={() => void perform(true)}>Finalize report</button>
      </div>
    </fieldset>
    {dirty ? <p className="text-sm text-amber-800">Unsaved changes — save before finalizing.</p> : null}
    {error ? <p role="alert" className="text-rose-700">{error}</p> : null}
    {notice ? <p role="status" className="text-emerald-800">{notice}</p> : null}
  </form>;
}

function ReportLoader({ testId, portal }: { testId: string; portal: "CITIZEN" | "PROFESSIONAL" }) {
  const [loaded, setLoaded] = useState<{ report: LabReport | null; canEdit: boolean } | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    void Promise.all([readLabReport(testId), portal === "PROFESSIONAL" ? loadProfessionalMe() : Promise.resolve(null)]).then(([report, me]) => {
      if (active) setLoaded({ report, canEdit: me?.role_code === "LAB_TECHNICIAN" && me.verification_status === "VERIFIED" });
    }, reason => { if (active) setError(reason instanceof Error ? reason.message : "Report unavailable."); });
    return () => { active = false; };
  }, [testId, portal, version]);
  if (error) return <ErrorState title="Report unavailable" message={error} onAction={() => { setError(""); setVersion(v => v + 1); }} />;
  if (!loaded) return <LoadingState label="Loading lab report" />;
  if (loaded.canEdit) return <LabReportEditor testId={testId} initial={loaded.report} />;
  return loaded.report ? <LabResults report={loaded.report} /> : <EmptyState title="Report not available" message="A finalized report is not available for this test." />;
}

export function LabReportPage({ testId, portal }: { testId: string; portal: "CITIZEN" | "PROFESSIONAL" }) {
  return <main id="main-content" className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-5 py-10 sm:px-8">
    <Link href={portal === "CITIZEN" ? "/citizen/lab-reports" : "/professional/diagnostics"} className="text-sm font-semibold text-sky-800">Back to {portal === "CITIZEN" ? "lab reports" : "diagnostics"}</Link>
    <h1 className="text-3xl font-bold">Lab report</h1>
    <LabPortalGate portal={portal}><ReportLoader key={testId} testId={testId} portal={portal} /></LabPortalGate>
  </main>;
}
