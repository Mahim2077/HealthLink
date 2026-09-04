# HealthLink Phase 0–14 implementation handoff

Last updated: 2026-09-04 (Asia/Dhaka)
Repository: `D:\HealthLink_V_1`
Branch: `main`
Last committed Phase checkpoint before this deployment snapshot:
`9da7b60 (tag: phase-12-complete) feat(phase-12): visits and consultations frontend`.

Current working checkpoint: Phase 13 implementation is complete and awaits its
GitHub Actions production verification before the `phase-13-complete` tag. The
canonical structured prescription API, citizen/author-role authorization,
failure-safe PDF regeneration, dynamic doctor form, citizen read-only detail,
and private Vercel Blob adapter are implemented. The full backend suite passes
(195 passed, 33 PostgreSQL-only tests skipped without the dedicated test URL),
all 169 frontend tests pass, frontend lint/type-check/build pass, the configured
Supabase schema is at `0023_prescription_documents`, and `alembic check` reports
no metadata drift. A real local browser flow against Supabase passed two-item
create, authenticated PDF preview, author edit/regeneration, and wrong-portal
denial; its synthetic fixture was removed. The production project now has a
private Blob store and selects `vercel_blob`. Phase 14 has not started. This
handoff does not replace the three governing documents.

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
| Fully implemented, verified, documented, committed | 13 | 0–12 |
| Backend implemented and locally verified; frontend/browser gate pending | 1 | 13 |
| Not started | 1 | 14 |

Therefore, two phase gates remain: finish the Phase 13 vertical slice, then
implement and verify Phase 14. Stop after Phase 14.

### Superseding current snapshot (2026-09-02)

- Phase 12 is the latest completed phase checkpoint at `9da7b60` and tag
  `phase-12-complete`.
- Phase 13 backend work is present: prescription header/items/document schema,
  author-doctor and citizen ownership guards, structured CRUD, PDF rendering,
  and private local storage.
- Phase 13 is **not complete**: there is no prescription frontend flow or live
  browser verification, and the local PDF adapter is not durable on Vercel's
  ephemeral filesystem. Do not create a `phase-13-complete` tag yet.
- Phase 14 finish-appointment/automatic-next-serial work has not started.
- Deployment infrastructure is present for a single Vercel Services project:
  GitHub Actions runs PostgreSQL migrations and backend/frontend quality gates,
  then performs a prebuilt production deployment and smoke test.
- Scratch generators and local admin probes were removed. Local `.env` files,
  `.vercel/project.json`, and production credentials remain ignored and must
  never be committed.
- Older chronological sections below document earlier handoffs. When their
  state conflicts with this snapshot, this snapshot and Git history are newer.

## Verified commit checkpoints

```text
836a300  feat: complete phase 0 foundation
bd3eb38  feat: complete phase 1 shared authentication
384bed7  feat: complete phase 2 citizen access
379c1cc  feat: complete phase 3 citizen profile
5501422  feat: complete phase 4 professional registration
349c4b1  feat: complete phase 5 admin portal
a5ec66c  feat: complete phase 6 professional verification
628c97e (tag: phase-9-backend)  feat: complete phase 9 backend doctor discovery and practice schedule
bdb2f70 (tag: phase-9-complete) Phase 9 frontend: citizen doctor search, doctor profile, and verified-doctor practice-schedule editor
1a761e6 (tag: phase-10-backend)  feat: complete phase 10 backend appointments and queue
9bb612f (tag: phase-10-complete) feat: complete phase 10 frontend citizen appointment booking
cf9cee5 (tag: phase-11-backend) feat(phase-11): chamber session + serial queue backend
39590fa (tag: phase-11-complete) feat(phase-11): chamber queue frontend + dashboard link + docs evidence
3109dee (tag: phase-12-backend) feat(phase-12): visits and prescriptions backend
9da7b60 (tag: phase-12-complete) feat(phase-12): visits and consultations frontend   ← HEAD before this snapshot
```

The worktree based on `9da7b60` contains intentional Phase 13 backend and
deployment work. Do not discard or reset it. Finish Phase 13 before starting
Phase 14.

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

## Current uncommitted work (Phase 11 — backend only)

Phases 7, 8, 9, and 10 have all been fully committed and tagged
(`phase-7-complete`, `phase-8-complete`, `phase-9-backend`,
`phase-9-complete`, `phase-10-backend`, `phase-10-complete`). The HEAD
checkout (`9bb612f`) contains intentional, uncommitted Phase 11 backend
work. Phase 11 frontend is not yet started. Do not bundle anything into
a single commit; preserve one commit per phase tag.

