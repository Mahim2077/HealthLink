"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
} from "react";

import { CitizenShell } from "@/components/citizen/citizen-shell";
import { usePortalAuth } from "@/components/auth/auth-provider";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/async-state";
import { searchDoctors } from "@/lib/doctors/api";
import type {
  DoctorSearchFilters,
  DoctorSummary,
  PracticeWeekday,
} from "@/lib/doctors/types";
import { citizenErrorMessage } from "@/lib/citizen/presentation";

const WEEKDAY_OPTIONS: { value: PracticeWeekday; label: string }[] = [
  { value: "MONDAY", label: "Monday" },
  { value: "TUESDAY", label: "Tuesday" },
  { value: "WEDNESDAY", label: "Wednesday" },
  { value: "THURSDAY", label: "Thursday" },
  { value: "FRIDAY", label: "Friday" },
  { value: "SATURDAY", label: "Saturday" },
  { value: "SUNDAY", label: "Sunday" },
];

const WEEKDAY_LABEL: Record<PracticeWeekday, string> = WEEKDAY_OPTIONS.reduce(
  (accumulator, option) => {
    accumulator[option.value] = option.label;
    return accumulator;
  },
  {} as Record<PracticeWeekday, string>,
);

function DoctorRow({ doctor }: { doctor: DoctorSummary }) {
  return (
    <article
      className="rounded-[1.4rem] border border-slate-200 bg-white p-5 shadow-sm"
      data-testid="doctor-row"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-slate-950">{doctor.name}</h2>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                doctor.verified
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {doctor.verified ? "VERIFIED" : "UNVERIFIED"}
            </span>
            <span className="rounded-full bg-sky-50 px-2.5 py-1 text-xs font-bold text-sky-800">
              {doctor.role_code}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-600">{doctor.designation}</p>
          <p className="mt-1 text-sm text-slate-700">
            <span className="font-semibold">{doctor.facility_name}</span>
            <span className="ml-2 text-xs uppercase tracking-wide text-slate-500">
              {doctor.facility_type}
            </span>
          </p>
          {doctor.specialization ? (
            <p className="mt-2 text-sm text-slate-600">
              Specialization: {doctor.specialization}
            </p>
          ) : null}
        </div>
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white transition hover:bg-teal-800"
          href={`/citizen/doctors/${doctor.id}`}
        >
          View doctor
        </Link>
      </div>
    </article>
  );
}

