import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import type { CitizenLoginResponse } from "@/lib/citizen/types";

import { CitizenLoginForm } from "./login-form";

const navigationMocks = vi.hoisted(() => ({
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navigationMocks.replace }),
}));

const loginResponse: CitizenLoginResponse = {
  access_token: "citizen-access-token",
  expires_in: 1800,
  portal: "CITIZEN",
  token_type: "bearer",
};

function fillLogin() {
  fireEvent.change(screen.getByLabelText(/Email address/i), {
    target: { value: " CITIZEN@EXAMPLE.COM " },
  });
  fireEvent.change(screen.getByLabelText(/Password/i), {
    target: { value: "secret-password" },
  });
}

describe("CitizenLoginForm", () => {
  beforeEach(() => {
    navigationMocks.replace.mockReset();
  });

  it("shows registration success, signs in, and opens the dashboard", async () => {
    const loginAction = vi.fn().mockResolvedValue(loginResponse);
    render(
      <CitizenLoginForm
        loginAction={loginAction}
        registrationComplete
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      "Your citizen account is ready",
    );
    fillLogin();
    fireEvent.click(
      screen.getByRole("button", { name: "Sign in to Citizen Portal" }),
    );

    await waitFor(() => expect(loginAction).toHaveBeenCalledOnce());
    expect(loginAction).toHaveBeenCalledWith({
      email: "citizen@example.com",
      password: "secret-password",
    });
    expect(navigationMocks.replace).toHaveBeenCalledWith(
      "/citizen/dashboard",
    );
  });

  it("does not call the API for an invalid form", () => {
    const loginAction = vi.fn();
    render(<CitizenLoginForm loginAction={loginAction} />);

    fireEvent.click(
      screen.getByRole("button", { name: "Sign in to Citizen Portal" }),
    );

    expect(screen.getByText("Enter your account email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(loginAction).not.toHaveBeenCalled();
  });

  it("mirrors the documented password maximum", () => {
    const loginAction = vi.fn();
    render(<CitizenLoginForm loginAction={loginAction} />);
    const passwordInput = screen.getByLabelText(/Password/i);

    expect(passwordInput).toHaveAttribute("maxlength", "128");
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "citizen@example.com" },
    });
    fireEvent.change(passwordInput, { target: { value: "x".repeat(129) } });
    fireEvent.click(
      screen.getByRole("button", { name: "Sign in to Citizen Portal" }),
    );

    expect(
      screen.getByText("Password cannot exceed 128 characters."),
    ).toBeInTheDocument();
    expect(loginAction).not.toHaveBeenCalled();
  });

  it("shows an authentication error and restores the submit button", async () => {
    const loginAction = vi
      .fn()
      .mockRejectedValue(new ApiError(401, "Incorrect email or password."));
    render(<CitizenLoginForm loginAction={loginAction} />);
    fillLogin();

    fireEvent.click(
      screen.getByRole("button", { name: "Sign in to Citizen Portal" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Incorrect email or password.",
    );
    expect(
      screen.getByRole("button", { name: "Sign in to Citizen Portal" }),
    ).toBeEnabled();
    expect(navigationMocks.replace).not.toHaveBeenCalled();
  });
});
