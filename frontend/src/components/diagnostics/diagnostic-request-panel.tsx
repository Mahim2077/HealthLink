"use client";

import { useEffect, useRef, useState } from "react";
import { createDiagnosticTest } from "@/lib/diagnostics/api";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import type { TestChoice } from "@/lib/diagnostics/session-api";
import { TestPicker } from "./test-picker";

export function DiagnosticRequestPanel({ visitId, disabled = false, onEditStateChange }: {
  visitId: string; disabled?: boolean;
  onEditStateChange: (value: { dirty: boolean; saving: boolean }) => void;
}) {
  const [test, setTest] = useState<TestChoice | null>(null);
  const [search, setSearch] = useState("");
  const [instructions, setInstructions] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const dirty = Boolean(test || search.trim() || instructions);
  useUnsavedChanges(dirty || pending);
  useEffect(() => { onEditStateChange({ dirty, saving: pending }); }, [dirty, pending, onEditStateChange]);
  return <section className="rounded-2xl border border-sky-200 bg-sky-50/50 p-5">
    <h2 className="text-lg font-bold text-slate-950">Request a diagnostic test</h2>
    <p className="mt-1 text-sm text-slate-600">The patient can arrange the test at a participating facility of their choice.</p>
    <form className="mt-4 space-y-4" onSubmit={async event => {
      event.preventDefault();
      if (inFlight.current || disabled || !test) return;
      inFlight.current = true; setPending(true); setNotice(""); setError("");
      try {
        await createDiagnosticTest({ visit_id: visitId, catalog_code: test.code, instructions: instructions || null });
        setTest(null); setSearch(""); setInstructions(""); setNotice("Diagnostic test requested.");
      } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to request diagnostic test"); }
      finally { inFlight.current = false; setPending(false); }
    }}>
      <fieldset disabled={pending || disabled} className="space-y-4 disabled:opacity-60">
        <TestPicker value={test} onChange={setTest} search={search} onSearchChange={setSearch} />
        <label className="block text-sm font-semibold text-slate-700">Instructions
          <textarea className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2" rows={2} value={instructions} onChange={event => setInstructions(event.target.value)} />
        </label>
        <div className="flex gap-3">
          <button className="min-h-11 rounded-xl bg-sky-700 px-5 text-sm font-bold text-white disabled:opacity-50" type="submit" disabled={!test}>{pending ? "Requesting…" : "Request test"}</button>
          <button className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm" type="button" onClick={() => { setTest(null); setSearch(""); setInstructions(""); setError(""); }}>Clear request</button>
        </div>
      </fieldset>
      {error ? <p role="alert" className="text-sm text-rose-700">{error}</p> : null}
      {notice ? <p role="status" className="text-sm text-emerald-700">{notice}</p> : null}
    </form>
  </section>;
}
