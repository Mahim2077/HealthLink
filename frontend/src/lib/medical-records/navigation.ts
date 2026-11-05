import type { MedicalHistoryQuery } from "./types";

const historyPath = "/citizen/medical-history";
const fallbackPath = "/citizen/appointments";
const localOrigin = "https://healthlink.invalid";

function dateValue(value: string | null): string | undefined {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().startsWith(value) ? value : undefined;
}

export function historyQueryFromSearch(params: Pick<URLSearchParams, "get">): MedicalHistoryQuery {
  const type = params.get("resource_type");
  const page = params.get("page");
  const from = dateValue(params.get("date_from"));
  const to = dateValue(params.get("date_to"));
  return {
    ...(type === "VISIT" || type === "PRESCRIPTION" ? { resource_type: type } : {}),
    ...(from ? { date_from: from } : {}),
    ...(to && (!from || to >= from) ? { date_to: to } : {}),
    page: page && /^[1-9]\d{0,3}$/.test(page) && Number(page) <= 1000 ? Number(page) : 1,
    page_size: 10,
  };
}

export function citizenHistoryPath(query: MedicalHistoryQuery): string {
  const params = new URLSearchParams();
  if (query.resource_type) params.set("resource_type", query.resource_type);
  if (query.date_from) params.set("date_from", query.date_from);
  if (query.date_to) params.set("date_to", query.date_to);
  if (query.page && query.page > 1) params.set("page", String(query.page));
  const search = params.toString();
  return search ? `${historyPath}?${search}` : historyPath;
}

/** Only a known local history entry point may override the direct-link fallback. */
export function citizenPrescriptionBackPath(returnTo?: string): string {
  if (!returnTo?.startsWith("/")) return fallbackPath;
  try {
    const url = new URL(returnTo, localOrigin);
    if (url.origin !== localOrigin || url.pathname !== historyPath) return fallbackPath;
    return citizenHistoryPath(historyQueryFromSearch(url.searchParams));
  } catch {
    return fallbackPath;
  }
}
