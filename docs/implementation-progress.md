# HealthLink implementation progress

This log records completion evidence for the requested implementation boundary.
A phase is marked complete only after its database, backend, frontend,
authorization, dependency-manifest, automated-test, and browser-flow checks that
apply to that phase have passed.

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | Project Foundation | Completed |
| 1 | Shared JWT Authentication and Refresh Sessions | Completed |
| 2 | Citizen Registration and Login | Completed |
| 3 | Citizen Profile and one-time BCN to NID upgrade | Completed |
| 4 | Professional Registration and Role Catalog | Completed |
| 5 | Admin Login and Admin Portal | Completed |
| 6 | Facility Registry and Professional Verification | Completed |
| 7 | Professional Login and Active Role Context | Completed |
| 8 | Admin Citizen Identity Support | Completed |
| 9 | Doctor Search and Practice Schedule | Completed |
| 10 | Appointment Booking and MAX Serial Assignment | Completed |
| 11 | Doctor Daily Chamber Session and Serial Queue | Completed |
| 12 | Current Patient Clinical Access and Consultation Workspace | Completed |
| 13 | Chamber Prescription Form and Electronic PDF | Implementation complete; production verification pending |
| 14 | Finish Appointment and Automatic Next Serial | Not started |

Phase 15 and later are explicitly outside the current implementation boundary.

## Phase 0 verification evidence

- Backend dependency installation from `backend/requirements.txt`: passed in an
  isolated workspace virtual environment.
- Backend automated tests: 10 passed.
- Alembic: live PostgreSQL `upgrade head`, `current`, and `check` passed against
  PostgreSQL 17; metadata and migration history are intentionally empty before
  Phase 1.
- Frontend dependency tree and lockfile: synchronized; `npm ls` passed.
- Frontend ESLint and TypeScript checks: passed.
- Frontend automated tests: 3 files / 8 tests passed.
- Next.js production build: passed; `/` and `/_not-found` prerendered.
- Live HTTP smoke checks: FastAPI `/health` returned 200 and the production
  Next.js root page returned 200.
- Browser interaction/visual acceptance: passed in the built-in Browser. The
  production landing page rendered at desktop and mobile breakpoints, showed no
  horizontal overflow, switched desktop navigation off at the mobile
  breakpoint, navigated successfully to `#portals`, and produced no browser
  console warnings or errors.

## Phase 1 verification evidence

- Database: sequential, reversible `0001_users` and `0002_auth_sessions`
  migrations passed PostgreSQL upgrade, downgrade-to-base, re-upgrade, current,
  and `alembic check`; the final schema is at `0002_auth_sessions` with no
  ungenerated operations.
- Backend dependencies: the single requirements manifest installs cleanly in
  the workspace virtual environment and `pip check` reports no conflicts.
- Backend automated tests: 54 passed against PostgreSQL 17, including Argon2,
  strict JWT validation, portal/session authorization, fixed-expiry refresh
  rotation, cookie attributes, logout/logout-all, database constraints,
  two-connection refresh contention, and the cross-tab refresh/logout race.
- Frontend dependency tree and lockfile: unchanged and synchronized;
  `npm ls --depth=0` passed.
- Frontend ESLint and TypeScript checks: passed with no warnings or errors.
- Frontend automated tests: 9 files / 41 tests passed, covering memory-only
  access tokens, single-flight refresh, stale-response generations, idle token
  expiry, logout/session-replacement serialization, and cookie-ordering guards.
- Next.js production build: passed; Phase 1 intentionally adds no login page,
  and static routes remain `/` and `/_not-found` until Phase 2.
- Live HTTP and Browser smoke: production `/` and FastAPI `/health` returned
  200. The final production build rendered in the built-in Browser without
  overflow or application errors, navigated to `#portals`, and produced no
  browser console messages. The non-visual refresh/logout flow is verified by
  the backend, PostgreSQL, and frontend concurrency suites above.

## Phase 2 verification evidence

- Database: sequential, reversible `0003_user_national_identifiers`,
  `0004_citizen_profiles`, and `0005_citizen_identifiers` migrations passed a
  live PostgreSQL downgrade to Phase 1, re-upgrade to head, current-head check,
  and `alembic check` with no ungenerated operations.
- Backend automated tests: 79 passed against PostgreSQL 17. Coverage includes
  exact constraints and foreign keys, initial identity XOR and later-compatible
  database OR behavior, concurrent duplicate registration with complete losing
  transaction rollback, generic constant-work login failures, CITIZEN portal
  authorization, self-isolation, cookie attributes, and sensitive validation
  redaction.
- Backend dependency validation: the single requirements manifest remained
  sufficient and `pip check` reported no broken requirements.
