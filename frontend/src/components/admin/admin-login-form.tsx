"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { citizenInputClassName, FormField } from "@/components/citizen/form-field";
import { StatusAlert } from "@/components/citizen/status-alert";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { loginAdmin } from "@/lib/admin/api";
import type { AdminLoginRequest, AdminLoginResponse } from "@/lib/admin/types";

export function AdminLoginForm({
  loginAction = loginAdmin,
}: {
  loginAction?: (request: AdminLoginRequest) => Promise<AdminLoginResponse>;
}) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await loginAction({ email: email.trim(), password });
      router.replace("/admin/dashboard");
    } catch (reason) {
      setError(citizenErrorMessage(reason, "Invalid email or password."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:px-10" id="main-content">
      <section>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-700">Trusted operations</p>
        <h1 className="mt-4 max-w-lg font-display text-4xl font-bold tracking-[-0.045em] text-slate-950 sm:text-5xl">Administrative access with clear boundaries.</h1>
        <p className="mt-5 max-w-lg text-base leading-7 text-slate-600">Admin accounts are provisioned through a trusted operational process. There is no public admin registration.</p>
      </section>
      <section className="rounded-[2rem] border border-white bg-white/95 p-6 shadow-xl shadow-slate-900/[0.07] sm:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-700">Admin sign in</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-950">Welcome back</h2>
        <form className="mt-7 space-y-5" onSubmit={submit}>
          <FormField htmlFor="admin-email" label="Email address" required><input autoComplete="email" className={citizenInputClassName} disabled={submitting} id="admin-email" maxLength={320} onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></FormField>
          <FormField htmlFor="admin-password" label="Password" required><input autoComplete="current-password" className={citizenInputClassName} disabled={submitting} id="admin-password" maxLength={128} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /></FormField>
          {error ? <StatusAlert message={error} /> : null}
          <button className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-indigo-700 px-6 text-sm font-bold text-white hover:bg-indigo-800 disabled:cursor-wait disabled:opacity-60" disabled={submitting} type="submit">{submitting ? "Signing in…" : "Sign in to Admin Portal"}</button>
        </form>
      </section>
    </main>
  );
}
