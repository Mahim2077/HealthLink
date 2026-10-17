# Phases 28–31: local implementation and release gates

Checkpoint: 2026-10-18. **Released application `2bb55b8` is live.** The owner
authorized commit, push, deployment and private production Groq configuration.
The previous hold/blockers below are historical. Current verified execution and
remaining limits: `PRODUCTION_RELEASE_2026_10_18.md`. This
checklist does not authorize other accounts, projects or unrelated changes.

## Phase status

| Phase | Local state | Outstanding gate |
| --- | --- | --- |
| 28 — dashboard/UX consolidation | Implemented; real projections and fresh four-width/role acceptance passed | Specialist/manual accessibility checks are not certification claims |
| 29 — security hardening | Local fixes and automated permission matrix implemented | Production log/infrastructure review belongs to the authorized release |
| 30 — end-to-end QA | All four known issues repaired; 532 backend / 263 frontend tests, 8 production-build browser cases and 9 live AI/UI cases passed | Local scoped acceptance complete; external/manual limitations remain explicit |
| 31 — final release | Released `2bb55b8`; Actions 39058877324 passed, stable deployment READY; 555 backend / 263 frontend tests, 18 CI smoke and 9 independent stable probes passed | Authenticated production/live AI confirmation, runtime-log access and manual/provider/privacy review limits remain explicit |

Do not report Phase 30 browser acceptance or Phase 31 production release complete
based solely on passing unit/integration tests.

Latest integrity evidence: `PHASE_31_INTEGRITY_AUDIT_2026_10_17.md` (532 backend,
263 frontend and 8 production-build browser cases passed again; no fresh live AI
calls). It adds a CI release-ordering blocker to the preceding
`PHASE_31_LOCAL_RELEASE_REPORT.md` and supersedes historical failed/pending QA
below. Final browser pass uses the built production frontend
with local Services-equivalent routing, actual API/PostgreSQL, synthetic data and
no earlier workarounds. All four known issues were repaired without loosening AI
safety validation. No production release action was taken.

## Product changes preserved

- Specialty-first doctor discovery, approximate GPS opt-in and Bangladesh
  zila/upazila selection remain intact. Facility coordinates remain backend-only
  and facility confirmation remains admin-only.
- Citizen diagnostic tests, reports and trends remain one section. Legacy result
  routes keep their permanent redirects.
- Consultation notes and prescriptions remain one atomic form with dirty-state
  protection. Prior-prescription reads do not grant edit rights.
- PDF bytes are regenerated on demand: no Blob upload or new document rows.
- The removed reminder workflow is not restored. Existing saved schedules and
  notification data remain, with honest inactive-delivery wording.
- Groq/Gemini/mock selection stays environment-driven. The AI is explanation-only,
  cannot prescribe/diagnose, and cannot change a clinical record.

## New dashboard contracts

All paths below are under `/api/v1` and require the matching portal/session.

| Endpoint | Projection |
| --- | --- |
| `GET /citizens/me/overview` | Own upcoming booking, latest finalized prescription/report, saved emergency-profile status, existing reminder/notification counts |
| `GET /professionals/me/overview` | Verified selected DOCTOR or LAB_TECHNICIAN only; bounded doctor chamber serial/counts or exact lab-assignment workload |
| `GET /admin/overview` | Active-admin-only real application/facility/location-confirmation counts |

Dashboards do not invoke AI, mutate queues or serialize clinical narrative.
Every linked resource reauthorizes its own request. Failure displays a retryable
state rather than fake zero metrics. Sensitive UI is keyed to the auth session.

Security details: [permission matrix](SECURITY_PERMISSION_MATRIX.md).

## QA evidence and scope

Fresh automated results are recorded in `implementation-progress.md` and the
current handover. The new `backend/tests/test_release_journey.py` walks a
synthetic HTTP-to-database journey through combined consultation/prescription,
diagnostic assignment, draft/final report, citizen results/trends, appointment
completion, dashboard projections, PDF regeneration and mock explanations. It
also checks cross-citizen and wrong-portal denial. It is **not** a browser test.

Historical browser observations from 2026-10-02:

- Citizen overview linked the seeded prescription and merged diagnostic detail.
  A mobile overview had no horizontal overflow. The prescription explanation
  preserved original instructions and did not invent medicine purpose.
- Doctor role login, current serial, unified consultation save and appointment
  completion passed with synthetic local data.
- Lab role login hid doctor-only tools, displayed the assigned test, transitioned
  it to IN_PROGRESS and saved a draft report.
- The lab finalization confirmation blocked the browser controller; finalization
  was not verified in the browser. Admin sign-in/overview acceptance was also not
  completed. Automated tests cover these backend/UI boundaries independently.

The owner subsequently authorized Playwright using the working terminal. Fresh
2026-10-17 Edge QA completed **6 passed, 1 failed, zero skipped**, with both chamber
promotion persistence and full-name sharing search confirmed as defects. See
`BROWSER_QA_2026_10_17.md` for current evidence, workarounds and exact limitations.
The native-runtime blocker is superseded; browser sign-off is still blocked by
these defects. The acceptance checklist remains:

1. Citizen: login/profile → modern finder/booking → appointment/history → source
   prescription and fresh PDF → diagnostic results/trends → emergency profile,
   saved reminder/notification data, access history/grants and mock AI features.
