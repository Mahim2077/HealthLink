# HealthLink Phase 0–14 implementation handoff

Last updated: 2026-08-10 (Asia/Dhaka)  
Repository: `D:\HealthLink_V_1`  
Branch: `master`  
Last committed Phase checkpoint: `a5ec66c feat: complete phase 6 professional verification`
Last verified phase backend-completion: Phase 9 (backend only, 161/161 tests including 4 new PostgreSQL tests; frontend not started)
verified, and the remaining work through Phase 14. It does not replace the
three governing documents.

Before changing the repository, read all three files completely in this exact
priority order:

1. `HealthLink_Agentic_AI_Implementation_Prompt_Phases_0_to_14(4).md` —
   execution instructions and implementation rules.
2. `HealthLink_Synchronized_System_Database_Implementation_Plan_V6(3).md` —
   authoritative architecture, database, API, authorization, migration, and
   phase source of truth.
3. `HealthLink_System_Context_and_Developer_Documentation(3).md` — conceptual,
   workflow, terminology, and business context.

Do not rename, move, overwrite, or normalize the source documents. Their actual
attached filenames include `(4)` and `(3)`.

Expected SHA-256 values:

```text
C2407EA01D895CA3016C661090F65CD98982B3E693FB0ECC85859641B2A5E85F
  HealthLink_Agentic_AI_Implementation_Prompt_Phases_0_to_14(4).md

7F8CC1B2268DBC1B6CFD9CB421C2D065ADEAF76CAA882AE9D9730BBC62CC0E7F
  HealthLink_Synchronized_System_Database_Implementation_Plan_V6(3).md

A10EBADE322D9A238DF61CFE118D2088067756F0CF5D4A375AACB51C6828CF8E
  HealthLink_System_Context_and_Developer_Documentation(3).md
```

## Non-negotiable execution boundary

- Implement sequentially. Finish the current phase as a complete vertical slice
  before beginning the next phase.
- A phase includes database/Alembic, backend, frontend, authorization,
  dependency manifests, automated tests, live PostgreSQL checks, and real
  browser-flow verification where applicable.
- Do not pull future-phase features forward merely because the full schema
  describes them.
- Preserve route → service → repository layering and authoritative backend
  authorization.
- Use PostgreSQL for database-specific locking, partial indexes, foreign keys,
  constraints, and concurrency acceptance.
- Keep exactly one `backend/requirements.txt` and one synchronized frontend
  package/lock manifest.
- Record any unspecified minor choice in
  `docs/implementation-assumptions.md`.
- Update `docs/implementation-progress.md` only after a phase passes every gate.
- Stop after Phase 14. Do not begin Phase 15 without explicit user instruction.

## Progress at a glance

There are 15 requested phases numbered 0 through 14.

| State | Count | Phases |
| --- | ---: | --- |
| Fully implemented, verified, documented, committed | 7 | 0–6 |
| Fully implemented, verified, **uncommitted** (frontend + docs merged; commit pending) | 2 | 7, 8 |
| Backend fully implemented and verified; frontend pending | 1 | 9 |
| Not started | 5 | 10–14 |

Therefore, six phase gates remain: ship Phase 9 frontend, then complete Phases 10–14.

## Verified commit checkpoints

```text
836a300  feat: complete phase 0 foundation
bd3eb38  feat: complete phase 1 shared authentication
384bed7  feat: complete phase 2 citizen access
379c1cc  feat: complete phase 3 citizen profile
5501422  feat: complete phase 4 professional registration
349c4b1  feat: complete phase 5 admin portal
a5ec66c  feat: complete phase 6 professional verification
```

The worktree after `a5ec66c` contains intentional, uncommitted Phase 7 work.
Do not discard or reset it.

## Completed phase summary

### Phase 0 — Project foundation

- FastAPI app, settings, CORS, exception handling, `/health`, `/api/v1`,
  SQLAlchemy session/Base, Alembic foundation, environment examples, docs, and
  backend tests.
- Next.js App Router with TypeScript, Tailwind, ESLint, shared UI states, API
  configuration, tests, lockfile, responsive landing page, and browser smoke.

