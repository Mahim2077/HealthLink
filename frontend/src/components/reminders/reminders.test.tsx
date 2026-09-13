import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReminderForm } from "./reminder-form";
import { RemindersPage, RemindersWorkspace } from "./reminders-page";
import * as api from "@/lib/reminders/api";

const auth = vi.hoisted(() => ({ status: "authenticated", isRequiredPortal: true, claims: { sid: "citizen-session" }, refreshSession: vi.fn() }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: () => auth }));
vi.mock("@/lib/reminders/api", () => ({ listPrescriptionChoices: vi.fn(), saveReminder: vi.fn(), listReminders: vi.fn(), listNotifications: vi.fn(), setReminderActive: vi.fn(), markNotification: vi.fn() }));

const reminder: api.Reminder = { id: "reminder", medicine: "Medicine A", prescription_item_id: null, start_date: "2026-09-12", end_date: null, timezone: "Asia/Dhaka", is_active: true, times: ["08:00:00"] };
beforeEach(() => {
  vi.clearAllMocks(); auth.isRequiredPortal = true;
  vi.mocked(api.listPrescriptionChoices).mockResolvedValue([]);
  vi.mocked(api.listReminders).mockResolvedValue([reminder]);
  vi.mocked(api.listNotifications).mockResolvedValue([]);
});

describe("reminders", () => {
  it("preserves a failed draft and submits separate daily times", async () => {
    vi.mocked(api.saveReminder).mockRejectedValue(new Error("Connection unavailable"));
    render(<ReminderForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Medicine"), { target: { value: "Medicine B" } });
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-09-12" } });
    fireEvent.change(screen.getByLabelText("Time 1"), { target: { value: "08:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Add daily time" }));
    fireEvent.change(screen.getByLabelText("Time 2"), { target: { value: "20:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save reminder" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Connection unavailable");
    expect(screen.getByLabelText("Medicine")).toHaveValue("Medicine B");
    expect(api.saveReminder).toHaveBeenCalledWith(expect.objectContaining({ times: ["08:00", "20:00"], timezone: "Asia/Dhaka" }), undefined);
  });

  it("prevents duplicate saves while a request is pending", async () => {
    vi.mocked(api.saveReminder).mockReturnValue(new Promise(() => {}));
    render(<ReminderForm initial={reminder} onSaved={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save reminder" }));
    expect(await screen.findByRole("button", { name: "Saving…" })).toBeDisabled();
    expect(screen.getByLabelText("Medicine")).toBeDisabled();
    expect(api.saveReminder).toHaveBeenCalledTimes(1);
  });

  it("links an owned prescription choice without accepting a changed medicine", async () => {
    vi.mocked(api.listPrescriptionChoices).mockResolvedValue([{ id: "item", medicine: "Prescribed A", dosage: "1", prescription_date: "2026-09-11" }]);
    render(<ReminderForm onSaved={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: /Prescribed A/ });
    fireEvent.change(screen.getByLabelText("Prescription medicine (optional)"), { target: { value: "item" } });
    expect(screen.getByLabelText("Medicine")).toHaveValue("Prescribed A");
    expect(screen.getByLabelText("Medicine")).toHaveAttribute("readonly");
  });

  it("toggles active reminders and acknowledges notices separately", async () => {
    vi.mocked(api.listNotifications).mockResolvedValue([{ id: "notice", kind: "MEDICINE", message: "Medicine A reminder", due_at: "2026-09-12T02:00:00Z", read_at: null, acknowledged_at: null }]);
    vi.mocked(api.setReminderActive).mockResolvedValue({ ...reminder, is_active: false });
    render(<RemindersWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
    await waitFor(() => expect(api.setReminderActive).toHaveBeenCalledWith("reminder", false));
    await waitFor(() => expect(screen.getByRole("button", { name: "Acknowledge" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
    await waitFor(() => expect(api.markNotification).toHaveBeenCalledWith("notice", "acknowledge"));
  });

  it("does not fetch reminders for another portal", () => {
    auth.isRequiredPortal = false;
    render(<RemindersPage />);
    expect(screen.getByText("Citizen portal required")).toBeInTheDocument();
    expect(api.listReminders).not.toHaveBeenCalled();
  });
});
