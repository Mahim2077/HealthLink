import { apiClient } from "@/lib/api/client";

export type ReminderInput = { medicine: string; prescription_item_id: string | null; start_date: string; end_date: string | null; timezone: "Asia/Dhaka"; is_active: boolean; times: string[] };
export type Reminder = ReminderInput & { id: string };
export type ReminderNotification = { id: string; kind: "MEDICINE" | "APPOINTMENT"; message: string; due_at: string; read_at: string | null; acknowledged_at: string | null };
export type PrescriptionChoice = { id: string; medicine: string; dosage: string; prescription_date: string };
export const listReminders = (page = 1) => apiClient.get<Reminder[]>(`citizens/me/reminders?page=${page}`);
export const saveReminder = (body: ReminderInput, id?: string) => id ? apiClient.put<Reminder, ReminderInput>(`citizens/me/reminders/${encodeURIComponent(id)}`, body) : apiClient.post<Reminder, ReminderInput>("citizens/me/reminders", body);
export const setReminderActive = (id: string, is_active: boolean) => apiClient.put<Reminder, { is_active: boolean }>(`citizens/me/reminders/${encodeURIComponent(id)}/active`, { is_active });
export const listPrescriptionChoices = (page = 1) => apiClient.get<PrescriptionChoice[]>(`citizens/me/reminder-prescription-items?page=${page}`);
export const listNotifications = (page = 1) => apiClient.get<ReminderNotification[]>(`citizens/me/notifications?page=${page}`);
export const markNotification = (id: string, action: "read" | "acknowledge") => apiClient.post<ReminderNotification>(`citizens/me/notifications/${encodeURIComponent(id)}/${action}`);