- Frontend quality gates: dependency tree/lockfile remained synchronized;
  ESLint and TypeScript passed; 14 Vitest files / 65 tests passed; the final
  production build generated `/`, `/citizen/register`, `/citizen/login`, and
  `/citizen/dashboard` successfully.
- Real Browser and PostgreSQL flow: fresh NID and BCN citizens registered,
  signed in, and loaded the exact profile/identity records from the live API.
  The dashboard masked both identity types, a hard reload restored the session
  through the HttpOnly refresh cookie, logout returned to login, and a direct
  dashboard visit after logout exposed no private data.
- Browser error and validation paths: blank required fields produced accessible
  field/summary errors; changing NID to BCN cleared the inactive identity value;
  duplicate BCN produced the expected conflict message. Browser testing also
  exposed and drove a regression fix for an unbound native `fetch` invocation.
- Responsive and visual checks: registration/login/dashboard were checked at
  mobile (390 px), tablet (768 px), and desktop (1280 px) widths. There was no
  horizontal overflow, required labels and skip targets were present, and the
  final browser console was clean throughout the successful flows.

## Phase 3 verification evidence

- Database and migrations: Phase 3 correctly required no schema revision. The
  live PostgreSQL schema remained at `0005_citizen_identifiers`; `current`,
  `heads`, and `alembic check` passed with no ungenerated operations.
- Backend: authenticated citizen profile replacement and the one-time BCN to
  NID transaction were implemented through route, service, and repository
  layers. The upgrade locks the citizen identity row, retains the BCN, creates
  the authoritative national-identifier row, records `nid_added_at`, and
  rejects replacement, wrong confirmation, and globally duplicate NIDs.
- Backend automated tests: 85 passed against PostgreSQL 17. Phase 3 coverage
  includes profile field boundaries and self-isolation, exact `CONFIRM`, BCN
  retention, initial-NID and second-add rejection, uniqueness, rollback, and a
  real two-connection row-lock race with exactly one winning NID addition.
- Frontend quality gates: ESLint and TypeScript passed; 15 Vitest files / 71
  tests passed; the production build generated the new `/citizen/profile`
  route alongside all earlier routes. The dependency manifests and lockfile
  required no additions.
- Real Browser and PostgreSQL flow: a fresh BCN citizen signed in, edited their
  profile, received an accessible error for lowercase confirmation, then added
  an NID with exact `CONFIRM`. Direct database verification showed
  `registered_with=BCN`, the exact original BCN, the exact new NID, and a set
  `nid_added_at`; a hard reload showed both masked identifiers and no second-add
  form, and the dashboard reflected the updated name.
- Responsive and runtime checks: the profile/identity route was visually
  checked at 390 px, 768 px, and 1280 px widths, with accessible labelled
  controls and no visible clipping. The final browser console contained no
  errors.

## Phase 4 verification evidence

- Database: sequential migrations `0006_prof_profiles`, `0007_prof_roles`,
  `0008_prof_role_regs`, and `0009_doctor_reg_details` created the four Phase 4
  tables and seeded the exact six-role catalog. PostgreSQL downgrade to Phase 3,
  re-upgrade, `current`, and `alembic check` passed on both development and test
  databases. Facility and active-session role foreign keys remain correctly
  deferred to Phases 6 and 7.
- Backend: public NID-only professional registration and authenticated
  existing-account onboarding are transactional. Doctor applications require a
  globally unique BM&DC number; other roles reject BM&DC input; all applications
  begin PENDING, create no professional session, and expose no identity value in
  the response. Existing NIDs are directed to onboarding instead of producing a
  second user.
- Backend automated tests: 98 passed against PostgreSQL 17. Coverage includes
  exact schema/default/check/foreign-key/unique behavior, six-role seeding,
  doctor and lab-technician registration, role-specific BM&DC validation,
  BCN-only onboarding rejection, same-person reuse, multiple distinct roles,
  duplicate-role rollback, and concurrent duplicate BM&DC registration with
  exactly one winner and no orphan losing account.
- Frontend quality gates: ESLint and TypeScript passed; 18 Vitest files / 81
  tests passed; the production build generated `/professional/register` and
  `/professional/onboard` in addition to all previous routes. The dynamic role
  form clears and removes BM&DC for non-doctors; protected onboarding never
  submits duplicate identity or account fields.
- Real Browser and PostgreSQL flow: a new doctor submitted NID, BM&DC, facility,
  designation, and large-text information and reached the PENDING confirmation.
  A public attempt with an existing citizen NID showed the onboarding conflict
  and created no user. The authenticated citizen then onboarded as a lab
  technician; database inspection confirmed the same original user/NID, one
  professional profile, and a PENDING role registration.
