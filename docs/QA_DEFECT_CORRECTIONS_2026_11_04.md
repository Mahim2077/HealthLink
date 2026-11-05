# Local QA defect corrections — 2026-11-04

> This records the successful QA-01/QA-02 corrections. A later
> [final assessment](PHASE_32_FINAL_READINESS_2026_11_04.md) found FR-01 in the
> secondary-facility care workflow. Its subsequent
> [correction](FR_01_SECONDARY_FACILITY_CORRECTION_2026_11_04.md) is now verified
> locally; publication remains held.

## Result

QA-01 is fixed and verified. QA-02's focus timing is guarded and its regression
test now exercises a deliberately pending retry. All checks below pass on the
current local working tree. **No commit, push or deployment was performed;
publication remains held.** This continuation belongs to Phase 32.

The [2026-11-03 QA report](LOCAL_WHITE_BOX_BLACK_BOX_TEST_REPORT_2026_11_03.md)
is preserved as historical evidence of the defects and original failed checks.
Its results describe the pre-fix version, not the current correction.

## QA-01 — unfinished prescription exposed through AI

An owning Citizen could request an AI explanation of a draft prescription while
the ordinary JSON, PDF and visit routes correctly returned 404. The AI service
had a separate Citizen ownership shortcut that bypassed publication rules.

Removed that shortcut and its unused import from
`backend/app/ai/clinical_service.py`. All prescription explanations now use
the existing `ClinicalReadPolicy`, with the visit's actual finalized state,
before extracting medical information, writing an AI access audit or calling
the provider. No new authorization framework or schema change was introduced.

Verified behavior:

| Actor / state | AI explanation |
| --- | --- |
| Owning Citizen, draft | 404; no provider call or AI_ACCESS event |
| Foreign Citizen, draft | 404 |
| Doctor who is only the author, draft | 404 |
| Verified treating Doctor with CURRENT_PATIENT authority, draft | 200; existing clinical authority preserved |
| Owning Citizen, same prescription after actual Finish Appointment | 200 |
| Authorized finalized-record reads | Existing behavior preserved |

Replaced the stale unit expectation that accepted Citizen draft access. A new
regression creates an actual appointment/queue/visit/prescription, verifies
Citizen denial and treating-Doctor success, completes the appointment through
the real finalization operation, then verifies Citizen success for the same ID.
It checks provider-call counts and the two legitimate audit access sources.

The persistent Edge care journey now performs the same-ID AI request before
and after clicking **Finish Appointment**. Supplemental independent HTTP checks
also verify draft JSON/PDF/visit/AI denial, foreign-owner denial and finalized
positive controls. Test authentication stays in memory; no PDF is stored.

## QA-02 — manual area retry focus timing

The initial survey recorded an intermittent unit-test focus failure. The earlier
real-browser checks passed, so a production-visible defect was not established.

The private `LocationDialog` effect now waits for area loading to finish, selects
only an enabled select and reruns when the loading state changes. This avoids
attempting to focus Zila while it is disabled. Existing dialog containment,
Escape handling and trigger-focus restoration remain covered.

The public DoctorSearch integration test holds the retry promise pending. It
checks disabled Zila, focus remaining inside the dialog and no redundant Doctor
search; after releasing the catalog, it waits for both enabled state and focus.
The focus assertion was retained. No component export or test-only API was added.

Added a persistent nineteenth Edge case that aborts only the first area catalog
network request, retries against the real local API, verifies focused/enabled
Zila and submits a successful manual nearby search. Two additional independent
fault-injection attempts also pass, each with exactly two catalog requests,
no Doctor search during retry and a 200 search after area selection.

## Fresh verification

| Check | Result |
| --- | --- |
| Backend full suite | **602 passed**, zero failures/errors/skips; 72.64 seconds |
| Actual PostgreSQL cases within backend total | **40 executed**; remaining 562 use the suite's other fixtures |
| Fresh synthetic database | `healthlink_fix_87d9cbfc37e4`, loopback port 55433; head `0031_ai_conversations`, no Alembic metadata drift |
| Focused DoctorSearch suite | **16 passed** |
| Full frontend suite | **343 passed**, 64 files; 11.36 seconds |
| Security / dependency-adapter regressions | **17 passed** |
| ESLint / TypeScript | Both passed |
| Optimized Next build | Passed; compilation, type checking and all 44 static pages |
| Optimized-build Edge acceptance | **19 passed**, zero retries/flaky/skipped/failed; 85.07 seconds |
| Supplemental HTTP checks | **28 passed**, zero failed; previously 27/28 |
| Additional area-retry browser probes | **2/2 passed**, asserted keyboard focus and functional recovery |
| Whitespace validation | `git diff --check` passed |

The backend focused explanation/prescription/grant run also passed **79 tests**
during the correction work. It overlaps the full suite; it is not added to the
602 total. Test counts are not a coverage percentage.

Existing non-failing TestClient deprecation and React `act(...)` test warnings
remain. A sandbox-only Vitest cache permission failure ran zero tests; the
authorized rerun executed and passed. No application workaround was used.
Dependency audits and lock reproduction from the preceding QA remain dated
evidence; these source fixes changed no dependency or lock file and did not
rerun those scans.

## Scope, evidence and resume point

Workspace `D:\HealthLink_V_1`, branch `main`, base HEAD
`70059d3df275be7cabfd92a24d963f1d0b4849cd`, plus existing uncommitted work.
Next.js/React/TypeScript/ESLint, the local minimatch compatibility adapter,
dependency versions, locks and security gates are unchanged by this correction.
No production database, live AI key, real account or external service account
was used. Browser traffic targets only `http://127.0.0.1:3001`, routed to the
optimized frontend on 3003 and real API on 8001, with synthetic PostgreSQL data
and mock AI. Dedicated services were stopped after verification; fixtures remain.

The source manifest still contains **528** application/test/config files. Only
these six differ from the preserved pre-fix QA manifest:

- `backend/app/ai/clinical_service.py`
- `backend/tests/test_ai_clinical_explanations.py`
- `frontend/src/components/citizen/doctor-search.tsx`
- `frontend/src/components/citizen/doctor-search.test.tsx`
- `scripts/browser-qa/healthlink.spec.cjs`
- `scripts/browser-qa/README.md`

The current manifest hash is
`411fe0bd880e20348eb51334ee140d5f0bea9736d435e98cce85e8c970d06ffa`
(SHA-256 of compact JSON sorted relative-path/content-hash pairs; full algorithm
and per-file comparison retained with the receipt). Documentation is outside
that manifest. Earlier survey and dependency corrections are preserved.

Ignored evidence lives under `.runtime/qa-defect-fixes-20261104/`:
`backend-full-junit.xml`, `backend-full-run.json`, `frontend-focused.json`,
`frontend-full.json`, `frontend.md`, `build.md`, `browser-results.json`,
`browser-report/`, `browser-results/`, `api-blackbox-results.json`,
`area-retry-results.json` and `code-fingerprint.json`. Original 2026-11-03 evidence
was not overwritten. The persistent browser suite and regression tests are in
the repository; ad-hoc supplemental probes remain in ignored runtime storage.

Both reported QA items are locally addressed within the tested scope. Browser
coverage is Edge only; live-provider semantics, production, penetration testing
and exhaustive accessibility were not re-certified. A later authorized release
must verify its exact commit and normal CI gates. **Await publication instruction.**
