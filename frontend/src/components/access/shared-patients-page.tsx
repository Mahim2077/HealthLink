"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AccessSession } from "./access-grants-page";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { apiClient } from "@/lib/api/client";
import { grantedPatients, scopes, sharedRecords, type GrantedPatient, type Page, type SharedRecord } from "@/lib/access/api";

function Fields({ values }: { values: Record<string, unknown> }) {
  return <dl className="space-y-3">{Object.entries(values).filter(([key]) => !["id", "citizen_id"].includes(key)).map(([key, value]) => <div key={key}><dt className="font-semibold capitalize">{key.replaceAll("_", " ")}</dt><dd className="whitespace-pre-wrap break-words">{value == null || value === "" ? "Not provided" : String(value)}</dd></div>)}</dl>;
}

function VisitDetail({ citizenId, id }: { citizenId: string; id: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() { setBusy(true); setError(""); try { setData(await apiClient.get(`professionals/patients/${citizenId}/visits/${id}`)); } catch { setData(null); setError("Visit unavailable. Access may have expired or been revoked."); } finally { setBusy(false); } }
  return <div className="mt-3">{data ? <Fields values={data} /> : <button className="font-semibold underline" disabled={busy} onClick={() => void load()}>{busy ? "Loading…" : "Read visit"}</button>}{error && <p role="alert">{error}</p>}</div>;
}

function Records({ grant }: { grant: GrantedPatient }) {
  const [kind, setKind] = useState(grant.access_scope === "VISITS_ONLY" ? "VISIT" : grant.access_scope === "PRESCRIPTIONS_ONLY" ? "PRESCRIPTION" : grant.access_scope === "LAB_REPORTS_ONLY" ? "LAB_REPORT" : grant.access_scope === "EMERGENCY_PROFILE_ONLY" ? "EMERGENCY_PROFILE" : "");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ records: SharedRecord[]; has_next: boolean } | null>(null);
  const [emergency, setEmergency] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => { let active = true;
    const work = kind === "EMERGENCY_PROFILE" ? apiClient.get<Record<string, unknown>>(`professionals/patients/${grant.citizen_id}/emergency-profile`).then(value => { if (active) setEmergency(value); }) : sharedRecords(grant.citizen_id, kind, page).then(value => { if (active) setData(value); });
    void work.catch(() => { if (active) { setData(null); setEmergency(null); setError("Records unavailable. The grant may have expired or been revoked."); } });
    return () => { active = false; };
  }, [grant.citizen_id, kind, page, version]);
  function reset() { setData(null); setEmergency(null); setError(""); }
  return <section className="space-y-4 rounded-2xl border border-slate-200 p-5"><h2 className="text-xl font-bold">{grant.citizen_name}: shared records</h2>
    <p>{scopes[grant.access_scope]} · Read only</p>
    {grant.access_scope === "FULL_MEDICAL_HISTORY" && <label className="block">Record type<select className="ml-3 rounded-lg border p-2" value={kind} onChange={event => { reset(); setPage(1); setKind(event.target.value); }}><option value="">All clinical records</option><option value="VISIT">Visits</option><option value="PRESCRIPTION">Prescriptions</option><option value="LAB_REPORT">Lab reports</option><option value="EMERGENCY_PROFILE">Emergency profile</option></select></label>}
    <button className="font-semibold underline" onClick={() => { reset(); setVersion(v => v + 1); }}>Refresh records</button>
    {error ? <ErrorState message={error} onAction={() => { reset(); setVersion(v => v + 1); }} /> : emergency ? <Fields values={emergency} /> : !data ? <LoadingState label="Loading shared records" /> : data.records.length === 0 ? <EmptyState title="No finalized records" message="There are no finalized records in this scope." /> : data.records.map(record => <article key={`${record.resource_type}-${record.id}`} className="rounded-xl bg-slate-50 p-4"><h3 className="font-bold">{record.title}</h3><p className="text-sm">{new Date(record.occurred_at).toLocaleString()}</p><p className="whitespace-pre-wrap">{record.summary}</p>{record.detail_url && <Link className="font-semibold underline" href={record.detail_url}>Open report</Link>}{record.resource_type === "VISIT" && <VisitDetail citizenId={grant.citizen_id} id={record.id} />}</article>)}
    {kind !== "EMERGENCY_PROFILE" && <div className="flex gap-4"><button disabled={page === 1} onClick={() => { reset(); setPage(p => p - 1); }}>Previous</button><span>Page {page}</span><button disabled={!data?.has_next} onClick={() => { reset(); setPage(p => p + 1); }}>Next</button></div>}
  </section>;
}

function SharedPatients() {
  const [data, setData] = useState<Page<GrantedPatient> | null>(null);
  const [selected, setSelected] = useState<GrantedPatient | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => { let active = true; void grantedPatients(page).then(value => { if (active) { setData(value); setError(""); } }, () => { if (active) { setData(null); setSelected(null); setError("Unable to load shared patients. A verified Doctor role is required."); } }); return () => { active = false; }; }, [page, version]);
  return <div className="space-y-5">{error ? <ErrorState message={error} onAction={() => setVersion(v => v + 1)} /> : !data ? <LoadingState label="Loading shared patients" /> : data.grants.length === 0 ? <EmptyState title="No active grants" message="Citizens can share selected records with you through medical record sharing." /> : data.grants.map(grant => <article key={grant.id} className="rounded-xl border border-slate-200 p-4"><h2 className="font-bold">{grant.citizen_name}</h2><p>{scopes[grant.access_scope]} · {grant.expires_at ? `Expires ${new Date(grant.expires_at).toLocaleString()}` : "No expiry"}</p><button className="mt-2 font-semibold underline" onClick={() => setSelected(grant)}>Read shared records</button></article>)}
    <div className="flex gap-4"><button disabled={page === 1} onClick={() => { setData(null); setSelected(null); setPage(p => p - 1); }}>Previous</button><span>Page {page}</span><button disabled={!data?.has_next} onClick={() => { setData(null); setSelected(null); setPage(p => p + 1); }}>Next</button></div>
    {selected && <Records key={selected.id} grant={selected} />}
  </div>;
}

export function SharedPatientsPage() { return <main id="main-content" className="mx-auto w-full max-w-5xl px-5 py-10"><h1 className="mb-6 text-3xl font-bold">Shared patient records</h1><AccessSession portal="PROFESSIONAL"><SharedPatients /></AccessSession></main>; }