2. Doctor: selected-role login → schedule/chamber/queue → CURRENT patient/history
   → unified consultation/diagnostics/prescription → finish → later author-only edit.
3. Lab: selected-role login/no doctor tools → assigned queue → draft/edit/finalize
   → immutable report → owning citizen sees finalized result and trend update.
4. Admin: login/real overview → verification/facilities → private-body identity
   search/support → portal isolation. Do not alter production identities.
5. At mobile, tablet, desktop and wide desktop: keyboard/focus, labels/errors,
   touch targets, heading hierarchy, reduced-motion state, table/trend fallbacks
   and no horizontal overflow. Reset temporary browser viewport overrides.

Use synthetic local fixtures, not production credentials or real medical records.
Do not recreate already-existing synthetic accounts or overwrite user data.

## Local regression commands

Run from the repository root with the existing virtual environment. Point
`HEALTHLINK_TEST_DATABASE_URL` at a dedicated loopback-only PostgreSQL test DB,
never the production URL. Keep AI disabled/mock and record-context transfer off
for the general suite; individual tests use their own synthetic overrides.

```powershell
$env:AI_ENABLED = 'false'
$env:AI_PROVIDER = 'mock'
$env:AI_RECORD_CONTEXT_ENABLED = 'false'
# Set HEALTHLINK_TEST_DATABASE_URL privately to the isolated local test DB.
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

From `backend/`, with `DATABASE_URL` explicitly set to that local test DB:

```powershell
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic check
..\.venv\Scripts\python.exe -m pip check
```

From `frontend/`, using the configured Node 24 runtime:

```powershell
npm test -- --run
npm run lint
npm run typecheck
npm run build
```

Stop only the agent-owned dev server before a build that shares `.next`; do not
kill unrelated processes. A successful Next.js build is not a successful Vercel
Services deployment. The final Linux Actions build remains a release gate.

## Authorized release checklist — NOT executed

- [x] Finish scoped fresh browser/responsive acceptance above (8 cases passed).
- [x] Correct and locally verify whole-release CI serialization plus stale-commit guards;
  earlier separate job locks were replaced with one release lifecycle job.
  See the release receipt. Do not cancel in-progress database migrations
  or reuse a workflow lock group inside its own jobs.
- [x] Obtain explicit owner approval for commit, push and production deployment (2026-10-18).
- [x] Review the full dirty tree, including untracked AI/dashboard/tests/scripts;
  exclude `.runtime`, `.env`, keys, credentials and test/browser artifacts.
- [x] Verify repository/branch, intended commit, Vercel team/project and stable
  domain. Preserve Vercel Services, Supabase PostgreSQL and same-origin `/api/v1`.
- [ ] Verify protected production environment/branch approvals, required CI gates,
  credential scoping and pinned CLI compatibility before triggering the workflow.
  Do not print secrets or copy pulled environment files into artifacts.
- [ ] Both AI enable flags remain false unless a separately approved provider and
  health-data review permits activation. A key alone is not production sign-off.
- [x] Verify production Alembic head without exposing its connection URL. Local
  changes add no migrations; expected head remains `0030_doctor_locations`.
  No stamp, downgrade, schema reset or data deletion is part of this release.
- [x] Run complete local gates, then review green GitHub Actions quality jobs.
- [x] Only after approval, push the reviewed commit. A push/manual run on `main`
  can automatically migrate/deploy; do not use it merely to test local readiness.
- [x] Let existing Actions migration/build/prebuilt-deploy ordering run. Preserve
  the current architecture; do not substitute a direct deployment path silently.
- [x] Actions smoke invokes `scripts/smoke_release.py` for the generated
  deployment URL **and** `https://healthlink-sd.vercel.app`.
- [ ] Verify authenticated synthetic production journeys, private PDFs, AI-off
  handling and a bounded, privacy-preserving runtime-log window after release.
- [x] Record commit, Actions run, deployment URL, stable alias, migration head,
  exact test evidence and remaining limitations in the handover.

The smoke script probes production `/health`, home/three sign-in pages and four
anonymous-denial API boundaries. It uses HTTPS Vercel origins, bounded reads and
no application credentials/model calls. Protected staging uses the existing
Vercel CLI identity; stable-domain probes stay anonymous. It rejects redirects, wrong health environments,
missing HealthLink HTML and unexpectedly public protected endpoints. A healthy
process does not prove database health, user login, model availability or commit
identity. Check those separately. Never weaken deployment protection to make a
probe pass; use a separately reviewed supported access mechanism if necessary.

## Rollback and remaining risks

Restore a known-good application deployment or reviewed revert only after owner
approval. Database rollback is separate and must not be automated/destructive;
the code rollback must remain compatible with the current migrated schema.
Recheck the stable alias and automatic-promotion settings after any rollback.

The legacy identity-search GET endpoint remains deprecated for compatibility;
old clients can put identifiers in access-log URLs. Production log controls need
review. AI safety guards are not clinical validation; live Groq model access,
quotas, broader Bangla/medical output quality and health-data suitability remain
external/manual gates. A bounded live synthetic sample passed; it is not clinical
certification or permission to enable real-patient AI.
No global rate-limiter guarantee is made. These are explicit release constraints,
not reasons to restore removed product features or bypass authorization.
