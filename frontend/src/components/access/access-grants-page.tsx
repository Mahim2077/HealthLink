"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePortalAuth } from "@/components/auth/auth-provider";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/async-state";
import { createGrant, findDoctors, listGrants, revokeGrant, scopes, type Doctor, type Grant, type Page, type Scope } from "@/lib/access/api";

const field = "w-full rounded-xl border border-slate-300 bg-white p-3 disabled:opacity-60";
const button = "rounded-xl bg-[var(--portal-strong)] px-4 py-3 font-semibold text-white disabled:opacity-50";

export function AccessSession({ portal, children }: { portal: "CITIZEN" | "PROFESSIONAL"; children: React.ReactNode }) {
  const auth = usePortalAuth(portal);
  const { status, refreshSession } = auth;
  const [failed, setFailed] = useState(false);
  useEffect(() => { if (status === "authenticated") return; let active = true;
    void refreshSession().catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [status, refreshSession]);
  if (status !== "authenticated") return failed ? <EmptyState title="Sign in required" message="Sign in to manage shared medical records." action={<Link href={`/${portal.toLowerCase()}/login`}>Sign in</Link>} /> : <LoadingState label="Checking session" />;
  if (!auth.isRequiredPortal) return <EmptyState title="Portal access required" message="Switch to the correct portal to continue." />;
  return <div key={auth.claims?.sid}>{children}</div>;
}

function GrantManager() {
  const [data, setData] = useState<Page<Grant> | null>(null);
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [searchError, setSearchError] = useState("");
  const [doctor, setDoctor] = useState("");
  const [scope, setScope] = useState<Scope>("VISITS_ONLY");
  const [expiry, setExpiry] = useState("");
  const [confirm, setConfirm] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const inFlight = useRef(false);
  useEffect(() => { let active = true;
    void listGrants(page).then(value => { if (active) { setData(value); setError(""); } }, () => { if (active) setError("Unable to load access grants."); });
    return () => { active = false; };
  }, [page, version]);
  useEffect(() => { let active = true;
    const timer = setTimeout(() => { void findDoctors(search).then(value => { if (active) { setDoctors(value); setSearchError(""); } }, () => { if (active) { setDoctors([]); setSearchError("Unable to search doctors. Please try again."); } }); }, search.trim() ? 250 : 0);
    return () => { active = false; clearTimeout(timer); };
  }, [search, version]);
  async function mutate(id: string) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(""); setNotice("");
    try {
      if (id === "create") await createGrant({ professional_role_registration_id: doctor, access_scope: scope, expires_at: expiry ? new Date(expiry).toISOString() : null });
      else await revokeGrant(id);
      setNotice(id === "create" ? "Access granted. You can revoke it at any time." : "Access revoked.");
      setConfirm(null); setVersion(v => v + 1);
      if (id === "create") { setDoctor(""); setExpiry(""); }
    } catch { setError("Unable to save this change. Check that the doctor and expiry are valid, and that this grant does not already exist. Your selections have been kept."); }
    finally { inFlight.current = false; setBusy(false); }
  }
  return <div className="space-y-8">
    <form className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5" onSubmit={event => { event.preventDefault(); setConfirm("create"); }}>
      <h2 className="text-xl font-bold">Share with a doctor</h2>
      <p className="text-sm text-slate-600">Sharing allows reading the selected records. It does not allow changes to your records. Revoking a grant ends access through that grant; an active consultation can still allow access.</p>
      <label className="block">Search verified doctors<input className={field} value={search} disabled={busy} onChange={event => { setSearch(event.target.value); setDoctor(""); }} /></label>
      {searchError && <ErrorState message={searchError} onAction={() => setVersion(v => v + 1)} />}
      <label className="block">Doctor<select className={field} required value={doctor} disabled={busy} onChange={event => setDoctor(event.target.value)}><option value="">Select a verified doctor</option>{doctors.map(value => <option key={value.id} value={value.id}>{value.name} · {value.designation || "Doctor"} · {value.facility_name || "Independent practice"}</option>)}</select></label>
      <label className="block">Records to share<select className={field} value={scope} disabled={busy} onChange={event => setScope(event.target.value as Scope)}>{Object.entries(scopes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="block">Expiry (optional, your local time)<input className={field} type="datetime-local" value={expiry} disabled={busy} onChange={event => setExpiry(event.target.value)} /></label>
      <p className="text-sm text-slate-600">Without an expiry, access continues until you revoke it.</p>
      <button className={button} disabled={busy || !doctor}>Review sharing</button>
    </form>
    {confirm && <section role="alertdialog" aria-modal="false" aria-labelledby="grant-confirm-title" className="rounded-2xl border border-amber-300 bg-amber-50 p-5">
      <h2 id="grant-confirm-title" className="font-bold">{confirm === "create" ? "Confirm access grant" : "Revoke this access grant?"}</h2>
      <p className="my-3">{confirm === "create" ? `${doctors.find(value => value.id === doctor)?.name || "Selected doctor"} will be able to read: ${scopes[scope]}. ${expiry ? `Expires ${new Date(expiry).toLocaleString()}.` : "No expiry."}` : "The doctor will no longer be able to read records using this grant."}</p>
      <div className="flex gap-3"><button className={button} disabled={busy} onClick={() => void mutate(confirm)}>{busy ? "Saving…" : "Confirm"}</button><button disabled={busy} onClick={() => setConfirm(null)}>Cancel</button></div>
    </section>}
    {error && <ErrorState message={error} onAction={() => setVersion(v => v + 1)} />}
    {notice && <p role="status" className="rounded-xl bg-emerald-50 p-4 text-emerald-900">{notice}</p>}
    <section className="space-y-3"><h2 className="text-xl font-bold">Your access grants</h2>
      {!data && !error ? <LoadingState label="Loading access grants" /> : data?.grants.length === 0 ? <EmptyState title="No access grants" message="Share selected records with a verified doctor when needed." /> : data?.grants.map(grant => <article className="rounded-xl border border-slate-200 p-4" key={grant.id}>
        <h3 className="font-bold">{grant.professional_name}</h3><p>{scopes[grant.access_scope]}</p><p className="text-sm">{grant.active ? "Active" : grant.revoked_at ? "Revoked" : "Expired"} · {grant.expires_at ? `Expires ${new Date(grant.expires_at).toLocaleString()}` : "No expiry"}</p>
        {grant.active && <button className="mt-3 font-semibold text-red-700" disabled={busy} onClick={() => setConfirm(grant.id)}>Revoke access</button>}
      </article>)}
      <div className="flex items-center gap-4"><button disabled={page === 1 || busy} onClick={() => { setData(null); setPage(p => p - 1); }}>Previous</button><span>Page {page}</span><button disabled={!data?.has_next || busy} onClick={() => { setData(null); setPage(p => p + 1); }}>Next</button></div>
    </section>
  </div>;
}

export function AccessGrantsPage() {
  return <main id="main-content" className="mx-auto w-full max-w-4xl px-5 py-10"><h1 className="mb-6 text-3xl font-bold">Medical record sharing</h1><AccessSession portal="CITIZEN"><GrantManager /></AccessSession></main>;
}
