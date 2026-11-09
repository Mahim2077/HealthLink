"use client";

import { useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import { updateAdminCitizenProfile } from "@/lib/admin/api";
import type { CitizenIdentityDetail } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

const fields = [
  { name: "first_name", label: "First name", type: "text", maxLength: 100, required: true },
  { name: "last_name", label: "Last name", type: "text", maxLength: 100, required: true },
  { name: "email", label: "Email address", type: "email", maxLength: 320, required: true },
  { name: "date_of_birth", label: "Date of birth", type: "date", required: true },
  { name: "gender", label: "Gender", type: "text", maxLength: 32, required: true },
  { name: "blood_group", label: "Blood group", type: "text", maxLength: 8, required: false },
] as const;

type Draft = Record<(typeof fields)[number]["name"] | "address" | "reason", string>;

export function CitizenProfileEditor({
  detail,
  onSaved,
}: {
  detail: CitizenIdentityDetail;
  onSaved: (detail: CitizenIdentityDetail) => void;
}) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  function edit() {
    setMessage(null);
    setDraft({
      first_name: detail.first_name,
      last_name: detail.last_name,
      email: detail.email,
      date_of_birth: detail.date_of_birth ?? "",
      gender: detail.gender ?? "",
      blood_group: detail.blood_group ?? "",
      address: detail.address ?? "",
      reason: "",
    });
  }

  function change(name: keyof Draft, value: string) {
    setDraft((current) => current && { ...current, [name]: value });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || saving) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateAdminCitizenProfile(detail.user_id, {
        ...draft,
        address: draft.address.trim() || null,
        blood_group: draft.blood_group.trim() || null,
      });
      onSaved(updated);
      setDraft(null);
      setMessage({ tone: "success", text: "Citizen profile updated." });
    } catch (error) {
      setMessage({ tone: "error", text: citizenErrorMessage(error, "We could not update this citizen profile.") });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="hl-card p-6">
      <h2 className="text-xl font-bold text-slate-950">Citizen profile</h2>
      <p className="mt-2 text-sm text-slate-600">
        Correct account and profile information with a reason recorded in the admin audit log.
      </p>
      <div className="mt-4 space-y-4">
        {message ? <StatusAlert tone={message.tone} message={message.text} /> : null}
        {draft ? (
          <form onSubmit={save} aria-label="Edit citizen profile">
            <fieldset className="grid gap-4 sm:grid-cols-2" disabled={saving}>
              {fields.map((field) => (
                <FormField key={field.name} htmlFor={`admin-profile-${field.name}`} label={field.label} required={field.required}>
                  <input
                    id={`admin-profile-${field.name}`}
                    className={citizenInputClassName}
                    type={field.type}
                    maxLength={"maxLength" in field ? field.maxLength : undefined}
                    required={field.required}
                    value={draft[field.name]}
                    onChange={(event) => change(field.name, event.target.value)}
                  />
                </FormField>
              ))}
              <FormField className="sm:col-span-2" htmlFor="admin-profile-address" label="Address">
                <textarea id="admin-profile-address" className={citizenInputClassName} value={draft.address} onChange={(event) => change("address", event.target.value)} />
              </FormField>
              <FormField className="sm:col-span-2" htmlFor="admin-profile-reason" label="Reason for profile change" required>
                <textarea id="admin-profile-reason" className={citizenInputClassName} maxLength={2000} required value={draft.reason} onChange={(event) => change("reason", event.target.value)} />
              </FormField>
              <div className="flex flex-wrap gap-2 sm:col-span-2">
                <button className="hl-button-primary" type="submit">{saving ? "Saving…" : "Save profile changes"}</button>
                <button className="hl-button-secondary" type="button" onClick={() => { setDraft(null); setMessage(null); }}>Cancel profile edit</button>
              </div>
            </fieldset>
          </form>
        ) : <button className="hl-button-secondary" type="button" onClick={edit}>Edit citizen profile</button>}
      </div>
    </section>
  );
}
