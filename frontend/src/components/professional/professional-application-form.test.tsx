import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";

import { ProfessionalApplicationForm } from "./professional-application-form";

const response = {
  professional_id: "professional-1",
  role_code: "DOCTOR" as const,
  role_registration_id: "registration-1",
  submitted_at: "2026-08-10T12:00:00Z",
  user_id: "user-1",
  verification_status: "PENDING" as const,
};

function fillRoleFields(role = "DOCTOR") {
  fireEvent.change(screen.getByLabelText(/Professional role/), { target: { value: role } });
  fireEvent.change(screen.getByLabelText(/Medical facility name/), { target: { value: " Dhaka Medical College " } });
  fireEvent.change(screen.getByLabelText(/Designation/), { target: { value: " Consultant " } });
  fireEvent.change(screen.getByLabelText(/Additional information/), { target: { value: " Experienced healthcare professional. " } });
  if (role === "DOCTOR") {
    fireEvent.change(screen.getByLabelText(/BM&DC Registration Number/), { target: { value: " BMDC-001 " } });
  }
}

function fillNewAccount() {
  fireEvent.change(screen.getByLabelText(/First name/), { target: { value: " Amina " } });
  fireEvent.change(screen.getByLabelText(/Last name/), { target: { value: " Rahman " } });
  fireEvent.change(screen.getByLabelText(/^National ID/), { target: { value: " 001-NID " } });
  fireEvent.change(screen.getByLabelText(/Email address/), { target: { value: " doctor@example.com " } });
  fireEvent.change(screen.getByLabelText(/^Password/), { target: { value: "StrongPassword123!" } });
  fireEvent.change(screen.getByLabelText(/Confirm password/), { target: { value: "StrongPassword123!" } });
}

describe("ProfessionalApplicationForm", () => {
  it("submits a complete doctor application with BM&DC and PENDING success", async () => {
    const registerAction = vi.fn().mockResolvedValue(response);
    render(<ProfessionalApplicationForm mode="new" registerAction={registerAction} />);
    fillNewAccount();
    fillRoleFields();
    fireEvent.click(screen.getByRole("button", { name: "Submit professional application" }));

    await waitFor(() => expect(registerAction).toHaveBeenCalledOnce());
    expect(registerAction).toHaveBeenCalledWith({
      additional_info: "Experienced healthcare professional.",
      bmdc_registration_number: "BMDC-001",
      designation: "Consultant",
      email: "doctor@example.com",
      facility_name: "Dhaka Medical College",
      first_name: "Amina",
      last_name: "Rahman",
      nid_number: "001-NID",
      password: "StrongPassword123!",
      role_code: "DOCTOR",
    });
    expect(await screen.findByRole("heading", { name: /application is pending/ })).toBeInTheDocument();
    expect(screen.getByText("PENDING")).toBeInTheDocument();
  });

  it("dynamically removes and clears BM&DC for a non-doctor role", async () => {
    const registerAction = vi.fn().mockResolvedValue({ ...response, role_code: "LAB_TECHNICIAN" });
    render(<ProfessionalApplicationForm mode="new" registerAction={registerAction} />);
    fillNewAccount();
    fillRoleFields();
    fireEvent.change(screen.getByLabelText(/Professional role/), { target: { value: "LAB_TECHNICIAN" } });
    expect(screen.queryByLabelText(/BM&DC Registration Number/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Submit professional application" }));

    await waitFor(() => expect(registerAction).toHaveBeenCalledOnce());
    expect(registerAction.mock.calls[0][0].role_code).toBe("LAB_TECHNICIAN");
    expect(registerAction.mock.calls[0][0]).not.toHaveProperty("bmdc_registration_number");
  });

  it("shows the existing-account onboarding conflict without losing the form", async () => {
    const registerAction = vi.fn().mockRejectedValue(
      new ApiError(409, "This NID belongs to an existing HealthLink account. Sign in and use professional onboarding."),
    );
    render(<ProfessionalApplicationForm mode="new" registerAction={registerAction} />);
    fillNewAccount();
    fillRoleFields();
    fireEvent.click(screen.getByRole("button", { name: "Submit professional application" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Sign in and use professional onboarding");
    expect(screen.getByRole("button", { name: "Submit professional application" })).toBeInTheDocument();
  });

  it("onboards without rendering or submitting duplicate account identity", async () => {
    const onboardAction = vi.fn().mockResolvedValue({ ...response, role_code: "NURSE" });
    render(<ProfessionalApplicationForm mode="onboard" onboardAction={onboardAction} />);
    expect(screen.queryByLabelText(/Email address/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^National ID/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Password/)).not.toBeInTheDocument();
    fillRoleFields("NURSE");
    fireEvent.click(screen.getByRole("button", { name: "Submit role for verification" }));

    await waitFor(() => expect(onboardAction).toHaveBeenCalledOnce());
    expect(onboardAction.mock.calls[0][0]).toEqual({
      additional_info: "Experienced healthcare professional.",
      designation: "Consultant",
      facility_name: "Dhaka Medical College",
      role_code: "NURSE",
    });
  });

  it("validates matching passwords and required doctor BM&DC before the API", () => {
    const registerAction = vi.fn();
    render(<ProfessionalApplicationForm mode="new" registerAction={registerAction} />);
    fillNewAccount();
    fireEvent.change(screen.getByLabelText(/Confirm password/), { target: { value: "different-password" } });
    fireEvent.change(screen.getByLabelText(/Medical facility name/), { target: { value: "Hospital" } });
    fireEvent.change(screen.getByLabelText(/Designation/), { target: { value: "Doctor" } });
    fireEvent.change(screen.getByLabelText(/Additional information/), { target: { value: "Details" } });
    fireEvent.change(screen.getByLabelText(/BM&DC Registration Number/), { target: { value: " " } });
    fireEvent.click(screen.getByRole("button", { name: "Submit professional application" }));
    expect(screen.getByRole("alert")).toHaveTextContent("BM&DC Registration Number is required");
    expect(registerAction).not.toHaveBeenCalled();
  });
});
