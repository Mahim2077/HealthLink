"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AdminPortalGuard } from "@/components/admin/admin-portal-guard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import {
  correctCitizenIdentity,
  loadCitizenIdentity,
} from "@/lib/admin/api";
import type {
  CitizenIdentityCorrectionRequest,
  CitizenIdentityCorrectionType,
  CitizenIdentityDetail as CitizenIdentityDetailType,
} from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";


function asDate(value: string | null): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function CitizenIdentityDetailContent({ userId }: { userId: string }) {
  const [detail, setDetail] = useState<CitizenIdentityDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [correctionType, setCorrectionType] =
    useState<CitizenIdentityCorrectionType>("NID");
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const result = await loadCitizenIdentity(userId);
      setError(null);
      setDetail(result);
      setNewValue(
        correctionType === "NID"
          ? result.nid_number ?? ""
          : result.birth_certificate_number ?? "",
      );
    } catch (cause) {
      setError(citizenErrorMessage(cause, "We could not load this citizen identity."));
    }
  }, [userId, correctionType]);

  useEffect(() => {
    let active = true;
    void loadCitizenIdentity(userId).then(
      (result) => {
        if (!active) return;
        setError(null);
        setDetail(result);
        setNewValue(
          correctionType === "NID"
            ? result.nid_number ?? ""
            : result.birth_certificate_number ?? "",
        );
      },
      (cause: unknown) => {
        if (active) setError(citizenErrorMessage(cause, "We could not load this citizen identity."));
      },
    );
    return () => {
      active = false;
    };
  }, [userId, correctionType]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setActionError(null);
    setActionMessage(null);
    const trimmedValue = newValue.trim();
    const trimmedReason = reason.trim();
    if (!trimmedValue) {
      setActionError("A new value is required.");
      return;
    }
    if (!trimmedReason) {
      setActionError("A reason is required for audit.");
      return;
    }
    const payload: CitizenIdentityCorrectionRequest = {
      correction_type: correctionType,
      new_value: trimmedValue,
      reason: trimmedReason,
    };
    setSaving(true);
    try {
      const response = await correctCitizenIdentity(userId, payload);
      setActionMessage(
        `Recorded ${response.correction_type} correction (audit log ${response.audit_log_id.slice(0, 8)}…).`,
      );
      setReason("");
      const refreshed = await loadCitizenIdentity(userId);
      setDetail(refreshed);
    } catch (cause) {
      setActionError(
        citizenErrorMessage(cause, "We could not record this correction."),
      );
    } finally {
      setSaving(false);
    }
  };

  const switchType = (next: CitizenIdentityCorrectionType) => {
    setCorrectionType(next);
    setActionError(null);
    setActionMessage(null);
    if (detail) {
      setNewValue(next === "NID" ? detail.nid_number ?? "" : detail.birth_certificate_number ?? "");
    }
  };

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-10 sm:px-8 lg:px-10" id="main-content">
      <Link className="text-sm font-bold text-indigo-700" href="/admin/citizen-identities">
        ← Identity search
      </Link>
      {!detail && !error ? (
        <div className="mt-8">
          <LoadingState description="Loading the trusted identity record." label="Loading identity" />
        </div>
      ) : null}
      {error ? (
        <div className="mt-8">
          <ErrorState
            message={error}
            onAction={() => {
              setError(null);
              void load();
            }}
            title="Identity unavailable"
          />
        </div>
      ) : null}
      {detail ? (
        <>
          <header className="mt-7 border-b border-slate-200 pb-7">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-700">
                Citizen identity
              </p>
              <span
                className={`rounded-full px-3 py-1 text-xs font-bold ${
                  detail.is_active
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {detail.is_active ? "ACTIVE" : "INACTIVE"}
              </span>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-800">
                Registered via {detail.registered_with}
              </span>
            </div>
            <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950">
              {detail.first_name} {detail.last_name}
            </h1>
            <p className="mt-2 break-words text-sm text-slate-600">{detail.email}</p>
          </header>
          <div className="mt-7 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-bold text-slate-950">Identity record</h2>
              <dl className="mt-5 grid gap-4">
                <div>
                  <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">National ID</dt>
                  <dd className="mt-1 break-words text-sm font-semibold text-slate-950">
                    {detail.nid_number ?? "Not recorded"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                    Birth Certificate Number
                  </dt>
                  <dd className="mt-1 break-words text-sm font-semibold text-slate-950">
                    {detail.birth_certificate_number ?? "Not recorded"}
                  </dd>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Date of birth</dt>
                    <dd className="mt-1 text-sm text-slate-800">{detail.date_of_birth ?? "Not recorded"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Gender</dt>
                    <dd className="mt-1 text-sm text-slate-800">{detail.gender ?? "Not recorded"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Blood group</dt>
                    <dd className="mt-1 text-sm text-slate-800">{detail.blood_group ?? "Not recorded"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Address</dt>
                    <dd className="mt-1 text-sm text-slate-800">{detail.address ?? "Not recorded"}</dd>
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                      Active auth sessions
                    </dt>
                    <dd className="mt-1 text-sm font-semibold text-slate-900">{detail.auth_session_count}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">
                      Identity last updated
                    </dt>
                    <dd className="mt-1 text-sm text-slate-800">{asDate(detail.identity_updated_at)}</dd>
                  </div>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">User ID</dt>
                  <dd className="mt-1 break-all text-xs text-slate-700">{detail.user_id}</dd>
                </div>
              </dl>
            </section>
            <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-bold text-slate-950">Record a correction</h2>
              <p className="mt-2 text-sm text-slate-600">
                Use this only when an existing NID or BCN is incorrect. Each correction is logged
                with the acting administrator and never triggers an automatic merge.
              </p>
              <form className="mt-5 grid gap-4" onSubmit={submit}>
                <fieldset>
                  <legend className="text-sm font-bold text-slate-700">Correction type</legend>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <label className="flex min-h-11 items-center gap-3 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold text-slate-700">
                      <input
                        checked={correctionType === "NID"}
                        name="correction_type"
                        onChange={() => switchType("NID")}
                        type="radio"
                      />
                      National ID
                    </label>
                    <label className="flex min-h-11 items-center gap-3 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold text-slate-700">
                      <input
                        checked={correctionType === "BCN"}
                        name="correction_type"
                        onChange={() => switchType("BCN")}
                        type="radio"
                      />
                      Birth Certificate Number
                    </label>
                  </div>
                </fieldset>
                <label className="text-sm font-bold text-slate-700">
                  New value
                  <input
                    className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                    maxLength={64}
                    onChange={(event) => setNewValue(event.target.value)}
                    required
                    value={newValue}
                  />
                </label>
                <label className="text-sm font-bold text-slate-700">
                  Reason (recorded in audit log)
                  <textarea
                    className="mt-2 min-h-28 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm"
                    maxLength={2000}
                    onChange={(event) => setReason(event.target.value)}
                    required
                    value={reason}
                  />
                </label>
                {actionError ? (
                  <p aria-live="assertive" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">
                    {actionError}
                  </p>
                ) : null}
                {actionMessage ? (
                  <p aria-live="polite" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">
                    {actionMessage}
                  </p>
                ) : null}
                <button
                  className="min-h-11 rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white disabled:opacity-60"
                  disabled={saving}
                  type="submit"
                >
                  {saving ? "Recording correction…" : "Record correction"}
                </button>
              </form>
              {!detail.nid_number && correctionType === "NID" ? (
                <EmptyState
                  message="No NID is currently recorded. Providing a value will create a new record."
                  title="Adding NID"
                />
              ) : null}
              {!detail.birth_certificate_number && correctionType === "BCN" ? (
                <EmptyState
                  message="No Birth Certificate Number is currently recorded. A BCN correction cannot be recorded while the value is missing."
                  title="BCN missing"
                />
              ) : null}
            </section>
          </div>
        </>
      ) : null}
    </main>
  );
}

export function CitizenIdentityDetail({ userId }: { userId: string }) {
  return (
    <AdminPortalGuard>
      <CitizenIdentityDetailContent userId={userId} />
    </AdminPortalGuard>
  );
}