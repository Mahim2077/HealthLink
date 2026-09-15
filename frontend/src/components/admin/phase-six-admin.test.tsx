import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  confirmFacilityLocation: vi.fn(), createFacility: vi.fn(), loadAreas: vi.fn(), loadFacilities: vi.fn(), loadRegistration: vi.fn(),
  loadRegistrations: vi.fn(), reject: vi.fn(), updateFacility: vi.fn(), verify: vi.fn(),
}));
vi.mock("@/components/admin/admin-portal-guard", () => ({ AdminPortalGuard: ({ children }: { children: React.ReactNode }) => children }));
vi.mock("@/lib/admin/api", () => ({
  confirmFacilityLocation: mocks.confirmFacilityLocation, createFacility: mocks.createFacility, loadFacilities: mocks.loadFacilities,
  loadProfessionalRegistration: mocks.loadRegistration,
  loadProfessionalRegistrations: mocks.loadRegistrations,
  rejectProfessionalRegistration: mocks.reject, updateFacility: mocks.updateFacility,
  verifyProfessionalRegistration: mocks.verify,
}));
vi.mock("@/lib/locations/api", () => ({ loadBangladeshAreas: mocks.loadAreas }));

import { FacilityManager } from "./facility-manager";
import { ProfessionalVerificationDetail } from "./professional-verification-detail";
import { ProfessionalVerificationQueue } from "./professional-verification-queue";

const facility = { id: "f1", name: "General Hospital", facility_type: "HOSPITAL", registration_number: "F-1", address: "Dhaka", district_code: "BD3026", upazila_code: "BD30260072", location_status: "PENDING", location_matched_address: null, location_confirmed_at: null, phone: null, email: null, is_active: true, created_at: "2026-08-10T10:00:00Z", updated_at: "2026-08-10T10:00:00Z" } as const;
const application = { id: "r1", professional_id: "p1", user_id: "u1", first_name: "Doctor", last_name: "Applicant", email: "doctor@example.com", role_code: "DOCTOR", role_name: "Doctor", facility_name_submitted: "Submitted Clinic", designation: "Consultant", verification_status: "PENDING", submitted_at: "2026-08-10T10:00:00Z", additional_info: "Evidence", bmdc_registration_number: "BMDC-100", specialization: "PEDIATRICS", qualification: "MBBS", facility: null, verified_at: null, verified_by: null, rejected_at: null, rejection_reason: null } as const;

describe("Phase 6 admin interfaces", () => {
  beforeEach(() => { Object.values(mocks).forEach((mock) => mock.mockReset()); mocks.loadAreas.mockResolvedValue({ districts: [{ code: "BD3026", name: "Dhaka", name_bn: "ঢাকা" }], upazilas: [{ code: "BD30260072", district_code: "BD3026", name: "Savar", name_bn: "সাভার" }] }); mocks.loadFacilities.mockResolvedValue([facility]); mocks.loadRegistrations.mockResolvedValue([application]); mocks.loadRegistration.mockResolvedValue(application); });

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
    expect(screen.getByLabelText("Match active facility")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("Match active facility"), { target: { value: "f1" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify and link facility" }));
    await waitFor(() => expect(mocks.verify).toHaveBeenCalledWith("r1", "f1", "PEDIATRICS", "MBBS"));

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
    fireEvent.change(screen.getByLabelText("Registration address"), { target: { value: " Dhaka " } });
    fireEvent.change(screen.getByLabelText("Zila"), { target: { value: "BD3026" } });
    fireEvent.change(screen.getByLabelText("Upazila"), { target: { value: "BD30260072" } });
    fireEvent.click(screen.getByRole("button", { name: "Create facility" }));
    await waitFor(() => expect(mocks.createFacility).toHaveBeenCalledWith(expect.objectContaining({ name: "New Clinic", facility_type: "CLINIC", address: "Dhaka", email: null })));
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();
  });
});
