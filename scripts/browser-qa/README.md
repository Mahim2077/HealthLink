# Local synthetic browser QA

This suite drives real Microsoft Edge against the local frontend, API and a
dedicated loopback PostgreSQL database. It does not mock frontend API responses.
AI responses come from the backend mock provider, never a live model.

Prerequisites for this workstation:

- Dedicated QA database `healthlink_phase27_qa` at `127.0.0.1:55433`, already
  migrated to the application's current head. Never substitute production.
- Backend at `127.0.0.1:8001`, explicitly configured without developer `.env`
  loading, using that database, mock AI and synthetic-only record-context access.
- Frontend at `127.0.0.1:3001`, with same-origin `/api/v1` rewritten to that API.
- Existing root `.venv` with backend/test requirements and Microsoft Edge.
- Node 24; Playwright installed separately in ignored runtime storage:

```powershell
npm install --prefix .runtime/browser-qa --no-audit --no-fund @playwright/test@1.64.1
node .runtime/browser-qa/node_modules/@playwright/test/cli.js test --config scripts/browser-qa/playwright.config.cjs
```

The seed script creates new uniquely named synthetic accounts and records for
each invocation; it refuses duplicate run IDs. It never overwrites or deletes
existing accounts. Failed runs intentionally leave their isolated synthetic
fixtures available for diagnosis. Passwords in this fixture are dummy local
test values, not production credentials.

Browser requests are restricted to the local frontend origin. Separate browser
contexts isolate each portal's session. Generated reports/screenshots remain
under ignored `.runtime/browser-qa`; no PDF is written to disk. The PDF assertion
checks the in-memory Blob actually received by the UI.

The suite now contains **20 cases** covering the care journey, privacy/AI,
four-viewport portal matrix, Settings/session controls, Light/Dark/System themes,
synthetic schedule/facility/verification operations and survey regressions. The
journey requires first-patient promotion to survive refresh, full-name sharing
search, denial of unfinished Citizen prescriptions and publication after actual
Finish Appointment; no workaround is used. The same prescription's AI explanation
must return 404 before Finish Appointment and 200 afterward. A fault-injection
case aborts the first area catalog request, then checks real-API retry, focus on
the enabled Zila select and successful manual nearby search without an extra
doctor search during catalog recovery.

Four survey cases cover landing bounds/response policies, filtered-history return
and native date Apply, mobile empty-chat top alignment, truthful reminder copy,
unsaved practice transitions, filtered-empty facility state and booking at a
selected secondary facility through its correct name in appointment history.
The secondary-facility case continues through selecting that chamber, queue
activation, consultation/prescription, draft denial, actual Finish Appointment
and finalized Citizen publication. It no longer stops at booking.
A closed-chamber regression checks that booking is rejected with useful copy,
then succeeds for the next published weekly date without consuming a serial
for the rejected request.
The seed provides a unique secondary facility without altering existing accounts.
The PDF browser assertion still checks the in-memory Blob; separate fully
synthetic metadata PDFs may be generated/rendered under ignored runtime storage
for date/age/facility layout checks, never as stored application prescriptions.

The 2026-10-17 final pass used the optimized production build locally. A temporary
loopback-only reverse proxy mirrored Vercel Services routing (frontend port 3003,
API port 8001, browser origin port 3001); it neither mocked responses nor changed
the committed Vercel/Next configuration. The normal development server uses the
existing development rewrite. See `docs/PHASE_31_LOCAL_RELEASE_REPORT.md`.

This is a focused Edge acceptance pass, not cross-browser, screen-reader,
penetration, real-provider, production or exhaustive accessibility certification.
No commit, push, deployment, production migration or live model call is made.
