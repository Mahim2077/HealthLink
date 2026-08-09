import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import { AdminLoginForm } from "./admin-login-form";

const mocks = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));

describe("AdminLoginForm", () => {
  beforeEach(() => mocks.replace.mockReset());

  it("submits trusted credentials and enters the admin dashboard", async () => {
    const loginAction = vi.fn().mockResolvedValue({ access_token: "token", portal: "ADMIN" });
    render(<AdminLoginForm loginAction={loginAction} />);
    fireEvent.change(screen.getByLabelText(/Email address/), { target: { value: " admin@example.com " } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in to Admin Portal" }));
    await waitFor(() => expect(loginAction).toHaveBeenCalledWith({ email: "admin@example.com", password: "secret" }));
    expect(mocks.replace).toHaveBeenCalledWith("/admin/dashboard");
  });

  it("shows the generic backend credential error and has no registration link", async () => {
    const loginAction = vi.fn().mockRejectedValue(new ApiError(401, "Invalid email or password."));
    render(<AdminLoginForm loginAction={loginAction} />);
    fireEvent.change(screen.getByLabelText(/Email address/), { target: { value: "normal@example.com" } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in to Admin Portal" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(screen.queryByRole("link", { name: /register/i })).not.toBeInTheDocument();
  });
});
