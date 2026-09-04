"use client";

import { useEffect, useState } from "react";

import {
  ConsultationWorkspace,
  type VisitsDeps,
} from "@/components/professional/consultation-workspace";
import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/async-state";
import { finishAppointment } from "@/lib/appointments/api";
import {
  loadCurrentPatient,
  readDoctorVisit,
  startVisitForCurrent,
  updateDoctorVisit,
} from "@/lib/visits/api";
import { loadProfessionalMe } from "@/lib/professional/api";
import type { ProfessionalMe } from "@/lib/professional/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

const defaultDeps: VisitsDeps = {
  finishAppointment,
  loadCurrentPatient,
  readVisit: readDoctorVisit,
  startVisitForCurrent,
  updateVisit: updateDoctorVisit,
};

export default function VisitsPage() {
  const auth = usePortalAuth("PROFESSIONAL");
  const status = auth.status;
  const refreshSession = auth.refreshSession;
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => {
      if (active) setFailed(true);
    });
    return () => {
      active = false;
    };
  }, [refreshSession, status]);

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
          setError(
            citizenErrorMessage(
              reason,
              "We could not load this professional role.",
            ),
          );
        }
      },
    );
    return () => {
      active = false;
    };
  }, [version]);

  if (status === "unauthenticated" && !failed) {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <LoadingState
          label="Checking Professional session"
          description="Verifying the Professional Portal access."
        />
      </main>
    );
  }
  if (status === "unauthenticated") {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <EmptyState
          title="Professional sign in required"
          message="Sign in with your NID and selected role."
        />
      </main>
    );
  }
  if (!auth.isRequiredPortal) {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <EmptyState
          title="Professional Portal access required"
          message="This session belongs to another HealthLink portal."
        />
      </main>
    );
  }

  if (!record && !error) {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <LoadingState
          label="Loading consultation"
          description="Fetching the verified role."
        />
      </main>
    );
  }
  if (error) {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <ErrorState
          title="Consultation unavailable"
          message={error}
          onAction={() => setVersion((value) => value + 1)}
        />
      </main>
    );
  }
  if (!record) return null;

  if (record.verification_status !== "VERIFIED") {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <EmptyState
          title={`${record.verification_status} role is restricted`}
          message="Consultation access begins only after this selected role is verified."
        />
      </main>
    );
  }
  if (record.role_code !== "DOCTOR") {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <EmptyState
          title="Doctor role required"
          message="Consultations are only available to verified doctors."
        />
      </main>
    );
  }
  if (!record.facility) {
    return (
      <main
        className="flex flex-1 items-center px-5 py-12"
        id="main-content"
      >
        <EmptyState
          title="No facility linked"
          message="Contact an administrator to link a verified facility to this role."
        />
      </main>
    );
  }

  return (
    <main
      className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 lg:px-10"
      id="main-content"
    >
      <header className="border-b border-slate-200 pb-7">
        <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
          Visits &middot; {record.role_name}
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          Today&rsquo;s consultations
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Draft charts and prescriptions for current serials at {record.facility.name}.
        </p>
      </header>
      <div className="mt-8">
        <ConsultationWorkspace visitsDeps={defaultDeps} />
      </div>
    </main>
  );
}
