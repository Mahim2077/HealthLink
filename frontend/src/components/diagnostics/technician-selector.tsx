"use client";

import { useEffect, useState } from "react";
import { listDiagnosticTechnicians } from "@/lib/diagnostics/api";
import type { TechnicianChoice } from "@/lib/diagnostics/types";

export function TechnicianSelector({ value, onChange, disabled, testId, visitId }: {
  value: string; onChange: (value: string) => void; disabled?: boolean;
  testId?: string; visitId?: string;
}) {
  const [search, setSearch] = useState("");
  const [choices, setChoices] = useState<TechnicianChoice[]>([]);
  const [error, setError] = useState(false);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => {
      void listDiagnosticTechnicians(search, { test_id: testId, visit_id: visitId }).then(
        result => { if (active) { setChoices(result); setError(false); } },
        () => { if (active) setError(true); },
      );
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [search, testId, visitId, version]);
  return <div className="space-y-2">
    <label className="block text-sm font-semibold text-slate-700">Search lab technicians
      <input type="search" maxLength={100} value={search} disabled={disabled}
        onChange={event => { setSearch(event.target.value); onChange(""); }}
        className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3" />
    </label>
    <label className="block text-sm font-semibold text-slate-700">Lab technician
      <select value={value} onChange={event => onChange(event.target.value)} disabled={disabled || error}
        className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3">
        <option value="">Leave unassigned</option>
        {choices.map(item => <option key={item.role_registration_id} value={item.role_registration_id}>{item.full_name} · {item.designation} · {item.facility_name}</option>)}
      </select>
    </label>
    {error ? <p role="alert" className="text-sm text-rose-700">Technician search failed. <button type="button" onClick={() => setVersion(v => v + 1)} className="underline">Retry search</button></p> : <p className="text-xs text-slate-500">Verified technicians at this facility. Refine your search if needed.</p>}
  </div>;
}
