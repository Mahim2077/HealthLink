# Phase 32 final release-readiness assessment — 2026-11-04

> **Historical pre-fix assessment.** FR-01 was subsequently corrected and
> verified; see [the correction report](FR_01_SECONDARY_FACILITY_CORRECTION_2026_11_04.md)
> for the current local candidate. The failed checks and decision below describe
> the earlier tested version and remain preserved evidence.

## Decision: NOT READY

The current local release candidate has one newly confirmed functional release
blocker, **FR-01 / P2**: a Citizen can book a Doctor's published secondary
facility, but the same Doctor cannot view or start that facility's chamber.
The booking is accepted, yet the normal care workflow cannot continue.

Existing regression totals are green, including the previous QA-01 and QA-02
corrections. The added end-to-end boundary check fails. Passing totals do not
override that failure. **Do not deploy this candidate to close Phase 32.**

This assessment does not introduce another phase. The planned Phase 32 closing
release remains open until the blocker is corrected, verified and successfully
deployed. No commit, push, production migration or deployment was performed.

## Candidate and isolation

- Date: **2026-11-04, Asia/Dhaka**.
- Workspace: `D:\HealthLink_V_1`, branch `main`, base HEAD
  `70059d3df275be7cabfd92a24d963f1d0b4849cd`, plus the current uncommitted work.
  Here, “staging” means that local candidate; no new hosted staging deployment
  was created or certified.
- Source identity: **528** application/test/config files, SHA-256
  `411fe0bd880e20348eb51334ee140d5f0bea9736d435e98cce85e8c970d06ffa`
  of compact JSON sorted relative-path/content-hash pairs. Manifest and per-file
  hashes are retained with the receipts. Product source was not changed to
  obtain these results; documentation and ignored test probes are separate.
- Runtime: Node **24.20.0**, npm **11.17.0**, Python **3.13.7**, PostgreSQL **17**,
  Next.js **16.4.2**, Microsoft Edge through Playwright **1.64.1**.
- Black-box origin: `http://127.0.0.1:3001`, with a loopback router to the fresh
  optimized frontend on 3003 and actual API on 8001. Synthetic fixtures use
  `healthlink_phase27_qa` on PostgreSQL port 55433.
- Explicit test settings disable developer environment-file loading, use mock
  AI and an empty provider key. No production account, production database,
  medical record or live model call was used. Unique fixture identities are
  created without overwriting earlier accounts.

## Fresh white-box and release-gate results

| Check | Result |
| --- | --- |
| Backend full pytest suite | **602 passed**, 63 modules; zero failures/errors/skips; 120.64 seconds |
| PostgreSQL cases within backend total | **40 executed**; other 562 use the suite's other fixtures |
| Fresh database migration / metadata | `healthlink_fix_224a12636600`, head `0031_ai_conversations`; no drift |
| Python consistency | `pip check` passed |
| Strict Python runtime/development audits | Both passed; no known vulnerabilities found |
| Python lock reproduction | Runtime and development locks both byte-identical after fresh compile with **uv 0.12.7** |
| Frontend Vitest | **343 passed**, 64 files; zero failed/pending; 10.05 seconds |
| Security / dependency-adapter tests | **17 passed**; zero failed/cancelled/skipped/todo |
| ESLint / TypeScript | Both passed |
| npm production audit gate | **0 flagged entries, 0 exceptions used** |
| npm full-tree audit gate | **0 flagged entries, 0 exceptions used** |
| Clean dependency installation | Passed in a separate ignored folder; **448 packages**, scripts disabled; lock byte-identical |
| Official minimatch engine in clean install | Genuine `minimatch@11.0.4`; existing compatibility guards pass |
| Optimized Next build | Passed after the frontend gates; **44 static pages** and dynamic routes; 6.73 seconds |
| Bounded source review | **FR-01 found**, then independently HTTP-confirmed |
| Source stability / whitespace | All **528** manifest files unchanged through testing; `git diff --check` passed |
| Heuristic credential check | **573** candidate text files scanned; zero actionable matches; one synthetic example-host unit fixture reviewed |

White-box work includes the regression suites' service, policy, provider,
component-state, migration and database-constraint checks plus targeted source
inspection. No statement/branch coverage percentage was measured.

The source review covered prescription publication across normal/AI routes,
saved-chat ownership and record consent, multi-facility scheduling and booking,
the development-only dependency adapter and approved-target/stale-head CI
guards. The framework, lint configuration, dependency locks and security policy
were not changed. Existing non-failing React `act(...)`, TestClient deprecation
and npm ESLint deprecation warnings are not presented as functional failures.
The backend harness also emits an `anyio` import/assert-rewrite warning; all
tests execute. An initial execution request stalled/aborted before returning a
test receipt. The subsequent approved command executed against the fresh
database above; the 602 count comes only from its completed JUnit receipt.
The lock compiler emits non-failing upstream version-metadata normalization
warnings; both commands exit zero and reproduce the exact source bytes.

## Fresh black-box results

| Check | Result |
| --- | --- |
| Optimized-build Edge acceptance | **19/19 passed**; zero failed/flaky/retries/skips; 95.65 seconds |
| Standard independent HTTP matrix | **28/28 passed** |
| Added secondary-facility workflow | **5/7 passed, 2 failed** — queue view and chamber start |

