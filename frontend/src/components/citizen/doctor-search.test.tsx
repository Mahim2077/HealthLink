import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  loadAreas: vi.fn(),
  loadFacilities: vi.fn(),
}));

vi.mock("@/components/auth/auth-provider", () => ({
  usePortalAuth: () => ({
    status: "authenticated",
    isRequiredPortal: true,
    refreshSession: vi.fn(),
  }),
}));
vi.mock("@/lib/doctors/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/doctors/api")>("@/lib/doctors/api");
  return { ...actual, loadDoctorDiscoveryFacilities: mocks.loadFacilities };
});
vi.mock("@/lib/locations/api", () => ({ loadBangladeshAreas: mocks.loadAreas }));

import { DoctorSearch } from "./doctor-search";

const doctor = {
  id: "doctor-1",
  name: "Dr. Ayesha Khan",
  first_name: "Ayesha",
  last_name: "Khan",
  facility_id: "facility-1",
  facility_name: "Savar Health Centre",
  facility_type: "HOSPITAL",
  designation: "Consultant",
  role_code: "DOCTOR",
  verified: true,
  specialization: "Pediatrics",
  specialization_code: "PEDIATRICS" as const,
  qualification: "MBBS, FCPS (Pediatrics)",
  facility_area: "Savar, Dhaka",
  next_practice: { weekday: "MONDAY" as const, start_time: "16:00:00", end_time: "18:00:00", facility_name: "Savar Health Centre", days_away: 1 },
  distance_km: null,
};
const areas = {
  districts: [{ code: "BD3026", name: "Dhaka", name_bn: "ঢাকা" }],
  upazilas: [{ code: "BD30260072", district_code: "BD3026", name: "Savar", name_bn: "সাভার" }],
};

describe("DoctorSearch", () => {
  beforeEach(() => {
    mocks.loadAreas.mockReset().mockResolvedValue(areas);
    mocks.loadFacilities.mockReset().mockResolvedValue([{ id: "facility-1", name: "Savar Health Centre", facility_type: "HOSPITAL", area: "Savar, Dhaka" }]);
  });

  it("loads verified doctors and filters from specialty cards", async () => {
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    expect(await screen.findByText("Dr. Ayesha Khan")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Pediatrics/ }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ specialization: "PEDIATRICS" })));
    expect(screen.getByText("MBBS, FCPS (Pediatrics)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Book appointment" })).toHaveAttribute("href", "/citizen/appointments/book?doctor_user_id=doctor-1");
  });

  it("uses zila and upazila selection without showing coordinate fields", async () => {
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(screen.getByLabelText("Sort by"), { target: { value: "NEAREST" } });
    expect(screen.getByRole("heading", { name: "Use your approximate location?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Enter area manually" }));
    fireEvent.change(screen.getByLabelText("Zila"), { target: { value: "BD3026" } });
    fireEvent.change(screen.getByLabelText("Upazila"), { target: { value: "BD30260072" } });
    fireEvent.click(screen.getByRole("button", { name: "Find doctors in this area" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "NEAREST", district_code: "BD3026", upazila_code: "BD30260072" })));
    expect(screen.queryByText(/latitude|longitude|coordinate/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("Savar, Dhaka").length).toBeGreaterThan(0);
  });

  it("rounds one-time browser location before searching and does not persist it", async () => {
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const getCurrentPosition = vi.fn((success: PositionCallback) => success({ coords: { latitude: 23.810331, longitude: 90.412521 } } as GeolocationPosition));
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition } });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(screen.getByLabelText("Sort by"), { target: { value: "NEAREST" } });
    fireEvent.click(screen.getByRole("button", { name: "Use approximate location" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "NEAREST", latitude: 23.81, longitude: 90.41 })));
    expect(setItem).not.toHaveBeenCalled();
  });

  it("uses a friendly label for facilities less than one kilometre away", async () => {
    const searchAction = vi.fn().mockResolvedValue({ items: [{ ...doctor, distance_km: 0 }], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    expect(await screen.findByText(/Less than 1 km away/)).toBeInTheDocument();
    expect(screen.queryByText(/About 0 km away/)).not.toBeInTheDocument();
  });
});
