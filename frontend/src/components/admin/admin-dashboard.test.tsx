import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { ApiError } from "@/lib/api/errors";
import { accessTokenStore } from "@/lib/auth/token-store";
import { AdminDashboard } from "./admin-dashboard";

const mocks = vi.hoisted(() => ({ logout: vi.fn(), refreshSession: vi.fn(), replace: vi.fn() }));
vi.mock("@/lib/auth/actions", () => ({ logout: mocks.logout, logoutAll: vi.fn(), refreshSession: mocks.refreshSession, replaceSession: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));

const admin = { admin_id: "admin-1", email: "admin@example.com", first_name: "Trusted", is_super_admin: true, last_name: "Operator", user_id: "user-1" };
function token(portal: "ADMIN" | "CITIZEN") { const e=(v:object)=>btoa(JSON.stringify(v)).replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_"); const n=Math.floor(Date.now()/1000); return `${e({alg:"none"})}.${e({exp:n+1800,iat:n,jti:"j",portal,sid:"s",sub:"u",type:"access"})}.x`; }
function renderDashboard(loadAction = vi.fn().mockResolvedValue(admin)) { render(<AuthProvider><AdminDashboard loadAction={loadAction} /></AuthProvider>); return loadAction; }

describe("AdminDashboard", () => {
  beforeEach(() => { accessTokenStore.clear(); mocks.logout.mockReset(); mocks.refreshSession.mockReset(); mocks.replace.mockReset(); });

  it("hydrates an admin session and loads only current trusted account data", async () => {
    mocks.refreshSession.mockImplementation(async () => { const value=token("ADMIN"); accessTokenStore.set(value); return value; });
    const load = renderDashboard();
    expect(await screen.findByText("Welcome, Trusted.")).toBeInTheDocument();
    expect(load).toHaveBeenCalledOnce();
    expect(screen.getByText("Super administrator")).toBeInTheDocument();
  });

  it("blocks a different portal before loading admin data", () => {
    act(() => accessTokenStore.set(token("CITIZEN")));
    const load = renderDashboard();
    expect(screen.getByText("Admin Portal access required")).toBeInTheDocument();
    expect(load).not.toHaveBeenCalled();
  });

  it("shows sign-in after failed cookie hydration", async () => {
    mocks.refreshSession.mockRejectedValue(new ApiError(401, "Expired"));
    const load = renderDashboard();
    expect(await screen.findByText("Admin sign in required")).toBeInTheDocument();
    expect(load).not.toHaveBeenCalled();
  });

  it("logs out and returns to separate admin login", async () => {
    act(() => accessTokenStore.set(token("ADMIN")));
    mocks.logout.mockImplementation(async () => accessTokenStore.clear());
    renderDashboard();
    await screen.findByText("Welcome, Trusted.");
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(mocks.logout).toHaveBeenCalledOnce());
    expect(mocks.replace).toHaveBeenCalledWith("/admin/login");
    expect(mocks.refreshSession).not.toHaveBeenCalled();
  });
});
