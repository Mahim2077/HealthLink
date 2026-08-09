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
| 6 | Facility Registry and Professional Verification | Not started |
| 7 | Professional Login and Active Role Context | Not started |
| 8 | Admin Citizen Identity Support | Not started |
| 9 | Doctor Search and Practice Schedule | Not started |
| 10 | Appointment Booking and MAX Serial Assignment | Not started |
| 11 | Doctor Daily Chamber Session and Serial Queue | Not started |
| 12 | Current Patient Clinical Access and Consultation Workspace | Not started |
| 13 | Chamber Prescription Form and Electronic PDF | Not started |
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
