"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { PrescriptionPanel } from "@/components/prescriptions/prescription-panel";
import { EmptyState, LoadingState } from "@/components/ui/async-state";
import type { Portal } from "@/lib/auth/types";

export function PrescriptionPage({
  prescriptionId,
  portal,
}: {
  prescriptionId: string;
  portal: Extract<Portal, "CITIZEN" | "PROFESSIONAL">;
}) {
  const auth = usePortalAuth(portal);
  const status = auth.status;
  const refreshSession = auth.refreshSession;
  const [hydrationFailed, setHydrationFailed] = useState(false);

  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => {
      if (active) setHydrationFailed(true);
    });
    return () => {
      active = false;
    };
  }, [refreshSession, status]);

  if (status === "unauthenticated" && !hydrationFailed) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState
          description={`Checking for an active ${portal.toLowerCase()} session.`}
          label="Checking prescription access"
        />
      </main>
    );
  }
  if (status === "unauthenticated") {
    const loginPath =
      portal === "CITIZEN" ? "/citizen/login" : "/professional/login";
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          action={
            <Link
              className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white"
              href={loginPath}
            >
              Sign in
            </Link>
          }
          message="Sign in through the correct portal to view this private medical document."
          title="Sign in required"
        />
      </main>
    );
  }
  if (!auth.isRequiredPortal) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          message="This session belongs to another HealthLink portal."
          title={`${portal === "CITIZEN" ? "Citizen" : "Professional"} Portal access required`}
        />
      </main>
    );
  }

  const backPath =
    portal === "CITIZEN"
      ? "/citizen/appointments"
      : "/professional/visits";

  return (
    <main
      className="mx-auto w-full max-w-6xl flex-1 px-5 py-10 sm:px-8 lg:px-10"
      id="main-content"
    >
      <Link
        className="text-sm font-bold text-teal-700 hover:text-teal-900"
        href={backPath}
      >
        ← Back
      </Link>
      <div className="mt-6">
        <PrescriptionPanel
          editable={portal === "PROFESSIONAL"}
          prescriptionId={prescriptionId}
        />
      </div>
    </main>
  );
}
