# Dependency integrity remediation — 2026-10-22

> Phase 32 checkpoint. Subsequent owner release approval supersedes the historical
> local hold below; follow the [Phase 32 receipt](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md).

## Result

The owner authorized careful fixes to the preceding integrity audit. Fixable
dependency findings and reproducibility/CI gaps are addressed **locally**.
Functional regressions were not found in the complete verification pass.

**One upstream development-only advisory remains unpatched**, with an explicit,
exact-version, expiring exception. Do not describe the raw full npm audit as
clean or imply that dependencies deployed earlier have already been replaced.
No commit, push, deployment or production-data change was performed.

## Changes

- Next.js and eslint-config-next: **16.3.0 → 16.4.2**, keeping React unchanged.
- Vitest: **4.1.10 → 4.1.12**; jsdom: **30.0.1 → 30.1.3**.
- Compatible locked transitives now include **sharp 0.35.5**, **source-map-js
  1.2.2**, **Vite 8.3.5** and **undici 8.12.3**. Registry sources and integrity
  digests were retained/reviewed; no incompatible alias or forced downgrade.
- Python security updates include **certifi 2026.10.19**, **PyJWT 2.15.1**,
  **Pillow 13.0.0**, **Mako 1.4.3**, **urllib3 2.8.0**, **pytest 9.0.3** and
  **pip 26.2.2**. Unaffected direct API/ORM/AI/PDF dependencies keep their prior
  tested versions. Resolved compatible transitives are explicitly locked.
- `requirements.in`/`requirements.txt`: reviewed runtime/migration inputs and
  universal, complete, hash-locked output. `requirements-dev.in`/
  `requirements-dev.txt`: matching runtime versions plus test/security tools.
  The runtime lock does not include pytest, pip-audit or pip.
- CI checks byte-stable lock generation with **uv 0.12.7**, installs exact
  binary distributions with hash enforcement, runs strict Python advisory scans
  against both locks and tests/enforces the npm security policy.
- All workflow actions now use immutable commit SHAs, resolved from the existing
  official version tags. Checkouts disable persisted credentials. Frontend
  quality installation disables lifecycle scripts, matching the verified local
  installation. Production migration/staging/promotion safeguards are retained.
- Current handoff, developer setup and dependency-security documentation updated.
  The new-PC guide also corrects the current migration head to `0031`.

No application feature logic, clinical policy, AI prompt/provider contract,
record-consent behavior, saved chat history/delete flow, Settings/theme design,
facility-location privacy or generated-PDF storage policy was changed by this
remediation. No database migration was added.

## Fresh evidence

| Check | Result |
| --- | --- |
| Python runtime lock, strict PyPI advisory/hash check | No known vulnerabilities |
| Python development lock, strict PyPI advisory/hash check | No known vulnerabilities |
| Independent OSV installed-environment scan | 103 packages, zero flagged |
| npm production audit | Zero flagged packages; no exceptions |
| npm full audit | Five package entries inherited from one accepted dev-only advisory |
| Security policy regression suite | 10/10 passed, including new findings, production exposure, expired/invalid dates, malformed reports and transport errors |
| Backend/PostgreSQL suite | 567 passed, 111.72 seconds |
| Final CI security/release-order contracts | 15 passed separately after final workflow edits |
| Frontend Vitest | 61 files / 298 tests passed |
| ESLint, TypeScript, optimized build | Passed under Node 24.20.0 / Next.js 16.4.2 |
| Fresh optimized-build Edge journeys | 14/14 passed, 91.29 seconds; zero skipped, unexpected or flaky tests |
| Lock regeneration | Both files byte-for-byte identical with uv 0.12.7 |
| Linux runtime binary/hash resolution | Passed as a dry run; not a deployment |
| Local Alembic | `0031_ai_conversations`; no metadata drift |
| Package compatibility | `pip check` passed |
| Secret-pattern / whitespace checks | No matching key/private-key patterns; no whitespace errors |

Browser coverage includes the complete care journey, prescription regeneration,
diagnostics, doctor discovery, grant isolation, chat history/new/delete, consent,
session revocation, Settings, role gates, responsive layouts and Light/Dark/System
behavior. Fresh dark Settings and AI-chat screenshots were visually inspected.
The API used only synthetic loopback PostgreSQL data and mock AI.

The existing Starlette/httpx TestClient deprecation warning remains non-failing.
It was not necessary to change the application HTTP/provider stack to hide it.

## Explicit upstream exception

`braces@3.0.3` remains affected by
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
No patched upstream release was available during this work. It is pulled only by
Next.js lint tooling and is absent from the production dependency graph.

The policy permits only this advisory, exact version and dev-only lock entries,
through **2026-11-21**. Inherited findings are traced to that leaf; unrelated
advisories are not ignored. Production findings, changed versions/exposure,
missing chains, invalid/expired policy, contradictory reports and unavailable
scans block CI. This is a bounded risk exception, **not a package fix**. Remove it
when a supported upstream fix becomes available; do not silently extend it.

## Release and assurance boundary

The CI/CD skill kept the approved-account guard and serialized migration → staged
smoke → promotion lifecycle intact. The verification skill required complete
browser → API → database → response checks after dependency changes, not just
successful installation. These skills influenced the CI hardening and full QA.

Existing production still requires a separately authorized release to receive
these patches. No live Groq calls, personal-record transfers, production database
inspection/migration, backup restoration or platform WAF/rate-limit changes were
performed. Previous monitoring/runtime-log gaps remain unverified. GitHub Actions
has not executed these uncommitted edits; local equivalent gates and offline CI
contracts passed. No security assurance beyond the stated checks is implied.

See [maintenance commands](DEPENDENCY_SECURITY.md) and
[the original audit](PROJECT_INTEGRITY_AUDIT_2026_10_22.md).
