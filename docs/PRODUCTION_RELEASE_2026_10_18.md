# Production release — 2026-10-18

> **Released successfully.** Application commit `2bb55b8` is READY and serves
> `https://healthlink-sd.vercel.app/`. Actions **39058877324** passed migration,
> staged authenticated smoke, explicit promotion and anonymous stable-domain
> smoke. The earlier blocked attempts below are historical, not current status.

## Final deployment receipt

| Field | Verified result |
| --- | --- |
| Application commit | `2bb55b827aec36f98fbf141493669c74f2bfec3d` |
| Main implementation commit | `5de35ffb285b74535f2eece623a6c16310a3f68b` |
| Actions run | [39058877324 — success](https://github.com/Mahim2077/HealthLink/actions/runs/39058877324), 4m 41s |
| Deployment | `dpl_AsYMM369iNxaNwbWdcij4zn4nQRA`, READY / production |
| Deployment URL | `https://healthlink-76ct8g1ev-mahim2077s-projects.vercel.app` |
| Stable origin | `https://healthlink-sd.vercel.app/`, resolved to that deployment/commit after promotion |
| Architecture | Existing Next.js + FastAPI Vercel Services, same-origin `/api/v1`, Supabase PostgreSQL |
| Production migration | `0030_doctor_locations (head)`; no new migration in this release |
| Backend CI | **555 passed**, zero skipped, 77.67 seconds; one upstream warning |
| Frontend CI | **263 tests**, lint, typecheck and production build passed |
| Services build | Vercel prebuilt build completed in **25 seconds** |
| CI smoke | **18 passed**: 9 authenticated staged probes, then 9 anonymous stable-domain probes |
| Independent stable smoke | **9/9 passed** after promotion from this workstation |
| Public production browser | Headless Edge login page/controls at 390, 768, 1366 and 1920px; no document overflow or browser exceptions; no credentials entered |

The owner resumed the existing Supabase project, clearing the connection error.
The next attempt migrated/built successfully but an anonymous staging probe hit
Vercel Authentication (302). Promotion remained blocked. The CI-only follow-up
used the installed CLI's documented `vercel curl` transport with the existing
approved CI identity; no protection setting was disabled, no separate bypass
secret was put in GitHub, and the stable-domain probe remains anonymous. Eleven
new offline transport tests bring the full backend suite to 555. Focused
smoke/ordering verification passed 35 tests before pushing the follow-up.

### Explicit post-release limits

- The sensitive Groq key and production enable/provider/model flags are saved
  server-side. **A live production AI response and authenticated production
  journey were not confirmed automatically.** The native browser runtime failed,
  and the secure hidden-input launcher stalled. A proposed weaker password input
  was rejected by the safety reviewer and was not applied. No login credentials
  were entered into that fallback; no real medical records were sent to Groq.
  The owner was asked to check a General-mode question manually.
- A credential-free headless Edge public login check passed at four widths, and
  its public-page screenshot was inspected. An initially over-exact password-label
  locator omitted the accessible `(required)` text; it was corrected against the
  observed source/control without an application change. This is public-page
  acceptance, not authenticated production journey acceptance. The ignored
  evidence is `.runtime/browser-qa/production-public-login-20261018.png`.
- The bounded error/fatal runtime-count request was denied (403) by the Vercel
  integration; local CLI authentication is unavailable. **No clean runtime-log
  scan is claimed.** Project-scoped drain inventory returned **zero drains**.
  Monitoring/log-access and provider/health-data suitability remain explicit
  follow-up items, not clinical or privacy certification.
- No clinical production fixture creation, prescriptions, booking, grant or
  diagnostic mutations were performed during this retry.

The earlier isolated local acceptance remains 8/8 real Edge cases and the earlier
synthetic live Groq sample remains 9/9; those are not new production results.
The standard rollback reference at the end remains available. The final receipt
is documentation-only and should be committed with `[skip ci]` to avoid another
production build; future releases must target the then-current reviewed main SHA.

## Authority and target

The owner authorized commit, push and production deployment, supplied a Groq key
for production-only secret configuration and restricted account use to:

- GitHub `Mahim2077`, repository `Mahim2077/HealthLink`, branch `main`.
- Vercel connection `Mahim2077`, team `mahim2077s-projects`, project `healthlink-sd`.
- Stable origin `https://healthlink-sd.vercel.app/`.

No other account was accessed. The intended Vercel project/team were verified
through that connection. An explicit team-filtered connector lookup returned a
misleading 404; account-level lookup resolved the exact saved IDs successfully.

## Pre-release repairs and checks

- Replaced separate migration/deployment locks with one non-cancelling release
  job covering migration, build, staged deployment, smoke and promotion.
- Added a credential-free, bounded main-head check before migration, staging and
  promotion. Old runs/reruns fail closed instead of replacing newer releases.
- Added an allowlist check for the approved Vercel project/team before migration.
- Staged production uses `--skip-domain`; smoke must pass before explicit
  promotion. Afterwards both the deployment URL and stable domain are checked.
- Vercel authentication is scoped to relevant steps and uses environment
  variables, not token-bearing process arguments. No AI key belongs in Actions.
- Added 12 offline release-ordering/guard regressions. Complete backend:
  **544 passed, zero skipped**, 89.86 seconds, isolated PostgreSQL. An earlier
  attempt had 543 passed and one Windows shared-temp fixture permission error;
  rerunning with a unique ignored workspace temp directory resolved it.
- Frontend: **57 files / 263 tests passed**, lint/typecheck and optimized
  production build passed. Prior full production-build Edge acceptance was 8/8
  on 2026-10-17; application UI was unchanged in this release-preparation pass.
- Alembic remains `0030_doctor_locations`, no metadata drift; `pip check` passed.
  One existing upstream Starlette/httpx warning remains.

The scan of commit-eligible source/docs found no Groq-shaped key. Remote
credential-URL matches were confined to intentional `example.invalid` dummy
configuration tests, not real credentials. Secret/runtime paths remain ignored.

## Private AI configuration

Vercel production now has `AI_API_KEY` as a **sensitive** server-only value,
`AI_PROVIDER=groq`, `AI_MODEL=qwen/qwen3.8-27b`, `AI_ENABLED=true`, and
`AI_RECORD_CONTEXT_ENABLED=true`, as requested for this rollout. The key was not
written to a local file, Git, a frontend variable, a commit message or a report.
Only environment variable names/types/targets were inspected after saving it.
The literal key must never be added to `.gitignore`; secret file paths, not key
values, belong there. Code/example defaults remain disabled.

Record use still requires server authorization and explicit per-request citizen
consent. AI remains educational/explanation-only, never a diagnostic/prescribing
replacement; guards cannot establish clinical safety. Production provider quota,
output quality, privacy/terms suitability and shared abuse controls are not
proven by saving a key. No real patient records were sent during preparation.

## Historical first attempt — committed/pushed; deployment blocked

- Release commit: `5de35ffb285b74535f2eece623a6c16310a3f68b`, pushed to the
  approved repository's `main` branch as Mahim2077.
- [GitHub Actions run 39057721548](https://github.com/Mahim2077/HealthLink/actions/runs/39057721548):
  both Linux quality jobs succeeded. The release job passed stale-head and
  approved-target checks, then failed at **Upgrade production database**.
- The configured Supabase shared pooler returned **tenant/user not found**.
  The database connection was not established: no migration was applied, and
  staging, promotion, new-deployment smoke and live AI checks were not reached.
- The stable alias was re-inspected afterwards: it still targets the previous
  READY deployment below and application commit `c8d2f26`. No rollback was needed.
  A READY application deployment does not establish current database health.
- No bypass of migration/quality gates, guessed database host, new database,
  schema stamp/reset, alternate account or direct deployment was attempted.
- The in-app browser automation runtime also failed to initialize; no production
  browser acceptance is claimed. Normal local development on port 3001 was
  restored against the isolated mock-only backend after the blocked release.

### Required owner action before retry

Check the existing Supabase project in its dashboard, including whether it is
active/restored. Copy its **current transaction-pooler connection string from
Connect**, rather than guessing a regional host/cluster index. Privately correct
GitHub `PRODUCTION_DATABASE_URL` and Vercel production `DATABASE_URL` if needed;
never paste them into source, report files or logs. No password reset is justified
solely by this error. Supabase explains that the error means the shared pooler
cannot match the host/username to a project in its
[official troubleshooting guide](https://supabase.com/docs/guides/troubleshooting/tenant-or-user-not-found).
The actual reason the existing endpoint no longer resolves its tenant is not
confirmed by this audit.

After the owner resolves access, recheck the intended main SHA and rerun the
failed release job (while that SHA is still current) or dispatch the workflow on
the latest reviewed main commit. Preserve staging → smoke → promotion ordering.
The Groq key remains configured privately, but production AI execution is **not
verified** because the release did not reach deployment. This blocked checkpoint
is saved locally after the application push; it was not pushed as an additional
automatic release trigger.

Previous production rollback reference:
`dpl_EkEkv35r1m7YdBDphL9wTPXr1XfL`, application commit
`c8d2f26a836d39f3153b1af3e9ff9d4ac079ba9e`, deployment
`healthlink-h9sd3mxar-mahim2077s-projects.vercel.app` (READY/production before release).
Rollback requires a deliberate authorized decision and must not downgrade or
reset the production database.
