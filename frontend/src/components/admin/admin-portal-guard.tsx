"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, LoadingState } from "@/components/ui/async-state";


export function AdminPortalGuard({ children }: { children: ReactNode }) {
  const auth = usePortalAuth("ADMIN");
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const authStatus = auth.status;
  const refreshSession = auth.refreshSession;

  useEffect(() => {
    if (authStatus === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => {
      if (active) setHydrationFailed(true);
    });
    return () => { active = false; };
  }, [authStatus, refreshSession]);

  if (auth.status === "unauthenticated" && !hydrationFailed) {
    return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><LoadingState description="Checking for a trusted Admin session." label="Checking Admin session" /></main>;
  }
  if (auth.status === "unauthenticated") {
    return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState action={<Link className="inline-flex min-h-11 items-center justify-center rounded-xl bg-indigo-700 px-5 text-sm font-bold text-white" href="/admin/login">Sign in to Admin Portal</Link>} message="A trusted administrator account is required." title="Admin sign in required" /></main>;
  }
  if (!auth.isRequiredPortal) {
    return <main className="flex flex-1 items-center px-5 py-12" id="main-content"><EmptyState message="This session belongs to another HealthLink portal." title="Admin Portal access required" /></main>;
  }
  return children;
}