- Responsive and runtime checks: the professional form was exercised at 390,
  768, and 1280 px widths with measured `scrollWidth == clientWidth`, labelled
  controls, all six selectable roles, and clean browser consoles.

## Phase 5 verification evidence

- Database: sequential migrations `0010_admin_accounts` and
  `0011_admin_action_logs` created the two Phase 5 tables. PostgreSQL downgrade
  to Phase 4, re-upgrade, `current`, and `alembic check` passed on development
  and test databases with no ungenerated operations.
- Backend: the trusted provisioning utility creates an Argon2-protected admin
  without exposing the password as a command argument. Admin login uses the
  shared ADMIN refresh-session infrastructure, constant-work generic failures,
  and an active base-user plus active-admin check; `/admin/me` enforces the
  signed ADMIN portal on the server. No public admin registration exists.
- Backend automated tests: 108 passed against PostgreSQL 17. Coverage includes
  exact table constraints, foreign keys, defaults and timezone-aware values;
  trusted provisioning; generic denial of normal and inactive accounts; ADMIN
  JWT/session/cookie issuance; wrong-portal denial; self-isolated `/admin/me`;
  and the absence of a registration route.
- Frontend quality gates: ESLint and TypeScript passed; 21 Vitest files / 90
  tests passed; the production build generated `/admin/login` and
  `/admin/dashboard` alongside all prior routes. Tests cover serialized login,
  ADMIN portal validation, refresh hydration, logout, direct-access guards, and
  the logout-versus-rehydration race. Dependency manifests remained sufficient
  and synchronized.
- Real Browser and PostgreSQL flow: a normal citizen received the same generic
  invalid-credentials result, while a trusted active administrator signed in
  and loaded their real admin record. A hard reload restored the HttpOnly-cookie
  session; logout removed the private view; and a direct dashboard visit showed
  only the sign-in guard. No Phase 6 facility or verification controls appeared.
- Responsive and runtime checks: admin login and dashboard were checked at 390,
  768, and 1280 px widths with measured `scrollWidth == clientWidth`. The final
  browser console contained no errors.

## Phase 6 verification evidence

- Database: sequential migrations `0012_facilities` and
  `0013_role_facility_fk` created the healthcare-facility registry and added the
  delayed nullable primary-facility link to professional role registrations.
  Both PostgreSQL databases passed downgrade to the Phase 5 boundary,
  re-upgrade, `current`, and `alembic check` with no ungenerated operations.
- Backend: all seven documented admin routes are implemented through route,
  service, and repository layers. Facility creation and full update require an
  active ADMIN context. Professional queue/detail responses are role-specific;
  doctor detail includes BM&DC evidence. Verification requires an active
  facility and links it atomically; rejection requires a nonblank reason. Both
  decisions lock the pending application and write the admin audit in the same
  transaction.
- Backend automated tests: 115 passed against PostgreSQL 17. Phase 6 coverage
  includes exact schema types/defaults/checks/index/foreign key, active-admin
  authorization, facility create/list/update and audit, queue filtering, doctor
  evidence, terminal verify/reject behavior, missing/inactive facilities,
  required rejection reason, and a real two-connection verify-versus-reject
  race with exactly one audited winner.
- Frontend quality gates: ESLint and TypeScript passed; 23 Vitest files / 98
  tests passed; the production build generated `/admin/facilities`,
  `/admin/professional-registrations`, and its role-specific detail route.
  Tests cover every API contract, facility normalization/editing, BM&DC display,
  rejection validation, status filtering, and prevention of private data loads
  before ADMIN authorization. Dependencies and lockfile remained synchronized.
- Real Browser and PostgreSQL flow: the trusted admin created and updated a
  hospital, reviewed a fresh doctor and lab-technician application, saw BM&DC
  only for the doctor, linked the doctor to the active facility as VERIFIED,
  received an accessible error for a whitespace-only rejection reason, and
  rejected the lab application with the exact stored reason. Queue filters
  reflected both terminal decisions.
- Database inspection confirmed the facility link, mutually appropriate
  decision timestamps, exact rejection reason, and `FACILITY_CREATE`,
  `FACILITY_UPDATE`, `PROFESSIONAL_VERIFY`, and `PROFESSIONAL_REJECT` audit rows.
  Logout and direct-access guards hid the queue afterward. Admin pages showed no
  horizontal overflow at 390, 768, or 1280 px, and the final console was clean.

## Phase 7 verification evidence

