import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ login: vi.fn(), replace: vi.fn() }));
vi.mock("@/lib/professional/api", () => ({ loginProfessional: mocks.login }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));

import { ProfessionalLoginForm } from "./professional-login-form";

describe("ProfessionalLoginForm", () => {
  beforeEach(() => { mocks.login.mockReset(); mocks.replace.mockReset(); });
  it("submits NID, password, and selected role then routes verified sessions", async () => {
    mocks.login.mockResolvedValue({ verification_status: "VERIFIED" }); render(<ProfessionalLoginForm />);
    fireEvent.change(screen.getByLabelText("National ID"), { target: { value: " NID-1 " } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.change(screen.getByLabelText("Professional role"), { target: { value: "LAB_TECHNICIAN" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in to Professional Portal" }));
    await waitFor(() => expect(mocks.login).toHaveBeenCalledWith({ nid_number: "NID-1", password: "secret", role_code: "LAB_TECHNICIAN" }));
    expect(mocks.replace).toHaveBeenCalledWith("/professional/dashboard");
  });
  it("routes pending and rejected sessions to status", async () => {
    mocks.login.mockResolvedValue({ verification_status: "PENDING" }); render(<ProfessionalLoginForm />);
    fireEvent.change(screen.getByLabelText("National ID"), { target: { value: "NID-2" } }); fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in to Professional Portal" }));
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/professional/status"));
  });
});
