"use client";

import { apiClient } from "@/lib/api/client";

import type { PrescriptionPayload, PrescriptionView } from "./types";

export async function createPrescription(
  visitId: string,
  payload: PrescriptionPayload,
): Promise<PrescriptionView> {
  return apiClient.post<PrescriptionView, PrescriptionPayload>(
    `visits/${visitId}/prescription`,
    payload,
  );
}

export async function readPrescription(
  prescriptionId: string,
): Promise<PrescriptionView> {
  return apiClient.get<PrescriptionView>(`prescriptions/${prescriptionId}`);
}

export async function updatePrescription(
  prescriptionId: string,
  payload: PrescriptionPayload,
): Promise<PrescriptionView> {
  return apiClient.put<PrescriptionView, PrescriptionPayload>(
    `prescriptions/${prescriptionId}`,
    payload,
  );
}

export async function downloadPrescriptionPdf(
  prescriptionId: string,
): Promise<Blob> {
  return apiClient.getBlob(`prescriptions/${prescriptionId}/pdf`);
}
