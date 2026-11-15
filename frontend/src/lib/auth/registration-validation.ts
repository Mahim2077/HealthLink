import { isApiError } from "@/lib/api/errors";

export const registrationGenders = [
  { value: "MALE", label: "Male" },
  { value: "FEMALE", label: "Female" },
  { value: "OTHER", label: "Other" },
  { value: "PREFER_NOT_TO_SAY", label: "Prefer not to say" },
] as const;

export function localCalendarDate(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return year + "-" + month + "-" + day;
}

export const registrationPasswordHint =
  "Use 8–128 characters, including an uppercase letter, a lowercase letter, a number, and a symbol.";

export function registrationPasswordError(password: string): string | undefined {
  if (
    password.length < 8 ||
    password.length > 128 ||
    !/\p{Lu}/u.test(password) ||
    !/\p{Ll}/u.test(password) ||
    !/\p{Nd}/u.test(password) ||
    !/[^\p{L}\p{N}\p{M}\s]/u.test(password)
  ) {
    return registrationPasswordHint;
  }
}

export function registrationErrorMessage(error: unknown, fallback: string): string {
  if (!isApiError(error) || error.status >= 500) return fallback;
  const message = error.message.trim();
  if (error.status === 409 && (!message || message === "Conflict" || message === "The HealthLink request could not be completed.")) {
    return "Account already exists. Sign in to continue.";
  }
  return message || fallback;
}
