# FR-02 / FR-03 corrections — 2026-11-04

## Result

**Both reported issues are fixed and verified locally.** Booking into a closed
chamber returns 409 with a useful alternate-date message and creates no
appointment/queue entry. Soft-deleted, unused practice facilities disappear
from chamber choices; accepted bookings remain serviceable after retirement.

The known blockers from the preceding assessment are resolved within the tested
scope. The candidate can proceed to the next authorized release process.
**No commit, push, production migration or deployment occurred.** Phase 32 and
the existing phased plan close only after that production release is verified.

## FR-02 — atomic booking/closure availability

Booking now takes its existing Doctor/date booking lock followed by the
Doctor-wide queue lock. It reads and refreshes the exact Doctor/facility/date
session under that lock and rejects `COMPLETED` before capacity/serial allocation
or appointment insertion. Chamber closure takes the same queue lock before
reading/refreshing and validating its session state.

The lock order matches cancellation: booking lock → queue lock. Closure takes
only the queue lock. There is no new reverse lock order or schema constraint.
When closure commits first, booking is rejected. When booking commits first,
closure follows it. Future dates and other open facilities remain bookable.

The API message is: “The doctor has closed this chamber for this date. Choose
another available date.” The existing booking form already handles this API
error and allows editing/resubmitting the date; no production frontend component
change was needed. New component and real-browser tests verify recovery.

## FR-03 — soft-delete-aware chamber choices

The schedule branch of `chamber_facilities_query` now also requires
`deleted_at IS NULL`. The independent linked-facility and owned-session branches
are preserved, so historical/accepted appointments do not lose access when a
schedule is retired.

The previous retirement regression now uses the actual schedule DELETE API
rather than physically deleting a fixture row. It verifies that a booked
secondary facility stays available and its Doctor can still activate the queue.
A new API regression verifies that an unused secondary practice is listed
before deletion and disappears after soft deletion.

## Verification

| Check | Fresh result |
| --- | --- |
| Focused backend chamber/consultation regressions | **53 passed** |
| Full backend suite | **614 passed**, 65 modules; zero failures/errors/skips; 104.57 seconds |
| Real PostgreSQL cases within backend total | **44 executed**, including both closure/booking lock orders |
| Fresh database migration / metadata | `healthlink_fix_3a8faeb94cdc`, head `0031_ai_conversations`; no drift |
| Focused booking-form suite | **13 passed** |
| Full frontend suite | **347 passed**, 65 files; zero failed/pending |
| Security / adapter regressions | **17 passed** |
| ESLint / TypeScript | Both passed |
| Optimized build | Passed; 44 static pages and dynamic routes |
| Optimized-build Edge journeys | **20 passed**, zero failed/flaky/retries/skips; 103.06 seconds |
| Standard independent HTTP matrix | **28/28 passed** |
| Secondary-facility HTTP reproduction | **7/7 passed** |
| Original FR-02/FR-03 lifecycle probe | **11/11 checks passed**, previously 9/11; includes 10 HTTP operations and a content assertion |
| Source/whitespace checks | Tested source manifest retained; `git diff --check` passed |

Backend checks verify repeated closed-day rejection without changing appointment
or queue counts/serials, successful booking at another facility or future date,
actual API soft deletion, and preserved access for accepted bookings. PostgreSQL
tests use independent sessions and actual advisory-lock contention in both
orders, including a preloaded session object; failed booking leaves no rows.

The new twentieth browser case closes a real synthetic chamber, attempts a
Citizen booking, checks the 409 and visible alternate-date guidance, then books
the next published weekly date with serial 1. Its screenshot was inspected.
The earlier full secondary-facility care/publication journey also passes.

The repeated lifecycle probe confirms `COMPLETED` with **zero waiting patients**
after rejected booking, and absence of the unused soft-deleted facility. Normal
closure remains irreversible for that date. No application validation or test
assertion was relaxed to obtain a passing result.

Dependency inputs/locks, framework, environment configuration, security policy
and official library files are unchanged. Clean npm/Python audits from the
immediately preceding [blocker recheck](DEPLOYMENT_BLOCKER_RECHECK_2026_11_04.md)
remain dated evidence; no dependency install/audit or production inspection was
repeated in this source-only correction. Existing non-failing React act and
TestClient/import warnings remain.

## Scope and evidence

Workspace `D:\HealthLink_V_1`, branch `main`, base HEAD
`70059d3df275be7cabfd92a24d963f1d0b4849cd` plus existing uncommitted work.
Only **seven** application/test/harness files differ from the preceding
assessment: two production backend files, two backend test files, one frontend
test file and the browser suite/README. All other existing work is preserved.
No migration is required; expected head remains 0031.

The manifest has **531 files**, fingerprint
`b7846bfd9ba52d7a0ea5b73cbccb9e50451713912dcdf234f4676aabce063011`
(SHA-256 of compact JSON sorted relative-path/content-hash pairs).

Tests used explicit no-environment-file settings, synthetic loopback PostgreSQL
data and mock AI with an empty provider key. No production account/database,
real medical record, service account or live model was used. QA API, optimized
frontend, router and exact PostgreSQL cluster were stopped; fixtures remain.

Ignored receipts: `.runtime/fr02-fr03-fix-20261104/`, including backend full/focused
JUnit/run metadata, frontend JSON/logs, browser report/results, standard and
secondary HTTP results, `chamber-lifecycle-results.json` and `code-fingerprint.json`.
Original failure receipts and historical readiness reports were preserved.

This is local Edge/API/concurrency verification. Normal exact-commit CI,
protected staged smoke and stable-production verification remain required for
the authorized closing release. No new phase has been created.