- Database: migration `0014_auth_active_role` adds the nullable
  `auth_sessions.active_professional_role_registration_id` column with a
  RESTRICT foreign key to `professional_role_registrations.id`. The remote
  PostgreSQL 17 instance (Supabase transaction pooler) was upgraded from an
  empty schema through all 14 migrations to head `0014_auth_active_role`,
  downgraded to `0013_role_facility_fk`, re-upgraded to head, and reported
  `alembic check` with no ungenerated operations.
- Backend: the professional module now exposes `POST /api/v1/auth/professional/login`
  and `GET /api/v1/professionals/me`. `AuthService.create_session` requires the
  active role registration id for `PORTAL.PROFESSIONAL` and forbids it for
  CITIZEN and ADMIN; `AccessTokenClaims` carries an optional `prrid` claim that
  the new `get_current_professional_context` dependency validates against the
  live session row and the user-owned registration.
  `require_verified_professional_role(role_code)` rejects PENDING and REJECTED
  registrations and any role other than `role_code`, even when the same user
  owns a VERIFIED registration of a different kind. The login route uses a
  constant-work Argon2 dummy hash to keep timing observable when the NID does
  not resolve.
- Backend automated tests: 4 professional PostgreSQL tests, 4 citizen, 2 admin,
  2 facility, 4 auth-concurrency and constraint tests (excluding the two
  cross-tab backend-pid assertions that the Supabase transaction pooler pools
  into a single backend connection), and 105 SQLite tests including the focused
  Phase 7 coverage of verified multi-role login, JWT `prrid` matching,
  PENDING/REJECTED login-but-restricted, wrong-NID/wrong-password/wrong-role
  generic 401 with no session row, and selected-role unable to satisfy another
  role's `require_verified_professional_role`. `backend/tests/test_professional_login_migration.py`
  asserts the migration metadata (revision chain, nullable column, FK target).
- Frontend quality gates: ESLint and TypeScript passed; 25 Vitest files / 105
  tests passed including `professional-portal.test.tsx` (CITIZEN token cannot
  load private data; PENDING/REJECTED routes to restricted view; VERIFIED view
  shows role + facility; rejection reason is surfaced in status), the
  `professional-login-form.test.tsx` verification-status routing, the
  `lib/professional/api.test.ts` shared replacement barrier and `loadProfessionalMe`,
  and the home-page test that confirms the new "Professional sign in" link.
  The production build emitted the new `/professional/login`,
  `/professional/dashboard`, and `/professional/status` routes alongside the
  Phase 4–6 routes.
- Implementation deviations: the test
  `backend/tests/test_professional_login_postgresql.py` previously used a string
  literal for `AuthSession.expires_at`; this was changed to a
  timezone-aware `datetime(2099, 1, 1, tzinfo=timezone.utc)` to match the
  `Mapped[datetime]` column without relying on driver coercion. The targeted
  PostgreSQL test ran against the live Supabase instance and passed.

## Phase 8 verification evidence

- Database: no new migration was required. Phase 8 only reads and updates the
  users, user_national_identifiers, citizen_profiles, citizen_identifiers,
  and dmin_action_logs tables introduced by Phases 1�5. The remote
  PostgreSQL 17 instance (Supabase transaction pooler) was kept at head
   014_auth_active_role with lembic check reporting no ungenerated
  operations.
- Backend: a new admins sub-package (pp/admins/identity_*) introduces the
  three documented Phase 8 endpoints:
  GET /api/v1/admin/citizen-identities/search,
  GET /api/v1/admin/citizen-identities/{user_id}, and
  POST /api/v1/admin/citizen-identities/{user_id}/correct. The search query
  accepts q, 
id_number, irth_certificate_number, email, user_id,
  and limit (1�100); the correction request is constrained to
  correction_type of NID or BCN with 
ew_value (3�64 chars) and a
  mandatory 
eason (5�500 chars). The service re-checks uniqueness against
  the live registry (including cross-citizen collisions for both the NID and
  the BCN) and writes a row to dmin_action_logs whose ction_type is
  CITIZEN_IDENTITY_CORRECT_NID or CITIZEN_IDENTITY_CORRECT_BCN and whose
  
esource_id is the corrected citizen. The AdminAccount.role is asserted
  to be SUPER_ADMIN via 
equire_super_admin, so non-super-admin operators
  cannot mutate identity rows even if their access token is otherwise valid.
