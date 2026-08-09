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
