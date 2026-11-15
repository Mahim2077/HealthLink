"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { ErrorState, LoadingState } from "@/components/ui/async-state";
import { ApiError } from "@/lib/api/errors";
import { safeReturnTo } from "@/lib/auth/return-to";
import { loadProfessionalMe } from "@/lib/professional/api";

export function PortalLoginGate({
  children,
  portal,
}: {
  children: ReactNode;
  portal: "CITIZEN" | "PROFESSIONAL";
}) {
  const router = useRouter();
  const { refreshSession } = usePortalAuth(portal);
  const [status, setStatus] = useState<"checking" | "signed-out" | "error">("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;

    async function resumeSession() {
      try {
        await refreshSession();
        if (!current) return;

        let destination = safeReturnTo(null, portal);
        if (portal === "CITIZEN") {
          const returnTo = new URLSearchParams(window.location.search).get("returnTo");
          destination = safeReturnTo(returnTo, portal);
        } else {
          const profile = await loadProfessionalMe();
          if (profile.verification_status !== "VERIFIED") destination = "/professional/status";
        }

        if (current) router.replace(destination);
      } catch (error) {
        if (current) setStatus(error instanceof ApiError && error.status === 401 ? "signed-out" : "error");
      }
    }

    void resumeSession();
    return () => { current = false; };
  }, [attempt, portal, refreshSession, router]);

  if (status === "signed-out") return children;

  return (
    <main className="flex flex-1 items-center" id="main-content">
      {status === "checking" ? (
        <LoadingState label="Checking your session" description="Opening your HealthLink portal." />
      ) : (
        <ErrorState
          title="Could not check your session"
          message="Please check your connection and try again."
          onAction={() => {
            setStatus("checking");
            setAttempt((previous) => previous + 1);
          }}
        />
      )}
    </main>
  );
}
