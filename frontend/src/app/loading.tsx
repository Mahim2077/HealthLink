import { LoadingState } from "@/components/ui/async-state";

export default function Loading() {
  return (
    <main className="min-h-screen bg-slate-50">
      <LoadingState label="Opening HealthLink" />
    </main>
  );
}
