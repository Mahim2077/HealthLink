# HealthLink frontend

The Next.js App Router frontend implements the complete authorized HealthLink
surface through Phase 14. Citizen, Professional, and Admin portals share one
responsive design system while retaining isolated authentication contexts and
role-specific navigation.

## Local setup

1. Copy `.env.example` to `.env.local` only when an override is needed.
2. Install dependencies with `npm install`.
3. Start development with `npm run dev`.

The default frontend address is `http://localhost:3000`. Browser API calls use
root-relative `/api/v1`; local Next.js rewrites forward them to
`HEALTHLINK_BACKEND_ORIGIN`, which defaults to `http://127.0.0.1:8000`.

## Current design system

- The public landing page is citizen-first, with separate citizen and
  professional sign-in destinations and no public administrator prompt.
- Authenticated pages share `PortalShell`: a compact identity header, a
  dedicated horizontally scrollable text-navigation row, and a
  collapsible/resizable icon sidebar.
- Below the desktop breakpoint, the text row and sidebar give way to the
  existing modal navigation drawer.
- Citizen Overview focuses on finding care and managing appointments. The
  account-level `Add a professional role` action is intentionally placed in
  Citizen Profile beside profile and identity controls.
- Identity values are excluded from Citizen Overview and masked within the
  authorized Profile and identity workflow.

## Portal routes

### Citizen

- `/citizen/register` and `/citizen/login`
- `/citizen/dashboard` for the care-focused overview
- `/citizen/doctors/search` and `/citizen/doctors/[doctor_user_id]`
- `/citizen/appointments` and `/citizen/appointments/book`
- `/citizen/profile`, including professional-role onboarding entry
- `/citizen/prescriptions/[prescription_id]`

### Professional

- `/professional/register`, `/professional/onboard`, and `/professional/login`
- `/professional/dashboard` and `/professional/status`
- `/professional/chamber` and `/professional/visits`
- `/professional/prescriptions/[prescription_id]`

### Admin

- `/admin/login` and `/admin/dashboard`
- `/admin/professional-registrations` and its detail route
- `/admin/facilities`
- `/admin/citizen-identities` and its controlled detail/correction route

## Authentication foundation

- Access tokens exist only in the in-memory access-token store.
- Refresh tokens remain in backend-issued HttpOnly cookies, and refresh,
  logout, logout-all, and session replacement share one serialization barrier.
- JWT decoding supports portal-aware presentation only; backend portal,
  session, role, ownership, and record-access checks remain authoritative.
- Direct-route guards prevent private data requests before the correct portal
  session has been restored.

## Quality commands

```powershell
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Vitest and Testing Library cover components and API adapters. The production
build currently generates 22 application routes without introducing Phase 15
features.
