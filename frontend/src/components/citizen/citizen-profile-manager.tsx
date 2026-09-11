"use client";

import { PlusIcon } from "@heroicons/react/24/outline";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  citizenInputClassName,
  FormField,
} from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/async-state";
import { useUnsavedChanges } from "@/components/ui/use-unsaved-changes";
import {
  addCitizenNid,
  loadCitizenDashboard,
  updateCitizenProfile,
} from "@/lib/citizen/api";
import {
  citizenErrorMessage,
  formatCitizenDate,
  maskIdentityValue,
} from "@/lib/citizen/presentation";
import type {
  CitizenAddNidRequest,
  CitizenDashboardData,
  CitizenIdentity,
  CitizenProfile,
  CitizenProfileUpdateRequest,
} from "@/lib/citizen/types";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CitizenDashboardData };

type ProfileForm = {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  gender: string;
  bloodGroup: string;
  address: string;
};

function fromProfile(profile: CitizenProfile): ProfileForm {
  return {
    address: profile.address ?? "",
    bloodGroup: profile.blood_group ?? "",
    dateOfBirth: profile.date_of_birth,
    firstName: profile.first_name,
    gender: profile.gender,
    lastName: profile.last_name,
  };
}

function Guard({ kind }: { kind: "signed-out" | "wrong-portal" }) {
  const wrongPortal = kind === "wrong-portal";
  return (
    <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-semibold text-white hover:bg-teal-800"
            href={wrongPortal ? "/" : "/citizen/login"}
          >
            {wrongPortal ? "Return to HealthLink" : "Sign in to Citizen Portal"}
          </Link>
        }
        message={
          wrongPortal
            ? "This session belongs to another HealthLink portal."
            : "Sign in to manage your citizen profile and identity."
        }
        title={wrongPortal ? "Citizen Portal access required" : "Sign in to continue"}
      />
    </main>
  );
}

