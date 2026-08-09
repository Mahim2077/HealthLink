"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { onboardProfessional, registerProfessional } from "@/lib/professional/api";
import {
  PROFESSIONAL_ROLES,
  type ProfessionalApplicationResponse,
  type ProfessionalOnboardingRequest,
  type ProfessionalRegistrationRequest,
  type ProfessionalRoleCode,
} from "@/lib/professional/types";

type FormState = {
  role: ProfessionalRoleCode;
  facility: string;
  designation: string;
  additionalInfo: string;
  bmdc: string;
  email: string;
  password: string;
  confirmPassword: string;
  firstName: string;
  lastName: string;
  nid: string;
};

const INITIAL_FORM: FormState = {
  additionalInfo: "",
  bmdc: "",
  confirmPassword: "",
  designation: "",
  email: "",
  facility: "",
  firstName: "",
  lastName: "",
  nid: "",
  password: "",
  role: "DOCTOR",
};

function PendingApplication({ result }: { result: ProfessionalApplicationResponse }) {
  const roleName = PROFESSIONAL_ROLES.find((role) => role.code === result.role_code)?.name ?? result.role_code;
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 items-center px-5 py-14 sm:px-8" id="main-content">
      <section className="w-full rounded-[2rem] border border-emerald-200 bg-white p-7 text-center shadow-xl shadow-slate-900/[0.06] sm:p-10">
        <span className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-emerald-100 text-3xl text-emerald-700">✓</span>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Application submitted</p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-slate-950">Your {roleName} application is pending.</h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-600">An administrator must verify this role and match your submitted facility before professional access becomes active. Registration does not grant clinical privileges.</p>
        <div className="mx-auto mt-7 max-w-md rounded-xl bg-slate-50 p-4 text-left text-sm">
          <p className="font-semibold text-slate-950">Status <span className="float-right rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">PENDING</span></p>
        </div>
        <Link className="mt-7 inline-flex min-h-11 items-center justify-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white hover:bg-sky-800" href="/">Return to HealthLink</Link>
      </section>
    </main>
  );
}

