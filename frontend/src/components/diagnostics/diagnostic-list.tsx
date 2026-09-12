"use client";

import { BeakerIcon } from "@heroicons/react/24/outline";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { assignDiagnosticTest } from "@/lib/diagnostics/api";
import type { DiagnosticStatus, DiagnosticTest, DiagnosticTestList } from "@/lib/diagnostics/types";
import { TechnicianSelector } from "./technician-selector";

function AssignmentEditor({ test, onSaved, disabled }: {
  test: DiagnosticTest; onSaved: (test: DiagnosticTest) => void; disabled: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [assignee, setAssignee] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  return <div className="mt-4">
    <button type="button" disabled={disabled || pending} className="min-h-11 rounded-xl border border-sky-200 px-4 text-sm font-bold text-sky-800"
      onClick={() => setEditing(value => !value)}>{editing ? "Close assignment" : "Assign technician"}</button>
    {editing ? <form className="mt-3 space-y-3" onSubmit={async event => {
      event.preventDefault();
      if (inFlight.current || disabled) return;
      inFlight.current = true; setPending(true); setError("");
      try { const updated = await assignDiagnosticTest(test.id, assignee || null); onSaved(updated); setEditing(false); }
      catch (reason) { setError(reason instanceof Error ? reason.message : "Assignment could not be saved."); }
      finally { inFlight.current = false; setPending(false); }
    }}>
      <TechnicianSelector testId={test.id} value={assignee} onChange={setAssignee} disabled={pending || disabled} />
      <button type="submit" disabled={pending || disabled} className="min-h-11 rounded-xl bg-sky-700 px-4 text-sm font-bold text-white">{pending ? "Saving…" : "Save assignment"}</button>
      {error ? <p role="alert" className="text-sm text-rose-700">{error}</p> : null}
    </form> : null}
  </div>;
}

export function DiagnosticList({ loadAction, transitionAction, role }: {
  loadAction: () => Promise<DiagnosticTestList>;
  transitionAction?: (id: string, status: DiagnosticStatus) => Promise<unknown>;
  role: "citizen" | "doctor" | "lab";
}) {
  const [data, setData] = useState<DiagnosticTestList | null>(null);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [version, setVersion] = useState(0);
  const [pending, setPending] = useState("");
  const inFlight = useRef(false);
  useEffect(() => {
    let active = true;
    void loadAction().then(value => { if (active) { setData(value); setError(""); } },
      reason => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load diagnostic tests"); });
    return () => { active = false; };
  }, [loadAction, version]);
  const transition = async (id: string, status: DiagnosticStatus) => {
    if (!transitionAction || inFlight.current) return;
    if (status === "CANCELLED" && !window.confirm("Cancel this diagnostic request?")) return;
    inFlight.current = true; setPending(id); setActionError("");
    try { await transitionAction(id, status); setData(null); setVersion(value => value + 1); }
    catch (reason) { setActionError(reason instanceof Error ? reason.message : "Unable to update diagnostic test"); }
    finally { inFlight.current = false; setPending(""); }
  };
  if (error) return <ErrorState message={error} onAction={() => { setData(null); setError(""); setVersion(value => value + 1); }} title="Diagnostic tests unavailable" />;
  if (!data) return <LoadingState label="Loading diagnostic tests" description="Fetching diagnostic requests." />;
  if (!data.tests.length) return <EmptyState icon={<BeakerIcon aria-hidden="true" className="size-6" />} title="No diagnostic tests" message="No diagnostic requests are available for this account." />;
  return <div className="space-y-4">
    {actionError ? <p role="alert" className="rounded-xl bg-rose-50 p-3 text-rose-800">{actionError}</p> : null}
    {data.tests.map(test => <article className="hl-card p-5" key={test.id}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-950">{test.test_name}</h2>
          <p className="mt-1 text-sm text-slate-600">Requested by Dr {test.requested_by_name}{test.facility_name ? " · " + test.facility_name : ""}</p>
          {test.instructions ? <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{test.instructions}</p> : null}
          <p className="mt-2 text-xs text-slate-500">Assigned to: {test.assigned_to_name ?? "Not assigned"}</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{test.status.replace("_", " ")}</span>
      </div>
      {role === "lab" && transitionAction && test.status === "REQUESTED" ? <button type="button" className="mt-4 min-h-11 rounded-xl bg-sky-700 px-4 text-sm font-bold text-white disabled:opacity-50" disabled={Boolean(pending)} onClick={() => void transition(test.id, "IN_PROGRESS")}>Begin work</button> : null}
      {role === "lab" && ["IN_PROGRESS", "COMPLETED"].includes(test.status) ? <Link className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-4 text-sm font-bold text-white" href={`/professional/diagnostics/${test.id}/report`}>Open lab report</Link> : null}
      {role === "citizen" && test.status === "COMPLETED" ? <Link className="mt-4 inline-flex min-h-11 items-center text-sm font-bold text-sky-800 underline" href={`/citizen/lab-reports/${test.id}`}>View lab report</Link> : null}
      {role === "doctor" && test.status === "REQUESTED" ? <>
        <AssignmentEditor test={test} disabled={Boolean(pending)} onSaved={updated => setData(current => current ? { tests: current.tests.map(item => item.id === updated.id ? updated : item) } : current)} />
        {transitionAction ? <button type="button" className="mt-4 min-h-11 rounded-xl border border-rose-200 px-4 text-sm font-bold text-rose-700 disabled:opacity-50" disabled={Boolean(pending)} onClick={() => void transition(test.id, "CANCELLED")}>Cancel request</button> : null}
      </> : null}
    </article>)}
  </div>;
}
