"use client";

import { SparklesIcon } from "@heroicons/react/24/outline";
import { useState } from "react";

import { AiDisclaimer } from "./ai-disclaimer";
import { AiProcessingNotice, sourceCategoryLabels } from "./ai-context-notice";
import { summarizeMedicalHistory } from "@/lib/ai/api";
import type { MedicalHistorySummary as Summary } from "@/lib/ai/types";

export function MedicalHistorySummary() {
  const [consented, setConsented] = useState(false);
  const [result, setResult] = useState<Summary | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const generate = async () => {
    if (!consented || pending) return;
    setPending(true); setError(""); setResult(null); setConsented(false);
    try { setResult(await summarizeMedicalHistory()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The summary is unavailable right now."); }
    finally { setPending(false); }
  };
  return <section aria-labelledby="history-summary-heading" className="mb-8 rounded-2xl border border-teal-200 bg-teal-50/50 p-5 sm:p-6">
    <div className="flex items-start gap-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-teal-700"><SparklesIcon aria-hidden="true" className="size-5" /></span><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-teal-700">Optional AI support</p><h2 className="mt-1 text-xl font-bold text-slate-950" id="history-summary-heading">Summarize my medical history</h2><p className="mt-2 text-sm leading-6 text-slate-600">Create a temporary plain-language overview from your finalized HealthLink records. This does not change your records.</p></div></div>
    <div className="mt-4"><AiProcessingNotice records /></div>
    <label className="mt-5 flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-700"><input className="mt-1 size-4 shrink-0" checked={consented} disabled={pending} onChange={(event) => setConsented(event.target.checked)} type="checkbox" /><span>I allow HealthLink AI to use my personal medical records for this summary request.</span></label>
    <button className="mt-4 min-h-11 rounded-xl border border-teal-300 bg-white px-5 text-sm font-bold text-teal-800 disabled:cursor-not-allowed disabled:opacity-50" disabled={!consented || pending} onClick={() => void generate()} type="button">{pending ? "Preparing summary…" : result ? "Refresh AI summary" : "Generate AI summary"}</button>
    {error ? <p className="mt-4 text-sm text-rose-700" role="alert">{error}</p> : null}
    {result ? <div className="mt-5 space-y-5 rounded-2xl border border-slate-200 bg-white p-5" aria-live="polite"><div><h3 className="font-bold">Overview</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{result.summary}</p></div>{result.record_observations.length ? <div><h3 className="font-bold">Key points from your record</h3><ul className="mt-2 space-y-3">{result.record_observations.map((point, index) => <li className="text-sm leading-6 text-slate-700" key={`${point.statement}-${index}`}><p>{point.statement}</p>{point.source_categories.length ? <p className="mt-1 text-xs font-semibold text-slate-500">Source: {sourceCategoryLabels(point.source_categories)}</p> : null}</li>)}</ul></div> : null}{result.questions_for_clinician.length ? <div><h3 className="font-bold">Questions for your clinician</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{result.questions_for_clinician.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}<AiDisclaimer>{result.disclaimer}</AiDisclaimer></div> : null}
  </section>;
}
