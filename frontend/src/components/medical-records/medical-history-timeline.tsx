"use client";

import {
  CalendarDaysIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { citizenErrorMessage } from "@/lib/citizen/presentation";
import type {
  MedicalHistoryLoadAction,
  MedicalHistoryPage,
  MedicalHistoryQuery,
  MedicalHistoryResourceType,
} from "@/lib/medical-records/types";

type HistoryPortal = "citizen" | "professional";

const RESOURCE_LABEL: Record<MedicalHistoryResourceType, string> = {
  VISIT: "Visit",
  PRESCRIPTION: "Prescription",
};

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-BD", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function HistoryEventCard({
  event,
  portal,
}: {
  event: MedicalHistoryPage["items"][number];
  portal: HistoryPortal;
}) {
  const Icon =
    event.resource_type === "PRESCRIPTION"
      ? DocumentTextIcon
      : ClipboardDocumentListIcon;
  const body = (
    <article className="relative rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start gap-4">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--portal-soft)] text-[var(--portal-strong)]">
          <Icon aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-slate-950">{event.title}</h3>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
              {RESOURCE_LABEL[event.resource_type]}
            </span>
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-700">
            {formatTimestamp(event.occurred_at)}
          </p>
          {event.subtitle ? (
            <p className="mt-2 text-sm text-slate-700">{event.subtitle}</p>
          ) : null}
          {event.summary ? (
            <p className="mt-2 text-sm leading-6 text-slate-600">{event.summary}</p>
          ) : null}
          <p className="mt-3 text-xs leading-5 text-slate-500">
            {[event.professional, event.facility, event.serial_number ? `Serial #${event.serial_number}` : null]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
      </div>
    </article>
  );

  if (portal === "citizen" && event.resource_type === "PRESCRIPTION") {
    return (
      <Link
        aria-label={`Open prescription from ${formatTimestamp(event.occurred_at)}`}
        className="block rounded-2xl transition hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--portal-accent)]"
        href={`/citizen/prescriptions/${event.resource_id}`}
      >
        {body}
      </Link>
    );
  }
  return body;
}

export function MedicalHistoryTimeline({
  loadAction,
  portal,
}: {
  loadAction: MedicalHistoryLoadAction;
  portal: HistoryPortal;
}) {
  const [resourceType, setResourceType] = useState<"" | MedicalHistoryResourceType>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [query, setQuery] = useState<MedicalHistoryQuery>({ page: 1, page_size: 10 });
  const [result, setResult] = useState<MedicalHistoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void loadAction(query).then(
      (response) => {
        if (active) {
          setResult(response);
          setError(null);
        }
      },
      (reason: unknown) => {
        if (active) {
          setError(
            citizenErrorMessage(
              reason,
              "We could not load this medical history right now.",
            ),
          );
        }
      },
    );
    return () => {
      active = false;
    };
  }, [loadAction, query, version]);

  const applyFilters = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setResult(null);
      setError(null);
      setQuery({
        ...(resourceType ? { resource_type: resourceType } : {}),
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
        page: 1,
        page_size: 10,
      });
    },
    [dateFrom, dateTo, resourceType],
  );

  const resetFilters = useCallback(() => {
    setResourceType("");
    setDateFrom("");
    setDateTo("");
    setResult(null);
    setError(null);
    setQuery({ page: 1, page_size: 10 });
  }, []);

  return (
    <section aria-labelledby="medical-history-heading" className="space-y-5">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--portal-strong)]">
          Longitudinal record
        </p>
        <h2 className="mt-2 text-2xl font-bold text-slate-950" id="medical-history-heading">
          Medical history
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Finalized visits and prescriptions, newest first. Draft clinical work is never shown here.
        </p>
      </div>

      <form className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2 lg:grid-cols-4" onSubmit={applyFilters}>
        <label className="text-sm font-semibold text-slate-700">
          Record type
          <select className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 font-normal" onChange={(event) => setResourceType(event.target.value as "" | MedicalHistoryResourceType)} value={resourceType}>
            <option value="">All records</option>
            <option value="VISIT">Visits</option>
            <option value="PRESCRIPTION">Prescriptions</option>
          </select>
        </label>
        <label className="text-sm font-semibold text-slate-700">
          From
          <input className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 font-normal" max={dateTo || undefined} onChange={(event) => setDateFrom(event.target.value)} type="date" value={dateFrom} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          To
          <input className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 font-normal" min={dateFrom || undefined} onChange={(event) => setDateTo(event.target.value)} type="date" value={dateTo} />
        </label>
        <div className="flex items-end gap-2">
          <button className="min-h-11 flex-1 rounded-xl bg-[var(--portal-accent)] px-4 text-sm font-bold text-white" type="submit">Apply</button>
          <button className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-bold text-slate-700" onClick={resetFilters} type="button">Reset</button>
        </div>
      </form>

      {error ? (
        <ErrorState className="min-h-[14rem] px-0 py-4" message={error} onAction={() => { setResult(null); setError(null); setVersion((value) => value + 1); }} title="Medical history unavailable" />
      ) : !result ? (
        <LoadingState className="min-h-[14rem] px-0 py-4" description="Collecting finalized visits and prescriptions." label="Loading medical history" />
      ) : result.items.length === 0 ? (
        <EmptyState className="min-h-[14rem] px-0 py-4" icon={<CalendarDaysIcon aria-hidden="true" className="size-6" />} message="No finalized visits or prescriptions match these filters." title="No medical history found" />
      ) : (
        <>
          <p aria-live="polite" className="text-sm text-slate-600">
            Showing {result.items.length} of {result.total} records
          </p>
          <div className="grid gap-4" data-testid="medical-history-events">
            {result.items.map((event) => (
              <HistoryEventCard event={event} key={event.id} portal={portal} />
            ))}
          </div>
          <nav aria-label="Medical history pages" className="flex items-center justify-between border-t border-slate-200 pt-4">
            <button className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-700 disabled:opacity-40" disabled={result.page <= 1} onClick={() => { setResult(null); setError(null); setQuery((current) => ({ ...current, page: Math.max(1, (current.page ?? 1) - 1) })); }} type="button">Previous</button>
            <span className="text-sm font-semibold text-slate-600">Page {result.page}</span>
            <button className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-700 disabled:opacity-40" disabled={!result.has_next} onClick={() => { setResult(null); setError(null); setQuery((current) => ({ ...current, page: (current.page ?? 1) + 1 })); }} type="button">Next</button>
          </nav>
        </>
      )}
    </section>
  );
}
