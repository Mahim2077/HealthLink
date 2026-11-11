"use client";

import { BellIcon } from "@heroicons/react/24/outline";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import type { Portal } from "@/lib/auth/types";
import { syncInbox } from "@/lib/reminders/api";

export const inboxCountEvent = "healthlink:inbox-count";
export type InboxCount = { sessionId?: string; count: number };

export function InboxLink({ portal, sessionId }: { portal: Portal; sessionId?: string }) {
  const [count, setCount] = useState(0);
  const href = `/${portal.toLowerCase()}/inbox`;
  const isInbox = usePathname() === href;

  useEffect(() => {
    let active = true;
    let loading = false;
    let revision = 0;
    async function refresh() {
      if (loading || document.visibilityState === "hidden") return;
      const requestRevision = revision;
      loading = true;
      try {
        const result = await syncInbox();
        if (active && revision === requestRevision) {
          window.dispatchEvent(new CustomEvent<InboxCount>(inboxCountEvent, {
            detail: { sessionId, count: result.unread_count },
          }));
        }
      } catch {
        // Keep the last known count. The inbox can retry and display API errors.
      } finally {
        loading = false;
      }
    }
    function update(event: Event) {
      const detail = (event as CustomEvent<InboxCount>).detail;
      if (detail.sessionId === sessionId) {
        revision += 1;
        setCount(detail.count);
      }
    }
    if (!isInbox) void refresh();
    const timer = window.setInterval(refresh, 60_000);
    document.addEventListener("visibilitychange", refresh);
    window.addEventListener(inboxCountEvent, update);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
      window.removeEventListener(inboxCountEvent, update);
    };
  }, [isInbox, sessionId]);

  return (
    <Link
      aria-current={isInbox ? "page" : undefined}
      aria-label={count ? `Inbox, ${count} unread` : "Inbox"}
      className="relative flex size-11 shrink-0 items-center justify-center rounded-xl text-[var(--portal-strong)] hover:bg-[var(--portal-soft)] focus-visible:outline-2 focus-visible:outline-[var(--portal-accent)]"
      href={href}
      title="Inbox"
    >
      <BellIcon aria-hidden="true" className="size-6" />
      {count > 0 ? (
        <span aria-hidden="true" className="absolute right-0 top-0 min-w-4 rounded-full bg-[var(--portal-accent)] px-1 text-center text-[0.65rem] font-bold leading-4 text-white">
          {count > 99 ? "99+" : count}
        </span>
      ) : null}
    </Link>
  );
}
