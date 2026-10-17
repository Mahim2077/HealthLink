# Fresh local browser QA — 2026-10-17

**Historical first pass: two defects reproduced. Final local pass: repaired,
8 cases passed, zero failures/skips (29.6 seconds).** See
`PHASE_31_LOCAL_RELEASE_REPORT.md` for current evidence. The final pass uses the
optimized production build and no workarounds; production deployment is held.

Owner requested testing, not a production release. Application code was not
changed in this pass; reproducible browser tests and this evidence were added.
No commit, push, deployment, production migration or production inspection ran.

## Environment and evidence

- Final run: **6 passed, 1 failed, 0 skipped, 46.0 seconds**. The failed case
  contains both confirmed regression assertions; the other cases use the
  explicitly documented workarounds. This is not a clean acceptance result.
- Real headless Microsoft Edge, Playwright 1.64.1, Node 24.20.0.
- Local Next.js frontend `127.0.0.1:3001` → same-origin `/api/v1` → FastAPI
  `127.0.0.1:8001` → dedicated PostgreSQL 17.6 at loopback port 55433.
- Unique synthetic users, facility, schedules and clinical records for each run.
  Existing accounts were not overwritten or deleted. No real patient records or
  production credentials were used. All browser external requests were blocked.
- Backend mock AI only. Record-aware synthetic testing was enabled locally;
  production/default AI flags were not changed. No external model requests.
- Browser sessions were isolated by actor. Authenticated API failures, browser
  exceptions, console errors and horizontal document overflow were checked.
  Expected anonymous session probes and explicit negative tests were excluded.
- Source: `scripts/browser-qa/`; setup/limits: its `README.md`.
- Ignored generated evidence: `.runtime/browser-qa/report/index.html`,
  `.runtime/browser-qa/results.json` and PNG attachments under `results/`.

## Defects

### P1 — Opening a chamber advertises a patient that is not persisted

Reproduction: book the synthetic doctor's first appointment, open today's chamber,
then refresh or follow Open consultation. Start returns serial 1 as CURRENT, but
the next request sees WAITING, and consultation displays No active patient.
Read-only inspection of the isolated database confirmed BOOKED/ACTIVE/WAITING
with matching doctor, facility and date.

Cause: `AppointmentService.start_session` commits at
`backend/app/appointments/service.py:511`, then promotes the first waiting patient
at line 522. Promotion only flushes. Request-session closure rolls it back, and
the earlier commit also releases the transaction advisory lock before promotion.

Tested workaround: Refresh queue, then Call next patient. That action commits its
promotion, allowing the full consultation journey to continue. This is not a fix.

Recommended repair: keep chamber activation and initial promotion in one locked
transaction, persist both before responding, and add a regression spanning
separate HTTP requests/database sessions (including concurrent opening).

### P2 — Record-sharing search misses the doctor's displayed full name

Reproduction: Medical record sharing → Search verified doctors → enter the exact
displayed first and last name. The response succeeds but contains no matching
doctor. Searching by the unique surname returns the doctor; grant creation and
revocation then work.

Cause: `backend/app/access/routes.py:61` matches the entire input separately
against first name, last name and designation, never the combined full name.
This is the privacy/sharing picker, not the modern appointment doctor finder.

Recommended repair: add escaped, case-insensitive full-name matching, preserving
verified/active doctor filtering, deterministic ordering and bounded results.

Both defects have explicit failing assertions in the final regression case.
The journey cases annotate their normal-UI workarounds; they must not be mistaken
for evidence that these defects were fixed.

## Functional coverage

- Citizen, doctor, lab technician and admin logins and real overview projections.
- Prescription explanation preserves recorded instructions and unknown doctor
  intent. Generated PDF is valid `%PDF` bytes in the UI's actual in-memory Blob,
  with private/no-store response headers; no PDF is downloaded or persisted.
- Doctor search, all 64 zila choices, manual upazila nearest search, distance
  display without coordinate jargon, and real appointment booking.
- Emergency profile edit is visible to the patient's current doctor.
- Historical prescription authored by another doctor is readable during the
  current consultation without edit controls. Unified clinical/prescription save,
  dirty-state Finish protection, test assignment, appointment completion and
  later author-only prescription editing work.
- Lab-only navigation and exact assigned test workflow: begin work, save/edit
  draft, dirty-state finalization protection, accept finalization confirmation,
  immutable report, citizen draft denial and finalized result/trend visibility.
- Admin overview, verification listing, facilities and identity search using a
  private POST body without identifiers in the URL. Wrong-portal access denied.
- Another synthetic citizen cannot read the new prescription (404/no medicine).
- General and record-aware mock AI, fresh consent per request, keyboard tab
  navigation, explicit emergency escalation and consent-gated history summary.
- Saved reminder creation, access-history display, scoped grant create/revoke
  (surname workaround), and legacy lab route redirect to Diagnostic tests.

## Responsive scope and limitations

Four widths: 390, 768, 1366 and 1920 pixels. Each role's dashboard, primary
workspace and populated detail screen are checked for document overflow and
captured. Details include citizen diagnostic results, doctor prescription editor,
lab finalized report and admin identity support. Dashboard skip links and heading
count are checked; contexts use reduced motion. Table containers may scroll
internally, without forcing the whole document wider.

This is not exhaustive WCAG/screen-reader or touch-target certification, live GPS
permission testing, a real-provider medical/Bangla evaluation, multi-browser
coverage or production verification. Admin approval/address geocoding mutations
were not performed. The earlier 514 backend/261 frontend automated checkpoint
was not rerun here because application code was unchanged.

Phase 30 remains open for repairs, repeat acceptance and remaining manual gates.
Phase 31 remains local release preparation only; owner approval is required for
commit, push and deployment.