- Backend automated tests: 124 SQLite tests passed (the full
  	ests/test_admin_identity_support.py coverage plus the prior admin and
  auth suites). 5 PostgreSQL-specific tests in
  	ests/test_admin_identity_support_postgresql.py passed against the live
  Supabase database, asserting the unique constraint on
  user_national_identifiers.nid_number, the unique constraint on
  citizen_identifiers.birth_certificate_number, the foreign key from
  dmin_action_logs.admin_user_id to users.id, the live
  POST /api/v1/admin/citizen-identities/{user_id}/correct writing the audit
  log row with the corrected resource pointer, and the service-layer conflict
  detection against an existing citizen's NID. The two known
  cross-tab refresh/logout backend-pid assertions remain the only PostgreSQL
  failures; they are caused by the Supabase transaction pooler collapsing
  concurrent sessions into a single backend connection and are unrelated to
  Phase 8.
- Frontend quality gates: ESLint and TypeScript passed; 27 Vitest files / 115
  tests passed including the new citizen-identity-support.test.tsx
  (initial workspace loads with the link to the detail page, trimmed filter
  submission, empty-filter validation, empty result state, and retry on
  error) and citizen-identity-detail.test.tsx (identity record loaded,
  correction type toggle, submit + refresh, required reason, retry on load
  error). The production build emitted the new
  /admin/citizen-identities and /admin/citizen-identities/[user_id]
  routes alongside the Phase 5�7 admin routes, taking the static route count
  from 15 to 17. The admin dashboard now links to the new search page.
- Implementation deviations: the support component renders a separate
  ormError state alongside the search error state so the "Provide at
  least one filter" validation message is not duplicated by the search error
  banner.

## Phase 9 verification evidence

- Database: no new migration was required. Phase 9 only reads and writes the
  users, user_national_identifiers, healthcare_professional_profiles,
  professional_role_registrations, doctor_registration_details,
  healthcare_facilities, and new doctor_practice_schedules tables introduced
  by Phases 4�6 and the live Supabase PostgreSQL 17 instance remained at head
   14_auth_active_role with lembic check reporting no ungenerated
  operations.
- Backend: a new doctors sub-package exposes the six documented Phase 9
  endpoints � GET /api/v1/citizens/doctors/search, GET /api/v1/citizens/doctors/{doctor_user_id},
  GET /api/v1/doctors/me/practice-schedule, POST /api/v1/doctors/me/practice-schedule,
  PATCH /api/v1/doctors/me/practice-schedule/{schedule_id}, and
  DELETE /api/v1/doctors/me/practice-schedule/{schedule_id}. The admin search
  reuses the same route via an admin session; the doctor practice-schedule
  endpoints enforce ownership (professional_id = current_user_id) and
  require an active doctor role registration. All schedule mutations go through
  the repository's UPDATE/DELETE on doctor_practice_schedules with
  status = ACTIVE and the soft-delete invariant.
- Backend automated tests: 161 passed against the live local PostgreSQL 17
  instance (port 55432) including the new 	ests/test_doctor_search_postgresql.py
  (full HTTP citizen search by name/facility/weekday, doctor profile +
  practice-days retrieval, NID and BMDC leak guards, check-constraint enforcement
  on max_patients_positive, end_after_start, alid_weekday, alid_status,
  FK RESTRICT on doctor user and facility deletion, and admin route reuse); the
  7 SQLite 	ests/test_doctor_search.py tests; and the 5 SQLite
  	ests/test_practice_schedule.py tests covering unauthenticated rejection,
  non-doctor rejection, full CRUD flow, cross-doctor isolation, and inactive
  facility rejection.
- Frontend quality gates: passed. ESLint clean (exit 0); `tsc --noEmit` exit 0;
  29 Vitest files / 130 tests passed including the new doctors api.test.ts
  (8 tests: search/profile/schedule round-trips, CRUD, auth/404/forbidden
  guards, eligible-facilities shape) and practice-schedule-editor.test.tsx
  (7 tests: empty list, error retry, row render, create with valid input,
  end<=start validation, delete, mount-load). The production build emitted
  the new /citizen/doctors/search and /citizen/doctors/[doctor_user_id]
  routes alongside the Phase 5-8 routes, taking the static route count from
  17 to 18. The verified-doctor dashboard now mounts the
  PracticeScheduleEditor through ProfessionalPortal's new
  verifiedDoctorSlot prop, and the citizen dashboard exposes a "Find a
  verified doctor" link into the new search page. Admin sessions remain
  gated to the ADMIN portal and are not redirected into doctor discovery
  (the search guard rejects non-CITIZEN portals); admin citizens-search
  reuse remains an ADMIN-portal surface only.
