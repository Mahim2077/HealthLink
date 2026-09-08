"use client";

import { useEffect } from "react";

let activeWarnings = 0;
const beforeUnload = (event: BeforeUnloadEvent) => {
  event.preventDefault();
  event.returnValue = "";
};
const navigate = (event: MouseEvent) => {
  if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  const target = event.target;
  if (!(target instanceof Element)) return;
  const anchor = target.closest<HTMLAnchorElement>("a[href]");
  if (!anchor || anchor.hasAttribute("download") || anchor.target === "_blank") return;
  const href = anchor.getAttribute("href");
  if (!href || href.startsWith("#") || anchor.href === window.location.href) return;
  if (!window.confirm("You have unsaved changes. Leave this page and discard them?")) {
    event.preventDefault();
    event.stopPropagation();
  }
};

/** Warn before leaving; never persist identity or clinical drafts in browser storage. */
export function useUnsavedChanges(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    if (activeWarnings++ === 0) {
      window.addEventListener("beforeunload", beforeUnload);
      document.addEventListener("click", navigate, true);
    }
    return () => {
      if (--activeWarnings === 0) {
        window.removeEventListener("beforeunload", beforeUnload);
        document.removeEventListener("click", navigate, true);
      }
    };
  }, [dirty]);
}
