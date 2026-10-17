"use client";

import { SparklesIcon } from "@heroicons/react/24/outline";
import { useState } from "react";

import { AiDisclaimer } from "./ai-disclaimer";
import { AiProcessingNotice } from "./ai-context-notice";
import { explainPrescription } from "@/lib/ai/api";
import type { PrescriptionExplanation as Explanation } from "@/lib/ai/types";

export function PrescriptionExplanation({ prescriptionId }: { prescriptionId: string }) {
  return <PrescriptionExplanationContent key={prescriptionId} prescriptionId={prescriptionId} />;
}

function PrescriptionExplanationContent({ prescriptionId }: { prescriptionId: string }) {
  const [result, setResult] = useState<Explanation | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const explain = async () => {
    if (pending) return;
    setPending(true);
    setError("");
    setResult(null);
    try {
      setResult(await explainPrescription(prescriptionId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The explanation is unavailable right now.");
    } finally {
      setPending(false);
    }
  };

  return (
    <section aria-labelledby="prescription-ai-heading" className="mt-6 rounded-2xl border border-teal-200 bg-teal-50/50 p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-teal-700">Optional AI support</p>
          <h3 className="mt-1 font-bold text-slate-950" id="prescription-ai-heading">Understand this prescription</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">Understand the recorded prescription and learn about medicine purposes. AI does not prescribe or replace your doctor.</p>
          <div className="mt-2"><AiProcessingNotice records /></div>
        </div>
        <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-teal-300 bg-white px-4 text-sm font-bold text-teal-800 disabled:opacity-60" disabled={pending} onClick={() => void explain()} type="button">
          <SparklesIcon aria-hidden="true" className="size-5" />
          {pending ? "Explaining…" : result ? "Explain again" : "Explain with AI"}
        </button>
      </div>
      {error ? <p className="mt-4 text-sm text-rose-700" role="alert">{error}</p> : null}
      {result ? (
        <div className="mt-5 space-y-5" aria-live="polite">
          <div><h4 className="text-sm font-bold text-slate-900">Plain-language summary</h4><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{result.plain_language_summary}</p></div>
          {result.medicine_explanations.length ? <div><h4 className="text-sm font-bold text-slate-900">Medicines</h4><div className="mt-2 grid gap-3">{result.medicine_explanations.map((medicine, index) => <article className="rounded-xl border border-slate-200 bg-white p-4" key={`${medicine.medicine_name}-${index}`}><h5 className="font-bold text-slate-950">{medicine.medicine_name}</h5>{medicine.general_education ? <div className="mt-2"><h6 className="text-sm font-semibold text-slate-900">General medicine knowledge</h6><p className="mt-1 text-sm text-slate-700">{medicine.general_education}</p><p className="mt-1 text-xs text-slate-600">General education, not a confirmed reason for your prescription.</p></div> : null}<p className="mt-2 text-sm text-slate-700">{medicine.purpose_or_role}</p><p className="mt-2 text-xs font-semibold text-slate-600">Doctor&apos;s recorded instructions (unchanged): {medicine.recorded_instructions}</p></article>)}</div></div> : null}
          {result.questions_to_ask_clinician.length ? <div><h4 className="text-sm font-bold text-slate-900">Questions for your clinician</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{result.questions_to_ask_clinician.map((question) => <li key={question}>{question}</li>)}</ul></div> : null}
          <AiDisclaimer>{result.disclaimer}</AiDisclaimer>
        </div>
      ) : null}
    </section>
  );
}
