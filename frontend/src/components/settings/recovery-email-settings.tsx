"use client";

import { useEffect, useState, type FormEvent } from "react";

import { EmailCodeForm } from "@/components/auth/email-code-form";
import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import { PasswordInput } from "@/components/ui/password-input";
import {
  emailActionError, loadRecoveryEmail, requestEnrollmentCode, verifyEnrollmentCode, type EmailChallenge,
} from "@/lib/auth/email-codes";

export function RecoveryEmailSettings() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof loadRecoveryEmail>> | null>(null);
  const [challenge, setChallenge] = useState<EmailChallenge | null>(null);
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    void loadRecoveryEmail().then(
      (result) => { if (active) setStatus(result); },
      () => { if (active) setError("Could not load recovery email settings."); },
    );
    return () => { active = false; };
  }, [retry]);

  const requestCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    setError("");
    setPending(true);
    try {
      setChallenge(await requestEnrollmentCode(password));
      setPassword("");
    } catch (reason) {
      setError(emailActionError(reason, "We could not send a verification code. Please try again."));
    } finally {
      setPending(false);
    }
  };

  if (!status) {
    return error ? (
      <section className="hl-settings-card space-y-3" aria-label="Recovery email">
        <StatusAlert message={error} />
        <button className="hl-button-secondary" onClick={() => { setError(""); setRetry((value) => value + 1); }} type="button">Retry</button>
      </section>
    ) : null;
  }
  if (!status.enabled) return null;

  return (
    <section className="hl-settings-card space-y-4" aria-labelledby="recovery-email-title">
      <h2 className="hl-section-title" id="recovery-email-title">Recovery email</h2>
      <p className="text-sm text-slate-600 break-all">{status.email}</p>
      {status.verified ? (
        <StatusAlert message="Email verified. You can use it to recover your account." tone="success" />
      ) : challenge ? (
        <EmailCodeForm
          backLabel="Request a new code"
          description="Enter the code sent to your registered email."
          initialChallenge={challenge}
          onBack={() => setChallenge(null)}
          onVerify={async (proof) => {
            await verifyEnrollmentCode(proof);
            setStatus({ ...status, verified: true });
            setChallenge(null);
          }}
        />
      ) : (
        <form className="space-y-4" onSubmit={requestCode}>
          <p className="text-sm leading-6 text-slate-600">Verify your email now so you can reset your password if you forget it.</p>
          {error ? <StatusAlert message={error} /> : null}
          <FormField htmlFor="recovery-current-password" label="Current password" required>
            <PasswordInput autoComplete="current-password" className={citizenInputClassName} id="recovery-current-password"
              maxLength={128} onChange={(event) => setPassword(event.target.value)} required value={password} />
          </FormField>
          <button className="hl-button-primary" disabled={pending} type="submit">{pending ? "Sending…" : "Send verification code"}</button>
        </form>
      )}
    </section>
  );
}
