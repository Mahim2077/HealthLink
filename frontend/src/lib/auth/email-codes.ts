import { apiClient } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { Portal } from "@/lib/auth/types";
import type { ProfessionalRoleCode } from "@/lib/professional/types";

export type EmailChallenge = { challenge_id: string; resend_after_seconds: number };
export type EmailCodeProof = { challenge_id: string; code: string };
export type ResetIdentity =
  | { portal: "CITIZEN" | "ADMIN"; email: string }
  | { portal: "PROFESSIONAL"; nid_number: string; role_code: ProfessionalRoleCode };

const publicRequest = { auth: false, retryOnUnauthorized: false };

export function requiresEmailVerification(error: unknown): boolean {
  return isApiError(error) && error.status === 428;
}

export function emailActionError(error: unknown, fallback: string): string {
  return isApiError(error) && (error.status < 500 || error.status === 503) ? error.message : fallback;
}

export function requestSignupCode(portal: Exclude<Portal, "ADMIN">, email: string) {
  return apiClient.post<EmailChallenge, { portal: typeof portal; email: string }>("auth/email/signup", { portal, email }, publicRequest);
}

export function requestResetCode(identity: ResetIdentity) {
  return apiClient.post<EmailChallenge, ResetIdentity>("auth/email/reset", identity, publicRequest);
}

export function verifyResetCode(proof: EmailCodeProof) {
  return apiClient.post<{ reset_token: string }, EmailCodeProof>("auth/email/reset/verify", proof, publicRequest);
}

export function completePasswordReset(challenge_id: string, reset_token: string, password: string) {
  return apiClient.post<void, { challenge_id: string; reset_token: string; password: string }>(
    "auth/email/reset/complete", { challenge_id, reset_token, password }, publicRequest,
  );
}

export function loadRecoveryEmail() {
  return apiClient.get<{ enabled: boolean; verified: boolean; email: string }>("auth/email/status", { auth: true });
}

export function requestEnrollmentCode(password: string) {
  return apiClient.post<EmailChallenge, { password: string }>("auth/email/enroll", { password }, { auth: true });
}

export function verifyEnrollmentCode(proof: EmailCodeProof) {
  return apiClient.post<void, EmailCodeProof>("auth/email/enroll/verify", proof, { auth: true });
}
