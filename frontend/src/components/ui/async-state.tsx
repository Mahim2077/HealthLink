import {
  ArchiveBoxIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import type { ReactNode } from "react";

type StateShellProps = {
  children: ReactNode;
  className?: string;
};

type LoadingStateProps = {
  label?: string;
  description?: string;
  className?: string;
};

type ErrorStateProps = {
  title?: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
};

type EmptyStateProps = {
  title: string;
  message: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
};

function StateShell({ children, className = "" }: StateShellProps) {
  return (
    <div
      className={
        "mx-auto flex min-h-[18rem] w-full max-w-3xl items-center justify-center px-6 py-12 " +
        className
      }
    >
      {children}
    </div>
  );
}

export function LoadingState({
  label = "Loading",
  description = "Preparing a secure HealthLink experience.",
  className,
}: LoadingStateProps) {
  return (
    <StateShell className={className}>
      <div
        aria-live="polite"
        className="flex max-w-md flex-col items-center text-center"
        role="status"
      >
        <span className="mb-6 flex size-12 items-center justify-center rounded-full bg-teal-50 text-teal-700 ring-1 ring-inset ring-teal-100">
          <ArrowPathIcon aria-hidden="true" className="size-6 animate-spin motion-reduce:animate-none" />
        </span>
        <p className="text-base font-semibold text-slate-950">{label}</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      </div>
    </StateShell>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  actionLabel = "Try again",
  onAction,
  className,
}: ErrorStateProps) {
  return (
    <StateShell className={className}>
      <div
        className="w-full max-w-lg rounded-2xl border border-rose-200 bg-white p-7 text-center shadow-[0_22px_60px_-34px_rgba(159,18,57,0.3)] sm:p-9"
        role="alert"
      >
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-rose-50 text-rose-700">
          <ExclamationTriangleIcon aria-hidden="true" className="size-6" />
        </span>
        <h2 className="mt-5 text-xl font-bold tracking-tight text-slate-950">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{message}</p>
        {onAction ? (
          <button
            className="mt-6 inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
            onClick={onAction}
            type="button"
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
    </StateShell>
  );
}

export function EmptyState({
  title,
  message,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <StateShell className={className}>
      <div className="w-full max-w-lg rounded-2xl border border-dashed border-slate-300 bg-white/85 p-8 text-center shadow-sm sm:p-10">
        <span className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-600">
          {icon ?? (
            <ArchiveBoxIcon aria-hidden="true" className="size-6" />
          )}
        </span>
        <h2 className="mt-5 text-xl font-bold tracking-tight text-slate-950">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{message}</p>
        {action ? <div className="mt-6">{action}</div> : null}
      </div>
    </StateShell>
  );
}
