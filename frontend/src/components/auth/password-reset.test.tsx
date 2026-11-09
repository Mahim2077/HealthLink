import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { PasswordReset } from "./password-reset";

const mocks = vi.hoisted(() => ({ request: vi.fn(), verify: vi.fn(), save: vi.fn() }));
vi.mock("@/lib/auth/email-codes", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/auth/email-codes")>(),
  requestResetCode: mocks.request,
  verifyResetCode: mocks.verify,
  completePasswordReset: mocks.save,
}));

beforeEach(() => {
  vi.resetAllMocks();
  mocks.request.mockResolvedValue({ challenge_id: "test-challenge", resend_after_seconds: 60 });
  mocks.verify.mockResolvedValue({ reset_token: "test-reset-grant" });
  mocks.save.mockResolvedValue(undefined);
});

function change(label: RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

it("recovers a professional account by NID and role and handles an incorrect code", async () => {
  mocks.verify.mockRejectedValueOnce(new ApiError(400, "Invalid or expired code."));
  render(<PasswordReset portal="PROFESSIONAL" />);
  change(/National ID/, "test-nid");
  change(/Professional role/, "NURSE");
  fireEvent.click(screen.getByRole("button", { name: "Send reset code" }));
  expect(await screen.findByRole("heading", { name: "Check your email" })).toBeInTheDocument();
  expect(mocks.request).toHaveBeenCalledWith({ portal: "PROFESSIONAL", nid_number: "test-nid", role_code: "NURSE" });
  expect(screen.getByRole("button", { name: /Resend in/ })).toBeDisabled();

  change(/Six-digit code/, "123456");
  fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid or expired code.");
  change(/Six-digit code/, "654321");
  fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
  expect(await screen.findByRole("heading", { name: "Create a new password" })).toBeInTheDocument();
  expect(mocks.verify).toHaveBeenLastCalledWith({ challenge_id: "test-challenge", code: "654321" });

  change(/^New password/, "Newpass!");
  change(/Confirm new password/, "Newpass!");
  fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
  expect(screen.getByRole("alert")).toHaveTextContent("including an uppercase letter");
  expect(mocks.save).not.toHaveBeenCalled();
  change(/^New password/, "NewPass1!");
  change(/Confirm new password/, "NewPass1!");
  fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
  expect(await screen.findByRole("heading", { name: "Password updated" })).toBeInTheDocument();
  expect(mocks.save).toHaveBeenCalledWith("test-challenge", "test-reset-grant", "NewPass1!");
  expect(screen.getByRole("link", { name: "Return to sign-in" })).toHaveAttribute("href", "/professional/login");
});

it.each(["CITIZEN", "ADMIN"] as const)("requests %s recovery by email with a neutral response", async (portal) => {
  render(<PasswordReset portal={portal} />);
  change(/Email address/, "qa@example.com");
  fireEvent.click(screen.getByRole("button", { name: "Send reset code" }));
  expect(await screen.findByText(/If the details match an eligible account/)).toBeInTheDocument();
  expect(mocks.request).toHaveBeenCalledWith({ portal, email: "qa@example.com" });
  expect(screen.queryByText("qa@example.com")).not.toBeInTheDocument();
});