export function ProfessionalApplicationForm({
  mode,
  registerAction = registerProfessional,
  onboardAction = onboardProfessional,
}: {
  mode: "new" | "onboard";
  registerAction?: (request: ProfessionalRegistrationRequest) => Promise<ProfessionalApplicationResponse>;
  onboardAction?: (request: ProfessionalOnboardingRequest) => Promise<ProfessionalApplicationResponse>;
}) {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProfessionalApplicationResponse | null>(null);
  const isDoctor = form.role === "DOCTOR";

  const setField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    const common = {
      additional_info: form.additionalInfo.trim(),
      designation: form.designation.trim(),
      facility_name: form.facility.trim(),
    };
    if (!common.additional_info || !common.designation || !common.facility_name) {
      setError("Complete every required professional field.");
      return;
    }
    if (isDoctor && !form.bmdc.trim()) {
      setError("BM&DC Registration Number is required for doctors.");
      return;
    }
    if (mode === "new") {
      if (!form.firstName.trim() || !form.lastName.trim() || !form.email.trim() || !form.nid.trim()) {
        setError("Complete every required identity and account field.");
        return;
      }
      if (form.password.length < 8 || form.password.length > 128) {
        setError("Password must be between 8 and 128 characters.");
        return;
      }
      if (form.password !== form.confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
    }

    const application = isDoctor
      ? { ...common, role_code: "DOCTOR" as const, bmdc_registration_number: form.bmdc.trim() }
      : { ...common, role_code: form.role as Exclude<ProfessionalRoleCode, "DOCTOR"> };
    setSubmitting(true);
    try {
      const submitted = mode === "new"
        ? await registerAction({
            ...application,
            email: form.email.trim(),
            first_name: form.firstName.trim(),
            last_name: form.lastName.trim(),
            nid_number: form.nid.trim(),
            password: form.password,
          } as ProfessionalRegistrationRequest)
        : await onboardAction(application as ProfessionalOnboardingRequest);
      setResult(submitted);
    } catch (reason) {
      setError(citizenErrorMessage(reason, "We could not submit this professional application."));
    } finally {
      setSubmitting(false);
    }
  };

  if (result) return <PendingApplication result={result} />;

  return (
    <main className="mx-auto grid w-full max-w-7xl flex-1 items-start gap-10 px-5 py-12 sm:px-8 sm:py-16 lg:grid-cols-[0.72fr_1.28fr] lg:px-10" id="main-content">
      <section className="max-w-lg pt-2 lg:sticky lg:top-10 lg:pt-10">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-700">Professional registration</p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-[-0.045em] text-slate-950 sm:text-5xl">Apply with one trusted identity.</h1>
        <p className="mt-5 text-base leading-7 text-slate-600">{mode === "new" ? "Professional registration requires an NID. If that NID already belongs to a HealthLink citizen, sign in and use onboarding instead." : "Your signed-in HealthLink identity and NID will be reused. No duplicate user account is created."}</p>
        <div className="mt-8 rounded-2xl border border-sky-100 bg-sky-50/80 p-5 text-sm leading-6 text-sky-950">
          Every role begins <strong>PENDING</strong>. Clinical capability is unavailable until an administrator verifies the role.
        </div>
        {mode === "new" ? <p className="mt-5 text-sm text-slate-600">Already a citizen? <Link className="font-bold text-sky-700 underline-offset-4 hover:underline" href="/citizen/login">Sign in first</Link>, then choose professional onboarding.</p> : null}
      </section>

      <section className="rounded-[2rem] border border-white bg-white/95 p-5 shadow-xl shadow-slate-900/[0.06] sm:p-8 lg:p-10">
        <form className="space-y-8" onSubmit={submit}>
          {mode === "new" ? (
            <fieldset className="grid gap-5 sm:grid-cols-2" disabled={submitting}>
              <legend className="col-span-full text-lg font-bold text-slate-950">Identity and account</legend>
              <FormField htmlFor="professional-first-name" label="First name" required><input className={citizenInputClassName} id="professional-first-name" maxLength={100} onChange={(event) => setField("firstName", event.target.value)} required value={form.firstName} /></FormField>
              <FormField htmlFor="professional-last-name" label="Last name" required><input className={citizenInputClassName} id="professional-last-name" maxLength={100} onChange={(event) => setField("lastName", event.target.value)} required value={form.lastName} /></FormField>
              <FormField htmlFor="professional-nid" hint="Birth Certificate Numbers cannot be used for professional registration." label="National ID" required><input className={citizenInputClassName} id="professional-nid" inputMode="numeric" maxLength={32} onChange={(event) => setField("nid", event.target.value)} required value={form.nid} /></FormField>
              <FormField htmlFor="professional-email" label="Email address" required><input autoComplete="email" className={citizenInputClassName} id="professional-email" maxLength={320} onChange={(event) => setField("email", event.target.value)} required type="email" value={form.email} /></FormField>
              <FormField htmlFor="professional-password" hint="Use 8–128 characters." label="Password" required><input autoComplete="new-password" className={citizenInputClassName} id="professional-password" maxLength={128} minLength={8} onChange={(event) => setField("password", event.target.value)} required type="password" value={form.password} /></FormField>
              <FormField htmlFor="professional-confirm-password" label="Confirm password" required><input autoComplete="new-password" className={citizenInputClassName} id="professional-confirm-password" maxLength={128} onChange={(event) => setField("confirmPassword", event.target.value)} required type="password" value={form.confirmPassword} /></FormField>
            </fieldset>
          ) : null}

          <fieldset className="grid gap-5 sm:grid-cols-2" disabled={submitting}>
            <legend className="col-span-full text-lg font-bold text-slate-950">Role application</legend>
            <FormField className="sm:col-span-2" htmlFor="professional-role" label="Professional role" required>
              <select className={citizenInputClassName} id="professional-role" onChange={(event) => { const role = event.target.value as ProfessionalRoleCode; setForm((current) => ({ ...current, bmdc: role === "DOCTOR" ? current.bmdc : "", role })); }} value={form.role}>
                {PROFESSIONAL_ROLES.map((role) => <option key={role.code} value={role.code}>{role.name}</option>)}
              </select>
            </FormField>
            {isDoctor ? <FormField className="sm:col-span-2" htmlFor="professional-bmdc" hint="Required only for the Doctor role and globally unique." label="BM&DC Registration Number" required><input className={citizenInputClassName} id="professional-bmdc" maxLength={100} onChange={(event) => setField("bmdc", event.target.value)} required value={form.bmdc} /></FormField> : null}
            <FormField htmlFor="professional-facility" hint="Submit the facility name as you know it; an administrator will match it later." label="Medical facility name" required><input className={citizenInputClassName} id="professional-facility" maxLength={255} onChange={(event) => setField("facility", event.target.value)} required value={form.facility} /></FormField>
            <FormField htmlFor="professional-designation" label="Designation" required><input className={citizenInputClassName} id="professional-designation" maxLength={150} onChange={(event) => setField("designation", event.target.value)} required value={form.designation} /></FormField>
            <FormField className="sm:col-span-2" htmlFor="professional-additional-info" hint="Include qualifications, experience, department, or other information useful for verification." label="Additional information" required><textarea className={citizenInputClassName + " min-h-40 py-3"} id="professional-additional-info" onChange={(event) => setField("additionalInfo", event.target.value)} required value={form.additionalInfo} /></FormField>
          </fieldset>

          {error ? <StatusAlert message={error} /> : null}
          <button className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-sky-700 px-6 text-sm font-bold text-white shadow-sm hover:bg-sky-800 disabled:cursor-wait disabled:opacity-60 sm:w-auto" disabled={submitting} type="submit">{submitting ? "Submitting application…" : mode === "new" ? "Submit professional application" : "Submit role for verification"}</button>
        </form>
      </section>
    </main>
  );
}
