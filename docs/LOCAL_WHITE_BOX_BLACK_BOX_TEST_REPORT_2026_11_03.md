# Local white-box and black-box test report — 2026-11-03

> **Historical pre-fix report.** QA-01 and QA-02 were addressed and retested on
> 2026-11-04. See [the correction report](QA_DEFECT_CORRECTIONS_2026_11_04.md)
> for current local status. Original failures and evidence below are preserved;
> publication remains held.

## Result: one confirmed defect; publication remains held

Testing covered the current local working tree, including the survey fixes,
Python security patch and minimal minimatch adapter. It found:

1. **QA-01 / P2 — confirmed:** an owning Citizen can obtain an AI explanation of
   an unfinished prescription even though its normal JSON, PDF and visit reads
   are denied. Independent local HTTP requests reproduced this publication bypass.
2. **QA-02 / P3 — intermittent test finding:** one manual-area retry focus test
   failed in the first executable frontend run. Isolated and full reruns passed;
   two real-browser fault-injection attempts also passed. A user-visible focus
   defect is not established, but the original test failure remains open evidence.

The existing browser suite passed, but the supplemental negative tests found
QA-01. **The local version should not be treated as release-ready from green
test totals alone.** Fix QA-01 and its stale regression expectation before release;
investigate QA-02's timing/test stability. No product code or existing tests were
changed to obtain these results. No commit, push or deployment was performed.

## Tested version and isolation

- Date/time context: **2026-11-03, Asia/Dhaka**.
- Workspace: `D:\HealthLink_V_1`; branch `main`; base HEAD
  `70059d3df275be7cabfd92a24d963f1d0b4849cd`, plus the existing uncommitted work.
  HEAD alone does not identify the tested application.
- Application/test/config fingerprint, identical before and after testing:
  `be555e9161d5f5439ae3c0c79d6fac80095e4cca08c7695b570c4ffd9efce395`.
  This hashes a sorted manifest of **528** tracked/unignored files under backend,
  frontend, scripts, security and workflows, excluding AGENTS documentation.
- Python **3.13.7**, Node **24.20.0**, npm **11.17.0**, PostgreSQL **17**,
  Microsoft Edge through the existing Playwright **1.64.1** harness.
- Backend regression database: newly created `healthlink_wb_c0c5125fec5e` on
  loopback port 55433. Browser/API fixtures use the separate synthetic
  `healthlink_phase27_qa` database. Each seed invocation creates unique accounts
  and refuses overwriting existing fixture identities.
- Black-box target: `http://127.0.0.1:3001`. A loopback proxy routes to the
  **optimized Next production build** on 3003 and real local API on 8001.
  Ordinary browser acceptance does not stub API responses.
- Explicit settings use `_env_file=None`, the loopback database, mock AI and an
  empty provider key. No production database, real account or live model was used.
- All API/frontend/proxy processes and the exact PostgreSQL cluster started for
  this task were stopped afterward. Synthetic data and ignored evidence remain.

## White-box testing

White-box work exercised internal functions, service/policy branches, database
constraints, provider boundaries and component state, and inspected selected
authorization and publication paths against their tests. No statement/branch
coverage percentage was measured; test counts must not be presented as one.

| Check | Fresh result |
| --- | --- |
| Backend pytest | **601 passed**, 63 modules, zero failures/errors/skips; 113.96 seconds |
| Actual PostgreSQL cases | **40 executed**; the other 561 use the suite's unit/model/route/provider/security fixtures, including SQLite/TestClient where designed |
| Fresh database migration | Head `0031_ai_conversations`; no Alembic metadata drift |
| Python consistency | `pip check` passed |
| Python runtime/development audits | Both strict PyPI/hash-lock scans passed, zero known vulnerabilities |
| Python lock reproduction | Both byte-identical with uv 0.12.7; source locks untouched |
| Frontend, first executable full run | **342 passed, 1 failed**, 64 files, 10.63 seconds — QA-02 |
| Focused QA-02 isolation | 1 passed, 15 deliberately filtered tests; not a full-suite skip result |
| Frontend, full confirmation | **343 passed**, 64 files, zero failures/skips; 11.63 seconds |
| Security / adapter tests | **17 passed**, zero failures/skips |
| ESLint / TypeScript | Both passed |
| npm production/full audit gates | Both zero flagged entries, zero exceptions used |
| Optimized Next build | Passed; all 44 static pages and dynamic routes compiled |