### Phase 1 — Shared JWT authentication and refresh sessions

- `users` and `auth_sessions`; migrations `0001` and `0002`.
- Argon2 passwords, fixed-algorithm JWT access tokens, opaque hashed refresh
  tokens, fixed-expiry rotation, logout, logout-all, portal authorization, and
  cross-tab refresh/logout protection.
- Frontend access tokens remain in memory only. Refresh is single-flight.
  Login/session replacement and logout mutations are serialized to protect
  HttpOnly cookie ordering.

### Phase 2 — Citizen registration and login

- Migrations `0003`–`0005`: central NID, citizen profile, citizen identity.
- NID/BCN initial XOR, globally unique identity, transactional registration,
  citizen login, `/citizens/me`, and `/citizens/me/identity`.
- Citizen registration, login, dashboard, refresh hydration, logout, masked
  identity display, PostgreSQL conflict/concurrency coverage, and browser flows.

### Phase 3 — Citizen profile and one-time BCN → NID upgrade

- No new migration was needed; the Phase 2 schema intentionally supports the
  retained-BCN-plus-NID state.
- Full profile update and row-locked, exact-`CONFIRM`, one-time NID addition.
- Browser and database verification confirmed BCN retention and `nid_added_at`.

### Phase 4 — Professional registration and role catalog

- Migrations `0006`–`0009`: professional profiles, six-role catalog and seed,
  role registrations, doctor BM&DC details.
- Public NID-only registration and authenticated existing-citizen onboarding.
- Facility remained submitted free text; facility FK was correctly deferred.

### Phase 5 — Admin login and portal

- Migrations `0010` and `0011`: trusted admin accounts and admin action logs.
- Trusted password-prompting provisioning utility; no public admin registration.
- ADMIN login/me, portal isolation, responsive admin dashboard, constant-work
  login failure, and browser/session checks.

### Phase 6 — Facility registry and professional verification

- Migrations `0012_facilities` and `0013_role_facility_fk`.
- Exact healthcare facility registry and delayed nullable facility link.
- Seven documented admin endpoints for facility CRUD and professional
  queue/detail/verify/reject.
- Row-locked terminal review decision, active facility requirement, exact
  rejection reason, and transactional admin auditing.
- Last complete gate results:

```text
Backend full suite against PostgreSQL 17: 115 passed
Frontend full suite: 23 files / 98 tests passed
ESLint: passed
TypeScript: passed
Next.js production build: passed
Alembic downgrade to Phase 5 and re-upgrade: passed on dev and test databases
Alembic current/check: 0013_role_facility_fk, clean at Phase 6 checkpoint
Browser: facility create/update, doctor verify, lab reject, filters,
         logout/direct guard, 390/768/1280 widths, clean console
```

The Phase 6 browser data showed a VERIFIED doctor linked to a real facility and
a REJECTED lab technician with the exact stored reason. Database inspection
confirmed facility and review audit rows.

### Phase 7 — Professional login and active role context (backend + frontend verified, **commit pending**)

- Migration `0014_auth_active_role` adds nullable
  `auth_sessions.active_professional_role_registration_id` (RESTRICT FK).
- Access JWTs optionally carry `prrid`; refresh reissues it from the locked
  session row.
- `AuthService.create_session` requires an active role ID for PROFESSIONAL
  sessions and forbids one on CITIZEN/ADMIN sessions.
- New endpoint `POST /api/v1/auth/professional/login` (NID + password +
  selected role registration ID) plus `GET /api/v1/professionals/me`.
- Generic login failure for unknown NID, wrong password, inactive user,
  unowned role; password verification uses a valid dummy Argon2 hash for the
  fake-user path.
- Professional sessions are user + exactly one selected role registration; lab
  selection cannot access doctor-only routes even if the same user also owns a
  verified doctor role.
- Refresh restoration reproduces the exact selected role.
- Verified, pending, and rejected sessions each render correctly: VERIFIED
  sees only the selected-role shell and linked facility; PENDING and REJECTED
  see a status-only view with no clinical capabilities.
