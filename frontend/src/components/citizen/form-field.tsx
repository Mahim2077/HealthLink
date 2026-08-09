import type { ReactNode } from "react";

export const citizenInputClassName =
  "min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3.5 text-sm text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-teal-600 focus:ring-4 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

export function FormField({
  children,
  className,
  error,
  hint,
  htmlFor,
  label,
  required,
}: {
  children: ReactNode;
  className?: string;
  error?: string;
  hint?: string;
  htmlFor: string;
  label: string;
  required?: boolean;
}) {
  return (
    <div className={className}>
      <label className="text-sm font-semibold text-slate-800" htmlFor={htmlFor}>
        {label}
        {required ? (
          <>
            <span aria-hidden="true" className="ml-1 text-rose-600">*</span>
            <span className="sr-only"> (required)</span>
          </>
        ) : null}
      </label>
      <div className="mt-2">{children}</div>
      {error ? (
        <p className="mt-1.5 text-xs font-medium text-rose-700" id={htmlFor + "-error"}>
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-xs leading-5 text-slate-500" id={htmlFor + "-hint"}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
