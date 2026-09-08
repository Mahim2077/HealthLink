import type { Portal } from "./types";

/** Allow only internal, same-portal destinations; never accept an external redirect. */
export function safeReturnTo(value: string | null | undefined, portal: Portal): string {
  const prefix = `/${portal.toLowerCase()}/`;
  const fallback = `${prefix}dashboard`;
  if (!value || !value.startsWith(prefix) || /[\\\u0000-\u001f]/.test(value)) return fallback;
  try {
    const url = new URL(value, "https://healthlink.invalid");
    if (url.origin !== "https://healthlink.invalid" || !url.pathname.startsWith(prefix) || /%2f|%5c/i.test(url.pathname)) return fallback;
    if (["login", "register", "onboard"].includes(url.pathname.slice(prefix.length).split("/")[0])) return fallback;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch { return fallback; }
}