The browser suite covers Citizen → Doctor → Lab → Citizen care, ordinary
prescription/PDF access, saved chat and consent, search/manual-area retry,
Settings/security/theme behavior, administrative operations, survey regressions
and responsive portal states at 390/768/1366/1920 pixels. It checks browser
exceptions, console errors and unexpected API failures; browser network traffic
is restricted to the local origin. API responses are not stubbed in ordinary
acceptance. The area-retry test deliberately aborts only the initial catalog
request, then uses the actual API for recovery.

The independent HTTP matrix exercises anonymous/malformed/revoked sessions,
role and ownership denial, invalid input, finalized prescription/PDF success,
draft JSON/PDF/visit/AI denial and finalized AI success. It verifies actual PDF
signatures without storing application prescription PDFs.

Previously corrected findings remain verified:

- **QA-01:** owning Citizen draft AI access returns 404 before provider/audit;
  authorized current-Doctor draft access remains. The browser journey and
  backend regression use the same prescription before and after actual Finish
  Appointment, then confirm Citizen access becomes available.
- **QA-02:** the deferred integration test retains disabled-state and eventual
  enabled/focus assertions. The browser catalog retry restores Zila focus and
  completes manual nearby search without an extra Doctor search during retry.

## FR-01 / P2 — secondary booking cannot reach the Doctor's chamber

### Independent reproduction

Using unique synthetic users with one verified Doctor registration at the
primary facility, exercise only public HTTP API operations after fixture setup:

| Step | Expected | Actual |
| --- | --- | --- |
| Sign in as the verified Doctor and owning Citizen | Both 200 | Both 200 |
| Publish an active practice schedule at the secondary facility | 201 | 201 |
| Book that Doctor/secondary facility on its published date | 201 | 201; correct secondary facility and Doctor registration |
| Start the same Doctor/date at the primary facility as a control | 200 | 200 |
| Read that Doctor/date's secondary chamber queue | 200 | **409** |
| Start that Doctor/date's secondary chamber | 200 | **409** |

Both failed responses return:

```json
{"detail": "Verified doctor is not associated with this facility."}
```

The positive controls exclude a missing route, invalid Doctor login or invalid
date as the explanation for the secondary facility failure. This is a functional
workflow mismatch, not evidence of cross-patient disclosure. Testing stopped
at this broken care boundary; no secondary consultation completion is claimed.

### Source cause and coverage gap

`backend/app/doctors/service.py` allows a verified Doctor to publish schedules at
active facilities beyond the registration's linked facility. The booking path
accepts such a published schedule. However,
`backend/app/appointments/service.py:495` and `:550` require the requested chamber
facility to equal the active Doctor registration's facility. The chamber UI in
`frontend/src/app/professional/chamber/page.tsx:170` also passes only that linked
facility, without selecting the secondary practice context.

Existing browser case 18 proves secondary schedule selection, booking and
display of the correct facility name. It ends at booking. The full care journey
uses the primary facility. Neither establishes that an accepted secondary
booking can be seen and serviced by its Doctor. The added HTTP probe exposes
this previously untested integration boundary.

### Required correction before release

Preserve the implemented multi-facility scheduling/booking feature. Align the
Doctor's authorized facility/session context across chamber selection, queue
reads and actions, current-patient consultation, prescription and finalization.
Retain verified identity/registration ownership, facility/patient isolation and
queue/concurrency constraints. Removing the facility check alone does not
establish a safe complete fix.

Add a persistent regression that takes an accepted secondary-facility booking
through queue activation, consultation/prescription, actual Finish Appointment
and finalized Citizen publication. Include unauthorized other-Doctor/facility
controls and multiple-session isolation. Recheck the primary journey as well.

## Evidence and operational limits

Ignored receipts: `.runtime/final-phase32-qa-20261104/`, including backend/Python
gate receipts, `frontend-full.json`, `frontend-*.log`, `frontend-*-run.json`,
`clean-install-run.json`, `browser-results.json`, `browser-report/`,
`browser-results/`, `api-blackbox-results.json`,
`secondary-facility-blackbox-results.json`, `source-review.md` and
`code-fingerprint.json`. The added HTTP probe returns a nonzero exit code for
its two failures. Older QA evidence was not overwritten.
The loopback frontend, API, router and exact PostgreSQL cluster were stopped
after testing. Synthetic fixtures and ignored evidence remain for diagnosis.

This is local Edge and API verification with mock AI. It does not certify live
provider semantics, all browsers, screen readers, penetration resistance,
production environment values or hosted staging/production state. A read-only
Vercel project lookup could not execute because the connector requires its
connection `link_id`; no alternate account or CLI identity was used.

After FR-01 is fixed, verify the corrected exact candidate and normal CI gates.
A later authorized release must retain migration → staged deployment without
live domains → protected smoke → promotion → stable-origin smoke, using only
the approved Mahim2077 GitHub/Vercel target. Close Phase 32 and the existing
phased plan only after that production receipt is recorded. New phases remain
for the owner's later planning.