### Internal boundaries inspected

| Area | What was examined/exercised | Conclusion within this scope |
| --- | --- | --- |
| Authentication/session lifecycle | Bearer/session ownership, expiry/revocation, refresh rotation, logout and concurrent PostgreSQL rotation | Existing tests and supplemental HTTP checks pass |
| Clinical access | Citizen ownership, Doctor verification/current patient/authorship, scoped live grants, denied mutations and finalization | Canonical reads enforce publication; QA-01 exposes an alternate AI route inconsistency |
| Scheduling/appointments | Capacity/serial constraints, queue concurrency, current-patient promotion, secondary-facility identity | Existing regressions and browser care journey pass |
| Prescriptions/PDFs | Actual finalization transition, foreign-owner denial, historical metadata, on-demand generation | Canonical JSON/PDF tests pass; returned browser/API PDF signatures verified |
| Diagnostics | Requests, lab assignment/workspace, draft/final report lifecycle and ownership | Existing tests and Citizen–Doctor–Lab journey pass |
| Saved AI conversations | Owner lookup/list/detail/delete, replay/idempotency, concurrent deletion and General/history isolation | Existing unit and browser checks pass |
| Explanation-only AI | Consent/mode contracts, structured output, prompt rules, blocked diagnosis/prescribing output, timeout/error behavior | Code/provider-mock safeguards tested; live-model semantics not certified |
| UI state/accessibility | Modal/menu containment, storage failure, themes, unsaved transitions, search paging and catalog retry | Existing checks mostly pass; intermittent QA-02 retained |
| Dependency adapter / release guards | Genuine patched engine, dev-only consumer set/versions, module interop, live lint diagnostics, fail-closed audits and deployment target/order guards | 17 security/adapter tests pass; no new exception or CI bypass |

The 601-pass backend result does not disprove QA-01: an existing test explicitly
expects the inconsistent draft-AI success behavior. Its oracle is stale relative
to the newer finalized-only Citizen publication rule.

## Black-box browser testing

The browser used real UI actions and local HTTP/database responses, independent
portal contexts and synthetic data. AI responses came from the mock provider.
The full run passed **18/18**, zero skips/retries/unexpected failures, in
**99.35 seconds**. Each case checks browser exceptions, relevant console errors,
unexpected API failures and attempts to leave the allowed loopback origin.

| Browser case/group | Result |
| --- | --- |
| Citizen → Doctor → Lab → Citizen care journey, including save/finalize/history and PDF Blob | Pass |
| Saved chat: reopen/follow-up/new/delete and responsive composer | Pass |
| Record consent, history isolation, saved schedules and privacy | Pass |
| Four-portal matrix at 390px | Pass |
| Four-portal matrix at 768px | Pass |
| Four-portal matrix at 1366px | Pass |
| Four-portal matrix at 1920px | Pass |
| Synthetic schedule edit, facility update and Admin verification | Pass |
| Role-aware Settings, legacy links, privacy and identity detail | Pass |
| Display persistence, large text, mobile focus containment/restoration | Pass |
| All-session revocation and another account's session isolation | Pass |
| Light/Dark/System, pre-paint persistence, OS changes and tab synchronization | Pass |
| Dark portal/workspace matrix | Pass |
| Chamber persistence/full-name sharing summary guard | Pass; asserts outcomes already exercised in preceding journeys |
| Landing bounds and response headers | Pass; widths 320/390/768/1024/1280/1366 |
| Filtered history Back, mobile empty chat and truthful reminder text | Pass |
| Unsaved practice transitions and facility no-match recovery | Pass |
| Secondary-facility booking and saved facility name | Pass |

The run captured **118 primary screenshots**. Four representative captures were
visually inspected: dark mobile consultation, Admin mobile dashboard, mobile
empty chat and 320px landing. Their layout was readable without a new confirmed
visual defect in those samples. Automated viewport checks cover additional
screens; this is not an assertion that all screenshots received manual review.

### Supplemental HTTP matrix

