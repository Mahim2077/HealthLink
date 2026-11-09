import { isApiError } from "@/lib/api/errors";

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
