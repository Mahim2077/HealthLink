"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { listNotifications, listReminders, markNotification, setReminderActive, type Reminder, type ReminderNotification } from "@/lib/reminders/api";
import { ReminderForm, reminderButtonClass } from "./reminder-form";

function PageControls({ page, count, setPage, label, disabled }: { page: number; count: number; setPage: (page: number) => void; label: string; disabled: boolean }) {
  return <nav aria-label={label} className="flex items-center gap-4"><button className={reminderButtonClass} disabled={disabled || page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button className={reminderButtonClass} disabled={disabled || count < 20} onClick={() => setPage(page + 1)}>Next</button></nav>;
}

export function RemindersWorkspace() {
  const [reminders, setReminders] = useState<Reminder[] | null>(null);
  const [notifications, setNotifications] = useState<ReminderNotification[] | null>(null);
  const [editing, setEditing] = useState<Reminder | "new" | null>(null);
  const [page, setPage] = useState(1);
  const [notificationPage, setNotificationPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  useEffect(() => {
    let active = true;
    void Promise.all([listReminders(page), listNotifications(notificationPage)]).then(([r, n]) => { if (active) { setReminders(r); setNotifications(n); } }, reason => { if (active) setError(reason instanceof Error ? reason.message : "Reminders unavailable."); });
    return () => { active = false; };
  }, [page, notificationPage, version]);
  async function action(run: () => Promise<unknown>) {
    if (inFlight.current) return;
    inFlight.current = true; setPending(true); setError(""); setNotice("");
    try { await run(); setVersion(v => v + 1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Change could not be saved."); }
    finally { inFlight.current = false; setPending(false); }
  }
  if (!reminders || !notifications) return error ? <ErrorState message={error} onAction={() => { setError(""); setVersion(v => v + 1); }} /> : <LoadingState label="Loading reminders" />;
  return <div className="space-y-7">
    {error && <ErrorState message={error} onAction={() => { setError(""); setVersion(v => v + 1); }} />}
    {notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    {editing ? <ReminderForm key={editing === "new" ? "new" : editing.id} initial={editing === "new" ? undefined : editing} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); setNotice("Reminder saved."); setPage(1); setVersion(v => v + 1); }} /> : <button disabled={pending} className={`${reminderButtonClass} bg-sky-800 text-white`} onClick={() => setEditing("new")}>Create reminder</button>}
    <section className="space-y-4" aria-labelledby="medicine-reminders-heading"><h2 id="medicine-reminders-heading" className="text-xl font-bold">Medicine reminders</h2>
      {!reminders.length && <EmptyState title="No reminders" message="Create a medicine reminder with one or more daily times." />}
      {reminders.map(reminder => <article key={reminder.id} className="hl-card space-y-3 p-5"><h3 className="font-bold">{reminder.medicine}</h3><p className="text-sm">{reminder.times.map(t => t.slice(0, 5)).join(", ")} · Asia/Dhaka · {reminder.is_active ? "Active" : "Inactive"}</p><p className="text-sm text-slate-600">{reminder.start_date} to {reminder.end_date ?? "no end date"}</p><div className="flex gap-3"><button disabled={pending || !!editing} className={reminderButtonClass} onClick={() => setEditing(reminder)}>Edit</button><button disabled={pending || !!editing} className={reminderButtonClass} onClick={() => void action(() => setReminderActive(reminder.id, !reminder.is_active))}>{reminder.is_active ? "Deactivate" : "Activate"}</button></div></article>)}
      <PageControls disabled={pending || !!editing} label="Reminder pages" page={page} count={reminders.length} setPage={p => { setReminders(null); setPage(p); }} />
    </section>
    <section className="space-y-4" aria-labelledby="notifications-heading"><div className="flex items-center justify-between gap-3"><h2 id="notifications-heading" className="text-xl font-bold">Notifications</h2><button disabled={pending || !!editing} className={reminderButtonClass} onClick={() => { setError(""); setVersion(v => v + 1); }}>Refresh notifications</button></div>
      <p className="text-sm text-slate-600">These are in-app notices and may arrive late. Acknowledging a notice does not record that medicine was taken.</p>
      {!notifications.length && <EmptyState title="No notifications" message="Due medicine reminders and booked appointment notices appear here." />}
      {notifications.map(item => <article key={item.id} className="hl-card space-y-3 p-5"><p>{item.message}</p><p className="text-sm text-slate-600">{item.acknowledged_at ? "Acknowledged" : item.read_at ? "Read" : "Unread"}</p><div className="flex flex-wrap gap-3"><button className={reminderButtonClass} disabled={pending || !!item.read_at} onClick={() => void action(() => markNotification(item.id, "read"))}>Mark read</button><button className={reminderButtonClass} disabled={pending || !!item.acknowledged_at} onClick={() => void action(() => markNotification(item.id, "acknowledge"))}>Acknowledge</button></div></article>)}
      <PageControls disabled={pending || !!editing} label="Notification pages" page={notificationPage} count={notifications.length} setPage={p => { setNotifications(null); setNotificationPage(p); }} />
    </section>
  </div>;
}

export function RemindersPage() {
  const auth = usePortalAuth("CITIZEN");
  const { status, refreshSession } = auth;
  const [failed, setFailed] = useState(false);
  useEffect(() => { if (status === "authenticated") return; let active = true; void refreshSession().catch(() => { if (active) setFailed(true); }); return () => { active = false; }; }, [status, refreshSession]);
  return <main id="main-content" className="mx-auto w-full max-w-4xl flex-1 space-y-6 px-5 py-10 sm:px-8"><h1 className="text-3xl font-bold">Reminders and notifications</h1><p className="text-sm text-slate-600">Manage your daily medicine reminders and view appointment notices.</p>
    {status !== "authenticated" ? failed ? <EmptyState title="Sign in required" message="Sign in to manage your reminders." action={<Link href="/citizen/login">Sign in</Link>} /> : <LoadingState label="Checking session" /> : !auth.isRequiredPortal ? <EmptyState title="Citizen portal required" message="Use your citizen session to manage reminders." /> : <RemindersWorkspace key={auth.claims?.sid} />}
  </main>;
}
