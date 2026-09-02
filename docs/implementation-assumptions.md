# Implementation assumptions

Only minor details not fixed by the governing documents are recorded here.
V6 remains authoritative if an assumption ever conflicts with it.

## Phase 0

- Local verification may use an isolated PostgreSQL 17 cluster under the
  ignored `.postgres-data/` directory when no Neon `DATABASE_URL` is supplied.
  Application code remains environment-driven and PostgreSQL-compatible.
- Backend Python packages are kept in the single documented
  `backend/requirements.txt`; frontend packages are kept in the single
  `frontend/package.json` and npm lockfile.
- The root landing page is informational in Phase 0. Portal login and workflow
  routes are introduced only in their documented phases.

## Phase 1

- Refresh-session expiry is a fixed absolute deadline. Rotation replaces only
  the stored token hash in the locked session row and does not extend
  `expires_at`.
- The refresh cookie uses `HttpOnly`, `SameSite=Lax`, and path
  `/api/v1/auth`; it is `Secure` in staging/production. This assumes the three
  portals and API are deployed in a same-site arrangement through Phase 14.
- Access tokens are invalidated immediately when their database session is
  revoked because every protected request validates both the signed JWT and
  the corresponding `auth_sessions` row.
- Access-token state exists only in client memory. Refreshes are single-flight,
  and refresh, logout, logout-all, and future login/session replacement are
  serialized so browser cookie response ordering cannot resurrect a terminated
  session.
- Idempotent single-session logout accepts the refresh cookie and an optional
  signed access-token session hint. Only expiration may be ignored for this
  logout-only decode; signature, fixed algorithm, type, and typed claims remain
  mandatory, and the operation can only revoke the token's own matching
  session. This keeps logout reliable after access-token expiry and across
  browser tabs without granting application access.

## Phase 2

- Citizen registration returns a `201` account-created response without issuing
  a session. The documented Register → Login workflow is explicit: only a
  successful citizen login creates the CITIZEN refresh session.
- Registration passwords are 8–128 characters. Login accepts 1–128 characters
  so every syntactically bounded wrong password reaches the same generic `401`.
  Login performs one Argon2 verification for every attempt, using a valid
  precomputed dummy hash when no account exists, to avoid an email timing oracle.
- Emails are trimmed and lowercased. Names, identity strings, and optional text
  are trimmed; NID and Birth Certificate Numbers remain opaque strings so
  leading zeroes and non-government-specific characters are preserved. No
  external government-format validation is invented.
- Date of birth may be any non-future local calendar date; no minimum age is
  imposed because BCN registration must support younger citizens. Gender and
  blood group remain bounded strings in the API/database; the frontend selects
  common presentation values without introducing authoritative database enums.
- Initial registration enforces exactly one NID or BCN in both request and
  service validation. The database intentionally requires at least one rather
  than exactly one so Phase 3 can retain the original BCN after adding an NID.
  `registered_with` is derived by the server and constrained to `NID` or `BCN`.
- Foreign keys use `RESTRICT`, consistent with the no-hard-delete model. Unique
  constraints are the authoritative NID/BCN indexes; no redundant indexes are
  added.
- The owner-authorized identity endpoint returns the citizen's exact nullable
  NID/BCN value because no masking contract is specified. The frontend masks it
  by default (fully masking identifiers of four or fewer characters) and never
  persists raw identity or access-token data in browser storage.

## Phase 3

- `PUT /citizens/me/profile` is a full replacement of the documented editable
  citizen fields: first and last name, date of birth, gender, blood group, and
  address. Email, password, user identifiers, NID, and BCN are forbidden from
  that payload. The same trim, length, and non-future-date rules used at
  registration remain in force.
- The BCN to NID confirmation is the exact, case-sensitive string `CONFIRM`;
  surrounding whitespace is not normalized. This check is performed
  independently by the frontend and backend.
- A successful self-service NID addition does not change `registered_with`:
  it remains `BCN` to preserve how the citizen originally registered. The BCN
  remains stored and visible in the owner-only identity response, while both
  values stay masked in the interface.
- Phase 3 needs no Alembic revision because Phase 2 deliberately created the
  nullable national-identifier link and `nid_added_at` column and its database
  check already permits the post-upgrade BCN-plus-NID state.

## Phase 4

- Alembic's standard `version_num VARCHAR(32)` cannot store the plan's full
  descriptive logical migration names. Internal revision identifiers use the
  ordered, unambiguous abbreviations `0006_prof_profiles`, `0007_prof_roles`,
  `0008_prof_role_regs`, and `0009_doctor_reg_details`; table names and phase
  ordering remain exactly as documented.
