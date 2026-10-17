# Integrity audit through Phase 31 — 2026-10-17

## Verdict

**Local application regression gates passed. Phase 31 release clearance is not
granted: one CI release-ordering defect needs correction before release.**
This was a verification-only pass. No application or workflow fix, commit, push,
Actions dispatch, production migration, deployment or AI enablement occurred.
Existing uncommitted implementation changes were preserved.

## Finding: P1 — an older workflow can replace a newer production release

Location: `.github/workflows/ci-cd.yml:108–153` (migration concurrency at 116–118;
deployment concurrency at 151–153).

Migration and deployment share a **job-level** concurrency group. This prevents
those individual jobs from running simultaneously, but does not serialize a
complete run from quality checks through migration and deployment. There is no
workflow-level release lock or stale-commit check.

For example, run A for an older commit can have slower quality checks. Newer run B
can finish quality checks, migrate and deploy first; A can then finish its checks,
migrate and deploy its older code. Every existing `needs` and job lock is satisfied,
yet production regresses to A. Migration/deployment pairs can also interleave
between runs. This is a source-confirmed race, not evidence it has occurred live.

GitHub documents separate job/workflow concurrency scopes. Queue ordering is based
on when execution starts waiting, not commit chronology; a queue alone does not
establish which commit is intended for production. See the official
[concurrency concepts](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency)
and [workflow concurrency controls](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

Required follow-up: serialize the full production release lifecycle without
cancelling in-progress migrations, and reject stale intended commits before
external mutations. If adding workflow-level concurrency, do not reuse an inner
job group that could block its own workflow. Explicit rollback/rerun behavior must
remain intentional. Test overlapping runs and stale reruns before clearing this
gate. This audit did not edit the workflow or trigger Actions to demonstrate the
race against production.

### Additional release hardening advisory

At workflow lines 186–197, `vercel deploy --prebuilt --prod` precedes the smoke
step. Under normal automatic production-domain assignment, smoke therefore detects
a bad version after it becomes live; it is not a pre-promotion gate, and this
workflow has no automatic rollback. The project's actual domain-assignment setting
was not inspected. Consider staged production deployment, smoke and explicit
promotion, preserving the existing Services architecture and owner approval.
Vercel documents the relevant `--prod`/`--skip-domain` behavior in its
[deployment CLI reference](https://vercel.com/docs/cli/deploy).
This is a qualified hardening advisory, not an observed outage.

## Fresh verification evidence

| Gate | Result in this audit |
| --- | --- |
| Full backend regression | **532 passed, zero skipped**, 63.24 seconds; isolated PostgreSQL 17.6 |
| Full frontend regression | **57 files / 263 tests passed**, 10.83 seconds |
| ESLint / TypeScript | Passed |
| Optimized Next.js production build | Passed |
| Real Edge acceptance on the production-mode build | **8 passed, zero failed/skipped/flaky**, 31.54 seconds |
| Alembic current / check | `0030_doctor_locations` / no new upgrade operations |
| Dependency consistency / Python compilation | `pip check` / `compileall` passed |
| Changed tracked whitespace | `git diff --check` passed |
| Targeted Groq-key-pattern scan | No matches in checked source, docs, scripts or built frontend |

The backend suite retains one upstream Starlette/httpx deprecation warning.
Repository-wide whitespace inspection also found existing trailing spaces in
historical Markdown; these are not new application defects and were not rewritten.
The bounded key-pattern scan is not a comprehensive secret audit.

Browser checks used actual local API/PostgreSQL and new synthetic fixtures, with
a loopback proxy mirroring Services routing, not mocked HTTP responses. Coverage
includes the citizen → doctor → lab → citizen care journey, persistent CURRENT
patient state, full-name sharing, grant revoke/portal isolation, prior-prescription
read versus edit rights, in-memory PDF bytes, finalized diagnostic results/trends,
mock-AI consent/safety flows, synthetic schedule/facility/admin operations and all
four roles at 390/768/1366/1920px. No unexpected authenticated API errors, browser
exceptions or horizontal document overflow occurred. A mobile consultation
screenshot was also inspected. This is not comprehensive accessibility or clinical
safety certification.

Targeted source review covered centralized clinical authorization, diagnostic
finalization/immutability, source-owned AI context and response validation,
private regenerated PDFs, real dashboard projections and bounded release smoke
probes. Reminder scheduling remains removed. AI defaults remain disabled in both
settings and example environment files.

## Evidence, scope and continuation

- Browser harness: `scripts/browser-qa/`; ignored current results:
  `.runtime/browser-qa/results.json`, `.runtime/browser-qa/report/index.html`
  and `.runtime/browser-qa/results/`.
- The prior **9/9 live Groq UI sample** is historical evidence from the immediately
  preceding repair pass, documented in `PHASE_31_LOCAL_RELEASE_REPORT.md`.
  **No live provider call was repeated in this integrity audit.**
- No production account, database, deployment, logs, branch protections or secret
  settings were inspected or changed. Local results do not validate Linux Actions,
  actual Vercel packaging, live domain behavior, provider quotas or health-data
  suitability.
- The temporary production preview/proxy were stopped after testing. Normal local
  development on port 3001 was restored against the synthetic mock-only backend
  on port 8001. No live-key backend remains running.
- Next work is the CI release-ordering correction and its verification, followed
  by the existing owner-controlled release checklist. Production remains the
  previously released Phase 21/improvements baseline, not these local changes.
