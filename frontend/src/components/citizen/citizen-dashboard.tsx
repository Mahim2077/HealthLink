"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/async-state";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { loadCitizenDashboard } from "@/lib/citizen/api";
import {
  citizenErrorMessage,
  formatCitizenDate,
  maskIdentityValue,
} from "@/lib/citizen/presentation";
import type { CitizenDashboardData } from "@/lib/citizen/types";

type DashboardRequestState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CitizenDashboardData };

function DataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3.5">
      <dt className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500">{label}</dt>
      <dd className="mt-1.5 break-words text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

function PortalMismatch() {
  return (
    <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-slate-800"
            href="/"
          >
            Return to HealthLink
          </Link>
        }
        message="This session belongs to a different HealthLink portal. Sign in through the Citizen Portal to view citizen information."
        title="Citizen Portal access required"
      />
    </main>
  );
}

function SignedOut() {
  return (
    <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-semibold text-white transition hover:bg-teal-800"
            href="/citizen/login"
          >
            Sign in to Citizen Portal
          </Link>
        }
        message="Your session may have expired, or this browser does not have an active Citizen Portal session."
        title="Sign in to continue"
      />
    </main>
  );
}

function DashboardContent({
  loadAction,
  onLogoutStarted,
}: {
  loadAction: () => Promise<CitizenDashboardData>;
  onLogoutStarted: () => void;
}) {
  const auth = usePortalAuth("CITIZEN");
  const router = useRouter();
  const [requestVersion, setRequestVersion] = useState(0);
  const [requestState, setRequestState] = useState<DashboardRequestState>({
    status: "loading",
  });
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void loadAction()
      .then((data) => {
        if (active) setRequestState({ data, status: "ready" });
      })
      .catch((error: unknown) => {
        if (active) {
          setRequestState({
            message: citizenErrorMessage(
              error,
              "We could not load your citizen dashboard. Please try again.",
            ),
            status: "error",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [loadAction, requestVersion]);

  const retry = () => {
    setRequestState({ status: "loading" });
    setRequestVersion((version) => version + 1);
  };

  const handleLogout = async () => {
    onLogoutStarted();
    setIsLoggingOut(true);
    setLogoutError(null);

    try {
      await auth.logout();
    } catch {
      setLogoutError(
        "Your local session is closed. The server could not confirm logout, so avoid using this browser until connectivity returns.",
      );
    } finally {
      router.replace("/citizen/login");
      setIsLoggingOut(false);
    }
  };

  if (requestState.status === "loading") {
    return (
      <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
        <LoadingState
          description="Securely loading your profile and identity overview."
          label="Preparing your Citizen Dashboard"
        />
      </main>
    );
  }

  if (requestState.status === "error") {
    return (
      <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
        <ErrorState
          message={requestState.message}
          onAction={retry}
          title="Dashboard unavailable"
        />
      </main>
    );
  }

  const { identity, profile } = requestState.data;
  const identityValue =
    identity.registered_with === "NID"
      ? identity.nid_number
      : identity.birth_certificate_number;
  const displayGender = profile.gender
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (character) => character.toUpperCase());

  return (
    <main className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 sm:py-14 lg:px-10" id="main-content">
      <div className="flex flex-col gap-6 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800">
            <span className="size-2 rounded-full bg-emerald-500" />
            Secure Citizen session
          </div>
          <h1 className="mt-4 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
            Welcome, {profile.first_name}.
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            This is your secure account and identity overview.
          </p>
        </div>
        <button
          className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-5 text-sm font-bold text-slate-700 shadow-sm transition hover:border-slate-400 hover:text-slate-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-wait disabled:opacity-60"
          disabled={isLoggingOut}
          onClick={handleLogout}
          type="button"
        >
          {isLoggingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>

      {logoutError ? (
        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert">
          {logoutError}
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[0.78fr_1.22fr]">
        <section className="rounded-[1.75rem] border border-teal-100 bg-teal-950 p-6 text-white shadow-xl shadow-teal-950/10 sm:p-7">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-300">Registered identity</p>
              <h2 className="mt-2 text-xl font-bold">{identity.registered_with === "NID" ? "National ID" : "Birth Certificate"}</h2>
            </div>
            <span className="flex size-11 items-center justify-center rounded-2xl bg-white/10 text-teal-200 ring-1 ring-inset ring-white/10">
              <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
                <path d="M12 3 5 6v5c0 4.7 2.8 8 7 10 4.2-2 7-5.3 7-10V6l-7-3Zm-3 9 2 2 4-4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
              </svg>
            </span>
          </div>
          <p
            aria-label={
              identityValue && identityValue.length > 4
                ? `Masked identity ending in ${identityValue.slice(-4)}`
                : "Masked identity"
            }
            className="mt-8 font-mono text-xl font-bold tracking-[0.14em] text-white"
            data-testid="masked-identity"
          >
            {maskIdentityValue(identityValue)}
          </p>
          <p className="mt-3 text-xs leading-5 text-teal-100/70">
            Identity numbers are masked in the interface. Identity changes are not available from this dashboard.
          </p>
          <div className="mt-7 rounded-xl border border-white/10 bg-white/[0.06] p-4">
            <p className="text-xs font-semibold text-teal-100">Registered using</p>
            <p className="mt-1 text-sm font-bold">{identity.registered_with === "NID" ? "NID" : "Birth Certificate Number"}</p>
          </div>
        </section>

        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Citizen profile</p>
              <h2 className="mt-2 text-xl font-bold tracking-tight text-slate-950">
                {profile.first_name} {profile.last_name}
              </h2>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500">Read only</span>
          </div>
          <dl className="mt-6 grid gap-3 sm:grid-cols-2">
            <DataItem label="Email" value={profile.email} />
            <DataItem label="Date of birth" value={formatCitizenDate(profile.date_of_birth)} />
            <DataItem label="Gender" value={displayGender} />
            <DataItem label="Blood group" value={profile.blood_group ?? "Not specified"} />
            <div className="sm:col-span-2">
              <DataItem label="Address" value={profile.address ?? "Not specified"} />
            </div>
          </dl>
        </section>
      </div>

      <section className="mt-6 rounded-[1.75rem] border border-slate-200 bg-white/80 p-6 sm:p-7">
        <div className="flex gap-4">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
            <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
              <path d="M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
            </svg>
          </span>
          <div>
            <h2 className="text-base font-bold text-slate-950">Your citizen account is connected</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Keep your personal details current and, if you registered with a Birth Certificate, add your NID once.
            </p>
            <Link className="mt-4 inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white hover:bg-teal-800" href="/citizen/profile">
              Manage profile and identity
            </Link>
            <Link className="ml-0 mt-3 inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-5 text-sm font-bold text-slate-700 hover:border-slate-400 sm:ml-3" href="/professional/onboard">
              Add a professional role
            </Link>
            <Link className="ml-0 mt-3 inline-flex min-h-11 items-center justify-center rounded-xl border border-teal-200 bg-teal-50 px-5 text-sm font-bold text-teal-800 hover:border-teal-300 sm:ml-3" href="/citizen/doctors/search">
              Find a verified doctor
            </Link>
            <Link className="ml-0 mt-3 inline-flex min-h-11 items-center justify-center rounded-xl border border-sky-200 bg-sky-50 px-5 text-sm font-bold text-sky-800 hover:border-sky-300 sm:ml-3" href="/citizen/appointments">
              Appointments &amp; prescriptions
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export function CitizenDashboard({
  loadAction = loadCitizenDashboard,
}: {
  loadAction?: () => Promise<CitizenDashboardData>;
}) {
  const auth = usePortalAuth("CITIZEN");
  const authStatus = auth.status;
  const refreshCitizenSession = auth.refreshSession;
  const [refreshOutcome, setRefreshOutcome] = useState<
    "pending" | "succeeded" | "failed"
  >("pending");
  const [manualLogout, setManualLogout] = useState(false);

  useEffect(() => {
    if (authStatus === "authenticated" || manualLogout) {
      return;
    }

    let active = true;
    void refreshCitizenSession()
      .then(() => {
        if (active) setRefreshOutcome("succeeded");
      })
      .catch(() => {
        if (active) setRefreshOutcome("failed");
      });

    return () => {
      active = false;
    };
  }, [authStatus, manualLogout, refreshCitizenSession]);

  if (auth.status === "unauthenticated") {
    if (!manualLogout && refreshOutcome !== "failed") {
      return (
        <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
          <LoadingState
            description="Securely checking whether your Citizen session is still active."
            label="Checking your Citizen session"
          />
        </main>
      );
    }

    return <SignedOut />;
  }

  if (!auth.isRequiredPortal) {
    return <PortalMismatch />;
  }

  return (
    <DashboardContent
      key={auth.claims?.sub ?? "citizen"}
      loadAction={loadAction}
      onLogoutStarted={() => setManualLogout(true)}
    />
  );
}
