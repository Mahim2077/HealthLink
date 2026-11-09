"use client";

import { useEffect, useId, useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import { emailActionError, type EmailChallenge, type EmailCodeProof } from "@/lib/auth/email-codes";

export function EmailCodeForm({
  initialChallenge,
  description,
  onVerify,
  onResend,
  onBack,
  backLabel,
}: {
  initialChallenge: EmailChallenge;
  description: string;
  onVerify: (proof: EmailCodeProof) => Promise<void>;
  onResend?: () => Promise<EmailChallenge>;
  onBack: () => void;
  backLabel: string;
}) {
  const inputId = useId();
  const [challenge, setChallenge] = useState(initialChallenge);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState<"verify" | "resend" | null>(null);
  const [error, setError] = useState("");
  const [resendTime, setResendTime] = useState(() => Date.now() + initialChallenge.resend_after_seconds * 1000);
  const [seconds, setSeconds] = useState(initialChallenge.resend_after_seconds);

  useEffect(() => {
    if (!onResend) return;
    const timer = window.setInterval(() => setSeconds(Math.max(0, Math.ceil((resendTime - Date.now()) / 1000))), 1000);
    return () => window.clearInterval(timer);
  }, [onResend, resendTime]);

  const verify = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || !/^[0-9]{6}$/.test(code)) return;
    setBusy("verify");
    setError("");
    try {
      await onVerify({ challenge_id: challenge.challenge_id, code });
    } catch (reason) {
      setError(emailActionError(reason, "We could not verify the code. Please try again."));
    } finally {
      setBusy(null);
    }
  };

  const resend = async () => {
    if (busy || seconds || !onResend) return;
    setBusy("resend");
    setError("");
    try {
      const next = await onResend();
      setChallenge(next);
      setCode("");
      setResendTime(Date.now() + next.resend_after_seconds * 1000);
      setSeconds(next.resend_after_seconds);
    } catch (reason) {
      setError(emailActionError(reason, "We could not send a new code. Please try again."));
    } finally {
      setBusy(null);
    }
  };

  return (
    <form className="space-y-5" onSubmit={verify}>
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-950">Check your email</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      </div>
      {error ? <StatusAlert message={error} /> : null}
      <FormField htmlFor={inputId} label="Six-digit code" hint="The code expires in 10 minutes." required>
        <input
          autoComplete="one-time-code"
          className={`${citizenInputClassName} max-w-xs font-mono tracking-[0.28em]`}
          id={inputId}
          inputMode="numeric"
          maxLength={6}
          onChange={(event) => setCode(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
          pattern="[0-9]{6}"
          required
          value={code}
        />
      </FormField>
      <div className="flex flex-wrap items-center gap-3">
        <button className="hl-button-primary" disabled={busy !== null || code.length !== 6} type="submit">
          {busy === "verify" ? "Verifying…" : "Verify code"}
        </button>
        {onResend ? (
          <button className="hl-button-secondary" disabled={busy !== null || seconds > 0} onClick={() => void resend()} type="button">
            {busy === "resend" ? "Sending…" : seconds > 0 ? `Resend in ${seconds}s` : "Resend code"}
          </button>
        ) : null}
        <button className="hl-button-secondary" disabled={busy !== null} onClick={onBack} type="button">{backLabel}</button>
      </div>
    </form>
  );
}
