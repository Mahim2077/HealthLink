"use client";

// Phase 11 chamber queue: shows current/waiting/finished serials and
// the seven chamber actions. Rendered behind the verified-doctor
// portal guard. Data plane is injected via `chamberDeps` so unit tests
// can mock fetch without touching the real apiClient.

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import {
  describeQueueStatus,
  describeSessionStatus,
  type ChamberAppointmentView,
  type ChamberQueueActionResponse,
  type ChamberSessionFinishResponse,
  type ChamberSessionStartRequest,
  type ChamberSessionView,
  type QueueStatus,
} from "@/lib/chamber/types";

export type ChamberDeps = {
  loadSession: (
    facility_id: string,
    session_date: string | null,
  ) => Promise<ChamberSessionView | null>;
  startSession: (
    payload: ChamberSessionStartRequest,
  ) => Promise<ChamberSessionView>;
  finishSession: (
    facility_id: string,
    session_date: string | null,
  ) => Promise<ChamberSessionFinishResponse>;
  callNext: (
    facility_id: string,
    session_date: string | null,
  ) => Promise<ChamberQueueActionResponse>;
  actOnCurrent: (
    queue_id: string,
    action: "complete" | "skip" | "no-show",
  ) => Promise<ChamberQueueActionResponse>;
  removeEntry: (queue_id: string) => Promise<ChamberQueueActionResponse>;
};

type SessionState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; session: ChamberSessionView | null };

type ActionKey =
  | "start"
  | "call-next"
  | "complete"
  | "skip"
  | "no-show"
  | "remove"
  | "finish";

function todayISO(): string {
  // The doctor portal uses local-date for the session date, but the
  // backend accepts an ISO-8601 date string. We use UTC date to keep
  // the test deterministic across time zones.
  return new Date().toISOString().slice(0, 10);
}

function badgeClass(status: QueueStatus): string {
  switch (status) {
    case "CURRENT":
      return "bg-emerald-50 text-emerald-700";
    case "WAITING":
      return "bg-amber-50 text-amber-800";
    case "COMPLETED":
      return "bg-sky-50 text-sky-700";
    case "SKIPPED":
      return "bg-orange-50 text-orange-700";
    case "NO_SHOW":
      return "bg-rose-50 text-rose-700";
    case "REMOVED":
      return "bg-slate-100 text-slate-600";
  }
}

