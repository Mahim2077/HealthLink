"use client";

// Phase 12 consultation workspace: shows the CURRENT chamber patient
// (when one exists) and the doctor`s draft visit form. Rendered behind
// the verified-doctor portal guard. Data plane is injected via
// `visitsDeps` so unit tests can mock fetch without touching the real
// apiClient.

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import {
  PrescriptionPanel,
  type PrescriptionDeps,
} from "@/components/prescriptions/prescription-panel";
import {
  badgeClassForVisit,
  describeVisitStatus,
  isFinalized,
  type DoctorCurrentPatientView,
  type VisitDraftUpdateRequest,
  type VisitDraftView,
} from "@/lib/visits/types";

export type VisitsDeps = {
  loadCurrentPatient: () => Promise<DoctorCurrentPatientView | null>;
  startVisitForCurrent: (queue_id: string) => Promise<VisitDraftView>;
  readVisit: (visit_id: string) => Promise<VisitDraftView>;
  updateVisit: (
    visit_id: string,
    payload: VisitDraftUpdateRequest,
  ) => Promise<VisitDraftView>;
};

type CurrentPatientState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; current: DoctorCurrentPatientView | null };

type ActionKey = "start" | "save";

export function ConsultationWorkspace({
  visitsDeps,
  prescriptionDeps,
}: {
  visitsDeps: VisitsDeps;
  prescriptionDeps?: PrescriptionDeps;
}) {
  const [state, setState] = useState<CurrentPatientState>({ kind: "idle" });
  const [pending, setPending] = useState<ActionKey | null>(null);
  const [version, setVersion] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const current = await visitsDeps.loadCurrentPatient();
      setState({ kind: "ready", current });
    } catch (reason) {
      setState({
        kind: "error",
        message:
          reason instanceof Error
            ? reason.message
            : "Unable to load consultation workspace",
      });
    }
  }, [visitsDeps]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh, version]);

  const current = state.kind === "ready" ? state.current : null;
  const visit = current?.visit ?? null;
  const finalized = isFinalized(visit);

  const onStart = useCallback(async () => {
    if (!current) return;
    setPending("start");
    setActionError(null);
    try {
      const next = await visitsDeps.startVisitForCurrent(current.queue_id);
      setState({
        kind: "ready",
        current: { ...current, visit: next },
      });
    } catch (reason) {
      setActionError(
        reason instanceof Error ? reason.message : "Unable to start visit",
      );
    } finally {
      setPending(null);
    }
  }, [current, visitsDeps]);

  const onSave = useCallback(
    async (payload: VisitDraftUpdateRequest) => {
      if (!visit) return;
      setPending("save");
      setActionError(null);
      try {
        const next = await visitsDeps.updateVisit(visit.id, payload);
        if (current) {
          setState({
            kind: "ready",
            current: { ...current, visit: next },
          });
        }
      } catch (reason) {
        setActionError(
          reason instanceof Error ? reason.message : "Unable to save draft",
        );
      } finally {
        setPending(null);
      }
    },
    [current, visit, visitsDeps],
  );

  const patientName = useMemo(() => {
    if (!current) return null;
    return current.patient.full_name;
  }, [current]);

  if (state.kind === "loading" || state.kind === "idle") {
    return (
      <LoadingState
        label="Loading consultation workspace"
        description="Fetching the current chamber patient."
      />
    );
  }
  if (state.kind === "error") {
    return (
      <ErrorState
        title="Consultation workspace unavailable"
        message={state.message}
        onAction={() => setVersion((value) => value + 1)}
      />
    );
  }
  if (!current) {
    return (
      <EmptyState
        title="No active patient"
        message="Call the next patient from the chamber queue to begin a consultation."
      />
    );
  }

  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
            Consultation � {current.facility_name}
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">
            Serial #{current.serial_number} � {patientName}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {visit
              ? `Visit started � ${describeVisitStatus(visit.status)}`
              : "No draft visit yet for this serial."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {visit ? (
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${badgeClassForVisit(visit.status)}`}
            >
              {describeVisitStatus(visit.status)}
            </span>
          ) : (
            <button
              type="button"
              onClick={onStart}
              disabled={pending !== null}
              className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white disabled:opacity-60"
            >
              {pending === "start" ? "Starting�" : "Open consultation"}
            </button>
          )}
        </div>
      </header>

      {actionError ? (
        <p
          role="alert"
          className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"
        >
          {actionError}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[260px,1fr]">
        <PatientPanel current={current} />
        <DraftForm
          visit={visit}
          finalized={finalized}
          pending={pending}
          onSave={onSave}
        />
      </div>
      {visit ? (
        <div className="mt-6">
          <PrescriptionPanel
            deps={prescriptionDeps}
            editable
            key={`${visit.id}-${visit.prescription_id ?? "new"}`}
            prescriptionId={visit.prescription_id}
            visitId={visit.id}
          />
        </div>
      ) : null}
    </section>
  );
}

function PatientPanel({
  current,
}: {
  current: DoctorCurrentPatientView;
}) {
  const dob = current.patient.date_of_birth;
  return (
    <aside className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
        Patient
      </p>
      <p className="mt-2 text-xl font-bold text-slate-950">
        {current.patient.full_name}
      </p>
      <dl className="mt-3 space-y-1 text-sm text-slate-700">
        <div className="flex justify-between">
          <dt className="font-semibold text-slate-600">Gender</dt>
          <dd>{current.patient.gender ?? "�"}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="font-semibold text-slate-600">Date of birth</dt>
          <dd>{dob ?? "�"}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="font-semibold text-slate-600">Age</dt>
          <dd>
            {current.patient.age_years !== null
              ? `${current.patient.age_years} yrs`
              : "�"}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="font-semibold text-slate-600">Blood group</dt>
          <dd>{current.patient.blood_group ?? "�"}</dd>
        </div>
      </dl>
    </aside>
  );
}

function DraftForm({
  visit,
  finalized,
  pending,
  onSave,
}: {
  visit: VisitDraftView | null;
  finalized: boolean;
  pending: ActionKey | null;
  onSave: (payload: VisitDraftUpdateRequest) => Promise<void>;
}) {
  const [chiefComplaint, setChiefComplaint] = useState<string>(
    visit?.chief_complaint ?? "",
  );
  const [clinicalNotes, setClinicalNotes] = useState<string>(
    visit?.clinical_notes ?? "",
  );
  const [diagnosis, setDiagnosis] = useState<string>(visit?.diagnosis ?? "");
  const [followUp, setFollowUp] = useState<string>(
    visit?.follow_up_instructions ?? "",
  );

  useEffect(() => {
    // The draft form mirrors the latest visit payload; re-syncing local
    // text fields whenever the upstream visit changes is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setChiefComplaint(visit?.chief_complaint ?? "");
    setClinicalNotes(visit?.clinical_notes ?? "");
    setDiagnosis(visit?.diagnosis ?? "");
    setFollowUp(visit?.follow_up_instructions ?? "");
  }, [visit?.id, visit?.chief_complaint, visit?.clinical_notes, visit?.diagnosis, visit?.follow_up_instructions]);

  if (!visit) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-5 text-sm text-slate-600">
        Start the consultation to begin recording clinical notes for this serial.
      </div>
    );
  }

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSave({
      chief_complaint: chiefComplaint,
      clinical_notes: clinicalNotes,
      diagnosis,
      follow_up_instructions: followUp,
    });
  };

  return (
    <form
      className="rounded-2xl border border-slate-200 bg-white p-5"
      onSubmit={onSubmit}
    >
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
        Clinical notes
      </p>
      <p className="mt-2 text-sm text-slate-600">
        {finalized
          ? "This visit is finalized; further edits are disabled."
          : "Save drafts often � Phase 14 finalises the visit on appointment close."}
      </p>

      <div className="mt-5 grid gap-4">
        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Chief complaint</span>
          <textarea
            value={chiefComplaint}
            disabled={finalized || pending !== null}
            onChange={(event) => setChiefComplaint(event.target.value)}
            rows={2}
            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
          />
        </label>
        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Clinical notes</span>
          <textarea
            value={clinicalNotes}
            disabled={finalized || pending !== null}
            onChange={(event) => setClinicalNotes(event.target.value)}
            rows={4}
            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
          />
        </label>
        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Diagnosis</span>
          <textarea
            value={diagnosis}
            disabled={finalized || pending !== null}
            onChange={(event) => setDiagnosis(event.target.value)}
            rows={2}
            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
          />
        </label>
        <label className="block text-sm">
          <span className="font-semibold text-slate-700">
            Follow-up instructions
          </span>
          <textarea
            value={followUp}
            disabled={finalized || pending !== null}
            onChange={(event) => setFollowUp(event.target.value)}
            rows={2}
            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
          />
        </label>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={finalized || pending !== null}
          className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white disabled:opacity-60"
        >
          {pending === "save" ? "Saving�" : "Save draft"}
        </button>
      </div>
    </form>
  );
}
