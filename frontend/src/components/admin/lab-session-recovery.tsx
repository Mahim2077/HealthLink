"use client";

import { useEffect, useRef, useState } from "react";
import { loadAdminMe } from "@/lib/admin/api";
import type { Facility } from "@/lib/admin/types";
import { apiClient } from "@/lib/api/client";
import { closureReasons, type ClosureReason } from "@/lib/diagnostics/session-api";

type RecoveryRow = { id: string; status: string; created_at: string };
const button = "min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50";

export function LabSessionRecovery({ facilities }: { facilities: Facility[] }) {
  const [allowed, setAllowed] = useState(false);
  const [facilityId, setFacilityId] = useState("");
  useEffect(() => {
    let active = true;
    void loadAdminMe().then(admin => { if (active) setAllowed(admin.is_super_admin); }, () => {});
    return () => { active = false; };
  }, []);
  if (!allowed) return null;
  return <details className="hl-card mt-8 space-y-3 p-5">
    <summary className="min-h-11 cursor-pointer font-semibold">Recover a stalled lab session</summary>
    <label className="block text-sm font-semibold">Facility
      <select className="ml-2 min-h-11 rounded-xl border border-slate-300 px-3" value={facilityId} onChange={event => setFacilityId(event.target.value)}>
        <option value="">Choose a facility</option>
        {facilities.map(facility => <option key={facility.id} value={facility.id}>{facility.name}</option>)}
      </select>
    </label>
    {facilityId && <RecoveryList key={facilityId} facilityId={facilityId} />}
  </details>;
}

function RecoveryList({ facilityId }: { facilityId: string }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ sessions: RecoveryRow[]; has_next: boolean } | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState<ClosureReason | "">("");
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const path = `admin/facilities/${facilityId}/diagnostic-sessions`;
  useEffect(() => {
    let active = true;
    void apiClient.get<{ sessions: RecoveryRow[]; has_next: boolean }>(`${path}?page=${page}`).then(result => {
      if (active) setData(result);
    }, failure => { if (active) setError(failure instanceof Error ? failure.message : "Unable to load lab sessions."); });
    return () => { active = false; };
  }, [page, path, reload]);
  const move = (next: number) => { setTarget(""); setReason(""); setData(null); setPage(next); };
  return <div className="space-y-3">
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    {notice && <p role="status" className="text-sm">{notice}</p>}
    {!data && !error && <p role="status">Loading sessions…</p>}
    {data?.sessions.length === 0 && <p className="text-sm">No active sessions on this page.</p>}
    {data?.sessions.map(item => <article key={item.id} className="space-y-2 rounded-xl border border-slate-200 p-3">
      <p className="break-all text-sm font-semibold">{item.id}</p>
      <p className="text-sm">{item.status.replaceAll("_", " ")} · {new Date(item.created_at).toLocaleString()}</p>
      {target === item.id ? <form className="flex flex-wrap items-center gap-2" onSubmit={async event => {
        event.preventDefault();
        if (!reason || inFlight.current) return;
        inFlight.current = true;
        setPending(true);
        setError("");
        setNotice("");
        try {
          await apiClient.post<void, { reason: ClosureReason }>(`${path}/${item.id}/close`, { reason });
          setTarget("");
          setReason("");
          setNotice("Session closed. The patient can start a new one.");
        } catch (failure) {
          setError(failure instanceof Error ? failure.message : "Unable to close the session.");
        } finally {
          setReload(value => value + 1);
          setPending(false);
          inFlight.current = false;
        }
      }}>
        <label className="text-sm">Reason <select required className={button} value={reason} onChange={event => setReason(event.target.value as ClosureReason)}>
          <option value="">Select a reason</option>
          {Object.entries(closureReasons).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
        </select></label>
        <button type="submit" className={button} disabled={pending}>Close session</button>
        <button type="button" className={button} disabled={pending} onClick={() => { setTarget(""); setReason(""); }}>Back</button>
      </form> : <button type="button" className={button} disabled={pending} onClick={() => { setTarget(item.id); setReason(""); }}>Unable to complete</button>}
    </article>)}
    {data && (page > 1 || data.has_next) && <div className="flex gap-2">
      <button type="button" className={button} disabled={pending || page === 1} onClick={() => move(page - 1)}>Previous sessions</button>
      <button type="button" className={button} disabled={pending || !data.has_next} onClick={() => move(page + 1)}>Next sessions</button>
    </div>}
  </div>;
}
