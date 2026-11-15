"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import { EmptyState } from "@/components/ui/async-state";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import { localCalendarDate, registrationGenders } from "@/lib/auth/registration-validation";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { setupProfessionalCitizenProfile } from "@/lib/professional/api";

export function ProfessionalCitizenProfileLink({ hasProfile }: { hasProfile: boolean | null }) {
  if (typeof hasProfile !== "boolean") return null;
  return (
    <Link className="hl-button-secondary" href={hasProfile ? "/citizen/login" : "/professional/citizen-profile"}>
      {hasProfile ? "Sign in to Citizen Portal" : "Set up Citizen profile"}
    </Link>
  );
}

export function ProfessionalCitizenProfileSetup({ hasProfile }: { hasProfile: boolean | null }) {
  const [completed, setCompleted] = useState(false);
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [gender, setGender] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const ready = hasProfile || completed;
  useUnsavedChanges(!ready && Boolean(dateOfBirth || gender));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) return;
    if (!dateOfBirth || !gender) {
      setError("Enter your date of birth and select a gender.");
      return;
    }
    if (dateOfBirth > localCalendarDate()) {
      setError("Date of birth cannot be in the future.");
      return;
    }

    inFlight.current = true;
    setSaving(true);
    setError("");
    try {
      await setupProfessionalCitizenProfile({ date_of_birth: dateOfBirth, gender });
      setCompleted(true);
    } catch (reason) {
      setError(citizenErrorMessage(reason, "We could not set up your Citizen profile. Please try again."));
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }

  return (
    <main className="hl-page" id="main-content">
      <header className="hl-page-header">
        <Link className="text-sm font-semibold text-sky-700 underline" href="/professional/settings">
          Account settings
        </Link>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-tight">Citizen profile</h1>
      </header>
      {typeof hasProfile !== "boolean" ? (
        <EmptyState title="Doctor role required" message="Sign in with your Doctor role to set up a Citizen profile." />
      ) : ready ? (
        <section className="hl-settings-card mt-6 max-w-xl space-y-4">
          <StatusAlert message="Your Citizen profile is ready." tone="success" />
          <p className="text-sm text-slate-600">Use your HealthLink email and password to sign in and manage your personal profile.</p>
          <ProfessionalCitizenProfileLink hasProfile />
        </section>
      ) : (
        <form className="hl-settings-card mt-6 max-w-xl space-y-5" onSubmit={submit}>
          <p className="text-sm text-slate-600">
            Enter your date of birth and gender to use the Citizen Portal with your existing HealthLink account and NID.
          </p>
          <fieldset className="grid gap-5 sm:grid-cols-2" disabled={saving}>
            <legend className="sr-only">Citizen profile details</legend>
            <FormField htmlFor="citizen-setup-date-of-birth" label="Date of birth" required>
              <input
                className={citizenInputClassName}
                id="citizen-setup-date-of-birth"
                max={localCalendarDate()}
                onChange={(event) => setDateOfBirth(event.target.value)}
                required
                type="date"
                value={dateOfBirth}
              />
            </FormField>
            <FormField htmlFor="citizen-setup-gender" label="Gender" required>
              <select
                className={citizenInputClassName}
                id="citizen-setup-gender"
                onChange={(event) => setGender(event.target.value)}
                required
                value={gender}
              >
                <option value="">Select gender</option>
                {registrationGenders.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
              </select>
            </FormField>
          </fieldset>
          {error ? <StatusAlert message={error} /> : null}
          <button className="hl-button-primary" disabled={saving} type="submit">
            {saving ? "Creating profile…" : "Create Citizen profile"}
          </button>
        </form>
      )}
    </main>
  );
}
