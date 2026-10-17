# Phase 31 — local release-readiness report

Checkpoint: 2026-10-17. **Local implementation and acceptance passed. Production
release remains on hold for owner approval.** This is not a deployment receipt.

**Later integrity audit:** fresh local gates passed again, but CI job-level locks
allow an older run to deploy after a newer run. Phase 31 release clearance now
requires that defect to be corrected, in addition to owner approval. Read
[the current integrity audit](PHASE_31_INTEGRITY_AUDIT_2026_10_17.md). The evidence
below records the preceding repair pass, including its live-provider sample.

## Outcome

All four issues from the fresh browser/live-AI review were repaired and retested:

1. Chamber activation and first-patient promotion now commit in one advisory-locked
   transaction. Reopening retains the existing CURRENT patient and activation time.
   PostgreSQL regressions cover separate sessions, concurrent opens and rollback
   of activation/promotion together on failure.
2. The sharing picker supports case-insensitive displayed full names and normalized
   input whitespace. SQL wildcard escaping, verified/active doctor filtering,
   deterministic ordering and bounded results remain enforced.
3. History summaries and record-aware chat omit structured medicine directions
   from model input, keeping medicine names and other authorized record facts.
4. Prescription explanations likewise send medicine names/item numbers rather
   than schedules. Canonical/task prompts prohibit copying even existing schedules
   from free text. Original prescription directions remain server-owned and
   unchanged in the UI. No safety regex/validator was relaxed or bypassed.

Synthetic-only, metadata-only live diagnostics showed both AI failures were caused
by generated fields echoing recorded medication schedules. The repair prevents
that prompting conflict rather than allowing generated schedules through.

A missing top-level prescription-page heading was also repaired without changing
visible layout, permissions, optional explanations or on-demand PDF behavior.

## Fresh verification

| Gate | Actual result |
| --- | --- |
| Backend suite | **532 passed, zero skipped**, 93.99 seconds, isolated PostgreSQL 17.6; AI mocked/in-memory in automated tests |
| Frontend suite | **57 files / 263 tests passed** |
| ESLint / TypeScript | Passed |
| Optimized Next.js production build | Passed |
| Real Edge acceptance | **8 passed, zero failures/skips**, 29.6 seconds |
| Live Groq/Qwen UI checks | **9 passed**; eight actual model generations plus deterministic no-provider emergency safeguard |
| Alembic current/check | `0030_doctor_locations`; no new upgrade operations |
| Dependency / compilation / whitespace | `pip check`, Python compilation, `git diff --check` passed |

The one existing upstream Starlette/httpx deprecation warning remains. No new
dependency, schema table or migration was needed for these repairs.

The final browser pass used the **production-mode local build**, real local API
and PostgreSQL, and synthetic-only fixtures. A temporary loopback proxy mirrored
Vercel Services same-origin routing; it did not mock responses or modify release
configuration. No earlier chamber or surname workaround remains in the tests.

Coverage includes Citizen → Doctor → Lab → Citizen booking/care/finalization,
prior-prescription read versus author edit, fresh in-memory PDF, immutable lab
results/trends, emergency profile, privacy/grant create/revoke, consent and mock AI,
admin private-body identity search and portal/cross-citizen denials. Added browser
checks also edit a synthetic schedule, update a synthetic facility contact while
preserving its confirmed location/no coordinate DTOs, and verify a synthetic
pending doctor application through the admin UI.

All four roles' dashboards, workspaces and populated details were checked at
390/768/1366/1920px. No horizontal document overflow, unexpected authenticated API
error or browser exception occurred. Heading/skip-link checks and screenshots
are included. This is focused accessibility acceptance, not WCAG certification.

The paced live pass covered English/Bangla education, direct prescribing refusal,
consented record awareness, role-play/injection refusal, history summary,
prescription explanation, lab explanation and emergency escalation. All HTTP
responses were 200 with no browser exceptions or throttling in this final pass.
Sampled explanations preserved source facts and unknown doctor intent; they did
not generate a prescription, dose schedule or new patient diagnosis. A small
sample is not a clinical safety or broad multilingual guarantee.

## Evidence and handoff

- Browser source: `scripts/browser-qa/` (eight cases, no workaround).
- Ignored browser HTML/JSON/PNG: `.runtime/browser-qa/report/index.html`,
  `.runtime/browser-qa/results.json`, `.runtime/browser-qa/results/`.
- Ignored final live evidence: `.runtime/browser-qa/live-groq-repaired-results.json`
  and corresponding synthetic screenshots. Historical failed reports remain
  documented for traceability; their status is superseded by this final pass.
- Read `AGENTIC_IMPLEMENTATION_HANDOFF_CURRENT.md` before resuming.

The Groq key was entered only through hidden input into the temporary backend's
process environment. It was not written to a file, `.env`, command argument,
frontend bundle or handoff. That process was terminated after the live pass and
the mock-only backend restored. Default AI enable flags remain false. No real
patient data or production credentials were used.

## Phase state and owner-controlled release gate

- Phases 22–29: implemented locally, preserved approved product changes.
- Phase 30: scoped automated, production-build browser and synthetic live-provider
  acceptance passed after the repairs above.
- Phase 31: local release preparation complete; **external production release is
  not complete** and requires fresh owner approval.

No commit, push, GitHub Actions dispatch, production migration, Vercel deployment,
promotion or production AI enablement was performed. Production remains the last
released Phases 15–21 plus approved improvements. Future release must follow
`PHASES_28_31_RELEASE_READINESS.md`: reviewed dirty tree/commit, protected CI,
existing Supabase/Vercel Services ordering, environment/health-data review,
stable-domain smoke, authenticated acceptance and rollback evidence.

Outstanding external/manual limits: production secret/log/branch-protection
review, Linux Actions clean-install/build, actual Vercel Services packaging and
deployment, production authenticated smoke, real GPS permissions/geocoding,
comprehensive assistive-technology testing and provider/health-data suitability.
Do not infer these passed from local tests or silently enable production AI.
