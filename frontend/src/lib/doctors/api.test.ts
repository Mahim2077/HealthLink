import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: apiMocks.get,
    post: apiMocks.post,
    put: apiMocks.put,
    delete: apiMocks.delete,
  },
}));

import {
  createPracticeSchedule,
  deletePracticeSchedule,
  loadDoctorProfile,
  loadEligibleFacilities,
  loadPracticeSchedule,
  searchDoctors,
  updatePracticeSchedule,
} from "./api";

describe("Doctor API", () => {
  beforeEach(() => {
    apiMocks.get.mockReset();
    apiMocks.post.mockReset();
    apiMocks.put.mockReset();
    apiMocks.delete.mockReset();
  });

  it("searches doctors using only the provided filters", async () => {
    const summaries = [
      {
        designation: "Consultant",
        facility_id: "facility-1",
        facility_name: "City Hospital",
        facility_type: "HOSPITAL",
        first_name: "Amina",
        id: "doctor-1",
        last_name: "Rahman",
        name: "Dr. Amina Rahman",
        role_code: "DOCTOR",
        specialization: "Cardiology",
        verified: true,
      },
    ];
    apiMocks.get.mockResolvedValue(summaries);

    await expect(
      searchDoctors({ name: "Amina", weekday: "MONDAY", limit: 5 }),
    ).resolves.toEqual(summaries);

    expect(apiMocks.get).toHaveBeenCalledWith(
      "doctors?name=Amina&weekday=MONDAY&limit=5",
    );
  });

  it("omits empty filters from the doctor search query string", async () => {
    apiMocks.get.mockResolvedValue([]);
    await expect(searchDoctors({ facility_name: "  " })).resolves.toEqual([]);
    expect(apiMocks.get).toHaveBeenCalledWith("doctors");
  });

  it("loads the doctor profile with the user id path segment", async () => {
    const profile = {
      designation: "Consultant",
      email: "doctor@example.com",
      facility_id: "facility-1",
      facility_name: "City Hospital",
      facility_type: "HOSPITAL",
      first_name: "Amina",
      id: "doctor-1",
      last_name: "Rahman",
      name: "Dr. Amina Rahman",
      practice_days: [],
      role_code: "DOCTOR",
      specialization: null,
      submitted_at: "2026-08-10T00:00:00Z",
      verified: true,
      verified_at: "2026-08-12T00:00:00Z",
    };
    apiMocks.get.mockResolvedValue(profile);

    await expect(loadDoctorProfile("doctor-1")).resolves.toEqual(profile);
    expect(apiMocks.get).toHaveBeenCalledWith("doctors/doctor-1");
  });

  it("loads the doctor's own practice schedule", async () => {
    const schedule = [
      {
        created_at: "2026-08-10T00:00:00Z",
        end_time: "12:00:00",
        facility_id: "facility-1",
        facility_name: "City Hospital",
        id: "schedule-1",
        max_patients: 20,
        start_time: "09:00:00",
        status: "ACTIVE",
        updated_at: "2026-08-10T00:00:00Z",
        weekday: "MONDAY",
      },
    ];
    apiMocks.get.mockResolvedValue(schedule);

    await expect(loadPracticeSchedule()).resolves.toEqual(schedule);
    expect(apiMocks.get).toHaveBeenCalledWith(
      "professionals/me/practice-schedule",
    );
  });

  it("creates a schedule row", async () => {
    const request = {
      end_time: "12:00:00",
      facility_id: "facility-1",
      max_patients: 20,
      start_time: "09:00:00",
      status: "ACTIVE" as const,
      weekday: "MONDAY" as const,
    };
    const response = {
      schedule: {
        created_at: "2026-08-10T00:00:00Z",
        end_time: "12:00:00",
        facility_id: "facility-1",
        facility_name: "City Hospital",
        id: "schedule-1",
        max_patients: 20,
        start_time: "09:00:00",
        status: "ACTIVE",
        updated_at: "2026-08-10T00:00:00Z",
        weekday: "MONDAY",
      },
    };
    apiMocks.post.mockResolvedValue(response);

    await expect(createPracticeSchedule(request)).resolves.toEqual(response);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "professionals/me/practice-schedule",
      request,
    );
  });

  it("updates a schedule row", async () => {
    const request = {
      end_time: "13:00:00",
      facility_id: "facility-1",
      max_patients: 25,
      start_time: "09:00:00",
      status: "ACTIVE" as const,
      weekday: "MONDAY" as const,
    };
    const entry = {
      created_at: "2026-08-10T00:00:00Z",
      end_time: "13:00:00",
      facility_id: "facility-1",
      facility_name: "City Hospital",
      id: "schedule-1",
      max_patients: 25,
      start_time: "09:00:00",
      status: "ACTIVE",
      updated_at: "2026-08-11T00:00:00Z",
      weekday: "MONDAY",
    };
    apiMocks.put.mockResolvedValue(entry);

    await expect(
      updatePracticeSchedule("schedule-1", request),
    ).resolves.toEqual(entry);
    expect(apiMocks.put).toHaveBeenCalledWith(
      "professionals/me/practice-schedule/schedule-1",
      request,
    );
  });

  it("deletes a schedule row", async () => {
    const response = {
      deleted_at: "2026-08-11T00:00:00Z",
      id: "schedule-1",
    };
    apiMocks.delete.mockResolvedValue(response);

    await expect(deletePracticeSchedule("schedule-1")).resolves.toEqual(
      response,
    );
    expect(apiMocks.delete).toHaveBeenCalledWith(
      "professionals/me/practice-schedule/schedule-1",
    );
  });

  it("loads the eligible facilities list for the schedule editor", async () => {
    const facilities = [
      {
        facility_type: "HOSPITAL",
        id: "facility-1",
        is_active: true,
        is_verified_assignment: true,
        name: "Home Hospital",
      },
      {
        facility_type: "CLINIC",
        id: "facility-2",
        is_active: true,
        is_verified_assignment: false,
        name: "Branch Clinic",
      },
    ];
    apiMocks.get.mockResolvedValue(facilities);

    await expect(loadEligibleFacilities()).resolves.toEqual(facilities);
    expect(apiMocks.get).toHaveBeenCalledWith(
      "professionals/me/eligible-facilities",
    );
  });
});