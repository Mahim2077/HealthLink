import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
import type { DoctorSearchFilters } from "@/lib/doctors/types";

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
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "NEAREST", district_code: "BD3026", upazila_code: "BD30260072", offset: 0 })));
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

  it("contains keyboard and programmatic focus, makes the background inert, and restores focus on Escape", async () => {
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    const { container } = render(<><button type="button">Background control</button><DoctorSearch searchAction={searchAction} /></>);
    await screen.findByText("Dr. Ayesha Khan");
    const sort = screen.getByLabelText("Sort by");
    sort.focus();
    const overflow = document.body.style.overflow;
    fireEvent.change(sort, { target: { value: "NEAREST" } });
    const dialog = screen.getByRole("dialog");
    const close = within(dialog).getByRole("button", { name: "Close location choice" });
    const last = within(dialog).getByRole("button", { name: "Not now" });
    expect(close).toHaveFocus();
    expect(container.inert).toBe(true);
    expect(dialog.closest("[inert]")).toBeNull();
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();
    fireEvent.keyDown(last, { key: "Tab" });
    expect(close).toHaveFocus();
    screen.getByRole("button", { name: "Background control" }).focus();
    expect(close).toHaveFocus();
    fireEvent.keyDown(close, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(container.inert).toBeFalsy();
    expect(document.body.style.overflow).toBe(overflow);
    expect(sort).toHaveFocus();
  });

  it("keeps focus contained when switching to the manual-area form and restores it on close", async () => {
    render(<DoctorSearch searchAction={vi.fn().mockResolvedValue({ items: [doctor], total: 1 })} />);
    await screen.findByText("Dr. Ayesha Khan");
    const sort = screen.getByLabelText("Sort by");
    sort.focus();
    fireEvent.change(sort, { target: { value: "NEAREST" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter area manually" }));
    expect(screen.getByLabelText("Zila")).toHaveFocus();
    const close = screen.getByRole("button", { name: "Close location choice" });
    close.focus();
    fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Back to location choices" })).toHaveFocus();
    fireEvent.click(close);
    expect(sort).toHaveFocus();
  });

  it("shows GPS denial in the open dialog and leaves manual area selection available", async () => {
    const getCurrentPosition = vi.fn((_success: PositionCallback, failure: PositionErrorCallback) => failure({ code: 1 } as GeolocationPositionError));
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: { getCurrentPosition } });
    render(<DoctorSearch searchAction={vi.fn().mockResolvedValue({ items: [doctor], total: 1 })} />);
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(screen.getByLabelText("Sort by"), { target: { value: "NEAREST" } });
    fireEvent.click(screen.getByRole("button", { name: "Use approximate location" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Choose a zila and upazila instead");
    fireEvent.click(within(dialog).getByRole("button", { name: "Enter area manually" }));
    expect(screen.getByLabelText("Zila")).toBeInTheDocument();
  });

  it("disambiguates same-name facilities without exposing internal IDs", async () => {
    mocks.loadFacilities.mockResolvedValue([
      { id: "internal-one", name: "City Hospital", area: "Savar, Dhaka", address: "North Road", registration_number: "HOSP-101" },
      { id: "internal-two", name: "City Hospital", area: "Savar, Dhaka", address: "South Road", registration_number: "HOSP-202" },
    ]);
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    const options = within(screen.getByLabelText("Facility"));
    expect(options.getByRole("option", { name: /North Road · Registration HOSP-101/ })).toBeInTheDocument();
    expect(options.getByRole("option", { name: /South Road · Registration HOSP-202/ })).toBeInTheDocument();
    expect(options.queryByText(/internal-/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Facility"), { target: { value: "internal-two" } });
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ facility_id: "internal-two" })));
    expect(screen.getByRole("button", { name: /City Hospital · Savar, Dhaka · South Road · Registration HOSP-202/ })).toBeInTheDocument();
  });

  it("pages beyond the first 50 doctors with one query per page and correct terminal controls", async () => {
    const doctors = Array.from({ length: 55 }, (_, index) => ({ ...doctor, id: `doctor-${index + 1}`, name: `Paging Doctor ${index + 1}` }));
    const searchAction = vi.fn().mockImplementation(async (filters: DoctorSearchFilters) => ({ items: doctors.slice(filters.offset ?? 0, (filters.offset ?? 0) + (filters.limit ?? 50)), total: doctors.length }));
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Paging Doctor 1");
    expect(screen.getAllByTestId("doctor-row")).toHaveLength(50);
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Paging Doctor 51");
    expect(searchAction).toHaveBeenCalledTimes(2);
    expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50, limit: 50 }));
    expect(screen.getAllByTestId("doctor-row")).toHaveLength(5);
    expect(screen.queryByText("Paging Doctor 1")).not.toBeInTheDocument();
    expect(screen.getByText("Page 2 · Showing 51–55 of 55")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    await screen.findByText("Paging Doctor 1");
    expect(searchAction).toHaveBeenCalledTimes(3);
    expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 0 }));
    expect(mocks.loadFacilities).toHaveBeenCalledTimes(1);
    expect(mocks.loadAreas).toHaveBeenCalledTimes(1);
  });

  it("pages the applied query, preserves unsent text, and resets paging for new filters", async () => {
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 70 });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    const text = screen.getByRole("textbox", { name: "Search doctor, specialty, or hospital" });
    fireEvent.change(text, { target: { value: "cardiologist" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(searchAction).toHaveBeenCalledTimes(2));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ query: "cardiologist", offset: 50 })));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(text, { target: { value: "orthopedic surgeon" } });
    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ query: "cardiologist", offset: 0 })));
    await screen.findByText("Dr. Ayesha Khan");
    expect(text).toHaveValue("orthopedic surgeon");
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ query: "orthopedic surgeon", offset: 0 })));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(screen.getByLabelText("Facility"), { target: { value: "facility-1" } });
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ facility_id: "facility-1", query: "orthopedic surgeon", offset: 0 })));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Pediatrics" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ specialization: "PEDIATRICS", offset: 0 })));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(screen.getByLabelText("Sort by"), { target: { value: "DOCTOR_NAME" } });
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "DOCTOR_NAME", offset: 0 })));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    await waitFor(() => expect(searchAction).toHaveBeenLastCalledWith({ sort: "BEST_MATCH", limit: 50, offset: 0 }));
    expect(text).toHaveValue("");
  });

  it("disables page controls during a request so repeated clicks do not duplicate it", async () => {
    let finishPage!: (value: { items: typeof doctor[]; total: number }) => void;
    const searchAction = vi.fn().mockResolvedValueOnce({ items: [doctor], total: 70 }).mockImplementationOnce(() => new Promise(resolve => { finishPage = resolve; }));
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    const next = screen.getByRole("button", { name: "Next" });
    fireEvent.click(next);
    expect(next).toBeDisabled();
    fireEvent.click(next);
    await waitFor(() => expect(searchAction).toHaveBeenCalledTimes(2));
    await act(async () => { finishPage({ items: [{ ...doctor, id: "doctor-page-two" }], total: 70 }); });
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("keeps results and specialty search available when both catalogs fail, with independent retry", async () => {
    mocks.loadFacilities.mockRejectedValueOnce(new Error("Facility catalog unavailable"));
    mocks.loadAreas.mockRejectedValueOnce(new Error("Area catalog unavailable"));
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    expect(screen.getByLabelText("Facility")).toBeDisabled();
    expect(screen.getByText(/Facility filtering is unavailable/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pediatrics" }));
    await waitFor(() => expect(searchAction).toHaveBeenCalledTimes(2));
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.click(screen.getByRole("button", { name: "Retry facility list" }));
    await waitFor(() => expect(screen.getByLabelText("Facility")).toBeEnabled());
    expect(screen.getByRole("option", { name: /Savar Health Centre/ })).toBeInTheDocument();
    expect(mocks.loadFacilities).toHaveBeenCalledTimes(2);
    expect(mocks.loadAreas).toHaveBeenCalledTimes(1);
    expect(searchAction).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole("button", { name: "Retry area list" }));
    await waitFor(() => expect(screen.queryByText(/Manual area choices are unavailable/)).not.toBeInTheDocument());
    expect(mocks.loadAreas).toHaveBeenCalledTimes(2);
    expect(searchAction).toHaveBeenCalledTimes(2);
  });

  it("recovers manual area selection within the dialog without refetching doctors", async () => {
    let finishAreas!: (value: typeof areas) => void;
    mocks.loadAreas.mockRejectedValueOnce(new Error("Area catalog unavailable"))
      .mockImplementationOnce(() => new Promise(resolve => { finishAreas = resolve; }));
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Dr. Ayesha Khan");
    fireEvent.change(screen.getByLabelText("Sort by"), { target: { value: "NEAREST" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter area manually" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Zila")).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "Find doctors in this area" })).toBeDisabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Retry area list" }));
    await waitFor(() => expect(mocks.loadAreas).toHaveBeenCalledTimes(2));
    expect(within(dialog).getByLabelText("Zila")).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "Close location choice" })).toHaveFocus();
    expect(searchAction).toHaveBeenCalledTimes(1);
    await act(async () => { finishAreas(areas); });
    await waitFor(() => {
      expect(within(dialog).getByLabelText("Zila")).toBeEnabled();
      expect(within(dialog).getByLabelText("Zila")).toHaveFocus();
    });
    expect(searchAction).toHaveBeenCalledTimes(1);
    fireEvent.change(within(dialog).getByLabelText("Zila"), { target: { value: "BD3026" } });
    fireEvent.change(within(dialog).getByLabelText("Upazila"), { target: { value: "BD30260072" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Find doctors in this area" }));
    await waitFor(() => expect(searchAction).toHaveBeenCalledTimes(2));
    expect(searchAction).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "NEAREST", upazila_code: "BD30260072", offset: 0 }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not block initial doctor results on pending catalog requests", async () => {
    mocks.loadFacilities.mockImplementationOnce(() => new Promise(() => undefined));
    mocks.loadAreas.mockImplementationOnce(() => new Promise(() => undefined));
    const searchAction = vi.fn().mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    expect(await screen.findByText("Dr. Ayesha Khan")).toBeInTheDocument();
    expect(screen.getByLabelText("Facility")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Search" })).toBeEnabled();
    expect(searchAction).toHaveBeenCalledTimes(1);
  });

  it("retries only the failed doctor request and not successfully loaded catalogs", async () => {
    const searchAction = vi.fn().mockRejectedValueOnce(new Error("Search failed")).mockResolvedValue({ items: [doctor], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    await screen.findByText("Doctor search unavailable");
    fireEvent.click(within(screen.getByRole("region", { name: "Doctor search results" })).getByRole("button", { name: "Try again" }));
    await screen.findByText("Dr. Ayesha Khan");
    expect(searchAction).toHaveBeenCalledTimes(2);
    expect(mocks.loadFacilities).toHaveBeenCalledTimes(1);
    expect(mocks.loadAreas).toHaveBeenCalledTimes(1);
  });

  it("does not let a slow initial search overwrite a newer submitted query", async () => {
    let finishInitial!: (value: { items: typeof doctor[]; total: number }) => void;
    const searchAction = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finishInitial = resolve; })).mockResolvedValue({ items: [{ ...doctor, id: "new-query-doctor", name: "New Query Doctor" }], total: 1 });
    render(<DoctorSearch searchAction={searchAction} />);
    await waitFor(() => expect(searchAction).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByRole("textbox", { name: "Search doctor, specialty, or hospital" }), { target: { value: "new query" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await screen.findByText("New Query Doctor");
    await act(async () => { finishInitial({ items: [doctor], total: 70 }); });
    expect(screen.getByText("New Query Doctor")).toBeInTheDocument();
    expect(screen.queryByText("Dr. Ayesha Khan")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(searchAction).toHaveBeenCalledTimes(2);
  });
});
