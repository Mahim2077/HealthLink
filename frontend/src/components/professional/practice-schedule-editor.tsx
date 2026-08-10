"use client";

// Doctor self-management editor for weekly practice windows. Renders only when
// the active professional role is a verified DOCTOR. Editing happens through
// the /professionals/me/practice-schedule endpoints and the eligible-facilities
// list. The component is intentionally framework-agnostic about the outer
// portal: it accepts an `loadSchedule`/`saveSchedule`/`removeSchedule`/`loadFacilities`
// seam so the unit tests can mock the data plane.

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import {
  createPracticeSchedule,
  deletePracticeSchedule,
  loadEligibleFacilities,
  loadPracticeSchedule,
  updatePracticeSchedule,
} from "@/lib/doctors/api";
import {
  PRACTICE_WEEKDAYS,
  type FacilityChoice,
  type PracticeScheduleEntry,
  type PracticeScheduleStatus,
  type PracticeWeekday,
} from "@/lib/doctors/types";

export type ScheduleEditorDeps = {
  loadSchedule: () => Promise<PracticeScheduleEntry[]>;
  loadFacilities: () => Promise<FacilityChoice[]>;
  createRow: (payload: {
    facility_id: string;
    weekday: PracticeWeekday;
    start_time: string;
    end_time: string;
    max_patients: number;
    status: PracticeScheduleStatus;
  }) => Promise<unknown>;
  updateRow: (
    scheduleId: string,
    payload: {
      facility_id: string;
      weekday: PracticeWeekday;
      start_time: string;
      end_time: string;
      max_patients: number;
      status: PracticeScheduleStatus;
    },
  ) => Promise<unknown>;
  deleteRow: (scheduleId: string) => Promise<unknown>;
};

const DEFAULT_DEPS: ScheduleEditorDeps = {
  createRow: createPracticeSchedule,
  deleteRow: deletePracticeSchedule,
  loadFacilities: loadEligibleFacilities,
  loadSchedule: loadPracticeSchedule,
  updateRow: updatePracticeSchedule,
};

type FormState = {
  facility_id: string;
  weekday: PracticeWeekday;
  start_time: string;
  end_time: string;
  max_patients: string;
  status: PracticeScheduleStatus;
};

const EMPTY_FORM: FormState = {
  end_time: "",
  facility_id: "",
  max_patients: "20",
  start_time: "",
  status: "ACTIVE",
  weekday: "MONDAY",
};

type FormErrors = Partial<Record<keyof FormState, string>>;

function validate(form: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!form.facility_id) {
    errors.facility_id = "Pick a facility for this window.";
  }
  if (!form.start_time) {
    errors.start_time = "Start time is required.";
  }
  if (!form.end_time) {
    errors.end_time = "End time is required.";
  } else if (
    form.start_time &&
    form.end_time &&
    form.end_time <= form.start_time
  ) {
    errors.end_time = "End time must be after start time.";
  }
  const capacity = Number(form.max_patients);
  if (!Number.isFinite(capacity) || capacity < 1) {
    errors.max_patients = "Capacity must be at least 1 patient.";
  } else if (capacity > 200) {
    errors.max_patients = "Capacity must be at most 200 patients.";
  }
  return errors;
}