function ProfileEditor({
  profile,
  saveAction,
  onSaved,
}: {
  profile: CitizenProfile;
  saveAction: (request: CitizenProfileUpdateRequest) => Promise<CitizenProfile>;
  onSaved: (profile: CitizenProfile) => void;
}) {
  const [form, setForm] = useState(() => fromProfile(profile));
  useUnsavedChanges(JSON.stringify(form) !== JSON.stringify(fromProfile(profile)));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ tone: "error" | "success"; text: string } | null>(null);

  const setField = (field: keyof ProfileForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);
    const firstName = form.firstName.trim();
    const lastName = form.lastName.trim();
    const gender = form.gender.trim();
    if (!firstName || !lastName || !gender || !form.dateOfBirth) {
      setMessage({ tone: "error", text: "Complete every required profile field." });
      return;
    }
    if (form.dateOfBirth > new Date().toISOString().slice(0, 10)) {
      setMessage({ tone: "error", text: "Date of birth cannot be in the future." });
      return;
    }

    setSaving(true);
    try {
      const updated = await saveAction({
        address: form.address.trim() || null,
        blood_group: form.bloodGroup.trim() || null,
        date_of_birth: form.dateOfBirth,
        first_name: firstName,
        gender,
        last_name: lastName,
      });
      setForm(fromProfile(updated));
      onSaved(updated);
      setMessage({ tone: "success", text: "Your profile has been updated." });
    } catch (error) {
      setMessage({
        tone: "error",
        text: citizenErrorMessage(error, "We could not update your profile."),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="hl-card p-6 sm:p-8">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Profile details</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Keep your information current</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Email and identity values cannot be changed through this form.</p>
      </div>
      <form className="mt-7 grid gap-5 sm:grid-cols-2" onSubmit={submit}>
        <FormField htmlFor="first-name" label="First name" required>
          <input className={citizenInputClassName} disabled={saving} id="first-name" maxLength={100} onChange={(event) => setField("firstName", event.target.value)} required value={form.firstName} />
        </FormField>
        <FormField htmlFor="last-name" label="Last name" required>
          <input className={citizenInputClassName} disabled={saving} id="last-name" maxLength={100} onChange={(event) => setField("lastName", event.target.value)} required value={form.lastName} />
        </FormField>
        <FormField htmlFor="profile-date-of-birth" label="Date of birth" required>
          <input className={citizenInputClassName} disabled={saving} id="profile-date-of-birth" max={new Date().toISOString().slice(0, 10)} onChange={(event) => setField("dateOfBirth", event.target.value)} required type="date" value={form.dateOfBirth} />
        </FormField>
        <FormField htmlFor="profile-gender" label="Gender" required>
          <select className={citizenInputClassName} disabled={saving} id="profile-gender" onChange={(event) => setField("gender", event.target.value)} required value={form.gender}>
            <option value="FEMALE">Female</option>
            <option value="MALE">Male</option>
            <option value="OTHER">Other</option>
            <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
          </select>
        </FormField>
        <FormField htmlFor="profile-blood-group" label="Blood group">
          <select className={citizenInputClassName} disabled={saving} id="profile-blood-group" onChange={(event) => setField("bloodGroup", event.target.value)} value={form.bloodGroup}>
            <option value="">Not recorded</option>
            {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(group => <option key={group} value={group}>{group}</option>)}
          </select>
        </FormField>
        <FormField className="sm:col-span-2" htmlFor="profile-address" label="Address">
          <textarea className={citizenInputClassName + " min-h-28 py-3"} disabled={saving} id="profile-address" onChange={(event) => setField("address", event.target.value)} value={form.address} />
        </FormField>
        <div className="sm:col-span-2">
          {message ? <StatusAlert message={message.text} tone={message.tone} /> : null}
          <button className="mt-4 inline-flex min-h-12 items-center justify-center rounded-xl bg-teal-700 px-6 text-sm font-bold text-white shadow-sm hover:bg-teal-800 disabled:cursor-wait disabled:opacity-60" disabled={saving} type="submit">
            {saving ? "Saving profile…" : "Save profile"}
          </button>
        </div>
      </form>
    </section>
  );
}

function IdentityManager({
  identity,
  addAction,
  onAdded,
}: {
  identity: CitizenIdentity;
  addAction: (request: CitizenAddNidRequest) => Promise<CitizenIdentity>;
  onAdded: (identity: CitizenIdentity) => void;
}) {
  const [nid, setNid] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ tone: "error" | "success"; text: string } | null>(null);
  const canAdd = identity.birth_certificate_number !== null && identity.nid_number === null;

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);
    if (!nid.trim()) {
      setMessage({ tone: "error", text: "Enter your National ID." });
      return;
    }
    if (confirmation !== "CONFIRM") {
      setMessage({ tone: "error", text: "Type CONFIRM exactly to continue." });
      return;
    }
    setSubmitting(true);
    try {
      const updated = await addAction({ confirmation, nid_number: nid.trim() });
      onAdded(updated);
      setNid("");
      setConfirmation("");
      setMessage({ tone: "success", text: "Your National ID was added. Your Birth Certificate Number remains on your account." });
    } catch (error) {
      setMessage({ tone: "error", text: citizenErrorMessage(error, "We could not add this National ID.") });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="rounded-2xl border border-teal-200 bg-teal-50/70 p-6 text-slate-950 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Identity</p>
      <h2 className="mt-2 text-2xl font-bold">Verified identifiers</h2>
      <dl className="mt-6 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-teal-100 bg-white p-4">
          <dt className="text-xs font-semibold text-slate-500">Birth Certificate Number</dt>
          <dd className="mt-2 font-mono text-sm font-bold tracking-wider">{maskIdentityValue(identity.birth_certificate_number)}</dd>
        </div>
        <div className="rounded-xl border border-teal-100 bg-white p-4">
          <dt className="text-xs font-semibold text-slate-500">National ID</dt>
          <dd className="mt-2 font-mono text-sm font-bold tracking-wider">{maskIdentityValue(identity.nid_number)}</dd>
        </div>
      </dl>
      {identity.nid_added_at ? <p className="mt-4 text-xs text-slate-500">NID added {formatCitizenDate(identity.nid_added_at)}</p> : null}

      {canAdd ? (
        <form className="mt-7 rounded-2xl bg-white p-5 text-slate-900 sm:p-6" onSubmit={submit}>
          <h3 className="text-lg font-bold">Add your National ID</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">This is a one-time, irreversible self-service action. Your Birth Certificate Number will be retained. Later corrections require an administrator.</p>
          <div className="mt-5 grid gap-5">
            <FormField htmlFor="new-nid" label="National ID" required>
              <input autoComplete="off" className={citizenInputClassName} disabled={submitting} id="new-nid" inputMode="numeric" maxLength={32} onChange={(event) => setNid(event.target.value)} required value={nid} />
            </FormField>
            <FormField htmlFor="nid-confirmation" hint="Confirmation is case-sensitive and cannot contain spaces." label='Type "CONFIRM"' required>
              <input autoComplete="off" className={citizenInputClassName} disabled={submitting} id="nid-confirmation" maxLength={32} onChange={(event) => setConfirmation(event.target.value)} required value={confirmation} />
            </FormField>
          </div>
          {message ? <div className="mt-5"><StatusAlert message={message.text} tone={message.tone} /></div> : null}
          <button className="mt-5 inline-flex min-h-12 items-center justify-center rounded-xl bg-rose-700 px-6 text-sm font-bold text-white hover:bg-rose-800 disabled:cursor-wait disabled:opacity-60" disabled={submitting} type="submit">
            {submitting ? "Adding National ID…" : "Add National ID permanently"}
          </button>
        </form>
      ) : (
        <div className="mt-7 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-800">
          {message ? message.text : "Your identity is locked against self-service replacement."}
        </div>
      )}
    </section>
  );
}

