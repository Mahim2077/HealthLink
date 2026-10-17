"use client";

import { ChatBubbleLeftRightIcon, HeartIcon } from "@heroicons/react/24/outline";
import { useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { AiDisclaimer } from "./ai-disclaimer";
import { AiProcessingNotice, sourceCategoryLabels } from "./ai-context-notice";
import { askAi, requestSymptomGuidance } from "@/lib/ai/api";
import type { AiChatResponse, ChatMode, SymptomGuidance } from "@/lib/ai/types";

type Tab = "CHAT" | "SYMPTOMS";
const TABS: Tab[] = ["CHAT", "SYMPTOMS"];
const INPUT_CLASS = "mt-2 block min-h-32 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal leading-6 outline-none focus:border-teal-700 focus:ring-4 focus:ring-teal-100 disabled:bg-slate-100";
const BUTTON_CLASS = "min-h-11 rounded-xl bg-teal-700 px-5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50";
const URGENCY_LABELS: Record<string, string> = {
  SELF_CARE_INFORMATION: "General self-care information",
  ROUTINE_CLINICAL_REVIEW: "Routine clinician review",
  PROMPT_CLINICAL_REVIEW: "Prompt clinician review",
  URGENT_OR_EMERGENCY_EVALUATION: "Urgent or emergency evaluation",
};

export function AiAssistant() {
  const [tab, setTab] = useState<Tab>("CHAT");
  const id = useId();
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);

  function navigateTabs(event: KeyboardEvent<HTMLButtonElement>) {
    const current = TABS.indexOf(tab);
    let index: number;
    if (event.key === "ArrowRight") index = (current + 1) % TABS.length;
    else if (event.key === "ArrowLeft") index = (current + TABS.length - 1) % TABS.length;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = TABS.length - 1;
    else return;
    event.preventDefault();
    setTab(TABS[index]);
    buttons.current[index]?.focus();
  }

  return (
    <div className="space-y-6">
      <div className="inline-flex w-full rounded-xl border border-slate-200 bg-slate-100 p-1 sm:w-auto" role="tablist" aria-label="AI assistant tools">
        {TABS.map((item, index) => (
          <button
            key={item}
            ref={(button) => { buttons.current[index] = button; }}
            id={`${id}-${item}-tab`}
            aria-controls={`${id}-${item}-panel`}
            aria-selected={tab === item}
            tabIndex={tab === item ? 0 : -1}
            className={`inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold transition sm:flex-none ${tab === item ? "bg-white text-teal-800 shadow-sm" : "text-slate-600"}`}
            onClick={() => setTab(item)}
            onKeyDown={navigateTabs}
            role="tab"
            type="button"
          >
            {item === "CHAT" ? <ChatBubbleLeftRightIcon aria-hidden="true" className="size-5" /> : <HeartIcon aria-hidden="true" className="size-5" />}
            {item === "CHAT" ? "Ask HealthLink AI" : "Symptom guidance"}
          </button>
        ))}
      </div>
      <section className="hl-card p-5 sm:p-7" role="tabpanel" id={`${id}-${tab}-panel`} aria-labelledby={`${id}-${tab}-tab`} tabIndex={0}>
        {tab === "CHAT" ? <ChatPanel /> : <SymptomPanel />}
      </section>
    </div>
  );
}

