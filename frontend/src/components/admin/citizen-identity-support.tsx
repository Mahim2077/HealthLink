"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AdminPortalGuard } from "@/components/admin/admin-portal-guard";
import { AdminSectionHeader } from "@/components/admin/admin-section-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { searchCitizenIdentities } from "@/lib/admin/api";
import type { CitizenIdentitySummary } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";


function asDateTime(value: string | null): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function CitizenIdentitySupportContent() {
  const [nidNumber, setNidNumber] = useState("");
  const [birthCertificateNumber, setBirthCertificateNumber] = useState("");
  const [email, setEmail] = useState("");
  const [userId, setUserId] = useState("");
  const [rows, setRows] = useState<CitizenIdentitySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const search = useCallback(
    async (filters: {
      nid_number?: string;
      birth_certificate_number?: string;
      email?: string;
      user_id?: string;
    }) => {
      try {
        const result = await searchCitizenIdentities({ ...filters, limit: 50 });
        setError(null);
        setRows(result);
      } catch (reason) {
        setError(citizenErrorMessage(reason, "We could not search citizen identities."));
        setRows([]);
      }
    },
    [],
  );

  useEffect(() => {
    let active = true;
    void searchCitizenIdentities({ limit: 50 }).then((result) => {
      if (!active) return;
      setError(null);
      setRows(result);
      setSubmitted(true);
    }).catch((reason) => {
      if (!active) return;
      setError(citizenErrorMessage(reason, "We could not search citizen identities."));
      setRows([]);
      setSubmitted(true);
    });
    return () => {
      active = false;
    };
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = {
      nid_number: nidNumber.trim(),
      birth_certificate_number: birthCertificateNumber.trim(),
      email: email.trim(),
      user_id: userId.trim(),
    };
    if (!Object.values(trimmed).some((value) => value)) {
      setFormError("Provide at least one of NID, Birth Certificate Number, email, or User ID.");
      return;
    }
    setFormError(null);
    setSubmitted(true);
    void search(trimmed);
  };

  const reset = () => {
    setNidNumber("");
    setBirthCertificateNumber("");
    setEmail("");
    setUserId("");
    setError(null);
    setFormError(null);
    setSubmitted(false);
    void search({});
  };

  return (
    <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
      <AdminSectionHeader
        description="Search by NID, Birth Certificate Number, email, or User ID. Corrections are recorded with the acting administrator's identity and are not auto-merged."
        eyebrow="Citizen identity support"
        title="Find a citizen identity"
      />
      <div className="mt-8 grid gap-7 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-slate-950">Search filters</h2>
          <p className="mt-2 text-sm text-slate-600">At least one filter is required.</p>
          <form className="mt-5 grid gap-4" onSubmit={submit}>
            <label className="text-sm font-bold text-slate-700">
              National ID (NID)
              <input
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                maxLength={32}
                onChange={(event) => setNidNumber(event.target.value)}
                value={nidNumber}
              />
            </label>
            <label className="text-sm font-bold text-slate-700">
              Birth Certificate Number
              <input
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                maxLength={64}
                onChange={(event) => setBirthCertificateNumber(event.target.value)}
                value={birthCertificateNumber}
              />
            </label>
            <label className="text-sm font-bold text-slate-700">
              Email
              <input
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                maxLength={320}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                value={email}
              />
            </label>
            <label className="text-sm font-bold text-slate-700">
              User ID (UUID)
              <input
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                maxLength={64}
                onChange={(event) => setUserId(event.target.value)}
                value={userId}
              />
            </label>
            {formError ? (
              <p aria-live="polite" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">
                {formError}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <button
                className="min-h-11 rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white"
                type="submit"
              >
                Search identities
              </button>
              <button
                className="min-h-11 rounded-xl border border-slate-300 px-5 text-sm font-bold text-slate-700"
                onClick={reset}
                type="button"
              >
                Clear filters
              </button>
            </div>
          </form>
        </section>
        <section aria-label="Identity search results" className="space-y-4">
          {!submitted && rows === null ? (
            <LoadingState description="Preparing the search workspace." label="Loading identity search" />
          ) : null}
          {submitted && rows === null && !error ? (
            <LoadingState description="Searching the trusted citizen identity registry." label="Searching identities" />
          ) : null}
          {error ? (
            <ErrorState
              message={error}
              onAction={() => {
                setError(null);
                void search({});
              }}
              title="Identity search unavailable"
            />
          ) : null}
          {submitted && rows && rows.length === 0 ? (
            <EmptyState
              message="No citizen identity matched these filters."
              title="No matches found"
            />
          ) : null}
          <div className="grid gap-4">
            {rows?.map((row) => (
              <article
                className="rounded-[1.4rem] border border-slate-200 bg-white p-5 shadow-sm"
                key={row.user_id}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-bold text-slate-950">
                        {row.first_name} {row.last_name}
                      </h2>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                          row.is_active
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {row.is_active ? "ACTIVE" : "INACTIVE"}
                      </span>
                      <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-800">
                        Registered via {row.registered_with}
                      </span>
                    </div>
                    <p className="mt-2 break-words text-sm text-slate-600">{row.email}</p>
                    <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">NID</dt>
                        <dd className="mt-1 break-words text-sm font-semibold text-slate-900">
                          {row.nid_number ?? "Not recorded"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                          Birth Certificate Number
                        </dt>
                        <dd className="mt-1 break-words text-sm font-semibold text-slate-900">
                          {row.birth_certificate_number ?? "Not recorded"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                          Identity created
                        </dt>
                        <dd className="mt-1 text-sm text-slate-800">
                          {asDateTime(row.identity_created_at)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                          Identity updated
                        </dt>
                        <dd className="mt-1 text-sm text-slate-800">
                          {asDateTime(row.identity_updated_at)}
                        </dd>
                      </div>
                    </dl>
                  </div>
                  <Link
                    className="inline-flex min-h-11 items-center justify-center rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white"
                    href={`/admin/citizen-identities/${row.user_id}`}
                  >
                    Open identity
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

export function CitizenIdentitySupport() {
  return (
    <AdminPortalGuard>
      <CitizenIdentitySupportContent />
    </AdminPortalGuard>
  );
}