function ProfileContent({
  initial,
  saveAction,
  addAction,
}: {
  initial: CitizenDashboardData;
  saveAction: (request: CitizenProfileUpdateRequest) => Promise<CitizenProfile>;
  addAction: (request: CitizenAddNidRequest) => Promise<CitizenIdentity>;
}) {
  const [profile, setProfile] = useState(initial.profile);
  const [identity, setIdentity] = useState(initial.identity);
  return (
    <main className="hl-page" id="main-content">
      <div className="flex flex-col gap-5 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Citizen account</p>
          <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">Profile and identity</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">Manage editable profile details and review your protected identity.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Link
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-5 text-sm font-bold text-sky-800 transition hover:border-sky-300 hover:bg-sky-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
            href="/professional/onboard"
          >
            <PlusIcon aria-hidden="true" className="size-5" />
            Add a professional role
          </Link>
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-5 text-sm font-bold text-slate-700 transition hover:border-slate-400 hover:text-slate-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700"
            href="/citizen/dashboard"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
      <div className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ProfileEditor onSaved={setProfile} profile={profile} saveAction={saveAction} />
        <IdentityManager addAction={addAction} identity={identity} onAdded={setIdentity} />
      </div>
    </main>
  );
}

export function CitizenProfileManager({
  loadAction = loadCitizenDashboard,
  saveAction = updateCitizenProfile,
  addAction = addCitizenNid,
}: {
  loadAction?: () => Promise<CitizenDashboardData>;
  saveAction?: (request: CitizenProfileUpdateRequest) => Promise<CitizenProfile>;
  addAction?: (request: CitizenAddNidRequest) => Promise<CitizenIdentity>;
}) {
  const auth = usePortalAuth("CITIZEN");
  const authStatus = auth.status;
  const isRequiredPortal = auth.isRequiredPortal;
  const refreshCitizenSession = auth.refreshSession;
  const [hydration, setHydration] = useState<"pending" | "failed" | "succeeded">("pending");
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (authStatus === "authenticated") return;
    let active = true;
    void refreshCitizenSession().then(
      () => { if (active) setHydration("succeeded"); },
      () => { if (active) setHydration("failed"); },
    );
    return () => { active = false; };
  }, [authStatus, refreshCitizenSession]);

  useEffect(() => {
    if (authStatus !== "authenticated" || !isRequiredPortal) return;
    let active = true;
    void loadAction().then(
      (data) => { if (active) setState({ data, status: "ready" }); },
      (error: unknown) => { if (active) setState({ message: citizenErrorMessage(error, "We could not load your profile."), status: "error" }); },
    );
    return () => { active = false; };
  }, [authStatus, isRequiredPortal, loadAction, version]);

  if (authStatus === "unauthenticated") {
    if (hydration !== "failed") {
      return <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content"><LoadingState description="Securely checking your Citizen session." label="Checking your Citizen session" /></main>;
    }
    return <Guard kind="signed-out" />;
  }
  if (!isRequiredPortal) return <Guard kind="wrong-portal" />;
  if (state.status === "loading") return <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content"><LoadingState description="Loading your editable profile and protected identity." label="Loading profile" /></main>;
  if (state.status === "error") return <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content"><ErrorState message={state.message} onAction={() => { setState({ status: "loading" }); setVersion((value) => value + 1); }} title="Profile unavailable" /></main>;
  return <ProfileContent addAction={addAction} initial={state.data} saveAction={saveAction} />;
}