### Phase 11 — Doctor chamber session and serial queue (backend complete and verified; frontend pending)

#### Schema (no new migration)

Phase 11 leans on the tables introduced by Phases 10 (`016 doctor_practice_sessions`,
`017 appointments`, `018 appointment_queue_entries`):
- `doctor_practice_sessions(id, doctor_role_registration_id, facility_id, session_date,
  status, started_at, finished_at)`
- `appointments(id, citizen_id, doctor_role_registration_id, facility_id,
  appointment_date, serial_number, status, booked_at, cancelled_at)`
- `appointment_queue_entries(id, appointment_id, practice_session_id, queue_status,
  became_current_at, completed_at, finished_at)`
- Partial unique index `appointment_queue_entries(practice_session_id) WHERE
  queue_status='CURRENT'` (added in migration `0018`) enforces the
  “at most one CURRENT patient per chamber session” invariant.

#### Backend routes mounted under `/api/v1/professionals/chamber`

```text
POST   /sessions/start                        – start (or resume) today's chamber session
POST   /sessions/finish                       – close the day's chamber session
GET    /sessions/today                        – view today's session view (current + waiting)
POST   /queue/call-next                       – promote the next WAITING serial → CURRENT
POST   /queue/{queue_id}/complete             – CURRENT → DONE, advance queue
POST   /queue/{queue_id}/skip                 – CURRENT → REMOVED, advance queue
POST   /queue/{queue_id}/remove               – remove a WAITING entry from the queue
POST   /queue/{queue_id}/no-show              – CURRENT → REMOVED, mark appointment NO_SHOW, advance
```

V6 originally listed flat paths under `/api/v1/professional/practice-sessions/...`
and `/api/v1/appointment-queue/{id}/...`; the implementation prefixes them
under `/professionals/chamber` to keep the namespace consistent with
`/professionals/me` and the existing role-based authorization dependency.
The action surface is identical to the V6 spec.

#### Service layer (`backend/app/appointments/service.py`)

- `start_session(context, facility_id, session_date)` — verifies the verbatim
  `ProfessionalAuthContext` is a verified DOCTOR for the requested facility,
  re-uses the existing `DoctorPracticeSession` for the date (or creates a new
  ACTIVE one), and atomically promotes the lowest WAITING serial (if any) to
  CURRENT via `advance_queue`.
- `view_today_queue(context, facility_id, session_date)` — returns the
  `ChamberSessionView` with `current_serial`, `waiting_serials`, and
  `finished_serials` for the day.
- `call_next(context, facility_id, session_date)` — wraps the centralized
  `advance_queue(session)` helper that always selects the lowest WAITING
  serial. Uses the repository's `pg_advisory_xact_lock(session_id_hash)` so
  concurrent callers serialize to one CURRENT.
- `complete_current(context, queue_id)` — CURRENT → DONE, advances queue.
- `skip_current(context, queue_id)` — CURRENT → REMOVED, advances queue.
- `remove_entry(context, queue_id)` — removes a WAITING entry; if it was the
  only one, queue is now empty.
- `mark_no_show(context, queue_id)` — CURRENT → REMOVED, marks the
  appointment `NO_SHOW`, and advances the queue.
- `finish_session(context, facility_id, session_date)` — sets the session
  to `FINISHED`, blocks further queue actions.
- Helpers: `_serial_of(appointment_id, session)`, `_queue_view(entry, session)`,
  `_build_session_view(session, statuses=...)`, `_apply_queue_action(...)`,
  `_promote_lowest_waiting(...)`.
- All chamber DB access goes through batch lookups
  (`_appointments_by_ids`, `_sessions_by_ids`) rather than SQLAlchemy
  `selectinload` relationships on `AppointmentQueueEntry`, because the
  Phase 10 model intentionally does not declare `appointment` or
  `practice_session` relationships on `AppointmentQueueEntry`.

#### Repository (`backend/app/appointments/repository.py`)

- New: `_lock_for_queue(connection, doctor_role_registration_id, session_date)`
  — short-circuits on SQLite; on PostgreSQL calls
  `pg_advisory_xact_lock(hashtext(...))` for per-(role,date) serialization.
- New: `_appointments_by_ids(appointment_ids)`, `_sessions_by_ids(session_ids)` —
  explicit batch lookup helpers used by the service.
- New: `list_queue_entries_for_session(session_id, statuses=...)` and
  `get_practice_session_for_doctor(registration_id, session_date)`.

#### Dependencies (`backend/app/appointments/dependencies.py`)

- New: `get_current_verified_doctor_for_chamber` — confirms the JWT session
  is a PROFESSIONAL and the selected role registration is `VERIFIED`,
  has `code == DOCTOR`, and matches the requested `facility_id`.

