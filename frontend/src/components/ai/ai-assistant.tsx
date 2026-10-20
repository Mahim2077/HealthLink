"use client";

import { useState, type FormEvent } from "react";
import { AiDisclaimer } from "./ai-disclaimer";
import { AiProcessingNotice } from "./ai-context-notice";
import { ChatWorkbench } from "./chat-workbench";
import { requestSymptomGuidance } from "@/lib/ai/api";
import type { SymptomGuidance } from "@/lib/ai/types";

const INPUT_CLASS = "mt-2 block min-h-32 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal leading-6 outline-none focus:border-teal-700 focus:ring-4 focus:ring-teal-100 disabled:bg-slate-100";
const BUTTON_CLASS = "min-h-11 rounded-xl bg-teal-700 px-5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50";
const URGENCY_LABELS: Record<string, string> = {
  SELF_CARE_INFORMATION: "General self-care information",
  ROUTINE_CLINICAL_REVIEW: "Routine clinician review",
  PROMPT_CLINICAL_REVIEW: "Prompt clinician review",
  URGENT_OR_EMERGENCY_EVALUATION: "Urgent or emergency evaluation",
};
export function AiAssistant() {
  return <ChatWorkbench symptomPanel={<SymptomPanel />} />;
}

function SymptomPanel() {
  const [symptoms, setSymptoms] = useState("");
  const [result, setResult] = useState<SymptomGuidance | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = symptoms.trim();
    if (value.length < 3 || pending) return;
    setPending(true);
    setError("");
    setResult(null);
    try { setResult(await requestSymptomGuidance(value)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Symptom guidance is unavailable right now."); }
    finally { setPending(false); }
  }

  return (
    <>
      <header>
        <h2 className="text-xl font-bold">Symptom guidance</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Describe what you notice for general safety guidance and possible next steps. This tool does not diagnose a condition.</p>
      </header>
      <p className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-900">If you think this is an emergency, seek urgent medical help now. Do not wait for an AI response.</p>
      <form className="mt-6 space-y-4" onSubmit={submit}>
        <AiProcessingNotice />
        <label className="block text-sm font-bold text-slate-800">
          Describe your symptoms
          <textarea className={INPUT_CLASS} disabled={pending} minLength={3} maxLength={1500} onChange={(event) => { setSymptoms(event.target.value); setResult(null); setError(""); }} placeholder="Include what you feel, when it started, and whether it is changing." required value={symptoms} />
        </label>
        <div className="flex justify-end"><button className={BUTTON_CLASS} disabled={pending || symptoms.trim().length < 3} type="submit">{pending ? "Reviewing symptoms…" : "Get general guidance"}</button></div>
      </form>
      {error ? <p className="mt-5 text-sm text-rose-700" role="alert">{error}</p> : null}
      {result ? (
        <div className="mt-6 space-y-5 rounded-2xl border border-slate-200 bg-slate-50 p-5" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-bold">Guidance</h3><span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">{URGENCY_LABELS[result.urgency_category] ?? "Discuss with a clinician"}</span></div>
          <p className="text-sm leading-6 text-slate-700">{result.symptom_summary}</p>
          {result.general_information.length ? <div><h4 className="text-sm font-bold">General information</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{result.general_information.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
          {result.red_flags.length ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4"><h4 className="text-sm font-bold text-rose-900">Seek urgent help if you notice</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-rose-900">{result.red_flags.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
          <div><h4 className="text-sm font-bold">Suggested next step</h4><p className="mt-2 text-sm leading-6 text-slate-700">{result.suggested_next_step}</p></div>
          <AiDisclaimer>{result.disclaimer}</AiDisclaimer>
        </div>
      ) : null}
    </>
  );
}
