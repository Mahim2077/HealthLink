"use client";

import { useEffect, useRef, useState } from "react";
import { createDiagnosticTest } from "@/lib/diagnostics/api";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import { TechnicianSelector } from "./technician-selector";

export function DiagnosticRequestPanel({ visitId, disabled = false, onEditStateChange }: {
  visitId: string; disabled?: boolean;
  onEditStateChange: (value: { dirty: boolean; saving: boolean }) => void;
}) {
  const [name, setName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [assignee, setAssignee] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const dirty = Boolean(name || instructions || assignee);
  useUnsavedChanges(dirty || pending);
  useEffect(() => { onEditStateChange({ dirty, saving: pending }); }, [dirty, pending, onEditStateChange]);
  return <section className="rounded-2xl border border-sky-200 bg-sky-50/50 p-5">
    <h2 className="text-lg font-bold text-slate-950">Request a diagnostic test</h2>
    <p className="mt-1 text-sm text-slate-600">Create a request for this patient. Submit or clear unfinished requests before finishing the appointment.</p>
    <form className="mt-4 space-y-4" onSubmit={async event => {
      event.preventDefault();
      if (inFlight.current || disabled) return;
      inFlight.current = true; setPending(true); setNotice(""); setError("");
      try {
        await createDiagnosticTest({ visit_id: visitId, test_name: name, instructions: instructions || null, assigned_to_role_registration_id: assignee || null });
        setName(""); setInstructions(""); setAssignee(""); setNotice("Diagnostic test requested.");
      } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to request diagnostic test"); }
      finally { inFlight.current = false; setPending(false); }
    }}>
      <fieldset disabled={pending || disabled} className="space-y-4 disabled:opacity-60">
        <label className="block text-sm font-semibold text-slate-700">Test name
          <input className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3" required maxLength={255} value={name} onChange={event => setName(event.target.value)} />
        </label>
        <TechnicianSelector visitId={visitId} value={assignee} onChange={setAssignee} disabled={pending || disabled} />
        <label className="block text-sm font-semibold text-slate-700">Instructions
          <textarea className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2" rows={2} value={instructions} onChange={event => setInstructions(event.target.value)} />
        </label>
        <div className="flex gap-3">
          <button className="min-h-11 rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" type="submit">{pending ? "Requesting…" : "Request test"}</button>
          <button className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm" type="button" onClick={() => { setName(""); setInstructions(""); setAssignee(""); setError(""); }}>Clear request</button>
        </div>
      </fieldset>
      {error ? <p role="alert" className="text-sm text-rose-700">{error}</p> : null}
      {notice ? <p role="status" className="text-sm text-emerald-700">{notice}</p> : null}
    </form>
  </section>;
}
