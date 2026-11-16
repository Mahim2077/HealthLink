import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DiagnosticRequestPanel } from "./diagnostic-request-panel";
import { DiagnosticList } from "./diagnostic-list";
import { DiagnosticsPage } from "./diagnostics-page";
import { DiagnosticSessions } from "./diagnostic-sessions";
import type { LabSession } from "@/lib/diagnostics/session-api";

const mocks = vi.hoisted(() => ({ create: vi.fn(), search: vi.fn(), assign: vi.fn(), citizen: vi.fn(), professional: vi.fn(), trends: vi.fn(), me: vi.fn(), auth: vi.fn(), catalog: vi.fn(), sessions: vi.fn(), stage: vi.fn(), publish: vi.fn() }));
vi.mock("@/lib/diagnostics/api", () => ({ createDiagnosticTest: mocks.create, listDiagnosticTechnicians: mocks.search, assignDiagnosticTest: mocks.assign, listCitizenDiagnostics: mocks.citizen, listProfessionalDiagnostics: mocks.professional, transitionDiagnosticTest: vi.fn() }));
vi.mock("@/lib/diagnostics/report-api", () => ({ listLabTrends: mocks.trends }));
vi.mock("@/lib/diagnostics/session-api", async importOriginal => ({
  ...await importOriginal<typeof import("@/lib/diagnostics/session-api")>(), getTestCatalog: mocks.catalog, getLabSessions: mocks.sessions,
  stageLabPdf: mocks.stage, publishLabPdf: mocks.publish,
}));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.me }));
vi.mock("@/components/auth/auth-provider", () => ({ usePortalAuth: mocks.auth }));

const testRecord = {
  id: "test-1", citizen_id: "citizen-1", visit_id: "visit-1", requested_by_role_registration_id: "doctor-1", assigned_to_role_registration_id: null,
  facility_id: "facility-1", facility_name: "City Hospital", test_name: "CBC", instructions: null, status: "REQUESTED" as const,
  requested_by_name: "Doctor", assigned_to_name: null, created_at: "2026-09-12", updated_at: "2026-09-12",
};

const performedSession: LabSession = {
  id: "session-1", catalog_code: "CBC", test_name: "Complete blood count", status: "PERFORMED",
  created_at: "2026-11-16T08:00:00Z", attendance_deadline: null, facility_name: "City Hospital",
  closed_reason: null, share_code: null, patient_name: "Test Patient", report_version: null,
  report_test_name: null, draft_version: null, draft_test_name: null, draft_tested_at: null,
};

const stagedSession: LabSession = {
  ...performedSession, draft_version: 1, draft_test_name: performedSession.test_name,
  draft_tested_at: "2026-11-16T09:00:00Z",
};

const publishedSession: LabSession = {
  ...performedSession, status: "PUBLISHED", report_version: 1, report_test_name: performedSession.test_name,
};

