"use client";

import { useEffect, useState } from "react";
import { LabPortalGate } from "./lab-report-page";
import { readDiagnosticPdf } from "@/lib/diagnostics/session-api";
import { ErrorState, LoadingState } from "@/components/ui/async-state";

export function DiagnosticPdfPreview({ id, version }: { id: string; version?: number }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | undefined;
    void readDiagnosticPdf(id, version, controller.signal).then(blob => {
      if (!controller.signal.aborted) {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      }
    }, reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Unable to load the diagnostic PDF.");
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id, version, attempt]);
  if (error) return <ErrorState message={error} onAction={() => { setError(""); setAttempt(value => value + 1); }} />;
  if (!url) return <LoadingState label="Loading diagnostic PDF" />;
  return <div className="space-y-2">
    <iframe src={url} title="Original diagnostic report PDF" className="h-[65vh] min-h-80 w-full rounded-xl border border-slate-300" />
    <a href={url} download="diagnostic-report.pdf" className="inline-flex min-h-11 items-center text-sm font-semibold text-sky-800 underline">Download PDF</a>
  </div>;
}

export function DiagnosticPdfPage({ id, portal }: { id: string; portal: "CITIZEN" | "PROFESSIONAL" }) {
  return <main id="main-content" className="mx-auto w-full max-w-5xl space-y-4 px-5 py-8">
    <h1 className="text-2xl font-bold">Diagnostic report</h1>
    <LabPortalGate portal={portal}><DiagnosticPdfPreview key={id} id={id} /></LabPortalGate>
  </main>;
}