function ChatPanel() {
  const [mode, setMode] = useState<ChatMode>("GENERAL");
  const [consented, setConsented] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<AiChatResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  function changeMode(nextMode: ChatMode) {
    setMode(nextMode);
    setConsented(false);
    setResult(null);
    setError("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = message.trim();
    if (content.length < 3 || pending || (mode === "RECORD_AWARE" && !consented)) return;
    setPending(true);
    setError("");
    setResult(null);
    // Consent is consumed by this attempt, not retained for the next request.
    setConsented(false);
    try {
      setResult(await askAi({ mode, message: content, use_my_health_records: mode === "RECORD_AWARE" }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "HealthLink AI is unavailable right now.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <header>
        <h2 className="text-xl font-bold">Ask a health question</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Choose general information or allow a one-time, record-aware response. This assistant cannot diagnose or prescribe.</p>
      </header>
      <form className="mt-6 space-y-5" onSubmit={submit}>
        <fieldset disabled={pending}>
          <legend className="text-sm font-bold text-slate-800">Response context</legend>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            <ModeOption checked={mode === "GENERAL"} description="General educational information without reading your medical records." label="General" onChange={() => changeMode("GENERAL")} />
            <ModeOption checked={mode === "RECORD_AWARE"} description="Use your finalized HealthLink records to make the guidance more relevant." label="Use my records" onChange={() => changeMode("RECORD_AWARE")} />
          </div>
        </fieldset>
        <AiProcessingNotice records={mode === "RECORD_AWARE"} />
        {mode === "RECORD_AWARE" ? (
          <label className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
            <input className="mt-1 size-4 shrink-0" checked={consented} disabled={pending} onChange={(event) => { setConsented(event.target.checked); setResult(null); }} type="checkbox" />
            <span>I allow HealthLink AI to use my personal medical records for this request.</span>
          </label>
        ) : null}
        <label className="block text-sm font-bold text-slate-800">
          Your question
          <textarea className={INPUT_CLASS} disabled={pending} minLength={3} maxLength={1500} onChange={(event) => { setMessage(event.target.value); setResult(null); setError(""); setConsented(false); }} placeholder="For example: What should I ask my doctor at my next visit?" required value={message} />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-500">Each question is answered independently. Responses are not saved as chat history on this device.</p>
          <button className={BUTTON_CLASS} disabled={pending || message.trim().length < 3 || (mode === "RECORD_AWARE" && !consented)} type="submit">{pending ? "Preparing response…" : "Ask HealthLink AI"}</button>
        </div>
      </form>
      {error ? <p className="mt-5 text-sm text-rose-700" role="alert">{error}</p> : null}
      {result ? <ChatResult result={result} /> : null}
    </>
  );
}

function ModeOption({ checked, description, label, onChange }: { checked: boolean; description: string; label: string; onChange: () => void }) {
  return (
    <label className={`flex cursor-pointer gap-3 rounded-xl border p-4 ${checked ? "border-teal-500 bg-teal-50" : "border-slate-200 bg-white"}`}>
      <input checked={checked} className="mt-1 size-4" name="ai-mode" onChange={onChange} type="radio" />
      <span><span className="block font-bold text-slate-900">{label}</span><span className="mt-1 block text-sm leading-5 text-slate-600">{description}</span></span>
    </label>
  );
}

function ChatResult({ result }: { result: AiChatResponse }) {
  return (
    <div className="mt-6 space-y-5 rounded-2xl border border-slate-200 bg-slate-50 p-5" aria-live="polite">
      <div><h3 className="font-bold">HealthLink AI response</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{result.answer}</p></div>
      {result.record_observations.length ? (
        <div>
          <h3 className="font-bold">From your HealthLink records</h3>
          <ul className="mt-2 space-y-2 text-sm text-slate-700">
            {result.record_observations.map((item, index) => <li key={`${item.statement}-${index}`}>{item.statement}{item.source_categories.length ? <span className="mt-1 block text-xs font-semibold text-slate-500">Source: {sourceCategoryLabels(item.source_categories)}</span> : null}</li>)}
          </ul>
        </div>
      ) : null}
      <QuestionList questions={result.questions_for_clinician} />
      <AiDisclaimer>{result.disclaimer}</AiDisclaimer>
    </div>
  );
}

function QuestionList({ questions }: { questions: string[] }) {
  if (!questions.length) return null;
  return <div><h3 className="font-bold">Questions for your clinician</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{questions.map((item) => <li key={item}>{item}</li>)}</ul></div>;
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
