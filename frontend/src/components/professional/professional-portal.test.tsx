import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/components/auth/auth-provider";
import { accessTokenStore } from "@/lib/auth/token-store";

const mocks = vi.hoisted(() => ({ load: vi.fn(), refresh: vi.fn(), replace: vi.fn() }));
vi.mock("@/lib/professional/api", () => ({ loadProfessionalMe: mocks.load }));
vi.mock("@/lib/auth/actions", () => ({ logout: vi.fn(), logoutAll: vi.fn(), refreshSession: mocks.refresh, replaceSession: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));

import { ProfessionalPortal } from "./professional-portal";

function token(portal: "PROFESSIONAL" | "CITIZEN") { const e=(v:object)=>btoa(JSON.stringify(v)).replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_"); const n=Math.floor(Date.now()/1000); return `${e({alg:"none"})}.${e({exp:n+1800,iat:n,jti:"j",portal,prrid:"r1",sid:"s",sub:"u",type:"access"})}.x`; }
const base = { user_id:"u",professional_id:"p",role_registration_id:"r1",first_name:"Amina",last_name:"Rahman",email:"a@example.com",role_code:"DOCTOR",role_name:"Doctor",designation:"Consultant",facility:{id:"f",name:"General Hospital",facility_type:"HOSPITAL",address:"Dhaka"},submitted_at:"2026-08-10T00:00:00Z",verified_at:null,rejected_at:null,rejection_reason:null };

describe("ProfessionalPortal",()=>{
  beforeEach(()=>{accessTokenStore.clear();mocks.load.mockReset();mocks.refresh.mockReset();mocks.replace.mockReset()});
  it("blocks another portal before loading private role data",()=>{act(()=>accessTokenStore.set(token("CITIZEN")));render(<AuthProvider><ProfessionalPortal mode="dashboard" /></AuthProvider>);expect(screen.getByText("Professional Portal access required")).toBeInTheDocument();expect(mocks.load).not.toHaveBeenCalled()});
  it("limits pending dashboard sessions to verification status",async()=>{act(()=>accessTokenStore.set(token("PROFESSIONAL")));mocks.load.mockResolvedValue({...base,verification_status:"PENDING"});render(<AuthProvider><ProfessionalPortal mode="dashboard" /></AuthProvider>);expect(await screen.findByText("PENDING role is restricted")).toBeInTheDocument();expect(screen.queryByText("Verified role context")).not.toBeInTheDocument()});
  it("shows only the selected verified role and linked facility",async()=>{act(()=>accessTokenStore.set(token("PROFESSIONAL")));mocks.load.mockResolvedValue({...base,verification_status:"VERIFIED",verified_at:"2026-08-10T01:00:00Z"});render(<AuthProvider><ProfessionalPortal mode="dashboard" /></AuthProvider>);expect(await screen.findByText("Verified role context")).toBeInTheDocument();expect(screen.getByText("General Hospital")).toBeInTheDocument();expect(screen.getAllByText("Doctor").length).toBeGreaterThan(0)});
  it("shows rejected reason in the restricted status view",async()=>{act(()=>accessTokenStore.set(token("PROFESSIONAL")));mocks.load.mockResolvedValue({...base,verification_status:"REJECTED",rejection_reason:"Credentials could not be validated."});render(<AuthProvider><ProfessionalPortal mode="status" /></AuthProvider>);expect(await screen.findByText("Credentials could not be validated.")).toBeInTheDocument();expect(screen.getByText("This restricted session can display verification status only.")).toBeInTheDocument()});
});