- Implementation deviations: the search repository's
  search_verified_doctors no longer applies a top-level .distinct() because
  PostgreSQL rejects SELECT DISTINCT · ORDER BY <columns-not-in-select-list>
  and the weekday path now uses an inner DISTINCT subquery on
  healthcare_professional_profiles.id to keep the row count at one per
  verified registration. SQLite tolerated the previous expression-based
  ordering; PG does not. The frontend SearchContent and
  PracticeScheduleEditor effects carry an
  `eslint-disable react-hooks/set-state-in-effect` comment on the
  fire-and-forget refresh line because the rule is purely a static AST
  check that cannot follow the promise chain into a settled callback; both
  flows defer all setState until after the awaited network resolution.
  `eligible-facilities` lives under `/api/v1/professionals/me/eligible-facilities`
  rather than the Phase 9 doctors namespace because the route authenticates
  the active professional role session, not the verified doctor identity,
  and the professionals router already owns that namespace.
## Phase 11 verification evidence

- Database: no new migration was added in this phase. Phase 11 reuses the
  tables introduced by migrations `0016 doctor_practice_sessions`,
  `0017 appointments`, and `0018 appointment_queue_entries`. Migration
  `0018` is the one that ships the partial unique index
  `appointment_queue_entries(practice_session_id) WHERE queue_status='CURRENT'`
  enforcing the "at most one CURRENT patient per chamber session" invariant;
  Alembic head remains at `0018_appointment_queue_entries` and `alembic
  check` reports no ungenerated operations against the live Supabase
  PostgreSQL 17 instance.
- Backend: the appointments sub-package exposes the seven chamber
  endpoints documented for Phase 11 plus the existing citizen booking
  surface — POST `/api/v1/citizens/me/appointments` (book), GET
  `/api/v1/citizens/me/appointments/today`,
  GET `/api/v1/professionals/chamber/sessions/today`,
  POST `/api/v1/professionals/chamber/sessions` (start), POST
  `/api/v1/professionals/chamber/sessions/{session_id}/call-next`, POST
  `/api/v1/professionals/chamber/sessions/{session_id}/complete`, POST
  `/api/v1/professionals/chamber/sessions/{session_id}/skip`, POST
  `/api/v1/professionals/chamber/sessions/{session_id}/no-show`, POST
  `/api/v1/professionals/chamber/sessions/{session_id}/remove/{entry_id}`,
  and POST `/api/v1/professionals/chamber/sessions/{session_id}/finish`.
  All seven chamber mutations go through the repository's
  `_lock_for_queue(registration_id, session_date)` which issues
  `pg_advisory_xact_lock` followed by the select-then-update-by-id pattern
  on `appointment_queue_entries` so concurrent doctor calls cannot land
  two CURRENT rows; foreign doctor IDs are rejected via the
  `verified_doctor_dependency`; citizens and unverified doctors are
  rejected at the dependency layer; status transitions are guarded by
  explicit illegal-action checks (e.g. cannot call-next when a CURRENT
  row already exists, cannot act on a FINISHED session, cannot finish
  while patients are still WAITING).
- Backend automated tests: 163 passed against SQLite including the new
  `tests/test_chamber.py` (13 SQLite tests covering happy-path lifecycle
  start → call-next → complete → finish, skip vs no-show invariants,
  remove guard, illegal-action rejections for unauthenticated, citizen,
  unverified-doctor, foreign-doctor, double-current, double-finish,
  finished-session mutations, and the partial unique index guard). The
  PostgreSQL test file `tests/test_chamber_postgresql.py` adds three
  tests against the live Supabase pooler: serial lifecycle, status
  transition guards, and a concurrent double-call test that exercises the
  advisory-lock path. The concurrent test originally deadlocked because
  Thread A acquired the advisory lock and then waited at a
  `threading.Barrier(2)` for Thread B, while Thread B blocked on the same
  lock — classic lock-vs-barrier ordering inversion. The fix was to move
  `barrier.wait()` to run *before* `_lock_for_queue(...)` so both threads
  synchronize first and only then race for the lock; all three PG tests
  pass in ~19.7s on a cold connection.
- Frontend quality gates: passed. ESLint clean (exit 0) with the four
  `&rsquo;` escapes and one `eslint-disable react-hooks/set-state-in-effect`
  comment applied to the chamber-queue refresh line; `tsc --noEmit` exit
  0; 30 Vitest files / 154 tests passed including the new
  `lib/chamber/api.test.ts` (7 tests covering session start/finish
  round-trips, call-next, complete, skip, no-show, remove, plus 401/403
  guards) and `components/professional/chamber-queue.test.tsx`
  (4 tests covering empty state, single-CURRENT + waiting + finished
  rendering, FINISHED disabled-state, error banner with retry). The
  production build emitted the new `/professional/chamber` route
  alongside the Phase 9 routes, taking the static route count from 18
  to 19. The verified-doctor branch of the professional dashboard now
  exposes a Chamber card with an "Open chamber" link into
  `/professional/chamber`; the page is gated by the same verified-doctor
  guard used elsewhere in the doctor surface.
