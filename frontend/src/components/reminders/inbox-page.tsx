"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import type { Portal } from "@/lib/auth/types";
import { listNotifications, markNotification, syncInbox, type InboxPage as InboxData, type ReminderNotification } from "@/lib/reminders/api";

import { inboxCountEvent, type InboxCount } from "./inbox-link";

const button = "min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50";
const titles: Record<ReminderNotification["kind"], string> = {
  MEDICINE: "Medicine reminder",
  APPOINTMENT: "Appointment",
  DIAGNOSTIC: "Diagnostic update",
  VERIFICATION: "Professional verification",
};
const destinations: Partial<Record<Portal, Partial<Record<ReminderNotification["kind"], [string, string]>>>> = {
  CITIZEN: {
    MEDICINE: ["/citizen/reminders", "Manage reminders"],
    APPOINTMENT: ["/citizen/appointments", "View appointments"],
    DIAGNOSTIC: ["/citizen/diagnostic-tests", "View diagnostic tests"],
  },
  PROFESSIONAL: { VERIFICATION: ["/professional/status", "View application status"] },
  ADMIN: { VERIFICATION: ["/admin/professional-registrations", "Open verification queue"] },
};
const displayDate = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Dhaka",
});

function publishUnread(sessionId: string | undefined, count: number) {
  window.dispatchEvent(new CustomEvent<InboxCount>(inboxCountEvent, { detail: { sessionId, count } }));
}

export function InboxWorkspace({ portal, sessionId }: { portal: Portal; sessionId?: string }) {
  const [data, setData] = useState<InboxData | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const inFlight = useRef(false);
  const newCount = useRef<number | null>(null);
  const olderLoaded = useRef(false);
  const [hasUpdates, setHasUpdates] = useState(false);

  useEffect(() => {
    let active = true;
    inFlight.current = true;
    void syncInbox().then(() => listNotifications()).then((result) => {
      if (!active) return;
      setData(result);
      newCount.current = result.unread_count;
      olderLoaded.current = false;
      publishUnread(sessionId, result.unread_count);
      setHasUpdates(false);
    }, () => {
      if (active) setError("The inbox could not be loaded. Please try again.");
    }).finally(() => {
      if (active) {
        inFlight.current = false;
        setBusy(false);
      }
    });
    return () => { active = false; };
  }, [refresh, sessionId]);

  useEffect(() => {
    function noteUpdate(event: Event) {
      if (inFlight.current || newCount.current === null) return;
      const detail = (event as CustomEvent<InboxCount>).detail;
      if (detail.sessionId !== sessionId || detail.count === newCount.current) return;
      if (olderLoaded.current) {
        setHasUpdates(true);
      } else {
        inFlight.current = true;
        setError("");
        setBusy(true);
        setRefresh((value) => value + 1);
      }
    }
    window.addEventListener(inboxCountEvent, noteUpdate);
    return () => window.removeEventListener(inboxCountEvent, noteUpdate);
  }, [sessionId]);

  function reload() {
    if (inFlight.current) return;
    inFlight.current = true;
    setError("");
    setBusy(true);
    setRefresh((value) => value + 1);
  }

  async function updateInbox(run: (current: InboxData) => Promise<InboxData>) {
    if (inFlight.current || !data) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await run(data);
      setData(result);
      newCount.current = result.unread_count;
      publishUnread(sessionId, result.unread_count);
    } catch {
      setError("The inbox could not be updated. Please try again.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  function loadOlder() {
    void updateInbox(async (current) => {
      if (!current.next_cursor) return current;
      const older = await listNotifications(current.next_cursor);
      olderLoaded.current = true;
      return { ...older, items: [...current.items, ...older.items] };
    });
  }

  function mark(item: ReminderNotification, action: "read" | "acknowledge") {
    void updateInbox(async (current) => {
      const { item: updated, unread_count } = await markNotification(item.id, action);
      return {
        ...current,
        unread_count,
        items: current.items.map((row) => row.id === updated.id ? updated : row),
      };
    });
  }

  if (!data) return error
    ? <ErrorState message={error} onAction={reload} />
    : <LoadingState label="Loading inbox" />;
  return (
    <div className="space-y-4" aria-busy={busy}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600" role="status">
          {hasUpdates ? "Your inbox has changed. Refresh to see the latest notices." : `${data.unread_count} unread`}
        </p>
        <button className={button} disabled={busy} onClick={reload} type="button">Refresh inbox</button>
      </div>
      {error ? <p className="rounded-xl bg-rose-50 p-3 text-rose-800" role="alert">{error}</p> : null}
      {data.items.length === 0 ? <EmptyState title="Your inbox is empty" message="Reminders and account updates will appear here." /> : (
        <ul className="space-y-3">
          {data.items.map((item) => {
            const destination = destinations[portal]?.[item.kind];
            return (
              <li className="hl-card space-y-3 p-5" key={item.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-bold text-slate-950">{titles[item.kind]}</h2>
                  <span className="text-sm text-slate-600">
                    {item.acknowledged_at ? "Acknowledged" : item.read_at ? "Read" : "Unread"}
                  </span>
                </div>
                <p className="break-words">{item.message}</p>
                <time className="block text-sm text-slate-600" dateTime={item.due_at}>{displayDate.format(new Date(item.due_at))} (Dhaka)</time>
                <div className="flex flex-wrap items-center gap-3">
                  {destination ? <Link className="inline-flex min-h-11 items-center font-semibold text-[var(--portal-strong)] underline" href={destination[0]}>{destination[1]}</Link> : null}
                  {!item.read_at ? <button className={button} disabled={busy} onClick={() => mark(item, "read")} type="button">Mark as read</button> : null}
                  {item.kind === "MEDICINE" && !item.acknowledged_at ? <button className={button} disabled={busy} onClick={() => mark(item, "acknowledge")} type="button">Acknowledge reminder</button> : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {data.next_cursor ? <button className={button} disabled={busy} onClick={loadOlder} type="button">Load older notices</button> : null}
    </div>
  );
}

export function InboxPage({ portal }: { portal: Portal }) {
  const { status, refreshSession, isRequiredPortal, claims } = usePortalAuth(portal);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 space-y-5 px-5 py-10 sm:px-8" id="main-content">
      <h1 className="text-3xl font-bold">Inbox</h1>
      {status === "authenticated" && isRequiredPortal ? <InboxWorkspace key={claims?.sid} portal={portal} sessionId={claims?.sid} />
        : status === "authenticated" ? <EmptyState title="Portal access required" message="Open the inbox in your active portal." />
        : failed ? <EmptyState title="Sign in required" message="Sign in to open your inbox." action={<Link href={`/${portal.toLowerCase()}/login`}>Sign in</Link>} />
        : <LoadingState label="Checking session" />}
    </main>
  );
}
