# HealthLink

HealthLink is a modular healthcare information platform with separate Citizen,
Professional, and Admin portal contexts. This repository implements the
documented roadmap sequentially through Phase 14 and intentionally stops before
Phase 15.

The current Phase 14 production release is available at
[healthlink-sd.vercel.app](https://healthlink-sd.vercel.app/). It is deployed as
one Vercel Services project: Next.js serves the web interface, FastAPI serves
`/api/v1/*` and `/health`, Supabase PostgreSQL stores application data, and
private Vercel Blob storage holds prescription PDFs.

## Applications

- `backend/` — FastAPI, SQLAlchemy, Alembic, and PostgreSQL
- `frontend/` — Next.js App Router, TypeScript, and Tailwind CSS
- `docs/` — implementation decisions, assumptions, and phase verification

The three Markdown files at the repository root are the governing project
documents and are preserved under their attached filenames.

## Implemented product through Phase 14

- Citizen registration, authentication, profile and protected identity
  management, verified-doctor discovery, appointment booking/cancellation,
  appointment history, and prescription access.
- Professional onboarding with one active role context, administrator review,
  doctor practice schedules, chamber queues, consultation notes, structured
  prescriptions, and atomic appointment completion.
- Trusted administrator authentication, facility management, professional
  verification/rejection, and controlled citizen-identity support.
- Same-origin refresh-cookie authentication with in-memory access tokens and
  backend-authoritative portal, role, ownership, and record-access checks.

## Current interface

- A citizen-first public landing page keeps administrator access out of the
  public navigation and provides clear citizen and professional entry points.
- Authenticated portals share a compact account header, a dedicated text-link
  navigation row, and a collapsible/resizable icon sidebar. Mobile layouts use the
  existing navigation drawer instead of duplicating the desktop row.
- Citizen Overview is reserved for care discovery and appointments. The
  `Add a professional role` account action lives in Citizen Profile alongside
  profile and identity management.
- National identifiers remain absent from Citizen Overview and are shown only
  inside the authorized Profile and identity workflow.

## Local prerequisites

- Python 3.13+
- Node.js 24.15+
- PostgreSQL 17+ (or a Neon PostgreSQL connection)

## Backend quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
# Set DATABASE_URL and a 32+ character JWT_SECRET_KEY in backend/.env.
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API health check is available at `http://localhost:8000/health`.

## Frontend quick start

```powershell
Set-Location frontend
npm.cmd install
Copy-Item .env.example .env.local
npm.cmd run dev
```

The web application is available at `http://localhost:3000`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
Set-Location frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test -- --run
npm.cmd run build
```

See [implementation progress](docs/implementation-progress.md) for phase-by-phase
status and verification evidence.

Future agents should begin with the
[Phase 0–14 implementation handoff](AGENTIC_IMPLEMENTATION_HANDOFF_PHASES_0_TO_14.md).
It records the exact Phase 14 boundary and the rules for starting Phase 15.

For production CI/CD and Vercel setup, see the
[GitHub Actions and Vercel deployment guide](docs/VERCEL_GITHUB_ACTIONS_DEPLOYMENT.md).
