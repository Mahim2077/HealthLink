"use client";

import { useEffect, useState } from "react";

import { ChamberQueue, type ChamberDeps } from "@/components/professional/chamber-queue";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import {
  actOnCurrentPatient,
  callNextPatient,
  finishChamberSession,
  loadChamberSession,
  loadChamberFacilities,
  removeQueueEntry,
  startChamberSession,
} from "@/lib/chamber/api";
import { loadProfessionalMe } from "@/lib/professional/api";
import type { ProfessionalMe } from "@/lib/professional/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import type { ChamberFacilityChoice } from "@/lib/chamber/types";

const defaultDeps: ChamberDeps = {
  actOnCurrent: actOnCurrentPatient,
  callNext: callNextPatient,
  finishSession: finishChamberSession,
  loadSession: loadChamberSession,
  removeEntry: removeQueueEntry,
  startSession: startChamberSession,
};

export default function ChamberPage() {
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
  const [facilities, setFacilities] = useState<ChamberFacilityChoice[]>([]);
  const [facilityId, setFacilityId] = useState("");

  useEffect(() => {
    let active = true;
    void loadProfessionalMe().then(
      async (value) => {
        const choices = value.role_code === "DOCTOR" && value.verification_status === "VERIFIED"
          ? await loadChamberFacilities() : [];
        if (active) {
          setRecord(value);
          setFacilities(choices);
          setFacilityId((selected) => choices.some((item) => item.id === selected) ? selected
            : choices.find((item) => item.id === value.facility?.id)?.id ?? choices[0]?.id ?? "");
          setError(null);
        }
      },
    ).catch(
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

  if (status === "unauthenticated" && !failed) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState
          label="Checking Professional session"
          description="Verifying the Professional Portal access."
        />
      </main>
    );
  }
  if (status === "unauthenticated") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          title="Professional sign in required"
          message="Sign in with your NID and selected role."
        />
      </main>
    );
  }
  if (!auth.isRequiredPortal) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          title="Professional Portal access required"
          message="This session belongs to another HealthLink portal."
        />
      </main>
    );
  }

  if (!record && !error) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState label="Loading chamber" description="Fetching the verified role." />
      </main>
    );
  }
  if (error) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <ErrorState
          title="Chamber unavailable"
          message={error}
          onAction={() => setVersion((value) => value + 1)}
        />
      </main>
    );
  }
  if (!record) return null;

  if (record.verification_status !== "VERIFIED") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          title={`${record.verification_status} role is restricted`}
          message="Chamber access begins only after this selected role is verified."
        />
      </main>
    );
  }
  if (record.role_code !== "DOCTOR") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          title="Doctor role required"
          message="Chamber operations are only available to verified doctors."
        />
      </main>
    );
  }
  if (!facilityId) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          title="No chamber facility available"
          message="Publish practice hours at an active facility or contact an administrator about your linked facility."
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
          Chamber · {record.role_name}
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          Today&rsquo;s chamber queue
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Manage serials at {facilities.find((item) => item.id === facilityId)?.name}.
        </p>
        {facilities.length > 1 && <label className="mt-5 block max-w-md text-sm font-semibold text-slate-700">
          Chamber facility
          <select className="mt-2 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-slate-900"
            onChange={(event) => setFacilityId(event.target.value)} value={facilityId}>
            {facilities.map((facility) => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
          </select>
        </label>}
      </header>
      <div className="mt-8">
        <ChamberQueue
          key={facilityId}
          facility_id={facilityId}
          chamberDeps={defaultDeps}
        />
      </div>
    </main>
  );
}
