"use client";

import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useState, type ComponentProps } from "react";

type PasswordInputProps = Omit<ComponentProps<"input">, "type"> & {
  visibilityIcon?: boolean;
  visibilityTarget?: string;
};

export function PasswordInput({
  visibilityIcon = false,
  visibilityTarget = "password",
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const action = visible ? "Hide" : "Show";
  const label = action + " " + visibilityTarget;
  const Icon = visible ? EyeSlashIcon : EyeIcon;
  return <div className="relative">
    <input {...props} className={`${props.className ?? ""} ${visibilityIcon ? "pr-14" : "pr-20"}`} type={visible ? "text" : "password"} />
    <button
      type="button"
      aria-controls={props.id}
      aria-label={label}
      aria-pressed={visibilityIcon ? undefined : visible}
      className={`absolute inset-y-0 my-auto rounded-lg text-xs font-bold text-slate-600 hover:text-slate-950 focus-visible:outline-2 focus-visible:outline-[var(--portal-accent)] ${visibilityIcon ? "right-1 inline-flex size-11 items-center justify-center" : "right-2 min-h-11 px-2"}`}
      disabled={props.disabled}
      onClick={() => setVisible(value => !value)}
      title={visibilityIcon ? label : undefined}
    >
      {visibilityIcon ? <Icon aria-hidden="true" className="size-5" /> : action}
    </button>
  </div>;
}
