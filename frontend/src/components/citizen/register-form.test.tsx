import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";
import type {
  CitizenRegistrationRequest,
  CitizenRegistrationResponse,
} from "@/lib/citizen/types";

import {
  CitizenRegisterForm,
  localCalendarDate,
  validateCitizenRegistration,
} from "./register-form";

const navigationMocks = vi.hoisted(() => ({
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navigationMocks.replace }),
}));

const registrationResponse: CitizenRegistrationResponse = {
  citizen_id: "citizen-1",
  created_at: "2026-08-10T08:00:00Z",
  email: "amina@example.com",
  first_name: "Amina",
  last_name: "Rahman",
  registered_with: "NID",
  user_id: "user-1",
};

function fillRequiredFields(
  identityNumber = "00A-19/BD",
  identityKind: "NID" | "BCN" = "NID",
) {
  fireEvent.change(
    screen.getByRole("textbox", {
      name:
        identityKind === "NID"
          ? /^National ID/i
          : /^Birth Certificate Number/i,
    }),
    {
    target: { value: identityNumber },
    },
  );
  fireEvent.change(screen.getByLabelText(/First name/i), {
    target: { value: " Amina " },
  });
  fireEvent.change(screen.getByLabelText(/Last name/i), {
    target: { value: " Rahman " },
  });
  fireEvent.change(screen.getByLabelText(/Date of birth/i), {
    target: { value: "1992-05-14" },
  });
  fireEvent.change(screen.getByLabelText(/Gender/i), {
    target: { value: "FEMALE" },
  });
  fireEvent.change(screen.getByLabelText(/Email address/i), {
    target: { value: " AMINA@EXAMPLE.COM " },
  });
  fireEvent.change(screen.getByLabelText(/^Password/i), {
    target: { value: "strong-password" },
  });
  fireEvent.change(screen.getByLabelText(/Confirm password/i), {
    target: { value: "strong-password" },
  });
}

describe("CitizenRegisterForm", () => {
  beforeEach(() => {
    navigationMocks.replace.mockReset();
  });

  it("submits an opaque NID as the only identity and routes to sign in", async () => {
    const registerAction = vi
      .fn<(request: CitizenRegistrationRequest) => Promise<CitizenRegistrationResponse>>()
      .mockResolvedValue(registrationResponse);

    render(<CitizenRegisterForm registerAction={registerAction} />);
    fillRequiredFields("00A-19/BD");
    fireEvent.click(screen.getByRole("button", { name: "Create citizen account" }));

    await waitFor(() => expect(registerAction).toHaveBeenCalledOnce());
    expect(registerAction).toHaveBeenCalledWith({
      address: null,
      blood_group: null,
      date_of_birth: "1992-05-14",
      email: "amina@example.com",
      first_name: "Amina",
      gender: "FEMALE",
      last_name: "Rahman",
      nid_number: "00A-19/BD",
      password: "strong-password",
    });
    expect(registerAction.mock.calls[0][0]).not.toHaveProperty(
      "birth_certificate_number",
    );
    expect(navigationMocks.replace).toHaveBeenCalledWith(
      "/citizen/login?registered=1",
    );
  });

  it("clears the prior value when switching and submits only the BCN", async () => {
    const registerAction = vi
      .fn<(request: CitizenRegistrationRequest) => Promise<CitizenRegistrationResponse>>()
      .mockResolvedValue({ ...registrationResponse, registered_with: "BCN" });

    render(<CitizenRegisterForm registerAction={registerAction} />);
    fireEvent.change(
      screen.getByRole("textbox", { name: /^National ID/i }),
      {
      target: { value: "old-nid" },
      },
    );
    fireEvent.click(
      screen.getByRole("radio", { name: /Birth Certificate Number/i }),
    );

    const bcnInput = screen.getByRole("textbox", {
      name: /^Birth Certificate Number/i,
    });
    expect(bcnInput).toHaveValue("");
    expect(bcnInput).toHaveAttribute("maxlength", "64");

    fillRequiredFields("BC-00/alpha", "BCN");
    fireEvent.click(screen.getByRole("button", { name: "Create citizen account" }));

    await waitFor(() => expect(registerAction).toHaveBeenCalledOnce());
    const request = registerAction.mock.calls[0][0];
    expect(request.birth_certificate_number).toBe("BC-00/alpha");
    expect(request).not.toHaveProperty("nid_number");
  });

  it("shows client errors without submitting and exposes documented limits", () => {
    const registerAction = vi.fn();
    render(<CitizenRegisterForm registerAction={registerAction} />);

    expect(
      screen.getByRole("textbox", { name: /^National ID/i }),
    ).toHaveAttribute(
      "maxlength",
      "32",
    );
    expect(screen.getByLabelText(/^Password/i)).toHaveAttribute(
      "maxlength",
      "128",
    );
    expect(screen.getByLabelText(/Confirm password/i)).toHaveAttribute(
      "maxlength",
      "128",
    );

    fireEvent.click(screen.getByRole("button", { name: "Create citizen account" }));

    expect(screen.getByText("National ID is required.")).toBeInTheDocument();
    expect(screen.getByText("Date of birth is required.")).toBeInTheDocument();
    expect(registerAction).not.toHaveBeenCalled();
  });

  it("surfaces a duplicate-account conflict returned by the API", async () => {
    const registerAction = vi
      .fn()
      .mockRejectedValue(
        new ApiError(409, "A citizen account already uses this email."),
      );
    render(<CitizenRegisterForm registerAction={registerAction} />);
    fillRequiredFields();

    fireEvent.click(screen.getByRole("button", { name: "Create citizen account" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("A citizen account already uses this email.");
    expect(navigationMocks.replace).not.toHaveBeenCalled();
  });
});

describe("citizen registration validation", () => {
  it("uses the local calendar date rather than a UTC date boundary", () => {
    const localEarlyMorning = new Date(2026, 7, 10, 0, 15, 0);

    expect(localCalendarDate(localEarlyMorning)).toBe("2026-08-10");
  });

  it("enforces only nonblank and documented identity maximum lengths", () => {
    const baseValues = {
      address: "",
      bloodGroup: "",
      confirmPassword: "12345678",
      dateOfBirth: "1990-01-01",
      email: "person@example.com",
      firstName: "Amina",
      gender: "FEMALE",
      identityKind: "NID" as const,
      identityNumber: "A".repeat(33),
      lastName: "Rahman",
      password: "12345678",
    };

    expect(validateCitizenRegistration(baseValues).identityNumber).toBe(
      "NID cannot exceed 32 characters.",
    );
    expect(
      validateCitizenRegistration({
        ...baseValues,
        identityKind: "BCN",
        identityNumber: "A".repeat(65),
      }).identityNumber,
    ).toBe("Birth Certificate Number cannot exceed 64 characters.");
    expect(
      validateCitizenRegistration({
        ...baseValues,
        identityNumber: "00-opaque/value",
      }).identityNumber,
    ).toBeUndefined();
  });
});
