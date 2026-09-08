"use client";

import { useState, type ComponentProps } from "react";

export function PasswordInput(props: Omit<ComponentProps<"input">, "type">) {
  const [visible, setVisible] = useState(false);
  return <div className="relative">
    <input {...props} className={`${props.className ?? ""} pr-20`} type={visible ? "text" : "password"} />
    <button type="button" aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} disabled={props.disabled} onClick={() => setVisible(value => !value)} className="absolute inset-y-0 right-2 my-auto min-h-11 rounded-lg px-2 text-xs font-bold text-slate-600 hover:text-slate-950">{visible ? "Hide" : "Show"}</button>
  </div>;
}
