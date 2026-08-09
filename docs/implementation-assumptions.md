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
