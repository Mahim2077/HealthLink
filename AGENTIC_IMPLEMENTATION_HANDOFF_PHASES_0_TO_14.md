# HealthLink Phase 0–14 implementation handoff

Last updated: 2026-09-04 (Asia/Dhaka)

Repository: `D:\HealthLink_V_1`

Branch: `main`
Final requested state: Phases 0–14 complete; Phase 15 not authorized.

This handoff is a navigation aid. It does not replace the three governing
documents. Before changing the project, read them completely in this order:

1. `HealthLink_Agentic_AI_Implementation_Prompt_Phases_0_to_14(4).md`
2. `HealthLink_Synchronized_System_Database_Implementation_Plan_V6(3).md`
3. `HealthLink_System_Context_and_Developer_Documentation(3).md`

Do not rename, move, overwrite, or normalize those source documents. Their
expected SHA-256 values are:

```text
C2407EA01D895CA3016C661090F65CD98982B3E693FB0ECC85859641B2A5E85F
  HealthLink_Agentic_AI_Implementation_Prompt_Phases_0_to_14(4).md

7F8CC1B2268DBC1B6CFD9CB421C2D065ADEAF76CAA882AE9D9730BBC62CC0E7F
  HealthLink_Synchronized_System_Database_Implementation_Plan_V6(3).md

A10EBADE322D9A238DF61CFE118D2088067756F0CF5D4A375AACB51C6828CF8E
  HealthLink_System_Context_and_Developer_Documentation(3).md
```

## Current checkpoint

| State | Count | Phases |
| --- | ---: | --- |
| Fully implemented and verified | 15 | 0–14 |
| Remaining in authorized scope | 0 | — |
| Not authorized | 1+ | 15 onward |

Phase 14 code is represented by these commits:

```text
2f346d6  feat(phase-14): finish appointments atomically
6b07440  test(phase-14): clean PostgreSQL fixtures in FK order
170e952  test(phase-14): bound concurrent finish checks
```

The `phase-14-complete` tag identifies the final documentation checkpoint.
GitHub Actions HealthLink CI/CD run 12 passed for `170e952`, including the
PostgreSQL test suite, frontend gates, production migration, prebuilt Vercel
deployment, and root/health smoke tests.

Production is served by the single Vercel Services project at
`https://healthlink-sd.vercel.app/`:

- Next.js frontend at `/`
- FastAPI at `/api/v1/*`
- health check at `/health`
- Supabase PostgreSQL as the production database
- private Vercel Blob storage for prescription PDFs

Credentials and environment values remain only in ignored local files, GitHub
secrets, and Vercel environment configuration. Never place them in source,
logs, documentation, commits, or chat output.

## Final Phase 14 behavior

The canonical endpoint is:

```text
POST /api/v1/appointments/{appointment_id}/finish
```

It requires all of the following:

- an authenticated PROFESSIONAL session;
- the active role registration is a VERIFIED DOCTOR;
- that role registration owns the appointment and practice session;
- the practice session is ACTIVE;
- the appointment is BOOKED and its queue row is CURRENT;
- a matching DRAFT medical visit exists;
- a prescription is optional.

The service executes one transaction under the existing per-doctor/date
PostgreSQL advisory lock and row locks:

```text
medical visit       DRAFT → FINALIZED
appointment         BOOKED → COMPLETED
current queue row   CURRENT → DONE
lowest eligible row WAITING → CURRENT (when one exists)
```

A retry is idempotent only when all three terminal states already agree. It
returns the existing CURRENT successor and never promotes another row. A
partial terminal combination returns a conflict. Any failure before commit
rolls back all lifecycle changes.

The old Phase 11 queue-only Complete endpoint and button were removed because
they could bypass the required medical-visit finalization. Skip, no-show,
remove, call-next, start-session, and finish-session remain queue operations.

The consultation workspace now owns the Finish Appointment action. After a
successful response it reloads the authoritative current-patient endpoint,
then renders the next serial or the no-active-patient state. The success
message uses the finish response's narrow queue projection. Verified author
doctors retain prescription edit/regeneration rights after completion.

No payment table, gateway, billing state, API, or UI was introduced. Chamber
payment remains entirely offline through Phase 14.

## Phase 14 verification evidence

- Alembic head: `0023_prescription_documents`; no Phase 14 migration was
  needed because all lifecycle fields and constraints already existed.
- Configured Supabase schema: at head; `alembic check` reports no drift.
- Backend against workspace-local PostgreSQL 17: `236 passed`.
- Backend SQLite pass: `202 passed, 34 skipped` (PostgreSQL-only cases).
- Phase 14 chamber PostgreSQL cases: `4 passed`, including simultaneous finish
  requests that both observe serial 2 while rows remain exactly
  DONE/CURRENT/WAITING.
- Frontend: ESLint passed, TypeScript passed, 37 Vitest files / 173 tests
  passed, optimized Next.js build passed with 22 generated routes.
- Python dependencies: `pip check` passed.
- Governing document hashes matched the values above.
- GitHub Actions run 12 passed end to end and deployed `170e952`.
- Live browser: a synthetic verified doctor opened serial 1 in the deployed
  consultation workspace, finished without a prescription, and naturally saw
  serial 2.
- Live API/database follow-up: repeating serial 1 finish returned serial 2
  without skipping it; serial 2 was opened and finished; no CURRENT row
  remained; both visits were FINALIZED, appointments COMPLETED, and queue rows
  DONE in Supabase.
- All exact synthetic users, profiles, role registration, facility,
  appointments, queue rows, visits, and auth sessions were removed afterward.

