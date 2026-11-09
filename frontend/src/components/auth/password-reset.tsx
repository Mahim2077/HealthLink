"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { EmailCodeForm } from "@/components/auth/email-code-form";
import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import {
  completePasswordReset, emailActionError, requestResetCode, verifyResetCode,
  type EmailChallenge, type ResetIdentity,
} from "@/lib/auth/email-codes";
import { registrationPasswordError, registrationPasswordHint } from "@/lib/auth/registration-validation";
import type { Portal } from "@/lib/auth/types";
import { PROFESSIONAL_ROLES, type ProfessionalRoleCode } from "@/lib/professional/types";

type ResetStep =
  | { name: "request" }
  | { name: "verify"; identity: ResetIdentity; challenge: EmailChallenge }
  | { name: "password"; challengeId: string; token: string }
  | { name: "complete" };

export function PasswordReset({ portal }: { portal: Portal }) {
  const [step, setStep] = useState<ResetStep>({ name: "request" });
  const [identifier, setIdentifier] = useState("");
  const [role, setRole] = useState<ProfessionalRoleCode>("DOCTOR");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const loginHref = `/${portal.toLowerCase()}/login`;
  const isProfessional = portal === "PROFESSIONAL";

  const startOver = () => {
    setStep({ name: "request" });
    setPassword("");
    setConfirmation("");
    setError("");
  };

  const requestCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = identifier.trim();
    if (!value || pending) return;
    const identity: ResetIdentity = isProfessional
      ? { portal, nid_number: value, role_code: role }
      : { portal, email: value };
    setError("");
    setPending(true);
    try {
      const challenge = await requestResetCode(identity);
      setStep({ name: "verify", identity, challenge });
    } catch (reason) {
      setError(emailActionError(reason, "We could not request a code. Please try again."));
    } finally {
      setPending(false);
    }
  };

  const savePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (step.name !== "password" || pending) return;
    const validation = registrationPasswordError(password)
      ?? (password === confirmation ? "" : "Passwords do not match.");
    setError(validation);
    if (validation) return;
    setPending(true);
    try {
      await completePasswordReset(step.challengeId, step.token, password);
      setPassword("");
      setConfirmation("");
      setStep({ name: "complete" });
    } catch (reason) {
      setError(emailActionError(reason, "We could not update the password. Please try again."));
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-xl flex-1 px-5 py-10 sm:py-16" id="main-content">
      <section className="hl-settings-card space-y-6">
        <header>
          <p className="text-xs font-bold uppercase tracking-widest text-[var(--portal-strong)]">Account recovery</p>
          <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-slate-950">
            {step.name === "complete" ? "Password updated" : "Reset your password"}
          </h1>
        </header>
        {error ? <StatusAlert message={error} /> : null}
        {step.name === "request" ? (
          <form className="space-y-5" onSubmit={requestCode}>
            <p className="text-sm leading-6 text-slate-600">Enter the details you use to sign in. The reset code goes to your verified recovery email.</p>
            <FormField htmlFor="reset-identifier" label={isProfessional ? "National ID (NID)" : "Email address"} required>
              <input autoComplete="username" className={citizenInputClassName} id="reset-identifier"
                maxLength={isProfessional ? 32 : 320} onChange={(event) => setIdentifier(event.target.value)}
                required type={isProfessional ? "text" : "email"} value={identifier} />
            </FormField>
            {isProfessional ? (
              <FormField htmlFor="reset-role" label="Professional role" required>
                <select className={citizenInputClassName} id="reset-role" onChange={(event) => setRole(event.target.value as ProfessionalRoleCode)} value={role}>
                  {PROFESSIONAL_ROLES.map(({ code, name }) => <option key={code} value={code}>{name}</option>)}
                </select>
              </FormField>
            ) : null}
            <button className="hl-button-primary" disabled={pending} type="submit">{pending ? "Requesting…" : "Send reset code"}</button>
          </form>
        ) : null}
        {step.name === "verify" ? (
          <EmailCodeForm
            backLabel="Change account details"
            description="If the details match an eligible account, we’ll send a code to its verified email. Check your spam folder if the message is missing."
            initialChallenge={step.challenge}
            onBack={startOver}
            onResend={() => requestResetCode(step.identity)}
            onVerify={async (proof) => {
              const grant = await verifyResetCode(proof);
              setStep({ name: "password", challengeId: proof.challenge_id, token: grant.reset_token });
            }}
          />
        ) : null}
        {step.name === "password" ? (
          <form className="space-y-5" onSubmit={savePassword}>
            <h2 className="text-xl font-bold tracking-tight">Create a new password</h2>
            <FormField htmlFor="reset-password" label="New password" hint={registrationPasswordHint} required>
              <input autoComplete="new-password" className={citizenInputClassName} id="reset-password"
                maxLength={128} minLength={8} onChange={(event) => setPassword(event.target.value)}
                required type="password" value={password} />
            </FormField>
            <FormField htmlFor="reset-confirmation" label="Confirm new password" required>
              <input autoComplete="new-password" className={citizenInputClassName} id="reset-confirmation"
                maxLength={128} onChange={(event) => setConfirmation(event.target.value)}
                required type="password" value={confirmation} />
            </FormField>
            <div className="flex flex-wrap gap-3">
              <button className="hl-button-primary" disabled={pending} type="submit">{pending ? "Saving…" : "Save new password"}</button>
              <button className="hl-button-secondary" disabled={pending} onClick={startOver} type="button">Request a new code</button>
            </div>
          </form>
        ) : null}
        {step.name === "complete" ? (
          <StatusAlert tone="success" message="Your previous sessions were signed out. Sign in with your new password." />
        ) : (
          <p className="text-sm leading-6 text-slate-600">If your recovery email is unverified or you can no longer access it, contact HealthLink support.</p>
        )}
        <Link className={step.name === "complete" ? "hl-button-primary" : "text-sm font-semibold underline underline-offset-4"} href={loginHref}>
          Return to sign-in
        </Link>
      </section>
    </main>
  );
}
