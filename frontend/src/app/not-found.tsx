import Link from "next/link";

import { EmptyState } from "@/components/ui/async-state";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-slate-50">
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
            href="/"
          >
            Return home
          </Link>
        }
        message="The address may be incomplete or the page may have moved."
        title="Page not found"
      />
    </main>
  );
}