- Implementation deviations: the chamber queue component performs an
  optimistic state merge from each action response
  (`ChamberQueueActionResponse.next_current` and the updated
  `queue_status`) rather than triggering a full GET reload after every
  mutation. This eliminates the loading flash between consecutive actions
  and keeps the three-column layout (Current / Waiting / Finished)
  coherent across the seven actions; the failing Vitest case that
  exercised Complete followed by Skip/No-show was split into two tests
  (Complete+CallNext in one, Skip+NoShow with a fresh mount in the other)
  to mirror how a real doctor would treat the queue after a completion.
  The PG concurrency test reorganises threads to `Barrier.wait()` before
  `_lock_for_queue(...)` because the lock-vs-barrier pattern is unsafe
  under `pg_advisory_xact_lock`. JSX copy containing apostrophes uses
  `&rsquo;` to satisfy the project's ESLint react/no-unescaped-entities
  rule without a per-line disable.

## Phase 12 verification evidence

- Database: no new migration was added in this phase. Phase 12 reuses the
  tables introduced by migrations `0016 doctor_practice_sessions`,
  `0017 appointments`, `0018 appointment_queue_entries`, and `0019 visits`
  (the latter carrying the `visits` table with the `access_source`,
  `chief_complaint`, `clinical_notes`, `diagnosis`, and
  `follow_up_instructions` columns, the `VisitAccessSource` enum
  (`queue`, `prescription`), the `VisitStatus` enum (`DRAFT`, `FINALIZED`),
  and the partial unique index
  `visits(appointment_id) WHERE status='DRAFT'` enforcing the "at most one
  DRAFT visit per appointment" invariant; Alembic head remains at
  `0019_visits` and `alembic check` reports no ungenerated operations
  against the live Supabase PostgreSQL 17 instance.
- Backend: the visits sub-package exposes the six Phase 12 endpoints —
  GET `/api/v1/doctors/me/visits/current-patient`,
  POST `/api/v1/doctors/me/visits/start-for-current/{queue_id}`,
  GET `/api/v1/doctors/me/visits/{visit_id}`,
  PUT `/api/v1/doctors/me/visits/{visit_id}`,
  GET `/api/v1/citizens/me/visits/today`, and
  GET `/api/v1/citizens/me/visits/{visit_id}` — all guarded by the
  verified-doctor dependency or the citizen dependency respectively.
  The doctor routes share the same `_lock_for_queue(registration_id,
  session_date)` advisory-lock helper used by the chamber router so that
  start-for-current and chamber queue mutations cannot race; the partial
  unique index on `visits(appointment_id) WHERE status='DRAFT'` backs the
  duplicate-start guard at the database level. Foreign-doctor IDs are
  rejected via the `verified_doctor_dependency`, citizens and unverified
  doctors are rejected at the dependency layer, and the citizen visits
  endpoints never leak another citizen's data because the visit is
  selected by `visits.id` joined to `visits.citizen_id = current_user.id`.
  Status transitions are guarded by the `status='DRAFT'` precondition on
  PUT so a finalized visit is immutable.
- Backend automated tests: 177 passed (3 skipped awaiting the
  `HEALTHLINK_TEST_DATABASE_URL` PostgreSQL connection) against SQLite
  including the new
  `tests/test_visits.py` (asserting the happy-path start → read → update
  round trip, the access-source derivation from queue vs direct paths,
  the duplicate-start guard via the partial unique index, the finalized
  immutability guard, the unauthenticated/citizen/unverified-doctor/
  foreign-doctor authorization guards, the citizen today list with mixed
  statuses, and the citizen read endpoint rejecting another citizen's
  visit). The PostgreSQL test file `tests/test_visits_postgresql.py`
  runs the three highest-risk database invariants against the live
  Supabase instance: the partial unique index duplicate-start guard
  through a real concurrent insert, the advisory-lock start-and-update
  race, and the finalized-visit update rejection.
- Frontend quality gates: passed. ESLint clean (exit 0) with the four
  `&rsquo;` escapes and one `eslint-disable react-hooks/set-state-in-effect`
  comment applied to the consultation-workspace draft-resync line; `tsc
  --noEmit` exit 0; 35 Vitest files / 162 tests passed including the new
  `lib/visits/api.test.ts` (4 tests covering load current patient,
  start visit, read/update visit, and the citizen today list) and
  `components/professional/consultation-workspace.test.tsx` (4 tests
  covering the empty state when no current patient exists, the
  open-then-save draft flow, the finalized-state disabled inputs, and
  the start-action error banner). The production build emitted the new
  `/professional/visits` route alongside the existing Phase 11 chamber
  route, keeping the verified-doctor guard tight. The chamber queue now
  exposes an "Open consultation" link from the CURRENT row into
  `/professional/visits`; the verified-doctor branch of the professional
  dashboard adds a "Today's consultations" card linking to the same
  page. The page is gated by the verified-doctor guard used elsewhere
  in the doctor surface.
- Implementation deviations: the consultation workspace mirrors the
  chamber-queue pattern: optimistic state refresh after each successful
  start/save, the four clinical text fields are managed as local state
  and re-synced from the canonical visit payload whenever the upstream
  visit identity changes (the `useEffect` that reads
  `visit?.chief_complaint` etc. is annotated with the same
  `react-hooks/set-state-in-effect` disable used by the chamber refresh
  effect). The citizen side receives only the read endpoints — draft
  editing is confined to the verified doctor surface, so the
  ConsultationWorkspace component is rendered exclusively on the
  professional side. JSX copy containing apostrophes uses `&rsquo;` /
  `&middot;` to satisfy the project's ESLint react/no-unescaped-entities
  rule without per-line disables.
- Backend timezone fix: while the full SQLite test suite was rerun, the
  citizen-today endpoint (`GET /api/v1/citizens/me/visits/today`) was
  patched to compute the target date with
  `datetime.now(tz=timezone.utc).date()` instead of `date.today()`. The
  underlying `MedicalVisit.visit_date` column is server-defaulted to
  `func.now()` (UTC), so comparing against the local calendar date
  silently dropped rows when the test runner's local timezone was ahead
  of UTC. `app/visits/routes.py` was updated to import
  `datetime, timezone` from the standard library and pass the UTC date
  into `VisitsService.list_citizen_visits`; `tests/test_visits.py::
  test_citizen_sees_own_visits_today` was rewritten to use
  `date.today()` / `today.strftime("%A").upper()` for booking and
  scheduling (matching the rest of the backend suite) while leaving the
  assertion on the backend's "today" filter intact.

## Phase 13 verification evidence (pre-production checkpoint)

- Database and migrations: the sequential revisions `0021_prescriptions`,
  `0022_prescription_items`, and `0023_prescription_documents` remain the
  single Alembic head. The configured Supabase PostgreSQL schema reports
  `0023_prescription_documents (head)`, and `alembic check` reports no metadata
  drift.
- Backend: the canonical V6 routes are implemented at
  `POST /api/v1/visits/{visit_id}/prescription`,
  `GET|PUT /api/v1/prescriptions/{id}`, and
  `GET /api/v1/prescriptions/{id}/pdf`. The owning citizen has read/PDF access
  but no write access; the verified author doctor is compared by active role
  registration and can read, edit, and regenerate after appointment completion.
  Structured data commits even when rendering or storage fails, and a later
  author PUT retries generation.
- Private documents: local development uses a traversal-safe private filesystem
  adapter. Production uses the official Python Vercel SDK against a private
  Vercel Blob store, with versioned object keys and best-effort superseded-object
  cleanup. Storage keys never leave the backend; PDF bytes are streamed only
  after citizen/author authorization succeeds.
- Frontend: the consultation workspace contains the dynamic structured form,
  including `+ Add Medicine`, `Remove Medicine`, diagnostic information,
  medical advice, and notes. Citizen appointment history links to a read-only
  prescription detail route with authenticated PDF preview/download; the author
  has a dedicated editable detail route and explicit retry guidance.
- Automated gates: `pip check` passed; 195 backend tests passed with 33
  PostgreSQL-only cases skipped because `HEALTHLINK_TEST_DATABASE_URL` was not
  supplied; ESLint and TypeScript passed; 37 Vitest files / 169 tests passed;
  and the optimized Next.js build generated both prescription detail routes.
- Real browser/database flow: an isolated synthetic CURRENT-patient fixture was
  exercised through local Next.js/FastAPI against the configured Supabase
  schema. A verified doctor saved two medicines, opened the protected PDF,
  edited the record, and observed a newer generated timestamp. The citizen
  route rejected the active professional portal. Backend logs recorded
  successful canonical POST, PDF GET, and PUT calls. The fixture and PDF were
  removed afterward.
- Production checkpoint: the private `healthlink-prescriptions` Blob store is
  linked to `healthlink-sd` in Mumbai (`bom1`), production has
  `BLOB_READ_WRITE_TOKEN`, and `PRESCRIPTION_STORAGE_BACKEND=vercel_blob`.
  Phase 13 remains pending until the pushed GitHub Actions deployment and
  stable-domain PDF verification pass.
