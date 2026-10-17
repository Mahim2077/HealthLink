import { InformationCircleIcon } from "@heroicons/react/24/outline";

export function AiDisclaimer({ children }: { children: string }) {
  return (
    <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
      <InformationCircleIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
      <p>{children}</p>
    </div>
  );
}
