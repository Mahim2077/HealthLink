"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import { listPrescriptionChoices, saveReminder, type PrescriptionChoice, type Reminder, type ReminderInput } from "@/lib/reminders/api";

export const reminderInputClass = "mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2";
export const reminderButtonClass = "min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold disabled:opacity-50";
const blankDraft = (): ReminderInput => ({ medicine: "", prescription_item_id: null, start_date: "", end_date: null, timezone: "Asia/Dhaka", is_active: true, times: [""] });

export function ReminderForm({ initial, onSaved, onCancel }: { initial?: Reminder; onSaved: () => void; onCancel: () => void }) {
  const [draft, setDraft] = useState<ReminderInput>(() => initial ? { medicine: initial.medicine, prescription_item_id: initial.prescription_item_id, start_date: initial.start_date, end_date: initial.end_date, timezone: initial.timezone, is_active: initial.is_active, times: initial.times.map(t => t.slice(0, 5)) } : blankDraft());
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [choices, setChoices] = useState<PrescriptionChoice[]>([]);
  const [choiceError, setChoiceError] = useState("");
  const [choicePage, setChoicePage] = useState(1);
  const [choiceRetry, setChoiceRetry] = useState(0);
  const [moreChoices, setMoreChoices] = useState(false);
  const inFlight = useRef(false);
  useUnsavedChanges(dirty);
  useEffect(() => {
    let active = true;
    void listPrescriptionChoices(choicePage).then(rows => { if (active) { setChoices(previous => [...previous.filter(p => !rows.some(r => r.id === p.id)), ...rows]); setMoreChoices(rows.length === 50); } }, () => { if (active) setChoiceError("Prescription choices could not be loaded. You can still enter a medicine manually."); });
    return () => { active = false; };
  }, [choicePage, choiceRetry]);
  function update(patch: Partial<ReminderInput>) { setDraft(current => ({ ...current, ...patch })); setDirty(true); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current) return;
    if (new Set(draft.times).size !== draft.times.length) { setError("Choose different daily times."); return; }
    if (draft.end_date && draft.end_date < draft.start_date) { setError("End date must be on or after start date."); return; }
    inFlight.current = true; setPending(true); setError("");
    try { await saveReminder(draft, initial?.id); setDirty(false); onSaved(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Reminder could not be saved."); }
    finally { inFlight.current = false; setPending(false); }
  }
  return <form onSubmit={submit} className="hl-card space-y-5 p-5">
    <h2 className="text-xl font-bold">{initial ? "Edit reminder" : "Create medicine reminder"}</h2>
    <p className="text-sm text-slate-600">Times use Asia/Dhaka. Changes apply to future reminders. Follow the schedule agreed with your clinician.</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <fieldset disabled={pending} className="space-y-4">
      <label className="block text-sm font-semibold">Prescription medicine (optional)<select className={reminderInputClass} value={draft.prescription_item_id ?? ""} onChange={e => { const choice = choices.find(c => c.id === e.target.value); update({ prescription_item_id: e.target.value || null, ...(choice ? { medicine: choice.medicine } : {}) }); }}>
        <option value="">Enter medicine manually</option>
        {draft.prescription_item_id && !choices.some(c => c.id === draft.prescription_item_id) && <option value={draft.prescription_item_id}>{draft.medicine} — linked prescription</option>}
        {choices.map(choice => <option key={choice.id} value={choice.id}>{choice.medicine} · {choice.dosage} · {choice.prescription_date}</option>)}
      </select></label>
      {choiceError && <div className="text-sm" role="status">{choiceError} <button type="button" className="underline" onClick={() => { setChoiceError(""); setChoiceRetry(v => v + 1); }}>Retry prescription choices</button></div>}
      {moreChoices && <button type="button" className={reminderButtonClass} onClick={() => { setMoreChoices(false); setChoicePage(p => p + 1); }}>Load older prescription medicines</button>}
      <label className="block text-sm font-semibold">Medicine<input required maxLength={200} className={reminderInputClass} value={draft.medicine} readOnly={!!draft.prescription_item_id} onChange={e => update({ medicine: e.target.value })} /></label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-semibold">Start date<input type="date" required className={reminderInputClass} value={draft.start_date} onChange={e => update({ start_date: e.target.value })} /></label>
        <label className="block text-sm font-semibold">End date (optional)<input type="date" min={draft.start_date} className={reminderInputClass} value={draft.end_date ?? ""} onChange={e => update({ end_date: e.target.value || null })} /></label>
      </div>
      <div className="space-y-3"><p className="text-sm font-semibold">Daily times (Asia/Dhaka)</p>{draft.times.map((value, index) => <div className="flex items-end gap-3" key={index}>
        <label className="min-w-0 flex-1 text-sm">Time {index + 1}<input required type="time" step={60} className={reminderInputClass} value={value} onChange={e => update({ times: draft.times.map((t, i) => i === index ? e.target.value : t) })} /></label>
        <button type="button" aria-label={`Remove time ${index + 1}`} disabled={draft.times.length === 1} className={reminderButtonClass} onClick={() => update({ times: draft.times.filter((_, i) => i !== index) })}>Remove</button>
      </div>)}<button type="button" disabled={draft.times.length >= 24} className={reminderButtonClass} onClick={() => update({ times: [...draft.times, ""] })}>Add daily time</button></div>
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={draft.is_active} onChange={e => update({ is_active: e.target.checked })} />Active reminder</label>
      <div className="flex gap-3"><button type="submit" className={`${reminderButtonClass} bg-sky-800 text-white`}>{pending ? "Saving…" : "Save reminder"}</button><button type="button" className={reminderButtonClass} onClick={() => { if (!dirty || window.confirm("Discard your unsaved reminder changes?")) onCancel(); }}>Cancel</button></div>
    </fieldset>
  </form>;
}
