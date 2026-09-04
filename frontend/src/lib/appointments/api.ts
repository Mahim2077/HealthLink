"use client";

import { apiClient } from "@/lib/api/client";

import type {
  AppointmentBookingRequest,
  AppointmentBookingResponse,
  AppointmentFinishResponse,
  AppointmentListResponse,
} from "./types";

export async function bookAppointment(
  payload: AppointmentBookingRequest,
): Promise<AppointmentBookingResponse> {
  return apiClient.post<AppointmentBookingResponse, AppointmentBookingRequest>(
    "citizens/appointments",
    payload,
  );
}

export async function listMyAppointments(): Promise<AppointmentListResponse> {
  return apiClient.get<AppointmentListResponse>("citizens/appointments");
}

export async function finishAppointment(
  appointmentId: string,
): Promise<AppointmentFinishResponse> {
  return apiClient.post<AppointmentFinishResponse, Record<string, never>>(
    `appointments/${appointmentId}/finish`,
    {},
  );
}
