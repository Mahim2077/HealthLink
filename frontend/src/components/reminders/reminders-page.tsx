"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { listReminders, setReminderActive, type Reminder } from "@/lib/reminders/api";

import { ReminderForm, reminderButtonClass } from "./reminder-form";

export function RemindersWorkspace() {
  const [reminders, setReminders] = useState<Reminder[] | null>(null);
  const [editing, setEditing] = useState<Reminder | "new" | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);

  useEffect(() => {
    let active = true;
    void listReminders(page).then(({ items, has_more }) => {
      if (!active) return;
      setReminders((previous) => {
        if (page === 1 || !previous) return items;
        const loaded = new Set(previous.map((item) => item.id));
        return [...previous, ...items.filter((item) => !loaded.has(item.id))];
      });
      setHasMore(has_more);
      setError("");
    }, () => {
      if (active) setError("Reminders could not be loaded. Please try again.");
    }).finally(() => {
      if (active) {
        inFlight.current = false;
        setPending(false);
      }
    });
    return () => { active = false; };
  }, [page, version]);

  async function toggle(reminder: Reminder) {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setError("");
    setNotice("");
    try {
      const updated = await setReminderActive(reminder.id, !reminder.is_active);
      setReminders((items) => items?.map((item) => item.id === updated.id ? updated : item) ?? null);
      setNotice(updated.is_active ? "Reminder activated." : "Reminder deactivated.");
    } catch {
      setError("The reminder could not be updated. Please try again.");
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  function reload() {
    setError("");
    setPage(1);
    setVersion((value) => value + 1);
  }

  if (!reminders) return error
    ? <ErrorState message={error} onAction={reload} />
    : <LoadingState label="Loading reminders" />;
  return (
    <div className="space-y-5">
      {error ? <ErrorState message={error} onAction={reload} /> : null}
      {notice ? <p className="text-sm text-emerald-800" role="status">{notice}</p> : null}
      {editing ? (
        <ReminderForm
          key={editing === "new" ? "new" : editing.id}
          initial={editing === "new" ? undefined : editing}
          onCancel={() => setEditing(null)}
          onSaved={() => { setEditing(null); setNotice("Reminder saved."); reload(); }}
        />
      ) : (
        <button className={reminderButtonClass + " bg-sky-800 text-white"} disabled={pending} onClick={() => setEditing("new")} type="button">
          Create reminder
        </button>
      )}
      <section aria-labelledby="medicine-reminders-heading" className="space-y-4">
        <h2 className="text-xl font-bold" id="medicine-reminders-heading">Medicine schedules</h2>
        {reminders.length === 0 ? <EmptyState title="No reminders yet" message="Create a schedule for your medicine." /> : null}
        {reminders.map((reminder) => (
          <article className="hl-card space-y-3 p-5" key={reminder.id}>
            <h3 className="font-bold">{reminder.medicine}</h3>
            <p className="text-sm">{reminder.times.map((time) => time.slice(0, 5)).join(", ")} · Asia/Dhaka · {reminder.is_active ? "Active" : "Inactive"}</p>
            <p className="text-sm text-slate-600">{reminder.start_date} to {reminder.end_date ?? "no end date"}</p>
            <div className="flex flex-wrap gap-3">
              <button className={reminderButtonClass} disabled={pending || !!editing} onClick={() => setEditing(reminder)} type="button">Edit</button>
              <button className={reminderButtonClass} disabled={pending || !!editing} onClick={() => void toggle(reminder)} type="button">
                {reminder.is_active ? "Deactivate" : "Activate"}
              </button>
            </div>
          </article>
        ))}
        {hasMore ? (
          <button
            className={reminderButtonClass}
            disabled={pending || !!editing}
            onClick={() => {
              if (inFlight.current) return;
              inFlight.current = true;
              setPending(true);
              setPage((value) => value + 1);
            }}
            type="button"
          >
            Load more schedules
          </button>
        ) : null}
      </section>
    </div>
  );
}

export function RemindersPage() {
  const { status, refreshSession, isRequiredPortal, claims } = usePortalAuth("CITIZEN");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (status === "authenticated") return;
    let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 space-y-5 px-5 py-10 sm:px-8" id="main-content">
      <h1 className="text-3xl font-bold">Reminders</h1>
      <p className="text-sm text-slate-600">Manage medicine schedules in Dhaka time. Due reminders appear in your inbox when you use HealthLink.</p>
      {status === "authenticated" && isRequiredPortal ? (
        <>
          <Link className="inline-flex min-h-11 items-center font-semibold text-[var(--portal-strong)] underline" href="/citizen/inbox">Open inbox</Link>
          <RemindersWorkspace key={claims?.sid} />
        </>
      ) : status === "authenticated" ? <EmptyState title="Citizen portal required" message="Use your citizen session to manage reminders." />
        : failed ? <EmptyState title="Sign in required" message="Sign in to manage your reminders." action={<Link href="/citizen/login">Sign in</Link>} />
        : <LoadingState label="Checking session" />}
    </main>
  );
}