describe("Diagnostic safety and assignment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.search.mockResolvedValue([]);
    mocks.trends.mockResolvedValue([]);
    mocks.sessions.mockResolvedValue([]);
    mocks.catalog.mockResolvedValue([{ code: "CBC", name: "Complete blood count", aliases: ["CBC"] }]);
  });

  it("keeps failed requests and binds submission to the displayed visit", async () => {
    mocks.create.mockRejectedValue(new Error("Consultation changed"));
    const onEditStateChange = vi.fn();
    render(<DiagnosticRequestPanel visitId="visit-1" onEditStateChange={onEditStateChange} />);
    fireEvent.change(screen.getByLabelText("Test name"), { target: { value: "CBC" } });
    fireEvent.click(await screen.findByRole("button", { name: "Complete blood count" }));
    fireEvent.click(screen.getByRole("button", { name: "Request test" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Consultation changed");
    expect(mocks.create).toHaveBeenCalledWith({ visit_id: "visit-1", catalog_code: "CBC", instructions: null });
    expect(screen.getByText("Complete blood count")).toBeInTheDocument();
    await waitFor(() => expect(onEditStateChange).toHaveBeenLastCalledWith({ dirty: true, saving: false }));
  });

  it("disables edits and duplicate submission during a request", async () => {
    let resolve!: (value: unknown) => void;
    mocks.create.mockReturnValue(new Promise(r => { resolve = r; }));
    render(<DiagnosticRequestPanel visitId="visit-1" onEditStateChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Test name"), { target: { value: "CBC" } });
    fireEvent.click(await screen.findByRole("button", { name: "Complete blood count" }));
    fireEvent.click(screen.getByRole("button", { name: "Request test" }));
    expect(screen.getByRole("button", { name: "Change test" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Requesting…" }));
    expect(mocks.create).toHaveBeenCalledTimes(1);
    await act(async () => resolve({}));
    expect(screen.getByLabelText("Test name")).toHaveValue("");
  });

  it("searches and assigns a technician using the selected test's facility", async () => {
    mocks.search.mockResolvedValue([{ role_registration_id: "lab-1", full_name: "Amina", designation: "Technician", facility_id: "facility-1", facility_name: "City Hospital" }]);
    mocks.assign.mockResolvedValue({ ...testRecord, assigned_to_role_registration_id: "lab-1", assigned_to_name: "Amina" });
    render(<DiagnosticList loadAction={async () => ({ tests: [testRecord] })} role="doctor" />);
    fireEvent.click(await screen.findByRole("button", { name: "Assign technician" }));
    fireEvent.change(screen.getByLabelText("Search lab technicians"), { target: { value: "Amina" } });
    await screen.findByRole("option", { name: /Amina/ });
    expect(mocks.search).toHaveBeenLastCalledWith("Amina", { test_id: "test-1", visit_id: undefined });
    fireEvent.change(screen.getByLabelText("Lab technician"), { target: { value: "lab-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save assignment" }));
    expect(await screen.findByText("Assigned to: Amina")).toBeInTheDocument();
    expect(mocks.assign).toHaveBeenCalledWith("test-1", "lab-1");
  });

  it("does not load citizen data for the wrong portal", () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: false, claims: { sid: "admin" }, refreshSession: vi.fn() });
    render(<DiagnosticsPage portal="CITIZEN" />);
    expect(screen.getByText("Portal access required")).toBeInTheDocument();
    expect(mocks.citizen).not.toHaveBeenCalled();
  });

  it("pages diagnostic records without leaving old page data visible", async () => {
    const load = vi.fn().mockImplementation(async (page: number) => ({
      tests: [{ ...testRecord, id: `test-${page}`, test_name: `Page ${page} test` }],
      page, page_size: 1, has_next: page === 1,
    }));
    render(<DiagnosticList loadAction={load} role="citizen" />);
    await screen.findByRole("heading", { name: "Page 1 test" });
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(screen.queryByRole("heading", { name: "Page 1 test" })).not.toBeInTheDocument();
    await screen.findByRole("heading", { name: "Page 2 test" });
    expect(load).toHaveBeenLastCalledWith(2);
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));
    await screen.findByRole("heading", { name: "Page 1 test" });
  });

  it("merges citizen requests, finalized-result access, and trends into one diagnostic section", async () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "citizen" }, refreshSession: vi.fn() });
    mocks.citizen.mockResolvedValue({ tests: [{ ...testRecord, status: "COMPLETED" }] });
    render(<DiagnosticsPage portal="CITIZEN" />);

    expect(screen.getByRole("heading", { level: 1, name: "Diagnostic tests" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Requests and results" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Numeric result trends" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "View results" })).toHaveAttribute("href", "/citizen/diagnostic-tests/test-1");
    expect(await screen.findByText("No numeric results")).toBeInTheDocument();
    expect(mocks.citizen).toHaveBeenCalledOnce();
    expect(mocks.trends).toHaveBeenCalledWith(1);
  });

  it("shows a retryable role failure instead of an endless spinner", async () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "lab" }, refreshSession: vi.fn() });
    mocks.me.mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValueOnce({ role_code: "LAB_TECHNICIAN", verification_status: "VERIFIED" });
    mocks.professional.mockResolvedValue({ tests: [] });
    render(<DiagnosticsPage portal="PROFESSIONAL" />);
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    await waitFor(() => expect(mocks.professional).toHaveBeenCalled());
    expect(await screen.findByText("No diagnostic tests")).toBeInTheDocument();
  });

  it("moves a newly finished session into the open history before either list refreshes", async () => {
    mocks.sessions.mockResolvedValueOnce([performedSession]).mockImplementation(() => new Promise(() => {}));
    mocks.stage.mockResolvedValue(stagedSession);
    mocks.publish.mockResolvedValue(publishedSession);
    render(<DiagnosticSessions lab />);

    const input = await screen.findByLabelText("Report PDF (up to 3 MB)");
    expect(screen.queryByRole("button", { name: "Finish lab session" })).not.toBeInTheDocument();
    const file = new File(["report"], "result.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.submit(input.closest("form")!);

    const finish = await screen.findByRole("button", { name: "Finish lab session" });
    expect(mocks.stage).toHaveBeenCalledWith(performedSession.id, file, undefined, undefined);
    const verification = screen.getByRole("checkbox", { name: /I checked that the PDF matches/ });
    expect(verification).toBeRequired();
    fireEvent.click(finish);
    expect(mocks.publish).not.toHaveBeenCalled();

    fireEvent.click(verification);
    fireEvent.click(finish);
    const history = await screen.findByRole("region", { name: "Finished lab sessions" });
    expect(within(history).getByText("Session finished")).toBeInTheDocument();
    expect(within(history).getByText("Open published PDF")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Lab sessions" })).queryByRole("heading", { name: performedSession.test_name })).not.toBeInTheDocument();
    expect(mocks.publish).toHaveBeenCalledExactlyOnceWith(performedSession.id, 1);
  });

  it("shows the finish action for a previously uploaded draft with the preview closed", async () => {
    mocks.sessions.mockResolvedValue([stagedSession]);
    render(<DiagnosticSessions lab />);

    expect(await screen.findByRole("button", { name: "Finish lab session" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Preview draft PDF" })).toHaveAttribute("aria-expanded", "false");
  });

  it("loads finished sessions under previously assigned tests alongside the doctor-assigned list", async () => {
    mocks.auth.mockReturnValue({ status: "authenticated", isRequiredPortal: true, claims: { sid: "lab" }, refreshSession: vi.fn() });
    mocks.me.mockResolvedValue({ role_code: "LAB_TECHNICIAN", verification_status: "VERIFIED" });
    mocks.professional.mockResolvedValue({ tests: [{ ...testRecord, status: "IN_PROGRESS" }] });
    mocks.sessions.mockImplementation(async (_lab, _page, finished) => finished ? [publishedSession] : []);
    render(<DiagnosticsPage portal="PROFESSIONAL" />);

    fireEvent.click(await screen.findByText("Previously assigned diagnostic tests"));
    const history = await screen.findByRole("region", { name: "Finished lab sessions" });
    expect(await within(history).findByRole("heading", { name: publishedSession.test_name })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Doctor-assigned tests" })).getByRole("link", { name: "Open lab report" })).toBeInTheDocument();
    expect(mocks.sessions).toHaveBeenCalledWith(true, 1, false);
    expect(mocks.sessions).toHaveBeenCalledWith(true, 1, true);
  });
});
