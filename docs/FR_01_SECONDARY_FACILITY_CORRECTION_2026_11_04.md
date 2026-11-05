# FR-01 secondary-facility care correction — 2026-11-04

> FR-01 remains fixed. A subsequent [boundary recheck](DEPLOYMENT_BLOCKER_RECHECK_2026_11_04.md)
> found FR-02 (closed-chamber booking) and FR-03 (retired facility choice).
> Both were then [corrected and verified](FR_02_FR_03_CORRECTIONS_2026_11_04.md).
> Publication still awaits instruction; the scoped results below remain valid.

## Result

**FR-01 is fixed locally and verified.** Published secondary-facility bookings
can now proceed through the Doctor's selected chamber, consultation,
prescription, Finish Appointment and finalized Citizen access. The two HTTP
operations that previously returned 409 now return 200 using the same
reproduction contract. No confirmed local functional blocker from the preceding
assessment remains within this tested scope.

The candidate is ready for the next authorized release process. **No commit,
push, production migration or deployment occurred.** Phase 32 and the existing
phased plan remain open until the closing production deployment is verified.
No new phase was introduced.

## Correction

- Added a verified-Doctor-only chamber facility list. It includes the linked
  facility, the Doctor's own active practice facilities and facilities with
  sessions owned by that registration. Another Doctor's schedules or sessions
  do not grant access. The list exposes only facility IDs and names.
- Chamber start/read authorization uses this same ownership rule. Existing
  accepted bookings remain serviceable if their practice schedule is later
  retired. New session activation still requires an active facility; queue
  actions remain tied to the owning Doctor/session.
- Added a **Chamber facility** selector to the Doctor page when multiple choices
  exist. Changing it mounts a fresh queue context, preventing a delayed response
  from the previous facility from appearing in the selected facility's queue.
- Serialized queue mutations across all facilities/dates for one Doctor
  registration using the existing PostgreSQL advisory-lock mechanism. Promotion
  refuses a second current patient while another active chamber has one. This
  matches the existing single-patient consultation workspace. Other Doctors
  remain independent, and empty active chambers do not prevent serving a
  secondary facility.
- Queue actions refresh state after acquiring the lock and reject closed
  sessions. Legacy data containing multiple active current patients produces a
  clear 409 in the workspace instead of silently selecting the latest patient.
- Kept existing clinical ownership, finalization and Citizen publication rules.
  No schema migration, dependency change, official-library modification,
  security exception or stack change was needed.

## Regression evidence

| Check | Result |
| --- | --- |
| Focused chamber/consultation/backend regressions | **49 passed** |
| Full backend suite | **610 passed**, 65 modules; zero failures/errors/skips; 127.97 seconds |
| Actual PostgreSQL cases within full total | **42 executed**, including two new simultaneous-start races |
| Fresh migration / schema check | `healthlink_fix_142f20097cd4`, head `0031_ai_conversations`; no metadata drift |
| Focused chamber UI/queue tests | **11 passed** |
| Full frontend suite | **346 passed**, 65 files; zero failures/pending |
| Security / adapter regressions | **17 passed** |
| ESLint / TypeScript | Both passed |
| Optimized Next build | Passed; 44 static pages and dynamic routes |
| Optimized-build Edge journeys | **19 passed**, zero failed/flaky/retries/skips; 112.82 seconds |
| Standard independent HTTP checks | **28/28 passed** |
| Original secondary-facility HTTP reproduction | **7/7 passed**, previously 5/7; both queue read/start now 200 |
| Whitespace validation | `git diff --check` passed |

The added backend tests exercise the full secondary clinical/publication
lifecycle, other-Citizen denial, other-Doctor facility/queue/visit/finish denial,
anonymous/Citizen facility-list denial, schedule retirement, sequential chamber
handover and ambiguous legacy current-patient state. PostgreSQL races cover
same-date and different-date simultaneous facility starts; exactly one succeeds
and exactly one current queue entry remains.

The persistent browser case that formerly stopped at secondary booking now
continues through the facility selector, queue activation, correct-facility
consultation, saved prescription, Citizen draft denial, actual Finish Appointment
and successful Citizen prescription display. Screenshots were inspected. The
existing primary-facility journey, saved chat, roles, Settings, themes and area
retry also pass.

A full-suite run exposed an unrelated ordering assumption in the earlier AI
publication regression: database retrieval order can place either medicine
first. Its assertion now compares the exact complete medicine-name list without
requiring that incidental order. Authorization, provider-call and audit checks
remain intact. Final 610/610 results come from the subsequent complete rerun.
Initial new-fixture length/timestamp mistakes and a UI error-copy expectation
were corrected before the passing results; no application validation was relaxed.

Dependency inputs/locks were unchanged. The clean installation, zero-finding
npm/Python audits and reproducible Python locks from the immediately preceding
[final assessment](PHASE_32_FINAL_READINESS_2026_11_04.md) remain dated evidence;
those scans were not repeated for this source-only correction. Existing
non-failing React act/TestClient/import warnings remain.

## Version, isolation and evidence

Workspace `D:\HealthLink_V_1`, branch `main`, base HEAD
`70059d3df275be7cabfd92a24d963f1d0b4849cd` plus existing uncommitted work.
Node 24.20.0 / npm 11.17.0 / Python 3.13.7 / PostgreSQL 17.

The application/test/config manifest contains **531 files**; **14 files** differ
from the preceding final-assessment manifest, including three new test files.
All other existing source/configuration/lock files are preserved. Fingerprint:
`6363ccfc26abdf38f73db0be562fb62c8a8d5df00349e25f7c225d117d1cbed6`
(SHA-256 of compact JSON sorted relative-path/content-hash pairs).

Testing used fresh synthetic loopback databases, explicit `_env_file=None`
settings, mock AI and an empty provider key. Browser origin 3001 routed to the
optimized frontend on 3003 and actual API on 8001. No production database,
account, API key, real medical record or live provider was used. QA services and
the exact local PostgreSQL cluster were stopped; synthetic fixtures remain.

Ignored receipts: `.runtime/fr01-fix-20261104/`, including full/focused backend
JUnit and run metadata, frontend JSON/logs, optimized browser report/results,
`api-blackbox-results.json`, `secondary-facility-blackbox-results.json` and
`code-fingerprint.json`. Initial failed-run evidence is retained separately;
the original final-assessment failure receipts were not overwritten.

This verifies local Edge/API behavior and the tested policy/concurrency paths.
The exact release commit must still pass normal CI, protected staged smoke and
stable-production verification after authorization. Record that production
receipt before marking Phase 32 or the existing phased plan complete.
