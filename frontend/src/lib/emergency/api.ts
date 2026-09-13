"use client";
import { apiClient } from "@/lib/api/client";

export type EmergencyInput = {
  allergies: string | null;
  chronic_conditions: string | null;
  current_medications: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  special_notes: string | null;
};
export type EmergencyProfile = EmergencyInput & { citizen_id: string; blood_group: string | null; updated_at: string | null };
export const loadEmergencyProfile = () => apiClient.get<EmergencyProfile>("citizens/me/emergency-profile");
export const saveEmergencyProfile = (payload: EmergencyInput) => apiClient.put<EmergencyProfile, EmergencyInput>("citizens/me/emergency-profile", payload);
export const loadCurrentEmergencyProfile = (citizenId: string) => apiClient.get<EmergencyProfile>(`professionals/current-patient/emergency-profile?citizen_id=${encodeURIComponent(citizenId)}`);