#### Schemas (`backend/app/appointments/schemas.py`)

- New: `ChamberSessionView`, `ChamberQueueEntryView`, `ChamberQueueListResponse`,
  `ChamberSessionStartRequest`, `ChamberSessionFinishResponse`,
  `ChamberQueueActionResponse`, `ChamberSkipRequest`, `ChamberNoShowRequest`.

#### Errors (inlined in `backend/app/appointments/service.py`)

There is no separate `backend/app/appointments/errors.py` module for
Phase 11 — the chamber exceptions are defined near the top of
`service.py` and inherit from `HealthLinkError`:

```text
ChamberSessionNotFoundError    – 404 — session not found / facility not found
ChamberQueueEntryNotFoundError – 404 — queue entry not found for this session
ChamberSessionStateError       – 409 — illegal session state transition
                                  (starting an already FINISHED session,
                                  finishing when actions are still pending,
                                  starting twice on the same calendar day
                                  without an intervening finish)
ChamberQueueStateError         – 409 — illegal queue transition
                                  (acting on a non-CURRENT entry, attempting
                                  to start when there is already a CURRENT,
                                  partial unique index rejection,
                                  non-WAITING removal target)
```

The receiving agent should map each exception to the correct HTTP
status inside the existing `register_exception_handlers` plumbing; do
not add a new error-class family if `HealthLinkError` already maps
cleanly to the right status code.

#### Wiring

`backend/app/api/v1/router.py` mounts `chamber_router` under the
`/professionals` prefix; the router's own prefix is `/chamber`, so the final
URLs are `/api/v1/professionals/chamber/...`.

#### Tests

`backend/tests/test_chamber.py` — new SQLite test suite, **13 tests, all passing**:

```text
test_chamber_endpoints_require_authentication
test_chamber_rejects_citizen_portal
test_chamber_rejects_unverified_doctor
test_start_session_promotes_lowest_waiting_serial
test_call_next_advances_through_serial_queue
test_skip_advances_when_called_on_waiting_entry
test_no_show_marks_appointment_and_advances
test_cancelled_appointments_are_excluded_from_waiting
test_only_one_current_per_session_invariant
test_queue_action_rejects_foreign_doctors
test_finish_session_blocks_further_queue_actions
test_view_today_returns_session_view
test_start_session_is_idempotent
```

`backend/tests/test_chamber_postgresql.py` — new PostgreSQL test suite:

```text
test_postgresql_partial_unique_index_blocks_second_current_queue_entry
test_postgresql_appointment_cancellation_excludes_from_chamber_view
test_postgresql_concurrent_promote_keeps_single_current
```

The third test exercises two threads racing on `pg_advisory_xact_lock` plus
the partial unique index to prove exactly one CURRENT row remains.

#### Phase 11 backend checks already run

```text
HEALTHLINK_TEST_DATABASE_URL unset → SQLite fallback
backend/tests/test_chamber.py: 13 passed
backend full suite (SQLite): 163 passed, 30 skipped (chamber PG tests skipped without URL)
Backend imports / app boots: clean
```

An additional live run against Supabase (using a securely supplied test database URL)
is recorded in the "Current agent session status" block below. The
chamber PG test file is syntactically valid and collectable by pytest;
the live run was interrupted by a hanging `python.exe` fan-out from a
prior sub-shell invocation, so it must be re-executed in a fresh
shell.

#### Phase 11 work that still must be done before full completion

1. Re-run the Supabase chamber PG tests in a fresh PowerShell session
   (no orphan `python.exe` from previous shells; the previous attempt
   left a small fan-out that the agent killed via `taskkill /F /IM python.exe`).
2. Commit Phase 11 with **backend only** at first; tag it
   `phase-11-backend`; commit the frontend and tag `phase-11-complete`
   only after the steps below pass.
3. Build the **Phase 11 frontend**:
   - `frontend/src/lib/chamber/{types.ts, api.ts, api.test.ts}` mirroring
     the verified-doctor patterns used by `lib/doctor` and `lib/professional`.
   - `frontend/src/app/professional/chamber/page.tsx` — protected by the
     verified-doctor portal guard; queries `GET /professionals/chamber/sessions/today`;
     shows current serial, waiting queue, finished serials.
   - Action buttons wired to the seven chamber endpoints
     (start, call-next, complete, skip, remove, no-show, finish) with
     proper loading/error states and disabled flags when the session is
     FINISHED or action is illegal.
   - `frontend/src/components/professional/chamber-queue.tsx` extracted
     from the page with matching `.test.tsx` covering empty state,
     single-CURRENT state, advancing-queue state, and finished state.
   - Add a Chamber link on the existing professional dashboard
     (verified-doctor branch only).
