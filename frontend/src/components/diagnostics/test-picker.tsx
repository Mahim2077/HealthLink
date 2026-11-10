"use client";

import { useEffect, useRef, useState } from "react";
import { getTestCatalog, type TestChoice } from "@/lib/diagnostics/session-api";

export function TestPicker({ value, onChange, search, onSearchChange }: {
  value: TestChoice | null;
  onChange: (value: TestChoice | null) => void;
  search?: string;
  onSearchChange?: (value: string) => void;
}) {
  const [catalog, setCatalog] = useState<TestChoice[]>([]);
  const [localQuery, setLocalQuery] = useState("");
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const change = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const query = search ?? localQuery;
  const setQuery = onSearchChange ?? setLocalQuery;
  useEffect(() => {
    let active = true;
    void getTestCatalog().then(items => { if (active) setCatalog(items); }, () => { if (active) setError(true); });
    return () => { active = false; };
  }, [attempt]);
  useEffect(() => {
    if (!restoreFocus.current) return;
    restoreFocus.current = false;
    (value ? change.current : input.current)?.focus();
  }, [value]);
  const matches = catalog.filter(item => [item.name, ...item.aliases].some(name => name.toLowerCase().includes(query.trim().toLowerCase())));
  if (value) return <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3">
    <span className="font-semibold">{value.name}</span>
    <button ref={change} type="button" className="min-h-11 px-3 text-sm font-semibold text-sky-800" onClick={() => {
      restoreFocus.current = true;
      onChange(null);
      setQuery("");
      setEditing(true);
    }}>Change test</button>
  </div>;
  return <div className="space-y-2">
    <label className="block text-sm font-semibold">Test name
      <input ref={input} type="search" className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3"
        placeholder="Search the test catalog" value={query} onFocus={() => setEditing(true)} onChange={event => { setQuery(event.target.value); setEditing(true); }} />
    </label>
    {error ? <button type="button" className="min-h-11 text-sm underline" onClick={() => { setError(false); setAttempt(n => n + 1); }}>Test catalog unavailable. Retry</button> : null}
    {editing && !error && (catalog.length === 0 ? <p role="status" className="text-sm">Loading test catalog…</p> : matches.length === 0 ? <p role="status" className="text-sm">No matching tests.</p> :
      <ul aria-label="Matching tests" className="max-h-60 overflow-auto rounded-xl border border-slate-200 bg-white">
        {matches.map(item => <li key={item.code}><button type="button" className="min-h-11 w-full px-3 text-left text-sm hover:bg-slate-100"
          onClick={() => { restoreFocus.current = true; onChange(item); setQuery(""); setEditing(false); }}>{item.name}</button></li>)}
      </ul>)}
  </div>;
}