function formatWeekday(value: PracticeWeekday): string {
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function statusBadge(status: PracticeScheduleStatus): string {
  return status === "ACTIVE"
    ? "bg-emerald-50 text-emerald-700"
    : "bg-slate-100 text-slate-700";
}

export function PracticeScheduleEditor({ deps }: { deps?: Partial<ScheduleEditorDeps> }) {
  const services = useMemo<ScheduleEditorDeps>(
    () => ({ ...DEFAULT_DEPS, ...(deps ?? {}) }),
    [deps],
  );

  const [entries, setEntries] = useState<PracticeScheduleEntry[]>([]);
  const [facilities, setFacilities] = useState<FacilityChoice[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [schedule, choices] = await Promise.all([
        services.loadSchedule(),
        services.loadFacilities(),
      ]);
      setEntries(schedule);
      setFacilities(choices);
      if (!form.facility_id && choices.length > 0) {
        const verifiedFirst =
          choices.find((choice) => choice.is_verified_assignment) ?? choices[0];
        setForm((current) => ({ ...current, facility_id: verifiedFirst.id }));
      }
    } catch (reason) {
      setLoadError(
        reason instanceof Error
          ? reason.message
          : "We could not load your practice schedule.",
      );
    } finally {
      setLoading(false);
    }
    // form.facility_id intentionally excluded: refresh should not auto-pick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [services]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  const beginEdit = useCallback((entry: PracticeScheduleEntry) => {
    setEditingId(entry.id);
    setSubmitError(null);
    setErrors({});
    setForm({
      end_time: entry.end_time,
      facility_id: entry.facility_id,
      max_patients: String(entry.max_patients),
      start_time: entry.start_time,
      status: entry.status,
      weekday: entry.weekday,
    });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setErrors({});
    setSubmitError(null);
  }, []);

  const handleChange = useCallback(
    <K extends keyof FormState>(key: K, value: FormState[K]) => {
      setForm((current) => ({ ...current, [key]: value }));
    },
    [],
  );

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const validation = validate(form);
      setErrors(validation);
      if (Object.keys(validation).length > 0) {
        return;
      }
      setSubmitting(true);
      setSubmitError(null);
      try {
        const payload = {
          end_time: form.end_time,
          facility_id: form.facility_id,
          max_patients: Number(form.max_patients),
          start_time: form.start_time,
          status: form.status,
          weekday: form.weekday,
        };
        if (editingId) {
          await services.updateRow(editingId, payload);
        } else {
          await services.createRow(payload);
        }
        cancelEdit();
        await refresh();
      } catch (reason) {
        setSubmitError(
          reason instanceof Error
            ? reason.message
            : "We could not save your practice schedule.",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [cancelEdit, editingId, form, refresh, services],
  );

  const handleDelete = useCallback(
    async (entry: PracticeScheduleEntry) => {
      setSubmitError(null);
      try {
        await services.deleteRow(entry.id);
        if (editingId === entry.id) {
          cancelEdit();
        }
        await refresh();
      } catch (reason) {
        setSubmitError(
          reason instanceof Error
            ? reason.message
            : "We could not remove that schedule row.",
        );
      }
    },
    [cancelEdit, editingId, refresh, services],
  );

  if (loading) {
    return (
      <LoadingState
        description="Loading your weekly practice windows."
        label="Practice schedule"
      />
    );
  }
  if (loadError) {
    return (
      <ErrorState
        message={loadError}
        onAction={() => void refresh()}
        title="Practice schedule unavailable"
      />
    );
  }

  const verifiedFirst = [...facilities].sort((left, right) => {
    if (left.is_verified_assignment === right.is_verified_assignment) {
      return left.name.localeCompare(right.name);
    }
    return left.is_verified_assignment ? -1 : 1;
  });

  return (
    <section className="space-y-8">
      <header className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <p className="text-xs font-bold uppercase tracking-[0.15em] text-sky-700">
          Verified doctor · practice windows
        </p>
        <h2 className="mt-3 text-2xl font-bold text-slate-950">
          Publish the hours you keep for patients
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Each row is one weekly window at one facility. Citizens searching the
          portal see the <span className="font-semibold">ACTIVE</span> rows in
          the order you list them here. Overlapping windows on the same weekday
          and facility are rejected by the server.
        </p>
      </header>

      {entries.length === 0 ? (
        <EmptyState
          message="Add the first weekly window to start publishing availability."
          title="No practice windows yet"
        />
      ) : (
        <ul className="space-y-3">
          {entries.map((entry) => (
            <li
              className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between"
              key={entry.id}
            >
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">
                  {formatWeekday(entry.weekday)}
                </p>
                <p className="mt-1 text-base font-semibold text-slate-950">
                  {entry.facility_name}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {entry.start_time} – {entry.end_time} · capacity{" "}
                  {entry.max_patients}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-3 py-1.5 text-xs font-bold ${statusBadge(entry.status)}`}
                >
                  {entry.status}
                </span>
                <button
                  className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-bold text-slate-700 transition hover:border-slate-400"
                  onClick={() => beginEdit(entry)}
                  type="button"
                >
                  Edit
                </button>
                <button
                  className="min-h-11 rounded-xl border border-rose-200 bg-white px-4 text-sm font-bold text-rose-700 transition hover:bg-rose-50"
                  onClick={() => void handleDelete(entry)}
                  type="button"
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form
        className="rounded-[1.75rem] border border-sky-200 bg-sky-50/40 p-6 shadow-sm sm:p-8"
        onSubmit={handleSubmit}
      >
        <h3 className="text-lg font-bold text-slate-950">
          {editingId ? "Edit weekly window" : "Add weekly window"}
        </h3>
        <p className="mt-1 text-sm text-slate-600">
          Times use 24-hour <code className="rounded bg-white px-1 py-0.5">HH:MM</code> format.
        </p>

        {submitError ? (
          <p
            className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"
            role="alert"
          >
            {submitError}
          </p>
        ) : null}

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Field label="Facility">
            <select
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              onChange={(event) => handleChange("facility_id", event.target.value)}
              value={form.facility_id}
            >
              <option value="">Select a facility…</option>
              {verifiedFirst.map((facility) => (
                <option key={facility.id} value={facility.id}>
                  {facility.name} ({facility.facility_type})
                  {facility.is_verified_assignment ? " · verified" : ""}
                </option>
              ))}
            </select>
            {errors.facility_id ? (
              <p className="mt-1 text-xs text-rose-700">{errors.facility_id}</p>
            ) : null}
          </Field>

          <Field label="Weekday">
            <select
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              onChange={(event) =>
                handleChange("weekday", event.target.value as PracticeWeekday)
              }
              value={form.weekday}
            >
              {PRACTICE_WEEKDAYS.map((day) => (
                <option key={day} value={day}>
                  {formatWeekday(day)}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Start time">
            <input
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              onChange={(event) => handleChange("start_time", event.target.value)}
              type="time"
              value={form.start_time}
            />
            {errors.start_time ? (
              <p className="mt-1 text-xs text-rose-700">{errors.start_time}</p>
            ) : null}
          </Field>

          <Field label="End time">
            <input
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              onChange={(event) => handleChange("end_time", event.target.value)}
              type="time"
              value={form.end_time}
            />
            {errors.end_time ? (
              <p className="mt-1 text-xs text-rose-700">{errors.end_time}</p>
            ) : null}
          </Field>

          <Field label="Max patients">
            <input
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              inputMode="numeric"
              min={1}
              onChange={(event) =>
                handleChange("max_patients", event.target.value)
              }
              type="number"
              value={form.max_patients}
            />
            {errors.max_patients ? (
              <p className="mt-1 text-xs text-rose-700">
                {errors.max_patients}
              </p>
            ) : null}
          </Field>

          <Field label="Status">
            <select
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              onChange={(event) =>
                handleChange(
                  "status",
                  event.target.value as PracticeScheduleStatus,
                )
              }
              value={form.status}
            >
              <option value="ACTIVE">ACTIVE — visible to citizens</option>
              <option value="INACTIVE">INACTIVE — paused</option>
            </select>
          </Field>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            className="min-h-11 rounded-xl bg-sky-700 px-5 text-sm font-bold text-white shadow-sm transition hover:bg-sky-800 disabled:opacity-60"
            disabled={submitting}
            type="submit"
          >
            {submitting
              ? editingId
                ? "Saving…"
                : "Publishing…"
              : editingId
                ? "Save changes"
                : "Publish window"}
          </button>
          {editingId ? (
            <button
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-5 text-sm font-bold text-slate-700"
              disabled={submitting}
              onClick={cancelEdit}
              type="button"
            >
              Cancel edit
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}

function Field({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.15em] text-slate-600">
        {label}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}