All 28 method/path combinations were cross-checked against the local published
OpenAPI schema, so a nonexistent route could not supply a false 404 pass.
Assertions use HTTP responses only after synthetic fixture preparation.
**27 passed; 1 failed (QA-01).**

| # | Condition | Expected / observed | Result |
| --- | --- | --- | --- |
| 1 | Anonymous Citizen history | 401 / 401 | Pass |
| 2 | Malformed bearer token | 401 / 401 | Pass |
| 3 | Missing login fields | 422 / 422 | Pass |
| 4 | Wrong synthetic password | 401 / 401 | Pass |
| 5 | Citizen login | 200 / 200 | Pass |
| 6 | Second Citizen login | 200 / 200 | Pass |
| 7 | Doctor login | 200 / 200 | Pass |
| 8 | Admin login | 200 / 200 | Pass |
| 9 | Owner's history | 200 / 200 | Pass |
| 10 | Doctor token on Citizen history | 403 / 403 | Pass |
| 11 | Admin token on Citizen history | 403 / 403 | Pass |
| 12 | History page zero | 422 / 422 | Pass |
| 13 | Malformed history date | 422 / 422 | Pass |
| 14 | Doctor-search limit zero | 422 / 422 | Pass |
| 15 | Malformed prescription UUID | 422 / 422 | Pass |
| 16 | Owner's finalized prescription JSON | 200 / 200 | Pass |
| 17 | Owner's finalized PDF | 200 / 200; `%PDF-` signature | Pass |
| 18 | Foreign Citizen's finalized JSON | 404 / 404 | Pass |
| 19 | Foreign Citizen's finalized PDF | 404 / 404 | Pass |
| 20 | Owner's draft prescription JSON | 404 / 404 | Pass |
| 21 | Owner's draft prescription PDF | 404 / 404 | Pass |
| 22 | Owner's draft visit | 404 / 404 | Pass |
| 23 | Owner's draft AI explanation | **404 / 200** | **Fail: QA-01** |
| 24 | Foreign Citizen's draft AI explanation | 404 / 404 | Pass |
| 25 | Author-only Doctor's draft AI explanation | 404 / 404 | Pass |
| 26 | Owner's finalized control-record AI explanation | 200 / 200 | Pass |
| 27 | Current-session logout | 204 / 204 | Pass |
| 28 | Access token after logout | 401 / 401 | Pass |

The finalized control in case 26 is a separate existing finalized fixture; it
does not claim that this draft was finalized during the HTTP probe. The browser
care journey separately exercises an actual Finish Appointment transition.

### Controlled area-list failure/retry

Two additional browser attempts interrupted **only the first area-catalog network
request**, then used the real API for retry. Both showed Zila disabled during
failure, enabled and focused after retry, no redundant Doctor search during
catalog recovery, and successful manual-area submission with HTTP 200. This is
explicit fault injection, separate from the unstubbed 18-case acceptance run.

## Findings and recommended follow-up

### QA-01 — AI explanation bypasses Citizen draft publication

**Priority:** P2 / medium. **Status:** confirmed in source, an existing stale test,
and independent local HTTP. **Fix status:** not changed in this QA task.

Prerequisites: an authenticated owning Citizen, a known ID of that Citizen's draft
prescription, and enabled record-aware clinical AI. The test establishes premature
publication of an owner's unfinished record, not a cross-patient IDOR.

Reproduction:

1. Prepare a synthetic prescription whose visit is `DRAFT` with no finalization.
2. Sign in as the owning Citizen.
3. GET `/api/v1/prescriptions/{id}`, `/api/v1/prescriptions/{id}/pdf`, and
   `/api/v1/citizens/me/visits/{visit_id}`: each returns **404**.
4. POST `/api/v1/ai/prescriptions/{id}/explain`, without a request body: returns
   **200** and exposes the unfinished medicine instructions.

The synthetic response includes `Medicine A` and
`Dosage: 1 tablet; Frequency: Daily; Duration: 5 days` in `recorded_instructions`.
Foreign-Citizen and author-only Doctor control requests returned 404.

