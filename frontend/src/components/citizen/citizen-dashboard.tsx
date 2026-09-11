"use client";

import {
  ArrowRightIcon,
  CalendarDaysIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { useEffect, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadCitizenDashboard } from "@/lib/citizen/api";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import type { CitizenDashboardData } from "@/lib/citizen/types";

type DashboardRequestState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CitizenDashboardData };

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
}: {
  loadAction: () => Promise<CitizenDashboardData>;
}) {
  const [requestVersion, setRequestVersion] = useState(0);
  const [requestState, setRequestState] = useState<DashboardRequestState>({
    status: "loading",
  });

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

  if (requestState.status === "loading") {
    return (
      <main className="flex flex-1 items-center px-5 py-12 sm:px-8" id="main-content">
        <LoadingState
          description="Securely loading your care overview."
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

  const { profile } = requestState.data;

  return (
    <main className="hl-page" id="main-content">
      <header className="max-w-3xl">
        <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-[-0.055em] text-slate-950 sm:text-5xl">
          Welcome, {profile.first_name}.
        </h1>
        <p className="mt-3 text-lg leading-7 text-indigo-800/80 sm:text-xl">
          Your health information, when you need it.
        </p>
      </header>

      <section className="mt-8 overflow-hidden rounded-2xl border border-teal-200/80 bg-teal-50/75">
        <div className="flex flex-col gap-6 p-6 sm:p-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-start gap-5">
            <span className="flex size-16 shrink-0 items-center justify-center rounded-full bg-white text-teal-700 shadow-sm ring-1 ring-inset ring-teal-100 sm:size-24">
              <MagnifyingGlassIcon aria-hidden="true" className="size-8 stroke-[1.8] sm:size-11" />
            </span>
            <div>
              <h2 className="text-2xl font-bold tracking-[-0.035em] text-slate-950 sm:text-3xl">
                Find a verified doctor
              </h2>
              <p className="mt-2 max-w-md text-base leading-6 text-indigo-800/80 sm:text-lg">
                Search for doctors and healthcare providers in your area.
              </p>
            </div>
          </div>
          <Link
            className="inline-flex min-h-14 shrink-0 items-center justify-center gap-3 rounded-xl bg-[#00695f] px-7 text-sm font-bold text-white shadow-sm transition hover:bg-[#005a52] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
            href="/citizen/doctors/search"
          >
            Find a verified doctor
            <ArrowRightIcon aria-hidden="true" className="size-5" />
          </Link>
        </div>
      </section>

      <section className="mt-10" aria-labelledby="care-links-title">
        <h2
          className="text-2xl font-bold tracking-[-0.04em] text-slate-950 sm:text-3xl"
          id="care-links-title"
        >
          Appointments &amp; prescriptions
        </h2>
        <Link
          className="group mt-5 flex min-h-24 items-center gap-4 border-b border-slate-200 py-4 transition hover:border-teal-300"
          href="/citizen/appointments"
        >
          <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-800 ring-1 ring-inset ring-teal-100">
            <CalendarDaysIcon aria-hidden="true" className="size-6" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-lg font-semibold text-slate-950">Appointments</span>
            <span className="mt-1 block text-sm text-indigo-800/80">
              View and manage your appointments and prescriptions
            </span>
          </span>
          <ArrowRightIcon
            aria-hidden="true"
            className="size-5 shrink-0 text-indigo-800 transition group-hover:translate-x-1"
          />
        </Link>
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

  useEffect(() => {
    if (authStatus === "authenticated") return;
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
  }, [authStatus, refreshCitizenSession]);

  if (auth.status === "unauthenticated") {
    if (refreshOutcome !== "failed") {
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

  if (!auth.isRequiredPortal) return <PortalMismatch />;

  return (
    <DashboardContent
      key={auth.claims?.sub ?? "citizen"}
      loadAction={loadAction}
    />
  );
}