- New professional registration returns a `201` PENDING application without a
  session. From Phase 7 onward, professional login is exposed at
  `POST /api/v1/auth/professional/login` and the selected role becomes the
  active role context for the session; the JWT carries an optional `prrid`
  claim that the professional dependency validates against the live session
  row. PENDING and REJECTED role registrations can complete login but cannot
  satisfy `require_verified_professional_role(role_code)`.
  Existing-account onboarding derives the user and NID exclusively from the
  authenticated session and central identity row; it never accepts client-owned
  user or NID fields.
- Facility input remains the submitted free-text name until Phase 6 performs
  administrator matching or creation. No facility table or foreign key is
  introduced early.
- The frontend role selector mirrors the six authoritative roles seeded by the
  database. Doctor input requires BM&DC; all non-doctor payloads omit it.
  Facility name, designation, and additional information are trimmed and
  required for every initial application, with additional information stored as
  unbounded database text.

## Phase 5

- There is no public or authenticated admin-registration API. The initial
  administrator is created only through the trusted local provisioning command,
  which prompts for the password twice instead of accepting it in command-line
  arguments or writing it to logs.
- Initial trusted provisioning refuses an email already owned by any user. The
  documents do not define a workflow for promoting an existing citizen or
  professional account, so that materially different identity-linking operation
  is not invented in Phase 5.
- Admin login issues the existing shared ADMIN session and token response; it
  does not create or alter an account. The same HttpOnly, fixed-expiry refresh
  cookie and in-memory access-token rules apply to the admin portal.
- `admin_action_logs` is created in Phase 5 as documented, but login itself is
  not treated as an administrator action. Audit rows begin when the documented
  facility, verification, and identity-correction actions exist in Phases 6
  and 8; no speculative login-audit behavior is added.

## Phase 6

- Alembic revision identifiers use the ordered abbreviations
  `0012_facilities` and `0013_role_facility_fk` to remain within Alembic's
  32-character version column. The foreign-key constraint also has a compact
  PostgreSQL-safe internal name; the documented table, column, and migration
  order are unchanged.
- The four documented facility types are enforced by request validation and a
  database check. Facility names and optional registration numbers are not made
  unique because the authoritative schema specifies no uniqueness rule; the
  documented name index supports matching without silently merging branches or
  organizations that share a name.
- `PUT /admin/facilities/{id}` is a full replacement of the editable facility
  fields. There is no delete route in Phase 6; administrators can mark a record
  inactive while preserving references and auditability.
- Verification accepts an existing active `facility_id`. When the submitted
  name has no match, the admin first uses the separately documented facility
  creation route and then verifies the application. Inline facility creation is
  not added to the review payload, keeping both documented operations explicit.
- A review decision is terminal: only `PENDING` applications can become
  `VERIFIED` or `REJECTED`. Repeated or competing decisions return a conflict;
  the row lock and single transaction ensure one audited winner. The documents
  define no appeal or re-review workflow through Phase 14.
- Facility create/update actions are audited in addition to the explicitly
  required verification/rejection actions because they are trusted admin
  mutations. Action types are stable uppercase literals and target the affected
  facility or professional role registration; rejection stores its exact
  trimmed reason.
- The list route accepts an optional `verification_status` filter and returns
  all statuses when it is omitted. The interface opens on `PENDING` for the
  operational queue and offers explicit All, Verified, and Rejected views.

## Deployment infrastructure

- Vercel deployment uses one `healthlink-sd` project with Vercel Services:
  `frontend/` is the Next.js service and `backend/` is the FastAPI service.
  This infrastructure does not change or complete any HealthLink
  implementation phase.
- Production deployment runs only after a push to `main` passes the backend,
  frontend, and migration gates. Pull requests run CI without changing the
  production database or deploying.
- Browser API requests use the root-relative `/api/v1` URL. Vercel routes them
  to the backend service on the same origin, preserving the existing host-only
  HttpOnly refresh-cookie model without weakening `SameSite=Lax` or adding a
  broad preview-origin CORS rule.
- `healthlink-sd` is the Vercel project slug and
  `healthlink-sd.vercel.app` is its deployed stable domain. A separately
  purchased custom domain can be attached later.
- Vercel Services and the Vercel Python runtime must be enabled for the account;
  Services is access-controlled while it remains in private beta. Nginx is not
  used because Vercel does not run persistent reverse-proxy processes.
- Local prescription storage is suitable only for development. Vercel's
  function filesystem is ephemeral, so Phase 13 prescription PDFs require a
  durable private object-storage adapter before that workflow is production
  ready.
