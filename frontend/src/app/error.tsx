"use client";

import { ErrorState } from "@/components/ui/async-state";

export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <main className="min-h-screen bg-slate-50">
      <ErrorState
        message="The page could not be prepared. Your information is safe; please try loading it again."
        onAction={reset}
        title="We could not open this page"
      />
    </main>
  );
}
