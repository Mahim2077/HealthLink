# Additional deployment-blocker review — 2026-11-04

> **Historical pre-fix assessment.** FR-02 and FR-03 were subsequently corrected
> and verified. See [the correction report](FR_02_FR_03_CORRECTIONS_2026_11_04.md)
> for current local status. The original failing checks below are preserved.

## Decision: NOT READY — one confirmed functional blocker

The secondary-facility care correction, FR-01, remains fixed. Additional
chamber lifecycle checks found **FR-02/P2**, which blocks release: a Citizen
can book after the Doctor has closed that day's chamber, leaving a confirmed
appointment that cannot enter consultation. A smaller issue, **FR-03/P3**, leaves
an unused facility in the chamber selector after its schedule is soft-deleted.

This was an assessment. **Product code was not changed; no commit, push,
production migration or deployment was performed.** Phase 32 remains open.

## FR-02 / P2 — new bookings accepted into a closed chamber

Independently reproduced through the actual local API with unique synthetic
Doctor/Citizen accounts, a published primary-facility schedule and no current
appointments:

| Operation | Actual result |
| --- | --- |
| Doctor opens the chamber | 200; no current patient |
| Doctor closes the chamber for that date | 200; status `COMPLETED` |
| Citizen books that same Doctor/facility/date afterward | **201**, appointment `BOOKED`, queue `WAITING`; expected rejection |
| Doctor reads the chamber | 200; still `COMPLETED`, now one waiting patient |
| Doctor attempts to reopen | **409**, “Chamber session is already closed for the day.” |

The booking is accepted after closure has already completed, so this is not
an ambiguous concurrency observation. The normal queue cannot serve the new
appointment. It is not evidence of cross-patient access.

`backend/app/appointments/service.py:224` reuses the existing practice session
and adds a waiting entry without rejecting `COMPLETED`. The start/action paths
correctly refuse to reopen or operate on a closed session. Existing closure
tests check subsequent queue actions, but not subsequent Citizen booking.

**Required correction:** reject a booking into a completed session before
creating an appointment/queue entry, and serialize that check with chamber
closure using a consistent lock order. Preserve future-date/open-session
booking. Add closed-day rejection and close-versus-book race regressions;
failed requests must not consume capacity or serials. The UI should display a
clear closed-chamber message and permit choosing another available date.

## FR-03 / P3 — retired, unbooked facility remains selectable

Using the same unique synthetic Doctor and a secondary facility with no
session or appointment:

1. Publish an active secondary-facility schedule: **201**.
2. Delete it through the actual practice-schedule API: **200**, with `deleted_at`.
3. Read `/api/v1/professionals/chamber/facilities`: **200**, but the unused
   secondary facility is still present; expected absent.

The new `AppointmentRepository.chamber_facilities_query` at
`backend/app/appointments/repository.py:339` filters schedule status but omits
`deleted_at IS NULL`. The deletion API uses a soft delete in
`backend/app/doctors/service.py:254`, leaving status unchanged. The earlier
retirement regression physically deleted a fixture row and therefore did not
exercise the normal API deletion behavior.

This is a smaller stale-choice regression, not a separate release blocker on
its own or evidence that another Doctor's records are accessible. Correct the
active-schedule branch to exclude soft-deleted rows while preserving the
independent owned-session branch: accepted bookings must remain accessible
after their schedule is retired. Add both unbooked-hide and booked-retain
regressions through the actual deletion operation.

## Deployment and dependency checks

| Check | Result |
| --- | --- |
| Additional local lifecycle probe | **11 checks: 9 pass, 2 fail**; 10 HTTP operations plus a response-content assertion |
| npm production/full dependency gates | Fresh pass; **0 flagged entries, 0 exceptions used** in both |
| Strict Python runtime/development hash-lock audits | Fresh pass; no known vulnerabilities; no exceptions |
| Vercel approved connection | **Mahim2077** can read `healthlink-sd` |
| Vercel project / owner guard | Project `prj_kQyhfaS1tFS7NXlUMYr9C0FA8W5f`, owner `team_l9GeumDweBdowhhoxPfAS0yM`; both match CI |
| Team / runtime | `mahim2077s-projects`, Services framework, Node `24.x`; matches current configuration |
| Stable production domain | `healthlink-sd.vercel.app` is verified and belongs to that project |
| Expected production environment keys | All 12 checked keys present; presence only, secret values not decrypted |
| Existing production anonymous smoke | **9/9 pass**: health/public pages 200; protected API routes 401 without redirects |
| GitHub `main` | Base HEAD `70059d3df275be7cabfd92a24d963f1d0b4849cd` confirmed |
| Latest GitHub Actions release | Run `39808112467`, success, application `6649931`; historical released version, not the uncommitted candidate |
| Existing source/test/config identity | **531 files unchanged** from the FR-01 correction receipt |

The Vercel project read succeeds under the selected account's default scope;
an explicit team-scoped lookup returned 404. The successful project, team and
domain reads establish the actual approved identity; no account change or
replacement project was used. The team slug matches the protected-smoke script.

The full **610 backend / 346 frontend / 17 security**, **19 browser** and
**35 HTTP** results in the [FR-01 correction report](FR_01_SECONDARY_FACILITY_CORRECTION_2026_11_04.md)
are carried forward against the identical source manifest, not claimed as
re-executed in this review. Fresh targeted checks exposed states those suites
did not cover. Diagnostic technician selection was also inspected: the
consultation passes `visit_id`, and the API derives the visit's facility rather
than always using the Doctor's linked facility. That suspected mismatch was
not reported as a defect.

No other confirmed dependency or project-identity blocker was found in this
bounded review. This does not certify all code paths. The live smoke tests
exercise the already released application, not the pending candidate;
`/health` checks process health, not database connectivity. Production secret
validity, runtime database access and CI credential expiry were not tested by
the metadata reads. The exact closing-release commit still needs normal CI,
production migration, protected staged smoke and stable-origin verification.

## Evidence, isolation and resume point

Workspace `D:\HealthLink_V_1`; source fingerprint:
`6363ccfc26abdf38f73db0be562fb62c8a8d5df00349e25f7c225d117d1cbed6`
(531 sorted relative-path/content-hash pairs, compact JSON, SHA-256).

New lifecycle tests used only `127.0.0.1:8001`, the dedicated synthetic
PostgreSQL database on port 55433, explicit no-environment-file test settings
and mock AI. No real medical record, production login, live AI call or
production data mutation occurred. The production checks were anonymous;
GitHub/Vercel reads used only the approved Mahim2077 connections. QA API and
the exact PostgreSQL cluster were stopped afterward; fixtures remain.

Ignored evidence: `.runtime/deployment-blocker-review-20261104/`, including
`chamber-lifecycle-results.json`, its reproducible probe and synthetic fixture,
`platform-readiness.json` (metadata only), `frontend-audit.log`,
`frontend-audit-run.json` and `python-audits.json`. No secret value is included
in the platform receipt. Earlier test/failure evidence was not overwritten.

**Next:** correct FR-02 and the smaller FR-03 issue, verify their lifecycle and
concurrency regressions, then reassess the exact candidate. Keep publication
held until those corrections and the normal release gates pass.
