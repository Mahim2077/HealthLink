import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { testSessionStore } from "@/test/session-store";

const mocks = vi.hoisted(() => ({ load: vi.fn(), refresh: vi.fn(), replace: vi.fn(), setup: vi.fn() }));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.load, setupProfessionalCitizenProfile: mocks.setup }));
vi.mock("@/lib/auth/actions", () => ({ logout: vi.fn(), logoutAll: vi.fn(), refreshSession: mocks.refresh, replaceSession: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));

import { ProfessionalPortal } from "./professional-portal";

function token(portal: "PROFESSIONAL" | "CITIZEN") { const e=(v:object)=>btoa(JSON.stringify(v)).replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_"); const n=Math.floor(Date.now()/1000); return `${e({alg:"none"})}.${e({exp:n+1800,iat:n,jti:"j",portal,prrid:"r1",sid:"s",sub:"u",type:"access"})}.x`; }
const base = { user_id:"u",professional_id:"p",role_registration_id:"r1",first_name:"Amina",last_name:"Rahman",email:"a@example.com",role_code:"DOCTOR",role_name:"Doctor",designation:"Consultant",facility:{id:"f",name:"General Hospital",facility_type:"HOSPITAL",address:"Dhaka"},submitted_at:"2026-08-10T00:00:00Z",verified_at:null,rejected_at:null,rejection_reason:null };

describe("ProfessionalPortal",()=>{
  beforeEach(()=>{testSessionStore.clear();mocks.load.mockReset();mocks.refresh.mockReset();mocks.replace.mockReset();mocks.setup.mockReset()});
  it("blocks another portal before loading private role data", async () => {
    mocks.refresh.mockRejectedValue(new Error("No professional session"));
    act(() => testSessionStore.set(token("CITIZEN")));
    render(<AuthProvider><ProfessionalPortal mode="dashboard" /></AuthProvider>);
    expect(await screen.findByText("Professional sign in required")).toBeInTheDocument();
    expect(mocks.load).not.toHaveBeenCalled();
  });
  it("limits pending dashboard sessions to verification status",async()=>{act(()=>testSessionStore.set(token("PROFESSIONAL")));mocks.load.mockResolvedValue({...base,verification_status:"PENDING"});render(<AuthProvider><ProfessionalPortal mode="dashboard" /></AuthProvider>);expect(await screen.findByText("PENDING role is restricted")).toBeInTheDocument();expect(screen.queryByText("Verified role context")).not.toBeInTheDocument()});
  it("shows only the selected verified role and linked facility",async()=>{act(()=>testSessionStore.set(token("PROFESSIONAL")));mocks.load.mockResolvedValue({...base,verification_status:"VERIFIED",verified_at:"2026-08-10T01:00:00Z"});render(<AuthProvider><ProfessionalPortal mode="dashboard" /></AuthProvider>);expect(await screen.findByText("Verified role context")).toBeInTheDocument();expect(screen.getByText("General Hospital")).toBeInTheDocument();expect(screen.getAllByText("Doctor").length).toBeGreaterThan(0)});
  it("shows rejected reason in the restricted status view",async()=>{act(()=>testSessionStore.set(token("PROFESSIONAL")));mocks.load.mockResolvedValue({...base,verification_status:"REJECTED",rejection_reason:"Credentials could not be validated."});render(<AuthProvider><ProfessionalPortal mode="status" /></AuthProvider>);expect(await screen.findByText("Credentials could not be validated.")).toBeInTheDocument();expect(screen.getByText("Clinical tools become available after this role is verified.")).toBeInTheDocument()});

  it("offers setup to a doctor whose application is under review", async () => {
    act(() => testSessionStore.set(token("PROFESSIONAL")));
    mocks.load.mockResolvedValue({ ...base, verification_status: "PENDING", has_citizen_profile: false });
    render(<AuthProvider><ProfessionalPortal mode="status" /></AuthProvider>);
    expect(await screen.findByRole("link", { name: "Set up Citizen profile" })).toHaveAttribute("href", "/professional/citizen-profile");
  });

  it("shows a Citizen sign-in link after the doctor supplies profile details", async () => {
    act(() => testSessionStore.set(token("PROFESSIONAL")));
    mocks.load.mockResolvedValue({ ...base, verification_status: "PENDING", has_citizen_profile: false });
    mocks.setup.mockResolvedValue(undefined);
    render(<AuthProvider><ProfessionalPortal mode="citizen-profile" /></AuthProvider>);

    fireEvent.change(await screen.findByLabelText(/Date of birth/), { target: { value: "1985-04-21" } });
    fireEvent.change(screen.getByLabelText(/^Gender/), { target: { value: "FEMALE" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Citizen profile" }));

    expect(await screen.findByRole("link", { name: "Sign in to Citizen Portal" })).toHaveAttribute("href", "/citizen/login");
    expect(mocks.setup).toHaveBeenCalledExactlyOnceWith({ date_of_birth: "1985-04-21", gender: "FEMALE" });
    expect(screen.queryByLabelText(/Date of birth/)).not.toBeInTheDocument();
  });
});