function SearchForm({
  filters,
  onChange,
  onSubmit,
  onReset,
  formError,
  submitting,
}: {
  filters: DoctorSearchFilters;
  onChange: (filters: DoctorSearchFilters) => void;
  onSubmit: () => void;
  onReset: () => void;
  formError: string | null;
  submitting: boolean;
}) {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
      <label className="text-sm font-bold text-slate-700">
        Doctor name
        <input
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          disabled={submitting}
          maxLength={200}
          onChange={(event) =>
            onChange({ ...filters, name: event.target.value })
          }
          placeholder="Full or partial name"
          value={filters.name ?? ""}
        />
      </label>
      <label className="text-sm font-bold text-slate-700">
        Facility
        <input
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          disabled={submitting}
          maxLength={200}
          onChange={(event) =>
            onChange({ ...filters, facility_name: event.target.value })
          }
          placeholder="Facility name"
          value={filters.facility_name ?? ""}
        />
      </label>
      <label className="text-sm font-bold text-slate-700">
        Available on weekday
        <select
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
          disabled={submitting}
          onChange={(event) => {
            const value = event.target.value;
            onChange({
              ...filters,
              weekday: value ? (value as PracticeWeekday) : undefined,
            });
          }}
          value={filters.weekday ?? ""}
        >
          <option value="">Any weekday</option>
          {WEEKDAY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {formError ? (
        <p
          aria-live="polite"
          className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800"
          data-testid="search-form-error"
        >
          {formError}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <button
          className="min-h-11 rounded-xl bg-teal-700 px-5 text-sm font-bold text-white transition hover:bg-teal-800 disabled:cursor-wait disabled:opacity-60"
          data-testid="search-submit"
          disabled={submitting}
          type="submit"
        >
          {submitting ? "Searching…" : "Search doctors"}
        </button>
        <button
          className="min-h-11 rounded-xl border border-slate-300 px-5 text-sm font-bold text-slate-700 transition hover:border-slate-400"
          data-testid="search-reset"
          disabled={submitting}
          onClick={onReset}
          type="button"
        >
          Clear filters
        </button>
      </div>
    </form>
  );
}

function SearchContent({
  searchAction,
}: {
  searchAction: (filters: DoctorSearchFilters) => Promise<DoctorSummary[]>;
}) {
  const [filters, setFilters] = useState<DoctorSearchFilters>({});
  const [results, setResults] = useState<DoctorSummary[] | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [requestVersion, setRequestVersion] = useState(0);

  const runSearch = useCallback(
    async (activeFilters: DoctorSearchFilters) => {
      setSubmitting(true);
      try {
        const rows = await searchAction(activeFilters);
        setResults(rows);
        setError(null);
      } catch (reason) {
        setResults([]);
        setError(
          citizenErrorMessage(
            reason,
            "We could not search doctors right now. Please try again.",
          ),
        );
      } finally {
        setSubmitting(false);
      }
    },
    [searchAction],
  );

  useEffect(() => {
    if (requestVersion === 0) {
      return;
    }
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void runSearch(filters).then(() => {
      if (active) setSubmitted(true);
    });
    return () => {
      active = false;
    };
  }, [filters, requestVersion, runSearch]);

  const handleSubmit = () => {
    const trimmedName = filters.name?.trim() ?? "";
    const trimmedFacility = filters.facility_name?.trim() ?? "";
    const hasWeekday = Boolean(filters.weekday);
    if (!trimmedName && !trimmedFacility && !hasWeekday) {
      setFormError(
        "Provide at least one of doctor name, facility, or weekday.",
      );
      return;
    }
    setFormError(null);
    setSubmitted(true);
    setRequestVersion((value) => value + 1);
  };

  const handleReset = () => {
    setFilters({});
    setFormError(null);
    setError(null);
    setResults(null);
    setSubmitted(false);
  };

  return (
    <main
      className="mx-auto w-full max-w-7xl flex-1 px-5 py-10 sm:px-8 lg:px-10"
      id="main-content"
    >
      <div className="border-b border-slate-200 pb-7">
        <Link
          className="text-sm font-bold text-teal-700 hover:text-teal-900"
          href="/citizen/dashboard"
        >
          ← Citizen Dashboard
        </Link>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.15em] text-teal-700">
          Doctor discovery
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          Find a verified doctor
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          Search by doctor name, facility, or the weekday you need an
          appointment. National IDs and BMDC numbers are never returned.
        </p>
      </div>

      <div className="mt-8 grid gap-7 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-slate-950">Search filters</h2>
          <p className="mt-2 text-sm text-slate-600">
            At least one filter is required.
          </p>
          <SearchForm
            filters={filters}
            formError={formError}
            onChange={setFilters}
            onReset={handleReset}
            onSubmit={handleSubmit}
            submitting={submitting}
          />
        </section>

        <section
          aria-label="Doctor search results"
          className="space-y-4"
          data-testid="doctor-search-results"
        >
          {!submitted && results === null ? (
            <LoadingState
              description="Use the filters to begin a search."
              label="Ready to search"
            />
          ) : null}
          {submitted && submitting && results === null ? (
            <LoadingState
              description="Searching verified doctors for the chosen filter."
              label="Searching doctors"
            />
          ) : null}
          {error ? (
            <ErrorState
              message={error}
              onAction={() => {
                setError(null);
                setRequestVersion((value) => value + 1);
              }}
              title="Doctor search unavailable"
            />
          ) : null}
          {submitted && results && results.length === 0 ? (
            <EmptyState
              message="No verified doctor matched these filters. Try widening your search."
              title="No matches found"
            />
          ) : null}
          <div className="grid gap-4">
            {results?.map((doctor) => (
              <DoctorRow doctor={doctor} key={doctor.id} />
            ))}
          </div>
        </section>
      </div>

      {results && results.length > 0 ? (
        <p className="mt-6 text-xs text-slate-500">
          Showing {results.length} doctor{results.length === 1 ? "" : "s"}.
          {filters.weekday
            ? ` Filtered to weekday ${WEEKDAY_LABEL[filters.weekday]}.`
            : ""}
        </p>
      ) : null}
    </main>
  );
}

function CitizenGuard({ children }: { children: React.ReactNode }) {
  const auth = usePortalAuth("CITIZEN");
  const [hydrationFailed, setHydrationFailed] = useState(false);
  const status = auth.status;
  const refresh = auth.refreshSession;

  useEffect(() => {
    if (status === "authenticated") {
      return;
    }
    let active = true;
    void refresh().catch(() => {
      if (active) setHydrationFailed(true);
    });
    return () => {
      active = false;
    };
  }, [refresh, status]);

  if (status === "unauthenticated" && !hydrationFailed) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <LoadingState
          description="Checking for an active Citizen Portal session."
          label="Checking Citizen session"
        />
      </main>
    );
  }

  if (status === "unauthenticated") {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          action={
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-teal-700 px-5 text-sm font-bold text-white"
              href="/citizen/login"
            >
              Sign in to Citizen Portal
            </Link>
          }
          message="Sign in to search for verified doctors."
          title="Citizen sign in required"
        />
      </main>
    );
  }

  if (!auth.isRequiredPortal) {
    return (
      <main className="flex flex-1 items-center px-5 py-12" id="main-content">
        <EmptyState
          message="This session belongs to another HealthLink portal."
          title="Citizen Portal access required"
        />
      </main>
    );
  }

  return <>{children}</>;
}

export function DoctorSearch({
  searchAction = searchDoctors,
}: {
  searchAction?: (filters: DoctorSearchFilters) => Promise<DoctorSummary[]>;
}) {
  return (
    <CitizenShell>
      <CitizenGuard>
        <SearchContent searchAction={searchAction} />
      </CitizenGuard>
    </CitizenShell>
  );
}