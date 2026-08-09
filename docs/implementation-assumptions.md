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