export function ChamberQueue({
  facility_id,
  chamberDeps,
}: {
  facility_id: string;
  chamberDeps: ChamberDeps;
}) {
  const sessionDate = todayISO();
  const [state, setState] = useState<SessionState>({ kind: "idle" });
  const [pending, setPending] = useState<ActionKey | null>(null);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const view = await chamberDeps.loadSession(facility_id, sessionDate);
      setState({ kind: "ready", session: view });
    } catch (reason) {
      setState({
        kind: "error",
        message: reason instanceof Error ? reason.message : "Unable to load chamber",
      });
    }
  }, [chamberDeps, facility_id, sessionDate]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh, version]);

  const runAction = useCallback(
    async (
      key: ActionKey,
      body: () => Promise<ChamberQueueActionResponse | unknown>,
      merge?: (response: ChamberQueueActionResponse) => void,
    ): Promise<void> => {
      setPending(key);
      setError(null);
      try {
        const response = (await body()) as ChamberQueueActionResponse | unknown;
        if (
          merge &&
          response &&
          typeof response === "object" &&
          "queue_id" in response
        ) {
          merge(response as ChamberQueueActionResponse);
        }
      } catch (reason) {
        setError(
          reason instanceof Error ? reason.message : "Action failed",
        );
      } finally {
        setPending(null);
      }
    },
    [],
  );

  // Apply a queue-action response to local session state without
  // triggering a full reload: this keeps the UI snappy and avoids a
  // loading flash between rapid successive actions in the chamber.
  const applyQueueAction = useCallback(
    (response: ChamberQueueActionResponse) => {
      setState((prev) => {
        if (prev.kind !== "ready" || !prev.session) return prev;
        const acted: ChamberAppointmentView = {
          appointment_id: response.appointment_id,
          became_current_at: response.became_current_at,
          booked_at:
            prev.session.waiting.find((row) => row.queue_id === response.queue_id)?.booked_at ??
            (prev.session.current?.queue_id === response.queue_id
              ? prev.session.current.booked_at
              : prev.session.finished.find((row) => row.queue_id === response.queue_id)?.booked_at ??
                ""),
          finished_at: response.finished_at,
          queue_id: response.queue_id,
          queue_status: response.queue_status,
          reason: null,
          removed_at: response.removed_at,
          serial_number: response.serial_number,
          status: response.appointment_status,
        };
        const nextCurrent = response.next_current;
        const waiting = prev.session.waiting.filter(
          (row) => row.queue_id !== response.queue_id,
        );
        const finished =
          response.queue_status === "COMPLETED" ||
          response.queue_status === "NO_SHOW" ||
          response.queue_status === "SKIPPED" ||
          response.queue_status === "REMOVED"
            ? [...prev.session.finished.filter((row) => row.queue_id !== response.queue_id), acted]
            : prev.session.finished.filter((row) => row.queue_id !== response.queue_id);
        return {
          kind: "ready",
          session: {
            ...prev.session,
            current: nextCurrent,
            finished,
            waiting,
          },
        };
      });
    },
    [],
  );

  const onStart = () =>
    runAction(
      "start",
      () =>
        chamberDeps.startSession({
          facility_id,
          session_date: sessionDate,
        }) as Promise<ChamberSessionView>,
      (response) => {
        setState({
          kind: "ready",
          session: response as unknown as ChamberSessionView,
        });
      },
    );

  const onFinish = () =>
    runAction("finish", () =>
      chamberDeps.finishSession(facility_id, sessionDate),
    );

  const onCallNext = () =>
    runAction(
      "call-next",
      () => chamberDeps.callNext(facility_id, sessionDate),
      applyQueueAction,
    );

  const onComplete = (queue_id: string) =>
    runAction(
      "complete",
      () => chamberDeps.actOnCurrent(queue_id, "complete"),
      applyQueueAction,
    );

  const onSkip = (queue_id: string) =>
    runAction(
      "skip",
      () => chamberDeps.actOnCurrent(queue_id, "skip"),
      applyQueueAction,
    );

  const onNoShow = (queue_id: string) =>
    runAction(
      "no-show",
      () => chamberDeps.actOnCurrent(queue_id, "no-show"),
      applyQueueAction,
    );

  const onRemove = (queue_id: string) =>
    runAction(
      "remove",
      () => chamberDeps.removeEntry(queue_id),
      applyQueueAction,
    );

  const current = state.kind === "ready" ? state.session?.current ?? null : null;
  const sessionStatus =
    state.kind === "ready" && state.session
      ? state.session.status
      : null;
  const isFinished = sessionStatus === "FINISHED";
  const isOpen = sessionStatus === "OPEN";

  const rows = useMemo(() => {
    if (state.kind !== "ready" || !state.session) return null;
    return state.session;
  }, [state]);

  if (state.kind === "loading" || state.kind === "idle") {
    return (
      <LoadingState
        label="Loading chamber"
        description="Fetching today's chamber session and queue."
      />
    );
  }

  if (state.kind === "error") {
    return (
      <ErrorState
        title="Chamber unavailable"
        message={state.message}
        onAction={() => setVersion((value) => value + 1)}
      />
    );
  }

  if (!rows) {
    return (
      <EmptyState
        title="No chamber session today"
        message="Open today's chamber to start calling patients."
        action={
          <button
            type="button"
            onClick={onStart}
            disabled={pending !== null}
            className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-5 text-sm font-bold text-white disabled:opacity-60"
          >
            {pending === "start" ? "Starting…" : "Open today's chamber"}
          </button>
        }
      />
    );
  }

  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
            Chamber · {rows.facility_name}
          </p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">
            {rows.session_date} · {describeSessionStatus(rows.status)}
          </h2>
          {rows.started_at ? (
            <p className="mt-1 text-sm text-slate-600">
              Started {new Date(rows.started_at).toLocaleTimeString()}
              {rows.ended_at
                ? ` · Closed ${new Date(rows.ended_at).toLocaleTimeString()}`
                : ""}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {isOpen ? (
            <>
              <button
                type="button"
                onClick={onCallNext}
                disabled={pending !== null || (rows.waiting.length === 0 && !current)}
                className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-4 text-sm font-bold text-white disabled:opacity-60"
              >
                {pending === "call-next" ? "Calling…" : "Call next patient"}
              </button>
              <button
                type="button"
                onClick={onFinish}
                disabled={pending !== null}
                className="inline-flex min-h-11 items-center rounded-xl border border-rose-300 bg-white px-4 text-sm font-bold text-rose-700 disabled:opacity-60"
              >
                {pending === "finish" ? "Closing…" : "Close chamber"}
              </button>
            </>
          ) : null}
          {!rows.id && !isFinished ? (
            <button
              type="button"
              onClick={onStart}
              disabled={pending !== null}
              className="inline-flex min-h-11 items-center rounded-xl bg-sky-700 px-4 text-sm font-bold text-white disabled:opacity-60"
            >
              {pending === "start" ? "Starting…" : "Open today's chamber"}
            </button>
          ) : null}
        </div>
      </header>

      {error ? (
        <p
          role="alert"
          className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"
        >
          {error}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <CurrentColumn
          current={current}
          isFinished={isFinished}
          isOpen={isOpen}
          pending={pending}
          onComplete={onComplete}
          onSkip={onSkip}
          onNoShow={onNoShow}
          onRemove={onRemove}
        />
        <QueueList
          title="Waiting"
          emptyLabel="No patients waiting."
          rows={rows.waiting}
          onRemove={onRemove}
          pending={pending}
          actionLabel="Remove"
          actionKey="remove"
        />
        <QueueList
          title="Finished today"
          emptyLabel="No patients finished yet."
          rows={rows.finished}
          onRemove={onRemove}
          pending={pending}
          readOnly
        />
      </div>
    </section>
  );
}

function CurrentColumn({
  current,
  isFinished,
  isOpen,
  pending,
  onComplete,
  onSkip,
  onNoShow,
  onRemove,
}: {
  current: ChamberAppointmentView | null;
  isFinished: boolean;
  isOpen: boolean;
  pending: ActionKey | null;
  onComplete: (id: string) => Promise<void>;
  onSkip: (id: string) => Promise<void>;
  onNoShow: (id: string) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
        With doctor
      </p>
      {current ? (
        <div className="mt-3">
          <p className="text-2xl font-bold text-slate-950">
            Serial #{current.serial_number}
          </p>
          <span
            className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-bold ${badgeClass(current.queue_status)}`}
          >
            {describeQueueStatus(current.queue_status)}
          </span>
          {current.reason ? (
            <p className="mt-3 text-sm text-slate-700">{current.reason}</p>
          ) : null}
          {isOpen ? (
            <div className="mt-5 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => onComplete(current.queue_id)}
                disabled={pending !== null}
                className="min-h-11 rounded-xl bg-emerald-600 px-3 text-sm font-bold text-white disabled:opacity-60"
              >
                {pending === "complete" ? "…" : "Complete"}
              </button>
              <button
                type="button"
                onClick={() => onSkip(current.queue_id)}
                disabled={pending !== null}
                className="min-h-11 rounded-xl border border-amber-300 bg-white px-3 text-sm font-bold text-amber-800 disabled:opacity-60"
              >
                {pending === "skip" ? "…" : "Skip"}
              </button>
              <button
                type="button"
                onClick={() => onNoShow(current.queue_id)}
                disabled={pending !== null}
                className="min-h-11 rounded-xl border border-rose-300 bg-white px-3 text-sm font-bold text-rose-700 disabled:opacity-60"
              >
                {pending === "no-show" ? "…" : "No-show"}
              </button>
              <button
                type="button"
                onClick={() => onRemove(current.queue_id)}
                disabled={pending !== null}
                className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold text-slate-700 disabled:opacity-60"
              >
                {pending === "remove" ? "…" : "Remove"}
              </button>
            </div>
          ) : null}
          <Link
            href="/professional/visits"
            className="mt-4 inline-flex min-h-11 items-center text-sm font-bold text-sky-700 underline-offset-4 hover:underline"
          >
            Open consultation
          </Link>
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          {isFinished
            ? "Chamber closed."
            : "Call the next patient to begin a consultation."}
        </p>
      )}
    </div>
  );
}

function QueueList({
  title,
  emptyLabel,
  rows,
  onRemove,
  pending,
  actionLabel,
  actionKey,
  readOnly = false,
}: {
  title: string;
  emptyLabel: string;
  rows: ChamberAppointmentView[];
  onRemove: (id: string) => Promise<void>;
  pending: ActionKey | null;
  actionLabel?: string;
  actionKey?: ActionKey;
  readOnly?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
        {title}
      </p>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">{emptyLabel}</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {rows.map((row) => (
            <li
              key={row.queue_id}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="text-sm font-bold text-slate-950">
                  Serial #{row.serial_number}
                </p>
                <span
                  className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-bold ${badgeClass(row.queue_status)}`}
                >
                  {describeQueueStatus(row.queue_status)}
                </span>
              </div>
              {!readOnly && actionLabel && actionKey ? (
                <button
                  type="button"
                  onClick={() => onRemove(row.queue_id)}
                  disabled={pending !== null}
                  className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs font-bold text-slate-700 disabled:opacity-60"
                >
                  {pending === actionKey ? "…" : actionLabel}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}