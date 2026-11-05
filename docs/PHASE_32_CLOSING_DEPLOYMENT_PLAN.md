# Prepared Phase 32 closing deployment

## Status and approved target

Prepared from the [fresh verification report](PHASE_32_CLOSING_RELEASE_CHECK_2026_11_04.md).
**Awaiting the owner's commit/push/deploy instruction. Nothing in this plan has
been published.** This is the closing release of Phase 32 and the existing
phased plan, with closure recorded only after production verification.

| Item | Approved value |
| --- | --- |
| GitHub | `Mahim2077/HealthLink`, branch `main` |
| Vercel connection | `Mahim2077` only |
| Team | `mahim2077s-projects`, `team_l9GeumDweBdowhhoxPfAS0yM` |
| Project | `healthlink-sd`, `prj_kQyhfaS1tFS7NXlUMYr9C0FA8W5f` |
| Stable origin | `https://healthlink-sd.vercel.app/` |
| Tested source fingerprint | `b7846bfd9ba52d7a0ea5b73cbccb9e50451713912dcdf234f4676aabce063011` (531 files) |
| Current base HEAD | `70059d3df275be7cabfd92a24d963f1d0b4849cd` |
| Expected DB head | `0031_ai_conversations`; no new migration in this increment |
| Captured fallback | `dpl_3RyPMHxWh3BVG6pgsrEEfHQrUyGr`, READY production, app `6649931e29bdf19a9b085ec2b0641a79f97777b7`; stable alias confirmed |

## Concrete commit preparation

Proposed title:

```text
fix: harden Phase 32 clinical workflows and release dependencies
```

Proposed body:

```text
Correct the production-survey issues in discovery, facility booking, clinical
publication, historical prescription metadata and portal state handling.

Complete secondary-facility care, prevent booking into closed chambers and
exclude retired unused practices while retaining accepted bookings. Preserve
Doctor ownership, current-patient isolation and finalized-only Citizen access.

Apply the reviewed Python security patch and minimal development minimatch
compatibility adapter with the genuine patched engine, preserving the existing
Next.js/React/TypeScript/ESLint stack. Include regression coverage and handoffs.

Validation: 614 backend tests (44 PostgreSQL), 347 frontend tests, 17 security
tests, lint/typecheck/build, clean install, clean npm/Python audits, reproducible
Python locks, 20 Edge journeys, 28 standard HTTP checks, 7 secondary workflow
checks and 11 lifecycle checks. Production anonymous smoke: 9/9.
```

The release packages all reviewed pending Phase 32 survey/security/correction
work, not just the last two fixes. Include new source/tests, the private
`frontend/tooling/minimatch-compat` adapter and `frontend/.npmrc`, plus current
release documentation. Review modified **and untracked** files before staging.
Exclude private environment files, runtime evidence, `.vercel`, dependency
directories and private storage; those exclusions passed the preparation scan.
No real credential belongs in the commit or description.

## Execution after publication is authorized

1. Confirm approved account/project/domain identities again, check remote `main`
   has not advanced, and verify the current worktree's source/root configuration
   against the prepared fingerprint. Reconcile any new changes before release.
   Stage only the reviewed source/test/docs and inspect the complete staged diff.
2. Commit the reviewed candidate and record the new commit SHA. Push to
   `Mahim2077/HealthLink` `main`. This push starts the existing release workflow;
   do not create an alternate Vercel project or parallel manual deployment.
3. Wait for **both** GitHub Actions quality jobs on that exact SHA: reproducible
   locks, hash-verified dependencies/audits, PostgreSQL migrations/drift/tests,
   frontend clean install/security/audits/lint/types/tests/build. A local green
   report does not replace those exact-commit checks.
4. Let the existing serialized production job enforce repository/main freshness
   and target IDs, upgrade/check head 0031, pull configuration through the
   approved CI secrets, and build both Services. It then stages a **production**
   deployment without live-domain assignment, runs protected smoke, rechecks the
   head and promotes that same tested deployment. Preserve these gates.
5. Confirm READY status and both services, verify stable-domain alias assignment
   to the new deployment, and run stable-origin smoke. Perform minimal read-only
   Citizen/Doctor/Admin sign-in and overview checks with the owner's supplied
   test accounts to exercise production database/authentication paths. Keep
   credentials/tokens in memory, record only outcomes and log out; do not create
   or edit medical records for this check. Record Actions URL,
   application SHA, deployment ID, domain mapping and database head. If any gate
   fails, keep the failed result visible and resolve it before claiming release.
6. Update the production receipt, current handoff and Phase 32 status with those
   actual results. Only then mark Phase 32 and the existing phased plan complete.
   Do not invent a new phase as part of this release.

Secrets remain in the existing private GitHub/Vercel configuration. Preparation
confirmed key presence without decrypting values; actual CI authentication and
runtime/staged checks remain part of execution. Use no alternate account,
replacement project, secret rotation or security-gate exception as a workaround.

## Recovery reference

Immediately before execution, recapture the current stable alias and READY
deployment; another authorized release could have advanced it since preparation.
The fallback above is the confirmed state at this checkpoint. If a release or
promotion fails, identify whether live aliases changed before selecting a
recovery action. Use only the approved project's previously verified production
deployment for application rollback when necessary; inspect the failed run and
verify the stable origin afterward. Do not downgrade schema or discard records.
This increment adds no migration. Keep failed-run/recovery evidence in the
release receipt instead of marking an unsuccessful closing deployment complete.
