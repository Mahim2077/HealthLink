"use client";

import {
  ArrowRightIcon,
  BuildingOffice2Icon,
  IdentificationIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { useEffect, useState, type ComponentType, type SVGProps } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { loadAdminMe } from "@/lib/admin/api";
import type { AdminMe } from "@/lib/admin/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; admin: AdminMe };

type AdminAction = {
  description: string;
  href: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
};

const adminActions: AdminAction[] = [
  {
    description: "Review pending applications, supporting details, and verification decisions.",
    href: "/admin/professional-registrations",
    icon: ShieldCheckIcon,
    title: "Professional verification",
  },
  {
    description: "Create and maintain the trusted facility registry used by verified professionals.",
    href: "/admin/facilities",
    icon: BuildingOffice2Icon,
    title: "Healthcare facilities",
  },
  {
    description: "Search citizen records and complete controlled identity corrections with a reason.",
    href: "/admin/citizen-identities",
    icon: IdentificationIcon,
    title: "Citizen identity support",
  },
];

export function AdminDashboard({
  loadAction = loadAdminMe,
}: {
  loadAction?: () => Promise<AdminMe>;
}) {
  const auth = usePortalAuth("ADMIN");
  const authStatus = auth.status;
  const isAdminPortal = auth.isRequiredPortal;
  const refreshSession = auth.refreshSession;
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const [state, setState] = useState<State>({ status: "loading" });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (authStatus === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => {
      if (active) setHydrationFailed(true);
    });
    return () => {
      active = false;
    };
  }, [authStatus, refreshSession]);

  useEffect(() => {
    if (authStatus !== "authenticated" || !isAdminPortal) return;
    let active = true;
    void loadAction().then(
      (admin) => {
        if (active) setState({ admin, status: "ready" });
      },
      (reason: unknown) => {
        if (active) {
          setState({
            message: citizenErrorMessage(reason, "We could not load this admin account."),
            status: "error",
          });
        }
      },
    );
    return () => {
      active = false;
    };
  }, [authStatus, isAdminPortal, loadAction, version]);

  if (authStatus === "unauthenticated" && !hydrationFailed) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState description="Checking for a trusted Admin session." label="Checking Admin session" />
      </main>
    );
  }
  if (authStatus === "unauthenticated") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          action={
            <Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white" href="/admin/login">
              Sign in to Admin Portal
            </Link>
          }
          message="A trusted administrator account is required."
          title="Admin sign in required"
        />
      </main>
    );
  }
  if (!isAdminPortal) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState message="This session belongs to another HealthLink portal." title="Admin Portal access required" />
      </main>
    );
  }
  if (state.status === "loading") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState description="Loading your trusted operational account." label="Loading Admin Dashboard" />
      </main>
    );
  }
  if (state.status === "error") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <ErrorState
          message={state.message}
          onAction={() => {
            setState({ status: "loading" });
            setVersion((value) => value + 1);
          }}
          title="Admin Dashboard unavailable"
        />
      </main>
    );
  }

  const admin = state.admin;
  return (
    <main className="hl-page" id="main-content">
      <header className="max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-indigo-700">Trusted operations</p>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-[-0.055em] text-slate-950 sm:text-5xl">
          Welcome, {admin.first_name}.
        </h1>
        <p className="mt-3 text-lg leading-7 text-slate-600">
          Review the operational work that keeps HealthLink trustworthy.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3 text-sm">
          <span className="rounded-full bg-emerald-50 px-3 py-1.5 font-bold text-emerald-700 ring-1 ring-inset ring-emerald-100">
            Active
          </span>
          <span className="font-semibold text-slate-600">
            {admin.is_super_admin ? "Super administrator" : "Administrator"}
          </span>
        </div>
      </header>

      <section className="mt-10" aria-labelledby="admin-work-title">
        <h2 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 sm:text-3xl" id="admin-work-title">
          Administrative workspace
        </h2>
        <div className="mt-5 divide-y divide-slate-200 border-y border-slate-200">
          {adminActions.map(({ description, href, icon: Icon, title }) => (
            <Link
              className="group flex items-center gap-4 py-5 transition hover:bg-white/65 sm:px-2"
              href={href}
              key={href}
            >
              <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-100">
                <Icon aria-hidden="true" className="size-6" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-base font-semibold text-slate-950">{title}</span>
                <span className="mt-1 block max-w-3xl text-sm leading-6 text-slate-600">{description}</span>
              </span>
              <ArrowRightIcon aria-hidden="true" className="size-5 shrink-0 text-indigo-700 transition group-hover:translate-x-1" />
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