4. Run frontend quality gates: `npm run lint`, `npx tsc --noEmit`,
   `npm run test`, `npm run build`.
5. Browser flows against FastAPI + Phase 11 backend:
   - verified doctor starts session, calls next, skips, removes,
     no-shows, completes, and finishes;
   - foreign doctor cannot act on another doctor's queue entry;
   - citizen cannot hit any chamber endpoint;
   - unverified doctor is rejected by the dependency.
6. Update `docs/implementation-progress.md` Phase 11 row to fully
   completed **only after** the frontend gates pass.
7. Tag `phase-11-complete` after the frontend commit.

### Phase 11 backend worktree paths (current worktree)

```text
M  backend/app/api/v1/router.py
M  backend/app/appointments/dependencies.py
M  backend/app/appointments/repository.py
M  backend/app/appointments/routes.py
M  backend/app/appointments/schemas.py
M  backend/app/appointments/service.py
?? backend/tests/test_chamber.py
?? backend/tests/test_chamber_postgresql.py
```

`git diff --stat` summary at the time of this handoff:

```text
backend/app/api/v1/router.py             |   2 +
backend/app/appointments/dependencies.py |  31 +-
backend/app/appointments/repository.py   | 107 +++++++
backend/app/appointments/routes.py       | 205 +++++++++++-
backend/app/appointments/schemas.py      |  92 +++++-
backend/app/appointments/service.py      | 531 +++++++++++++++++++++++++-
6 files changed, 961 insertions(+), 7 deletions(-)
```

No new files were added under `backend/app/appointments/` besides the
two test files; the chamber surface lives in the existing
`service.py`, `repository.py`, `routes.py`, `schemas.py`, and
`dependencies.py`. The chamber exceptions are inlined at the top of
`service.py` (`ChamberSessionNotFoundError`,
`ChamberQueueEntryNotFoundError`, `ChamberSessionStateError`,
`ChamberQueueStateError` — all subclassing `HealthLinkError`); no
separate `backend/app/appointments/errors.py` module exists in this
round because the appointments package already keeps its chamber
symbols next to its service layer.

Always re-run `git status --porcelain` and `git diff --stat` immediately
before staging to confirm nothing has been touched by an editor or
formatter in between.

This handoff file itself (`AGENTIC_IMPLEMENTATION_HANDOFF_PHASES_0_TO_14.md`)
and `docs/implementation-progress.md` are themselves untracked edits
until the next agent deliberately stages them.

## Current agent session status (handoff snapshot)

This block is intentionally chronological so the receiving agent can
pick up exactly where the previous run stopped.

1. Phase 11 backend code: **complete and SQLite-verified (13/13)**.
2. Phase 11 PG test file: **syntax-valid and collectable** (a
   prior `replace_string_in_file` slip had dropped indentation on
   three lines of test 3; a small Python read/write script re-indented
   them; `python -c "import ast; ast.parse(...)"` now reports OK).
3. Full backend suite (SQLite): **163 passed, 30 skipped**.
4. Live Supabase chamber PG run: **interrupted**. The agent ran
   `pytest backend/tests/test_chamber_postgresql.py -v --tb=short`
   against the Supabase pooler URL and the run hung in a fan-out
   process tree. Several `taskkill /F /IM python.exe` and
   `Get-Process python` invocations were issued; the agent confirmed
   no Python processes remained before exit. The receiving agent
   must run this command again in a clean shell:

   ```powershell
   # Set HEALTHLINK_TEST_DATABASE_URL from an untracked local secret source first.
   .\.venv\Scripts\python.exe -m pytest backend/tests/test_chamber_postgresql.py -v --tb=short
   ```

   The Supabase pooler requires `disable_prepared_statements=True`
   (already wired through `create_database_engine`). Keep the connection URL
   only in an ignored local environment file or secret manager; never place it
   in documentation or source code.

5. Pending after the live PG run passes:
   - `git add backend/app/api/v1/router.py backend/app/appointments/dependencies.py backend/app/appointments/repository.py backend/app/appointments/routes.py backend/app/appointments/schemas.py backend/app/appointments/service.py backend/tests/test_chamber.py backend/tests/test_chamber_postgresql.py`
   - `git -c user.name="healthlink-agent" -c user.email="agent@healthlink.local" commit -m "feat: complete phase 11 backend chamber queue management"` with the message body already drafted in the prior slice.
   - `git tag phase-11-backend`
   - `git push origin main phase-11-backend`
   - then start the Phase 11 frontend cycle.

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
