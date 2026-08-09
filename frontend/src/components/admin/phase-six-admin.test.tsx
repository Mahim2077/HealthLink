import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createFacility: vi.fn(), loadFacilities: vi.fn(), loadRegistration: vi.fn(),
  loadRegistrations: vi.fn(), reject: vi.fn(), updateFacility: vi.fn(), verify: vi.fn(),
}));
vi.mock("@/components/admin/admin-portal-guard", () => ({ AdminPortalGuard: ({ children }: { children: React.ReactNode }) => children }));
vi.mock("@/lib/admin/api", () => ({
  createFacility: mocks.createFacility, loadFacilities: mocks.loadFacilities,
  loadProfessionalRegistration: mocks.loadRegistration,
  loadProfessionalRegistrations: mocks.loadRegistrations,
  rejectProfessionalRegistration: mocks.reject, updateFacility: mocks.updateFacility,
  verifyProfessionalRegistration: mocks.verify,
}));

import { FacilityManager } from "./facility-manager";
import { ProfessionalVerificationDetail } from "./professional-verification-detail";
import { ProfessionalVerificationQueue } from "./professional-verification-queue";

const facility = { id: "f1", name: "General Hospital", facility_type: "HOSPITAL", registration_number: "F-1", address: "Dhaka", phone: null, email: null, is_active: true, created_at: "2026-08-10T10:00:00Z", updated_at: "2026-08-10T10:00:00Z" } as const;
const application = { id: "r1", professional_id: "p1", user_id: "u1", first_name: "Doctor", last_name: "Applicant", email: "doctor@example.com", role_code: "DOCTOR", role_name: "Doctor", facility_name_submitted: "Submitted Clinic", designation: "Consultant", verification_status: "PENDING", submitted_at: "2026-08-10T10:00:00Z", additional_info: "Evidence", bmdc_registration_number: "BMDC-100", facility: null, verified_at: null, verified_by: null, rejected_at: null, rejection_reason: null } as const;

describe("Phase 6 admin interfaces", () => {
  beforeEach(() => { Object.values(mocks).forEach((mock) => mock.mockReset()); mocks.loadFacilities.mockResolvedValue([facility]); mocks.loadRegistrations.mockResolvedValue([application]); mocks.loadRegistration.mockResolvedValue(application); });

  it("shows the pending queue and links to role-specific review", async () => {
    render(<ProfessionalVerificationQueue />);
    expect(await screen.findByText("Doctor Applicant")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review application" })).toHaveAttribute("href", "/admin/professional-registrations/r1");
    expect(mocks.loadRegistrations).toHaveBeenCalledWith("PENDING");
  });

  it("exposes BM&DC, verifies with an active facility, and requires rejection reason", async () => {
    mocks.verify.mockResolvedValue({ ...application, verification_status: "VERIFIED", facility });
    render(<ProfessionalVerificationDetail registrationId="r1" />);
    expect(await screen.findByText("BMDC-100")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verify and link facility" }));
    await waitFor(() => expect(mocks.verify).toHaveBeenCalledWith("r1", "f1"));

    mocks.verify.mockReset(); mocks.loadRegistration.mockResolvedValue(application);
    render(<ProfessionalVerificationDetail registrationId="r2" />);
    await screen.findAllByText("BMDC-100");
    fireEvent.change(screen.getAllByLabelText("Rejection reason").at(-1)!, { target: { value: "   " } });
    fireEvent.click(screen.getAllByRole("button", { name: "Reject application" }).at(-1)!);
    expect(await screen.findByText("A rejection reason is required.")).toBeInTheDocument();
    expect(mocks.reject).not.toHaveBeenCalled();
  });

  it("creates a facility with normalized optional values and supports editing", async () => {
    mocks.createFacility.mockResolvedValue(facility);
    render(<FacilityManager />);
    await screen.findByText("General Hospital");
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: " New Clinic " } });
    fireEvent.change(screen.getByLabelText("Facility type"), { target: { value: "CLINIC" } });
    fireEvent.change(screen.getByLabelText("Address"), { target: { value: " Dhaka " } });
    fireEvent.click(screen.getByRole("button", { name: "Create facility" }));
    await waitFor(() => expect(mocks.createFacility).toHaveBeenCalledWith(expect.objectContaining({ name: "New Clinic", facility_type: "CLINIC", address: "Dhaka", email: null })));
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();
  });
});
