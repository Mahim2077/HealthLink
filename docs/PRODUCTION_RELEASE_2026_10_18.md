# Production release — 2026-10-18

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

## Release execution — pending at commit preparation

Commit, Actions result, new deployment and stable-domain verification will be
recorded after execution. Do not infer completion from this document.

Previous production rollback reference:
`dpl_EkEkv35r1m7YdBDphL9wTPXr1XfL`, application commit
`c8d2f26a836d39f3153b1af3e9ff9d4ac079ba9e`, deployment
`healthlink-h9sd3mxar-mahim2077s-projects.vercel.app` (READY/production before release).
Rollback requires a deliberate authorized decision and must not downgrade or
reset the production database.
