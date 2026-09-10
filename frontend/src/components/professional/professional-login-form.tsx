"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { PasswordInput } from "@/components/ui/password-input";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { loginProfessional } from "@/lib/professional/api";
import {
  PROFESSIONAL_ROLES,
  type ProfessionalRoleCode,
} from "@/lib/professional/types";

const inputClass =
  "mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm text-slate-950 outline-none transition hover:border-slate-400 focus:border-sky-600 focus:ring-4 focus:ring-sky-100";

export function ProfessionalLoginForm() {
  const router = useRouter();
  const [nid, setNid] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<ProfessionalRoleCode>("DOCTOR");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await loginProfessional({
        nid_number: nid.trim(),
        password,
        role_code: role,
      });
      router.replace(
        result.verification_status === "VERIFIED"
          ? "/professional/dashboard"
          : "/professional/status",
      );
    } catch (reason) {
      setError(
        citizenErrorMessage(
          reason,
          "Invalid NID, password, or professional role.",
        ),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main
      className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-8 px-5 py-10 sm:px-8 sm:py-14 lg:grid-cols-[1fr_0.9fr] lg:gap-12 lg:px-10"
      id="main-content"
    >
      <section className="order-2 lg:order-1">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-sky-700">
          Role-aware access
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-[-0.05em] text-slate-950 sm:text-5xl">
          Enter the role you intend to use.
        </h1>
        <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">
          Your selected application becomes the active context for this
          session. Other roles never inherit its permissions.
        </p>
      </section>

      <section className="order-1 rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_22px_60px_-42px_rgba(15,23,42,0.45)] sm:p-8 lg:order-2">
        <h2 className="text-2xl font-bold text-slate-950">Professional sign in</h2>
        <form className="mt-6 grid gap-5" onSubmit={submit}>
          <label className="text-sm font-bold text-slate-700">
            National ID
            <input
              className={inputClass}
              maxLength={32}
              onChange={(event) => setNid(event.target.value)}
              required
              value={nid}
            />
          </label>
          <label className="text-sm font-bold text-slate-700">
            Password
            <PasswordInput
              autoComplete="current-password"
              className={inputClass}
              maxLength={128}
              onChange={(event) => setPassword(event.target.value)}
              required
              value={password}
            />
          </label>
          <label className="text-sm font-bold text-slate-700">
            Professional role
            <select
              className={inputClass}
              onChange={(event) =>
                setRole(event.target.value as ProfessionalRoleCode)
              }
              value={role}
            >
              {PROFESSIONAL_ROLES.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          {error ? (
            <p
              aria-live="assertive"
              className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800"
            >
              {error}
            </p>
          ) : null}
          <button
            className="min-h-12 rounded-xl bg-sky-700 px-5 text-sm font-bold text-white transition hover:bg-sky-800 disabled:opacity-60"
            disabled={submitting}
            type="submit"
          >
            {submitting ? "Signing in…" : "Sign in to Professional Portal"}
          </button>
        </form>
        <p className="mt-5 text-sm text-slate-600">
          Not registered?{" "}
          <Link className="font-bold text-sky-700" href="/professional/register">
            Apply with your NID
          </Link>
          .
        </p>
      </section>
    </main>
  );
}