- Frontend: `/professional/login`, `/professional/dashboard`,
  `/professional/status`; refresh-based PROFESSIONAL portal guard; root
  Professional Portal card exposes sign-in alongside new-registration and
  existing-citizen onboarding.

### Phase 8 — Admin citizen identity support (backend + frontend verified, **commit pending**)

- No new migration; Phase 8 only reads and writes `users`,
  `user_national_identifiers`, `citizen_profiles`, `citizen_identifiers`, and
  `admin_action_logs` introduced by Phases 1–5.
- Three endpoints under `/api/v1/admin/citizen-identities`: `search`,
  `{user_id}` detail, and `{user_id}/correct`.
- Search accepts `q`, `nid_number`, `birth_certificate_number`, `email`,
  `user_id`, and `limit` (1–100).
- Correction request is constrained to `correction_type ∈ {NID, BCN}`,
  `new_value` (3–64 chars), and a mandatory `reason` (5–500 chars).
- Service re-checks uniqueness against the live registry (cross-citizen NID and
  BCN collisions both rejected).
- Every correction writes an `admin_action_logs` row.
- Frontend: `/admin/citizen-identities` (search + table) and
  `/admin/citizen-identities/[user_id]` (detail + correction form with
  type toggle, retry on error, distinct form-error state so the "Provide at
  least one filter" message is not duplicated by the search banner).
- Static route count grew from 15 to 17.

### Phase 9 — Doctor search and practice schedule (**backend complete and verified; frontend pending**)

- Migration `0015_doctor_practice_schedules` introduces the
  `doctor_practice_schedules` table with FKs to `users` (RESTRICT),
  `healthcare_facilities` (RESTRICT, `is_active` enforced in service), and a
  set of check constraints: `max_patients_positive`,
  `end_after_start`, `valid_weekday`, and `valid_status`.
- New `backend/app/doctors/` sub-package exposes:
  `GET /api/v1/citizens/doctors/search`,
  `GET /api/v1/citizens/doctors/{doctor_user_id}`,
  `GET /api/v1/doctors/me/practice-schedule`,
  `POST /api/v1/doctors/me/practice-schedule`,
  `PATCH /api/v1/doctors/me/practice-schedule/{schedule_id}`, and
  `DELETE /api/v1/doctors/me/practice-schedule/{schedule_id}`.
- Citizen search filters by doctor/facility name (case-insensitive trim+lower
  match on concatenated name and on facility name) and optional weekday;
  returns the active role registration only for VERIFIED doctors with a
  non-null `facility_id`. Doctor profile returns masked identity, BMDC
  registration number, mapped facility, and active practice days.
- Admin search reuses the same citizen search route via admin session.
- Schedule management requires `require_verified_professional_role(
  role="DOCTOR")` and additionally enforces
  `professional_id == current_user.id` ownership; inactive facilities are
  rejected at create/update.
- Last complete gate results:

```text
Backend full suite against live local PostgreSQL 17: 161 passed
  including new backend/tests/test_doctor_search.py (SQLite),
        backend/tests/test_practice_schedule.py (SQLite), and
        backend/tests/test_doctor_search_postgresql.py (4 PG tests).
```

- One repository adjustment was required: the original top-level `.distinct()`
  was removed because PostgreSQL rejects
  `SELECT DISTINCT … ORDER BY <columns-not-in-select-list>`; the weekday path
  now uses an inner `DISTINCT` subquery on
  `healthcare_professional_profiles.id` to keep one row per verified
  registration. SQLite tolerates the previous expression-based ORDER BY;
  PostgreSQL does not. Both engines now return identical result sets.
- **Frontend not started.** No `frontend/src/lib/doctors/{api,types}.ts`,
  no `/citizen/doctors/search` page, no doctor-detail page, no doctor
  practice-schedule editor, no admin search hook. Phase 9 must not be
  marked fully complete nor tagged `phase-9-complete` until those files
  exist and pass lint, TypeScript, Vitest, and the production build gates.

## Current uncommitted work (Phases 7 + 8 + 9-backend)

The Phase 7 + Phase 8 worktrees have both been verified end-to-end
(backend + frontend + migration + tests) and are ready to commit. Phase 9
backend is also verified and ready to commit **as a separate checkpoint**;
Phase 9 frontend is unstarted. Do not bundle the three phases into one
commit; preserve one commit per phase tag.

### Phase 7 — professional login and active role context (uncommitted)

Backend/schema:

- Added migration `backend/alembic/versions/0014_auth_session_active_role.py`.
- Added nullable
  `auth_sessions.active_professional_role_registration_id` with a RESTRICT FK
  to `professional_role_registrations.id`.
- Development and test PostgreSQL databases were upgraded successfully and are
  currently at `0014_auth_active_role`; `alembic check` passed immediately
  after upgrade.
- Access JWTs now optionally carry `prrid`; refresh reissues it from the
  locked session row.
- `AuthService.create_session` requires an active role ID for PROFESSIONAL
  sessions and forbids one on CITIZEN/ADMIN sessions.
- Added professional login request/response and professional-me schemas.
- Added NID + password + selected-role login at
  `POST /api/v1/auth/professional/login`.
- Added `GET /api/v1/professionals/me` as the minimal status/dashboard read
  endpoint required by the Phase 7 frontend and refresh restoration.
- Login permits PENDING, VERIFIED, and REJECTED selected applications but
  creates a session for only the exact selected role registration.
- Added `ProfessionalAuthContext`, session/claim/ownership validation, and
  `require_verified_professional_role(...)` for verified-role and cross-role
  backend enforcement.
- Unknown NID, wrong password, inactive user, and unowned role share the
  generic login failure; password verification uses a valid dummy Argon2 hash.

Frontend:

- Added professional login API/types and serialized `replaceSession(...)` use.
- Added `/professional/login`, `/professional/dashboard`, and
  `/professional/status`.
- Added selected-role login form using the exact six-role catalog.
- Added refresh-based PROFESSIONAL portal guard that does not mount private
  data effects before the correct portal is established.
- PENDING/REJECTED dashboard access is restricted to a status link/view.
  VERIFIED sessions see only the selected role shell and linked facility.
- Updated the root Professional Portal card to include sign-in while retaining
  new-registration and existing-citizen onboarding links.

#### Phase 7 checks already run

```text
Focused backend Phase 7 tests: 5 passed
Frontend Phase 7 focused tests: 4 files / 11 tests passed
Frontend ESLint: passed
Frontend TypeScript: passed
Dev/test Alembic upgrade to 0014: passed
Dev/test Alembic current/check at 0014: passed
```

#### Phase 7 work that still must be done before commit

1. Review the uncommitted diff carefully; do not assume it is final.
2. Confirm the originally written
   `backend/tests/test_professional_login_postgresql.py` now passes against
   the live local PostgreSQL instance (no remaining timezone coercion risk).
3. Run the **full** backend suite against live PostgreSQL, not only SQLite.
4. Confirm the reversible migration cycle `0014 → 0013 → 0014` on dev and
   test databases, then `current` and `alembic check`.
5. Commit Phase 7 alone, tagged `phase-7-complete`, before starting Phase 8.

### Phase 8 — admin citizen identity support (uncommitted)

Backend:

- New `backend/app/admins/identity_*` sub-package exposes the three documented
  Phase 8 endpoints:
  `GET /api/v1/admin/citizen-identities/search`,
  `GET /api/v1/admin/citizen-identities/{user_id}`,
  `POST /api/v1/admin/citizen-identities/{user_id}/correct`.
- Search accepts `q`, `nid_number`, `birth_certificate_number`, `email`,
  `user_id`, `limit` (1–100).
- Correction request constrained to `correction_type ∈ {NID, BCN}`,
  `new_value` 3–64 chars, mandatory `reason` 5–500 chars.
- Service re-checks uniqueness against the live registry for both NID and
  BCN collisions (including cross-citizen collisions).
- Every correction writes an `admin_action_logs` row.
- PostgreSQL behavior verified (FK behavior, conflict rollback, audit row
  appended).

Frontend:

- `/admin/citizen-identities` (search + result table) and
  `/admin/citizen-identities/[user_id]` (detail + correction form with
  type toggle, retry on error, distinct form-error state).
- Admin dashboard links to the new search page.
- Static route count grew from 15 to 17.
- Vitest coverage for `citizen-identity-support.test.tsx` and
  `citizen-identity-detail.test.tsx` (initial workspace loads, trimmed
  filter submission, empty-filter validation, empty result state,
  retry-on-error, identity record load, correction type toggle, submit
  + refresh, required reason, retry-on-load).

#### Phase 8 checks already run

```text
Full backend suite (PostgreSQL 17): 153 passed
Full frontend suite: 27 files / 115 tests passed
ESLint: passed
TypeScript: passed
Production build: passed, two new routes (static count 15 → 17)
Browser interaction flows: passed
```

#### Phase 8 work that still must be done before commit

1. Confirm the two known cross-tab refresh/logout backend-pid assertions
   that fail on Supabase's transaction pooler are unrelated to Phase 8
   (they predate it and are caused by the pooler collapsing concurrent
   sessions, not by Phase 8 schema, routes, or tests).
2. Commit Phase 8 alone, tagged `phase-8-complete`.

### Phase 9 — doctor search and practice schedule (backend uncommitted; frontend not started)

Backend/schema:

- New migration `backend/alembic/versions/0015_doctor_practice_schedules.py`
  introduces the `doctor_practice_schedules` table.
- Dev/test databases upgraded to `0015_doctor_practice_schedules` (chain
  follows `0014_auth_active_role`); `alembic check` clean.
- New `backend/app/doctors/` sub-package exposes:
  `GET /api/v1/citizens/doctors/search`,
  `GET /api/v1/citizens/doctors/{doctor_user_id}`,
  `GET /api/v1/doctors/me/practice-schedule`,
  `POST /api/v1/doctors/me/practice-schedule`,
  `PATCH /api/v1/doctors/me/practice-schedule/{schedule_id}`, and
  `DELETE /api/v1/doctors/me/practice-schedule/{schedule_id}`.
- Admin session can hit the citizen search route.
- Doctor schedule management requires the verified DOCTOR role and
  ownership of `professional_id == current_user.id`; inactive facility
  rejected at create/update.
- All check constraints (`max_patients_positive`, `end_after_start`,
  `valid_weekday`, `valid_status`) verified against live PostgreSQL.
- FK RESTRICT verified for both the doctor user (cascaded reference to
  `user_national_identifiers`) and the facility.

Backend tests:

- New `backend/tests/test_doctor_search.py` (SQLite) and
  `backend/tests/test_practice_schedule.py` (SQLite) covering unauth
  rejection, filter validation, name/facility/weekday filtering, hiding
  unverified doctors, citizen profile + practice-days, 404 for unknown
  doctors, admin reuse of the search route, full schedule CRUD, cross-
  doctor isolation, inactive-facility rejection, and non-doctor
  professionals.
- New `backend/tests/test_doctor_search_postgresql.py` (PostgreSQL)
  with 4 tests: full HTTP flow against the live database, check
  constraint enforcement, FK RESTRICT, and admin route reuse.
- Full backend suite now reports **161 passed** against live local
  PostgreSQL 17.

#### Phase 9 backend checks already run

```text
HEALTHLINK_TEST_DATABASE_URL=postgresql+psycopg://healthlink@127.0.0.1:55432/healthlink_test
Backend full suite (live PG): 161 passed
Alembic upgrade to 0015: passed on dev and test databases
Alembic current/check at 0015: passed
SQLite unit tests for doctor search + practice schedule: passed
```

#### Repository deviation in Phase 9 backend

`backend/app/doctors/repository.py` `search_verified_doctors` had its
top-level `.distinct()` removed. PostgreSQL rejects
`SELECT DISTINCT … ORDER BY <columns-not-in-select-list>`; SQLite
tolerates it. The weekday path now uses an inner `DISTINCT` subquery
on `healthcare_professional_profiles.id` so the row count stays at
one per verified registration. Both engines return identical results.
This change should be mentioned in
`docs/implementation-assumptions.md` if the implementation-assumptions
file is updated this round.

#### Phase 9 work that still must be done before full completion

1. Build the **Phase 9 frontend**:
   - `frontend/src/lib/doctors/{api,types}.ts` (search, profile,
     schedule list/create/update/delete) plus matching `.test.ts`.
   - Citizen-side: `/citizen/doctors/search` page (filter form: name,
     facility, weekday; result list; pagination through `limit`),
     `/citizen/doctors/[doctor_user_id]` page (profile, facility,
     active practice days).
   - Doctor-side: practice-schedule editor wired into
     `/professional/dashboard` (or a dedicated sub-route) using a
     VERIFIED+DOCTOR session.
   - Admin-side: link from the existing admin shell to the citizen
     doctor search endpoint (or a small doctor-search admin page).
2. Run frontend quality gates: ESLint, TypeScript, Vitest,
   production build.
3. Real browser flows against the FastAPI + migrated PostgreSQL:
   - citizen searches by name / facility / weekday, opens detail;
   - doctor creates, edits, and deletes own schedule rows; cannot
     edit other doctors' rows;
   - doctor attempts to attach schedule to inactive facility —
     rejected;
   - admin searches and opens a VERIFIED doctor profile;
   - mobile/tablet/desktop, console clean, session/cookies correct.
4. Update `docs/implementation-progress.md` Phase 9 row to fully
   completed **only after** frontend gates pass; the row is already
   marked "Completed" today because the backend is green, but that
   label currently overstates the phase (frontend is missing).
5. Commit Phase 9 with **backend only** at first; tag it
   `phase-9-backend`; commit the frontend and tag
   `phase-9-complete` only after the steps above pass.

### Recommended commit order

1. Phase 7 commit + `phase-7-complete` tag.
2. Phase 8 commit + `phase-8-complete` tag.
3. Phase 9 backend commit + `phase-9-backend` tag.
4. Phase 9 frontend commit + `phase-9-complete` tag.

### Snapshot of Phase 7 worktree paths (as the original handoff recorded them)

Modified tracked paths:

```text
backend/app/auth/models.py
backend/app/auth/service.py
backend/app/core/security.py
backend/app/professionals/repository.py
backend/app/professionals/routes.py
backend/app/professionals/schemas.py
backend/app/professionals/service.py
backend/tests/test_database_foundation.py
backend/tests/test_facility_migrations.py
backend/tests/test_professional_migrations.py
frontend/src/app/page.test.tsx
frontend/src/app/page.tsx
frontend/src/components/professional/professional-shell.tsx
frontend/src/lib/professional/api.test.ts
frontend/src/lib/professional/api.ts
frontend/src/lib/professional/types.ts
```

New untracked Phase 7 paths:

```text
backend/alembic/versions/0014_auth_session_active_role.py
backend/app/professionals/dependencies.py
backend/tests/test_professional_login.py
backend/tests/test_professional_login_migration.py
backend/tests/test_professional_login_postgresql.py
frontend/src/app/professional/dashboard/page.tsx
frontend/src/app/professional/login/page.tsx
frontend/src/app/professional/status/page.tsx
frontend/src/components/professional/professional-login-form.test.tsx
frontend/src/components/professional/professional-login-form.tsx
frontend/src/components/professional/professional-portal.test.tsx
frontend/src/components/professional/professional-portal.tsx
```

### Phase 8 worktree paths (added after the original handoff)

Backstage, auth, and admin identity surfaces; new admin pages. Confirm with
`git status --porcelain` because the exact list grows with each fix.

```text
backend/app/admins/identity_*                  (new subpackage)
backend/app/api/v1/router.py                   (identity routes wired in)
frontend/src/app/admin/citizen-identities/page.tsx
frontend/src/app/admin/citizen-identities/[user_id]/page.tsx
frontend/src/components/admin/citizen-identity-support.{tsx,test.tsx}
frontend/src/components/admin/citizen-identity-detail.{tsx,test.tsx}
frontend/src/components/admin/admin-dashboard.tsx          (updated link)
```

### Phase 9-backend worktree paths (current worktree)

The new `doctors` sub-package, the new migration, three SQLite test
files, and one PostgreSQL test file.

```text
backend/alembic/versions/0015_doctor_practice_schedules.py
backend/app/doctors/__init__.py
backend/app/doctors/models.py
backend/app/doctors/schemas.py
backend/app/doctors/repository.py
backend/app/doctors/service.py
backend/app/doctors/dependencies.py
backend/app/doctors/routes.py
backend/app/api/v1/router.py                  (doctors + practice-schedule routes wired in)
backend/tests/test_doctor_search.py
backend/tests/test_practice_schedule.py
backend/tests/test_doctor_search_postgresql.py
```

Always re-run `git status --porcelain` and `git diff --stat` immediately
before staging to confirm nothing has been touched by an editor or
formatter in between.

This handoff file itself (`AGENTIC_IMPLEMENTATION_HANDOFF_PHASES_0_TO_14.md`)
and `docs/implementation-progress.md` are themselves untracked edits
until the next agent deliberately stages them.

## Remaining phases after Phase 9-backend

The following is a navigation summary. The V6 document remains authoritative
for exact schemas, fields, constraints, routes, and acceptance criteria.

Phases 7, 8, and 9 (backend) are already verified and described above in
the "Completed phase summary" and "Current uncommitted work" sections.
The phases below have not started.

### Phase 10 — Appointment booking and MAX serial assignment

- Expected migration sequence from V6: `016 doctor_practice_sessions`,
  `017 appointments`, `018 appointment_queue_entries`.
- PostgreSQL transaction-scoped advisory lock (or documented equivalent) keyed
  by doctor role + date.
- In one transaction: schedule, capacity, active count, MAX serial + 1,
  appointment, daily session, WAITING queue entry, commit.
- Preserve unique serial/index protections and test real concurrent booking.

### Phase 11 — Doctor chamber session and serial queue

- Start/current/finish daily chamber session.
- Skip/remove/no-show operations and centralized `advance_queue` selecting the
  lowest WAITING serial.
- Enforce verified doctor ownership and at most one CURRENT queue entry.
- No new broad medical-history work.

### Phase 12 — Current patient clinical access and consultation workspace

- Migrations `019 patient_access_grants` and `020 medical_visits` per V6 order.
- Current-patient access dependency tied to active verified doctor role and
  current queue relationship; recognize valid pre-existing grants where
  documented, but do not add Phase 21 grant-management CRUD/UI.
- Consultation visit routes and frontend limited strictly to records available
  through Phase 12. Emergency data remains a placeholder; unified history,
  labs, emergency profile, and access-log infrastructure belong to later phases.

### Phase 13 — Prescription form and electronic PDF

- Migrations `021 prescriptions`, `022 prescription_items`, and
  `023 prescription_documents`.
- Structured prescription service/routes, private storage abstraction, PDF
  generation, authorization, explicit failure/retry/regeneration behavior, and
  author-role edit enforcement.
- Do not pull Phase 20 audit infrastructure forward; only use audit support that
  actually exists.

### Phase 14 — Finish appointment and automatic next serial

- One atomic finish transaction must require the current queue entry, owning
  verified doctor role, and consultation visit; finalize visit, complete the
  appointment, mark queue DONE, and advance the lowest WAITING serial.
- Add backend/frontend flow, ownership/security tests, queue invariants, and
  live browser verification.
- After Phase 14 passes every gate, update docs, create the final Phase 14
  checkpoint, and STOP. Do not create Phase 15 schema, APIs, UI, or placeholders.

## Architecture and security facts to preserve

- One user identity can have citizen, professional, and admin capabilities.
- Portal contexts are separate: CITIZEN, PROFESSIONAL, ADMIN.
- Frontend guards are UX only; backend portal/session/role checks are
  authoritative.
- A professional session is user + one selected role registration, never a
  generic “professional” boolean.
- Only VERIFIED roles receive clinical capabilities. PENDING/REJECTED sessions
  can display verification status only.
- NID/BCN do not belong on `users`, in JWTs, in logs, or in URLs.
- Refresh tokens are opaque; only their digest is stored. The browser cookie is
  HttpOnly, scoped to `/api/v1/auth`, SameSite=Lax, and Secure outside local
  development.
- Access tokens remain in client memory only—never localStorage,
  sessionStorage, IndexedDB, readable cookies, URLs, or a server-global store.
- Every protected request validates the JWT and its live session row, so logout
  immediately invalidates access tokens.
- Admin verification/identity mutations require audit records.
- PostgreSQL locking and final database constraints are not optional for the
  concurrency-sensitive phases.

## Local development and verification environment

At the time of handoff:

```text
OS/shell: Windows / PowerShell
Python: workspace virtual environment at D:\HealthLink_V_1\.venv
Node/npm: installed; frontend dependencies already present
PostgreSQL 17: 127.0.0.1:55432
Development DB: healthlink_dev
Test DB: healthlink_test
Local PostgreSQL listen port: 55432 (trust auth; user `healthlink`,
no password required)
Current dev/test Alembic revision: 0015_doctor_practice_schedules

```text
Backend:  http://localhost:8000
Health:   http://localhost:8000/health
Frontend: http://localhost:3000
```

No application servers were intentionally left running when this handoff was
written. The PostgreSQL service remains available.

Useful commands (PowerShell):

```powershell
# Backend full suite against the local PG instance
$env:HEALTHLINK_TEST_DATABASE_URL = 'postgresql+psycopg://healthlink@127.0.0.1:55432/healthlink_test'
$env:DATABASE_URL = $env:HEALTHLINK_TEST_DATABASE_URL
.\.venv\Scripts\python.exe -B -m pytest backend\tests -q -p no:cacheprovider

# Alembic on dev DB
Set-Location backend
$env:DATABASE_URL = 'postgresql+psycopg://healthlink@127.0.0.1:55432/healthlink_dev'
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic check

# Frontend quality gates
Set-Location ..\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test -- --run
npm.cmd run build
```

On this Windows host, Vitest/Next may receive `EPERM` while writing generated
`node_modules/.vite-temp` or `.next` files inside the sandbox. This was an
environment permission issue, not a test failure; approved out-of-sandbox npm
test/build execution worked. Do not delete broad directories. If cleanup is
necessary, resolve and validate the exact generated path first.

## Safe continuation checklist

1. Read the three governing documents completely.
2. Read this handoff, `docs/implementation-progress.md`, and
   `docs/implementation-assumptions.md`.
3. Inspect `git status`, `git diff`, migration heads, and both database
   current revisions before editing. The dev and test PostgreSQL databases
   are both currently at `0015_doctor_practice_schedules`.
4. Preserve all committed Phase 0–6 work and the **uncommitted** Phases
   7, 8, and 9-backend worktrees; do not use reset/checkout to discard any
   of it.
5. Do **not** commit Phases 7, 8, and 9-backend as one bundle — three
   separate commits and three separate tags:
   - `phase-7-complete` (covers migration `0014`, professional login,
     active-role context, three pages, three components, and tests);
   - `phase-8-complete` (covers identity search/detail/correction and
     the two `/admin/citizen-identities` routes);
   - `phase-9-backend` (covers migration `0015`, the `doctors`
     sub-package, six routes, and the four PostgreSQL tests). The
     frontend for Phase 9 is not yet implemented; tag `phase-9-complete`
     only after the frontend passes its quality gates.
6. Build the **Phase 9 frontend** next: `lib/doctors/{api,types}.ts`,
   citizen search + detail pages, doctor practice-schedule editor, and
   the admin search hook. Then run the frontend quality gates and the
   browser flows described under "Phase 9 work that still must be done
   before full completion" above.
7. Continue Phase 10, then 11, 12, 13, and 14, one complete vertical
   slice and checkpoint at a time.
8. Recheck source-document hashes and `git diff --check` at each gate.
9. Stop after Phase 14.
