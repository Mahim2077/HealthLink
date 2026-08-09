import { isApiError } from "@/lib/api/errors";

export function maskIdentityValue(value: string | null): string {
  if (!value) {
    return "Not available";
  }

  if (value.length <= 4) {
    return "•".repeat(Math.max(4, value.length));
  }

  const visibleSuffix = value.slice(-4);
  const maskedLength = Math.max(4, Math.min(value.length - 4, 8));

  return "•".repeat(maskedLength) + " " + visibleSuffix;
}

export function citizenErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (isApiError(error) && error.message.trim().length > 0) {
    return error.message;
  }

  return fallback;
}

export function formatCitizenDate(value: string): string {
  const parsed = new Date(value + (value.includes("T") ? "" : "T00:00:00"));

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-BD", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(parsed);
}