The first Phase 14 pipeline attempt failed only in the new PostgreSQL test's
fixture teardown: it deleted a user before the user's practice-schedule row.
The production assertions had passed. Commit `6b07440` corrected foreign-key
cleanup order. Commit `170e952` additionally bounded the concurrent test's
barrier and PostgreSQL lock/statement waits so a future runner fails
diagnostically instead of hanging. Runs 11 and 12 then passed end to end.

## Implementation map

### Database and backend

- `backend/app/appointments/repository.py`: owner-scoped finish context,
  serial-ordered queue reads, transaction-lock support.
- `backend/app/appointments/service.py`: atomic finish, idempotency,
  consistency guards, automatic promotion, rollback.
- `backend/app/appointments/routes.py`: canonical appointment finish route;
  retired queue-only completion route.
- `backend/app/appointments/schemas.py`: finish response contract.
- `backend/app/visits/repository.py`: appointment visit lookup with optional
  row lock.
- `backend/app/api/v1/router.py`: lifecycle router wiring.
- `backend/tests/test_chamber.py`: authentication, ownership, preconditions,
  success, optional prescription, idempotency, last patient, rollback, and
  post-completion author-edit coverage.
- `backend/tests/test_chamber_postgresql.py`: real concurrent-finish and queue
  invariant coverage.

### Frontend

- `frontend/src/lib/appointments/{api,types}.ts`: finish call and response.
- `frontend/src/lib/chamber/{api,types}.ts`: exact backend enums and queue-only
  action surface.
- `frontend/src/components/professional/consultation-workspace.tsx`: finish
  action and natural next-patient refresh.
- `frontend/src/components/professional/chamber-queue.tsx`: retired Complete
  action, fixed NOT_STARTED-session opening, exact status rendering.
- `frontend/src/app/professional/visits/page.tsx`: finish dependency wiring.
- `frontend/src/app/citizen/appointments/page.tsx`: complete authoritative
  appointment-status labels, including NO_SHOW and REMOVED_BY_DOCTOR.
- Matching API/component tests cover success and failure flows.

## Phase history

- Phase 0: FastAPI/Next.js foundation, settings, migrations, health, base UI.
- Phase 1: shared JWT access tokens and opaque refresh sessions.
- Phase 2: citizen NID/BCN registration, login, profile, identity reads.
- Phase 3: citizen profile edit and one-time BCN-to-NID addition.
- Phase 4: professional registration, roles, doctor BM&DC details.
- Phase 5: trusted admin provisioning/login and admin action-log foundation.
- Phase 6: facility registry and professional verification/rejection.
- Phase 7: professional login with one active role-registration context.
- Phase 8: admin citizen identity search/detail/correction.
- Phase 9: citizen doctor discovery and doctor practice schedules.
- Phase 10: appointment booking, capacity, serial allocation, queue insertion.
- Phase 11: doctor chamber session and serial queue operations.
- Phase 12: current-patient access, medical visits, consultation workspace.
- Phase 13: structured prescriptions, private PDF generation/delivery, author
  editing, citizen read-only access.
- Phase 14: atomic appointment finish and automatic next serial.

The detailed evidence for every phase is in
`docs/implementation-progress.md`; recorded implementation choices are in
`docs/implementation-assumptions.md`; deployment operation is documented in
`docs/VERCEL_GITHUB_ACTIONS_DEPLOYMENT.md`.

## Architecture and security facts to preserve

- One user may have citizen, professional, and admin capabilities, but portal
  sessions remain isolated as CITIZEN, PROFESSIONAL, or ADMIN.
- A professional session selects exactly one role registration. It is never a
  generic professional capability flag.
- Frontend guards are UX only. Backend portal, session, role, ownership, and
  record-access checks are authoritative.
- Only VERIFIED roles receive clinical capabilities. PENDING and REJECTED
  roles can display status only.
- NID/BCN never belong on `users`, JWTs, URLs, or logs.
- Refresh tokens are opaque and stored only as digests. Browser refresh
  cookies remain HttpOnly, Secure outside local development, SameSite=Lax,
  and scoped to `/api/v1/auth`.
- Access tokens stay in frontend memory only—not localStorage, sessionStorage,
  IndexedDB, readable cookies, URLs, or server-global state.
- Protected requests validate both JWT claims and the live session row.
- PostgreSQL advisory locks, row locks, foreign keys, checks, unique
  constraints, and partial indexes are part of the correctness model.
- Prescription documents remain private and are streamed only after backend
  authorization; storage keys and raw Blob URLs never reach the browser.

## Reproducing the final quality gates

Use ignored local environment configuration; never paste production values
into commands, docs, or tracked files.

```powershell
# Backend. Set the dedicated PostgreSQL test URL in the current shell first.
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check

# Migration metadata check from backend/.
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic check

# Frontend from frontend/.
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

On this Windows host, sandboxed Vitest or Next.js can receive `EPERM` while
writing generated files under `node_modules/.vite-temp` or `.next`. Approved
execution outside the sandbox works. Do not delete broad directories; inspect
and resolve any exact generated target first.

## Safe continuation

1. Confirm `git status --short` is clean and `main` matches `origin/main`.
2. Read the governing documents and this final-state handoff.
3. Preserve ignored `.env` and `.vercel` configuration; never expose secrets.
4. Treat Phases 0–14 as the completed baseline.
5. Do not implement Phase 15 or later behavior without explicit user
   instruction.

The authorized task is complete at Phase 14. Stop here.
