"use client";

import { SparklesIcon } from "@heroicons/react/24/outline";
import { useState } from "react";

import { AiDisclaimer } from "./ai-disclaimer";
import { AiProcessingNotice } from "./ai-context-notice";
import { explainLabReport } from "@/lib/ai/api";
import type { LabReportExplanation as Explanation } from "@/lib/ai/types";

export function LabReportExplanation({ reportId }: { reportId: string }) {
  return <LabReportExplanationContent key={reportId} reportId={reportId} />;
}

function LabReportExplanationContent({ reportId }: { reportId: string }) {
  const [result, setResult] = useState<Explanation | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const explain = async () => {
    if (pending) return;
    setPending(true); setError(""); setResult(null);
    try { setResult(await explainLabReport(reportId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The explanation is unavailable right now."); }
    finally { setPending(false); }
  };
  return <section aria-labelledby="lab-ai-heading" className="rounded-2xl border border-teal-200 bg-teal-50/50 p-5">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-teal-700">Optional AI support</p><h2 className="mt-1 text-lg font-bold" id="lab-ai-heading">Understand these results</h2><p className="mt-1 text-sm leading-6 text-slate-600">Plain-language context only. The finalized laboratory record above remains authoritative.</p></div><button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-teal-300 bg-white px-4 text-sm font-bold text-teal-800 disabled:opacity-60" disabled={pending} onClick={() => void explain()} type="button"><SparklesIcon aria-hidden="true" className="size-5" />{pending ? "Explaining…" : result ? "Explain again" : "Explain with AI"}</button></div>
    <div className="mt-3"><AiProcessingNotice records /></div>
    {error ? <p className="mt-4 text-sm text-rose-700" role="alert">{error}</p> : null}
    {result ? <div className="mt-5 space-y-5" aria-live="polite"><p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{result.summary}</p>{result.parameter_explanations.length ? <div className="grid gap-3">{result.parameter_explanations.map((item, index) => <article className="rounded-xl border border-slate-200 bg-white p-4" key={`${item.parameter}-${index}`}><div className="flex flex-wrap items-baseline justify-between gap-2"><h3 className="font-bold">{item.parameter}</h3><p className="text-sm font-semibold text-slate-700">{item.result}{item.unit ? ` ${item.unit}` : ""}</p></div><p className="mt-2 text-sm leading-6 text-slate-700">{item.explanation}</p>{item.reference_range ? <p className="mt-2 text-xs text-slate-500">Recorded reference range: {item.reference_range}</p> : null}</article>)}</div> : null}{result.flagged_results.length ? <div><h3 className="text-sm font-bold">Results marked for attention in the report</h3><ul className="mt-2 space-y-2 text-sm text-slate-700">{result.flagged_results.map((item, index) => <li className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2" key={`${item.parameter}-${index}`}><span className="font-bold">{item.parameter}:</span> {item.result}{item.unit ? ` ${item.unit}` : ""} <span className="text-xs font-semibold uppercase text-amber-900">({item.flag})</span></li>)}</ul></div> : null}{result.questions_for_clinician.length ? <div><h3 className="text-sm font-bold">Questions for your clinician</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{result.questions_for_clinician.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}<AiDisclaimer>{result.disclaimer}</AiDisclaimer></div> : null}
  </section>;
}
