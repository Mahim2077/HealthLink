"use client";

import { useEffect, useRef, useState } from "react";
import {
  acceptLabSession, advanceLabSession, cancelLabSession, closeLabSession, closureReasons,
  getLabSessions, publishLabPdf, stageLabPdf, startLabSession, withdrawLabPdf,
  type ClosureReason, type LabSession, type SessionStatus, type TestChoice,
} from "@/lib/diagnostics/session-api";
import { DiagnosticPdfPreview } from "./diagnostic-pdf";
import { TestPicker } from "./test-picker";

const button = "min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50";
const primary = "min-h-11 rounded-xl bg-sky-700 px-4 text-sm font-semibold text-white disabled:opacity-50";
const input = "mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2";
const labels: Record<SessionStatus, string> = {
  REQUESTED: "Awaiting acceptance", ACCEPTED: "Accepted · Awaiting arrival", CHECKED_IN: "Checked in",
  COLLECTED: "Sample collected", PERFORMED: "Test performed", PUBLISHED: "Report available",
  EXPIRED: "Expired", CANCELLED: "Cancelled", UNABLE: "Unable to complete",
};

type Run = (action: () => Promise<unknown>) => Promise<void>;

function LabReportActions({ session, run, busy }: { session: LabSession; run: Run; busy: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [correction, setCorrection] = useState<TestChoice | null>(null);
  const [testedAt, setTestedAt] = useState("");
  const [preview, setPreview] = useState(false);
  const [withdraw, setWithdraw] = useState(false);
  const revision = session.draft_version;
  const publishedVersion = session.report_version;
  return <div className="space-y-3">
    <h4 className="font-semibold">Original report PDF</h4>
    <form className="space-y-2" onSubmit={event => {
      event.preventDefault();
      if (file) void run(async () => {
        await stageLabPdf(session.id, file, correction?.code, testedAt ? new Date(testedAt).toISOString() : undefined);
        setPreview(true);
      });
    }}>
      <fieldset className="space-y-2" disabled={busy}>
        <label className="block text-sm">Report PDF (up to 3 MB)
          <input type="file" accept="application/pdf,.pdf" required className={input} onChange={event => setFile(event.target.files?.[0] ?? null)} />
        </label>
        {session.status === "PUBLISHED" && <details className="space-y-2">
          <summary className="cursor-pointer text-sm font-semibold">Correct test details</summary>
          <TestPicker value={correction} onChange={setCorrection} />
          <label className="block text-sm">Corrected test time in your local time
            <input type="datetime-local" className={input} value={testedAt} onChange={event => setTestedAt(event.target.value)} />
          </label>
        </details>}
        <button type="submit" className={button}>Upload PDF</button>
      </fieldset>
    </form>
    {revision !== null && <>
      <button type="button" className={button} onClick={() => setPreview(value => !value)}>{preview ? "Hide draft PDF" : "Preview draft PDF"}</button>
      {preview && <>
        <p className="text-sm text-slate-600">{session.draft_test_name}{session.draft_tested_at && ` · Test time ${new Date(session.draft_tested_at).toLocaleString()}`}</p>
        <DiagnosticPdfPreview key={revision} id={session.id} version={revision} />
        <form className="space-y-2" key={revision} onSubmit={event => {
          event.preventDefault();
          void run(async () => { await publishLabPdf(session.id, revision); setPreview(false); });
        }}>
          <label className="flex items-start gap-2 text-sm"><input type="checkbox" required className="mt-1" /> I checked that the PDF matches this patient, the test type and test time.</label>
          <button type="submit" className={primary} disabled={busy}>Publish report</button>
        </form>
      </>}
    </>}
    {publishedVersion !== null && <div className="space-y-2">
      <PublishedLabPdf id={session.id} version={publishedVersion} />
      {withdraw ? <div className="flex flex-wrap gap-2">
        <button type="button" className={button} disabled={busy} onClick={() => void run(async () => {
          await withdrawLabPdf(session.id, publishedVersion);
          setWithdraw(false);
        })}>Confirm withdrawal</button>
        <button type="button" className={button} onClick={() => setWithdraw(false)}>Keep report</button>
      </div> : <button type="button" className={button} onClick={() => setWithdraw(true)}>Withdraw report</button>}
    </div>}
  </div>;
}

function PublishedLabPdf({ id, version }: { id: string; version: number }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer text-sm font-semibold">Open published PDF</summary>
    {open && <DiagnosticPdfPreview key={version} id={id} version={version} />}
  </details>;
}

function LabActions({ session, busy, run }: { session: LabSession; busy: boolean; run: Run }) {
  const [reason, setReason] = useState<ClosureReason | "">("");
  const [stepTime, setStepTime] = useState("");
  const { id, status } = session;
  const active = ["ACCEPTED", "CHECKED_IN", "COLLECTED", "PERFORMED"].includes(status);
  const recordStep = (step: "COLLECTED" | "PERFORMED") => run(async () => {
    await advanceLabSession(id, step, stepTime ? new Date(stepTime).toISOString() : undefined);
    setStepTime("");
  });
  return <>
    {(status === "CHECKED_IN" || status === "COLLECTED") && <label className="block text-sm">
      Actual step time in your local time (leave blank to use now)
      <input type="datetime-local" className={input} value={stepTime} onChange={event => setStepTime(event.target.value)} />
    </label>}
    <div className="flex flex-wrap gap-2">
      {status === "ACCEPTED" && <button type="button" className={primary} disabled={busy} onClick={() => void run(() => advanceLabSession(id, "CHECKED_IN"))}>Mark patient present</button>}
      {status === "CHECKED_IN" && <button type="button" className={button} disabled={busy} onClick={() => void recordStep("COLLECTED")}>Mark sample collected</button>}
      {(status === "CHECKED_IN" || status === "COLLECTED") && <button type="button" className={primary} disabled={busy} onClick={() => void recordStep("PERFORMED")}>Mark test performed</button>}
    </div>
    {active && <details className="space-y-2">
      <summary className="cursor-pointer text-sm font-semibold">Unable to complete</summary>
      <form className="space-y-2" onSubmit={event => { event.preventDefault(); if (reason) void run(() => closeLabSession(id, reason)); }}>
        <label className="block text-sm">Reason
          <select className={input} required value={reason} onChange={event => setReason(event.target.value as ClosureReason)}>
            <option value="">Select a reason</option>
            {Object.entries(closureReasons).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
        </label>
        <button type="submit" className={button} disabled={busy}>Close session</button>
      </form>
    </details>}
    {(status === "PERFORMED" || status === "PUBLISHED") && <LabReportActions session={session} run={run} busy={busy} />}
  </>;
}

function CitizenPdf({ session }: { session: LabSession }) {
  const [open, setOpen] = useState(false);
  return <div className="space-y-2">
    <button type="button" className={button} aria-expanded={open} onClick={() => setOpen(value => !value)}>
      {open ? "Close report PDF" : "Open report PDF"}
    </button>
    {open && <DiagnosticPdfPreview key={session.report_version} id={session.id} />}
  </div>;
}

export function DiagnosticSessions({ lab = false, selection = null, onSelection, onRefresh }: {
  lab?: boolean;
  selection?: TestChoice | null;
  onSelection?: (choice: TestChoice | null) => void;
  onRefresh?: () => void;
}) {
  const [sessions, setSessions] = useState<LabSession[] | null>(null);
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState("");
  const [deadline, setDeadline] = useState("");
  const locked = useRef(false);
  const createAttempt = useRef<{ id: string; code: string } | null>(null);

  useEffect(() => {
    let active = true;
    void getLabSessions(lab, page).then(data => {
      if (active) {
        setSessions(data);
        setLoadError("");
        if (reload > 0) onRefresh?.();
      }
    }, reason => {
      if (active) setLoadError(reason instanceof Error ? reason.message : "Unable to load lab sessions.");
    });
    return () => { active = false; };
  }, [lab, onRefresh, page, reload]);
  useEffect(() => {
    const timer = window.setInterval(() => { if (!document.hidden) setReload(value => value + 1); }, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const run: Run = async action => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setError("");
    try { await action(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to update the lab session."); }
    finally {
      setReload(value => value + 1);
      setBusy(false);
      locked.current = false;
    }
  };
  const create = (catalogCode: string) => run(async () => {
    const attempt = createAttempt.current?.code === catalogCode ? createAttempt.current : { id: crypto.randomUUID(), code: catalogCode };
    createAttempt.current = attempt;
    await startLabSession(attempt.id, catalogCode);
    createAttempt.current = null;
    onSelection?.(null);
    if (page !== 1) { setPage(1); setSessions(null); }
  });

  return <section id="diagnostic-new" className="space-y-4" aria-label="Lab sessions">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-xl font-bold">{lab ? "Lab sessions" : "Your lab sessions"}</h2>
      <button type="button" className={button} onClick={() => setReload(value => value + 1)}>Refresh sessions</button>
    </div>
    {lab ? <form className="hl-card space-y-3 p-5" onSubmit={event => {
      event.preventDefault();
      void run(async () => {
        await acceptLabSession(code.trim(), new Date(deadline).toISOString());
        setCode("");
        setDeadline("");
        if (page !== 1) { setPage(1); setSessions(null); }
      });
    }}>
      <h3 className="font-semibold">Accept a request</h3>
      <label className="block text-sm">Patient’s session code<input className={input} value={code} onChange={event => setCode(event.target.value)} required maxLength={32} autoComplete="off" /></label>
      <label className="block text-sm">Attendance deadline in your local time<input className={input} value={deadline} onChange={event => setDeadline(event.target.value)} required type="datetime-local" /></label>
      <button type="submit" className={primary} disabled={busy}>Accept request</button>
    </form> : onSelection && <form className="hl-card space-y-3 p-5" onSubmit={event => {
      event.preventDefault();
      if (selection) void create(selection.code);
    }}>
      <h3 className="font-semibold">Request a test</h3>
      <p className="text-sm text-slate-600">Share the session code with a technician at your chosen participating facility.</p>
      <TestPicker value={selection} onChange={onSelection} />
      <button type="submit" className={primary} disabled={!selection || busy}>Start session</button>
    </form>}
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    {loadError ? <p role="alert" className="text-sm text-rose-700">{loadError}</p> : !sessions ? <p role="status">Loading lab sessions…</p> : sessions.length === 0 && <p className="text-sm text-slate-600">No lab sessions on this page.</p>}
    {sessions?.slice(0, 20).map(session => <article className="hl-card space-y-3 p-5" key={session.id}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold">{session.test_name}</h3>
          <p className="text-sm text-slate-600">{[session.patient_name, session.facility_name, new Date(session.created_at).toLocaleDateString()].filter(Boolean).join(" · ")}</p>
        </div>
        <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-900">{session.status === "PUBLISHED" && session.report_version === null ? "Report withdrawn" : labels[session.status]}</span>
      </div>
      {session.status === "ACCEPTED" && session.attendance_deadline && <p className="text-sm">Arrive by {new Date(session.attendance_deadline).toLocaleString()}.</p>}
      {session.closed_reason && <p className="text-sm">{closureReasons[session.closed_reason]}</p>}
      {lab ? <LabActions session={session} busy={busy} run={run} /> : <>
        {session.status === "REQUESTED" && <div className="flex flex-wrap items-center gap-3">
          {session.share_code ? <label className="text-sm">Session code <input readOnly value={session.share_code} className="rounded-lg border border-slate-300 px-2 py-1 font-mono" onFocus={event => event.target.select()} /></label> :
            <p className="text-sm">The session code expired. Cancel this session and start a new one.</p>}
          <button type="button" className={button} disabled={busy} onClick={() => void run(() => cancelLabSession(session.id))}>Cancel session</button>
        </div>}
        {["EXPIRED", "CANCELLED", "UNABLE"].includes(session.status) && <button type="button" className={primary} disabled={busy} onClick={() => void create(session.catalog_code)}>Start new session</button>}
        {session.report_version !== null && <>
          {session.report_test_name !== session.test_name && <p className="text-sm">Report test type · {session.report_test_name}</p>}
          <CitizenPdf session={session} />
        </>}
      </>}
    </article>)}
    {sessions && (page > 1 || sessions.length > 20) && <nav aria-label="Lab session pages" className="flex flex-wrap items-center gap-3">
      <button type="button" className={button} disabled={page === 1 || busy} onClick={() => { setPage(page - 1); setSessions(null); }}>Previous sessions</button>
      <span className="text-sm">Page {page}</span>
      <button type="button" className={button} disabled={sessions.length <= 20 || busy} onClick={() => { setPage(page + 1); setSessions(null); }}>Next sessions</button>
    </nav>}
  </section>;
}
