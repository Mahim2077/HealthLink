"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import { loadCurrentEmergencyProfile, loadEmergencyProfile, saveEmergencyProfile, type EmergencyInput, type EmergencyProfile } from "@/lib/emergency/api";

const fields: { key: keyof EmergencyInput; label: string; max: number }[] = [
  { key: "allergies", label: "Allergies", max: 4000 },
  { key: "chronic_conditions", label: "Chronic conditions", max: 4000 },
  { key: "current_medications", label: "Current medications", max: 4000 },
  { key: "emergency_contact_name", label: "Emergency contact name", max: 150 },
  { key: "emergency_contact_phone", label: "Emergency contact phone", max: 32 },
  { key: "special_notes", label: "Special notes", max: 4000 },
];
function draftOf(profile: EmergencyProfile): EmergencyInput {
  return Object.fromEntries(fields.map(({ key }) => [key, profile[key]])) as EmergencyInput;
}

export function EmergencyProfileSummary({ profile }: { profile: EmergencyProfile }) {
  return <div>
    <p className="mb-4 text-sm text-slate-600">Citizen-provided information. Last updated: {profile.updated_at ? new Date(profile.updated_at).toLocaleString() : "Not yet provided"}.</p>
    <dl className="grid gap-4 sm:grid-cols-2">
      <div><dt className="font-semibold">Blood group</dt><dd>{profile.blood_group || "Not recorded"}</dd></div>
      {fields.map(({ key, label }) => <div key={key}><dt className="font-semibold">{label}</dt><dd className="whitespace-pre-wrap break-words text-slate-700">{profile[key] || "Not recorded"}</dd></div>)}
    </dl>
  </div>;
}

export function EmergencyProfileEditor({ initial }: { initial: EmergencyProfile }) {
  const [profile, setProfile] = useState(initial);
  const [draft, setDraft] = useState(() => draftOf(initial));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pending = useRef(false);
  const dirty = JSON.stringify(draft) !== JSON.stringify(draftOf(profile));
  useUnsavedChanges(dirty || saving);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true; setSaving(true); setError(""); setNotice("");
    try {
      const saved = await saveEmergencyProfile(draft);
      setProfile(saved); setDraft(draftOf(saved)); setNotice("Emergency profile saved.");
    } catch { setError("We could not save your emergency profile. Your changes are still here; please try again."); }
    finally { pending.current = false; setSaving(false); }
  }
  return <form onSubmit={save} className="space-y-5">
    <p className="text-sm text-slate-600">Keep these details up to date for your care team. A blank field means information has not been recorded.</p>
    <p>Blood group: <strong>{profile.blood_group || "Not recorded"}</strong> <span className="text-sm text-slate-600">(managed in your citizen profile)</span></p>
    <fieldset disabled={saving} className="grid gap-5 sm:grid-cols-2">
      {fields.map(({ key, label, max }) => <label className="block text-sm font-semibold" key={key}>{label}
        {key === "emergency_contact_name" || key === "emergency_contact_phone" ? <input className="mt-2 block w-full rounded-lg border border-slate-300 p-3 font-normal" type={key === "emergency_contact_phone" ? "tel" : "text"} value={draft[key] || ""} maxLength={max} onChange={event => { setDraft({ ...draft, [key]: event.target.value || null }); setNotice(""); }} /> : <textarea className="mt-2 block w-full rounded-lg border border-slate-300 p-3 font-normal" value={draft[key] || ""} rows={3} maxLength={max} onChange={event => { setDraft({ ...draft, [key]: event.target.value || null }); setNotice(""); }} />}
      </label>)}
    </fieldset>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {notice && <p role="status" className="text-emerald-700">{notice}</p>}
    {dirty && <p className="text-sm text-amber-800">You have unsaved changes.</p>}
    <div className="flex flex-wrap gap-3">
      <button disabled={saving} className="rounded-lg bg-[var(--portal-strong)] px-4 py-3 font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : "Save emergency profile"}</button>
      <button type="button" disabled={saving || !dirty} className="rounded-lg border px-4 py-3 disabled:opacity-50" onClick={() => { if (window.confirm("Discard your unsaved changes?")) { setDraft(draftOf(profile)); setError(""); } }}>Discard changes</button>
    </div>
  </form>;
}

function ProfileLoader({ citizenId }: { citizenId?: string }) {
  const [profile, setProfile] = useState<EmergencyProfile | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    void (citizenId ? loadCurrentEmergencyProfile(citizenId) : loadEmergencyProfile()).then(value => { if (active) setProfile(value); }, () => { if (active) setError(true); });
    return () => { active = false; };
  }, [citizenId, attempt]);
  if (error) return <ErrorState message="Emergency information could not be loaded." onAction={() => { setError(false); setAttempt(value => value + 1); }} />;
  if (!profile) return <LoadingState label="Loading emergency information" />;
  return citizenId ? <EmergencyProfileSummary profile={profile} /> : <EmergencyProfileEditor initial={profile} />;
}

export function EmergencyProfileContext({ citizenId }: { citizenId: string }) {
  return <section className="rounded-xl border border-slate-200 bg-white p-5" aria-label="Emergency information"><h2 className="mb-4 text-lg font-bold">Emergency information</h2><ProfileLoader key={citizenId} citizenId={citizenId} /></section>;
}

export function EmergencyProfilePage() {
  const auth = usePortalAuth("CITIZEN");
  const { status, refreshSession } = auth;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);
  const content = status !== "authenticated"
    ? failed ? <EmptyState title="Sign in required" message="Sign in to view your emergency profile." action={<Link href="/citizen/login">Sign in</Link>} /> : <LoadingState label="Checking session" />
    : !auth.isRequiredPortal ? <EmptyState title="Portal access required" message="Sign in through the citizen portal to view your emergency profile." />
      : <ProfileLoader key={auth.claims?.sid} />;
  return <main id="main-content" className="mx-auto w-full max-w-4xl flex-1 px-5 py-10 sm:px-8"><h1 className="mb-7 text-3xl font-bold">My emergency profile</h1>{content}</main>;
}