Source cause: [clinical_service.py](../backend/app/ai/clinical_service.py),
`_authorize_prescription` around line 169, computes finalization but returns
Citizen SELF access after ownership checking before centralized publication
policy. `explain_prescription` around line 313 then constructs the record payload
and invokes the provider. No real provider was invoked by this test.

The existing
[draft explanation test](../backend/tests/test_ai_clinical_explanations.py),
`test_own_draft_prescription_matches_citizen_read_authority_but_not_author_only`
around line 348, still expects Citizen 200. That explains why the backend suite
is green while this contract is inconsistent with canonical reads.

Recommended minimal repair: enforce the same finalized-only Citizen policy
before payload construction/provider invocation. Replace the stale expectation
with draft denial and zero provider calls, and verify success after the actual
finalization transition. Preserve legitimate Doctor scopes and foreign-owner
denial. No schema or technology-stack change is indicated by this finding.

### QA-02 — intermittent manual-area retry focus assertion

**Priority:** P3 / low, test stability/accessibility investigation.
**Status:** one executable unit-suite failure; user-visible defect unconfirmed.

The failed assertion is at
[doctor-search.test.tsx](../frontend/src/components/citizen/doctor-search.test.tsx)
around line 286. Zila was enabled while focus remained on Close. Focused and full
confirmation runs passed unchanged; two optimized-build browser attempts also
focused Zila and completed the manual search.

A possible timing window exists in
[doctor-search.tsx](../frontend/src/components/citizen/doctor-search.tsx): the
focus effect depends on `manual`/`areas`, but the select is also disabled by
`areasLoading`, which clears separately in `.finally()`. This is a hypothesis,
not a proven production-browser race. Investigate state/effect ordering and
asynchronous test synchronization; do not remove the focus requirement or count
passing retries as proof of deterministic behavior.

## Evidence, reproduction and limits

Local raw receipts live under `.runtime/white-black-qa-20261103/` and are Git
ignored. They are available on this workstation, not bundled into a fresh clone:

- [Backend execution receipt](../.runtime/white-black-qa-20261103/backend.md),
  [JUnit XML](../.runtime/white-black-qa-20261103/backend-junit.xml) and safety runner
  `run_backend.py`.
- [Frontend receipt](../.runtime/white-black-qa-20261103/frontend.md), including
  the original intermittent failure and all rerun/setup outcomes.
- [Browser JSON](../.runtime/white-black-qa-20261103/browser-results.json) and
  [HTML report](../.runtime/white-black-qa-20261103/browser-report/index.html).
- [HTTP results](../.runtime/white-black-qa-20261103/api-blackbox-results.json)
  and collector `api-blackbox.py`; response evidence is synthetic only.
- [Area retry results](../.runtime/white-black-qa-20261103/area-retry-results.json)
  and replay script `area-retry-blackbox.cjs`.
- Selected visual evidence:
  [Doctor mobile](../.runtime/white-black-qa-20261103/selected/doctor-mobile.png),
  [Admin mobile](../.runtime/white-black-qa-20261103/selected/admin-mobile.png),
  [chat mobile](../.runtime/white-black-qa-20261103/selected/chat-mobile.png),
  [landing 320px](../.runtime/white-black-qa-20261103/selected/landing-320.png).
- Matching before/after code-fingerprint JSON manifests in the same folder.

The existing browser command is
`node .runtime/browser-qa/node_modules/@playwright/test/cli.js test --config scripts/browser-qa/playwright.config.cjs`.
Use the README's isolated API/database setup; never substitute production.

Setup-only failures/warnings were kept separate: Windows sandbox EPERM prevented
the first frontend attempt from executing assertions; the approved external run
resolved setup. Backend emitted the existing Starlette TestClient deprecation
and a safety-wrapper anyio assertion-rewrite warning. Edge printed the existing
NO_COLOR/FORCE_COLOR tooling warning. None explains away QA-01 or the executable
QA-02 failure.

Scope excludes live Groq semantics, production deployment/environment/TLS,
cross-browser/mobile-device certification, load/soak testing, comprehensive
penetration or prompt-injection testing, formal screen-reader/WCAG assessment,
clinical correctness certification and measured statement/branch coverage.
Passing known cases does not prove all possible inputs safe. Existing synthetic
registry counts are test data, not an assessment of production registry quality.
