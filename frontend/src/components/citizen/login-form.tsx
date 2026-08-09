"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "./form-field";
import { StatusAlert } from "./status-alert";
import { loginCitizen } from "@/lib/citizen/api";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import type {
  CitizenLoginRequest,
  CitizenLoginResponse,
} from "@/lib/citizen/types";

type LoginErrors = {
  email?: string;
  password?: string;
};

export function CitizenLoginForm({
  loginAction = loginCitizen,
  onLoggedIn,
  registrationComplete = false,
}: {
  loginAction?: (request: CitizenLoginRequest) => Promise<CitizenLoginResponse>;
  onLoggedIn?: (response: CitizenLoginResponse) => void;
  registrationComplete?: boolean;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<LoginErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: LoginErrors = {};

    if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      nextErrors.email = "Enter your account email address.";
    }
    if (!password) {
      nextErrors.password = "Enter your password.";
    } else if (password.length > 128) {
      nextErrors.password = "Password cannot exceed 128 characters.";
    }

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      setApiError("Please enter your email and password.");
      return;
    }

    setIsSubmitting(true);
    setApiError(null);

    try {
      const response = await loginAction({
        email: email.trim().toLowerCase(),
        password,
      });

      if (onLoggedIn) {
        onLoggedIn(response);
      } else {
        router.replace("/citizen/dashboard");
      }
    } catch (error) {
      setApiError(
        citizenErrorMessage(
          error,
          "We could not sign you in. Check your email and password, then try again.",
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="border-b border-slate-200 pb-7">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">Citizen sign in</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Welcome back</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Use the email and password connected to your citizen account.
        </p>
      </div>

      <form className="mt-8 space-y-5" noValidate onSubmit={handleSubmit}>
        {registrationComplete ? (
          <StatusAlert
            message="Your citizen account is ready. Sign in to continue."
            tone="success"
          />
        ) : null}
        {apiError ? <StatusAlert message={apiError} /> : null}

        <FormField error={errors.email} htmlFor="email" label="Email address" required>
          <input
            aria-describedby={errors.email ? "email-error" : undefined}
            aria-invalid={Boolean(errors.email)}
            autoComplete="email"
            autoFocus
            className={citizenInputClassName}
            id="email"
            maxLength={320}
            onChange={(event) => {
              setEmail(event.target.value);
              setErrors((current) => ({ ...current, email: undefined }));
              setApiError(null);
            }}
            required
            type="email"
            value={email}
          />
        </FormField>

        <FormField error={errors.password} htmlFor="password" label="Password" required>
          <input
            aria-describedby={errors.password ? "password-error" : undefined}
            aria-invalid={Boolean(errors.password)}
            autoComplete="current-password"
            className={citizenInputClassName}
            id="password"
            maxLength={128}
            onChange={(event) => {
              setPassword(event.target.value);
              setErrors((current) => ({ ...current, password: undefined }));
              setApiError(null);
            }}
            required
            type="password"
            value={password}
          />
        </FormField>

        <button
          className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-teal-700 px-6 text-sm font-bold text-white shadow-lg shadow-teal-900/15 transition hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-wait disabled:opacity-65"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Signing in…" : "Sign in to Citizen Portal"}
        </button>

        <div className="rounded-xl bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500">
          Your HealthLink session is protected and securely restored on this browser when you return.
        </div>

        <p className="border-t border-slate-200 pt-5 text-sm text-slate-600">
          New to HealthLink?{" "}
          <Link className="font-bold text-teal-700 hover:text-teal-900" href="/citizen/register">
            Create a citizen account
          </Link>
        </p>
      </form>
    </div>
  );
}
