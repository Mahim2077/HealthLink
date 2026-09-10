"use client";

import {
  ArrowRightIcon,
  BuildingOffice2Icon,
  CheckBadgeIcon,
  ClipboardDocumentCheckIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import { loadProfessionalMe } from "@/lib/professional/api";
import type { ProfessionalMe } from "@/lib/professional/types";

function ProfessionalGuard({ children }: { children: ReactNode }) {
  const auth = usePortalAuth("PROFESSIONAL");
  const [failed, setFailed] = useState(false);
  const status = auth.status;
  const refresh = auth.refreshSession;

  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refresh().catch(() => {
      if (active) setFailed(true);
    });
    return () => {
      active = false;
    };
  }, [refresh, status]);

  if (status === "unauthenticated" && !failed) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState description="Checking for a Professional session." label="Checking Professional session" />
      </main>
    );
  }
  if (status === "unauthenticated") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          action={
            <Link className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" href="/professional/login">
              Professional sign in
            </Link>
          }
          message="Sign in with your NID and selected role."
          title="Professional sign in required"
        />
      </main>
    );
  }
  if (!auth.isRequiredPortal) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState message="This session belongs to another HealthLink portal." title="Professional Portal access required" />
      </main>
    );
  }
  return children;
}

function StatusBadge({ status }: { status: ProfessionalMe["verification_status"] }) {
  const label = status === "VERIFIED" ? "Verified" : status === "PENDING" ? "Under review" : "Not approved";
  const style = status === "VERIFIED"
    ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
    : status === "PENDING"
      ? "bg-amber-50 text-amber-800 ring-amber-100"
      : "bg-rose-50 text-rose-700 ring-rose-100";
  return (
    <span className={"inline-flex rounded-full px-3 py-1.5 text-xs font-bold ring-1 ring-inset " + style}>
      {label}
    </span>
  );
}

function ProfessionalPortalContent({
  mode,
  verifiedDoctorSlot,
}: {
  mode: "dashboard" | "status";
  verifiedDoctorSlot?: ReactNode;
}) {
  const [record, setRecord] = useState<ProfessionalMe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void loadProfessionalMe().then(
      (value) => {
        if (active) {
          setRecord(value);
          setError(null);
        }
      },
      (reason) => {
        if (active) {
          setError(citizenErrorMessage(reason, "We could not load this professional role."));
        }
      },
    );
    return () => {
      active = false;
    };
  }, [version]);

  const retry = useCallback(() => {
    setRecord(null);
    setError(null);
    setVersion((value) => value + 1);
  }, []);

  if (!record && !error) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState description="Loading the selected professional role." label="Loading Professional Portal" />
      </main>
    );
  }
  if (error) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <ErrorState message={error} onAction={retry} title="Professional Portal unavailable" />
      </main>
    );
  }
  if (!record) return null;

  const verified = record.verification_status === "VERIFIED";
  if (mode === "dashboard" && !verified) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          action={
            <Link className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white" href="/professional/status">
              View verification status
            </Link>
          }
          message="Clinical workspace access begins only after this selected role is verified."
          title={record.verification_status + " role is restricted"}
        />
      </main>
    );
  }

  if (mode === "status") {
    return (
      <main className="hl-page" id="main-content">
        <header className="hl-page-header">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-sky-700">Professional access</p>
          <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.045em] text-slate-950 sm:text-4xl">
            Verification status
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Review the standing of the role selected for this Professional Portal session.
          </p>
        </header>

        <section className="hl-card mt-8 max-w-3xl p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-100">
              <ClipboardDocumentCheckIcon aria-hidden="true" className="size-6" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-2xl font-bold tracking-tight text-slate-950">{record.role_name}</h2>
                <StatusBadge status={record.verification_status} />
              </div>
              <p className="mt-3 text-sm text-slate-600">Designation: {record.designation}</p>
            </div>
          </div>

          {record.rejection_reason ? (
            <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-rose-700">Reason</p>
              <p className="mt-2 text-sm leading-6 text-rose-900">{record.rejection_reason}</p>
            </div>
          ) : null}

          {verified ? (
            <Link className="mt-7 inline-flex min-h-11 items-center gap-2 rounded-xl bg-sky-700 px-5 text-sm font-bold text-white hover:bg-sky-800" href="/professional/dashboard">
              Enter role dashboard
              <ArrowRightIcon aria-hidden="true" className="size-4" />
            </Link>
          ) : (
            <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
              This restricted session can display verification status only.
            </p>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="hl-page" id="main-content">
      <header className="max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-sky-700">
          Active role · {record.role_name}
        </p>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-[-0.055em] text-slate-950 sm:text-5xl">
          Welcome, {record.first_name}.
        </h1>
        <p className="mt-3 text-lg text-slate-600">
          Your focused workspace for today&rsquo;s care.
        </p>
      </header>

      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <section className="hl-card p-6 sm:p-7">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100">
              <CheckBadgeIcon aria-hidden="true" className="size-6" />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-emerald-700">Verified role context</p>
              <h2 className="mt-2 text-xl font-bold text-slate-950">{record.role_name}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Your selected role determines the tools and clinical permissions available in this session.
              </p>
            </div>
          </div>
        </section>

        <section className="hl-card p-6 sm:p-7">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-100">
              <BuildingOffice2Icon aria-hidden="true" className="size-6" />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">Primary facility</p>
              <h2 className="mt-2 text-xl font-bold text-slate-950">{record.facility?.name ?? "No facility linked"}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {record.facility?.address ?? "Contact an administrator if this verified assignment is incomplete."}
              </p>
              <Link className="mt-4 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-sky-700" href="/professional/status">
                View verification details
                <ArrowRightIcon aria-hidden="true" className="size-4" />
              </Link>
            </div>
          </div>
        </section>
      </div>

      {verified && record.role_code === "DOCTOR" && verifiedDoctorSlot ? (
        <div className="mt-6">{verifiedDoctorSlot}</div>
      ) : null}
    </main>
  );
}

export function ProfessionalPortal({
  mode,
  verifiedDoctorSlot,
}: {
  mode: "dashboard" | "status";
  verifiedDoctorSlot?: ReactNode;
}) {
  return (
    <ProfessionalGuard>
      <ProfessionalPortalContent mode={mode} verifiedDoctorSlot={verifiedDoctorSlot} />
    </ProfessionalGuard>
  );
}
