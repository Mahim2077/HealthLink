# HealthLink full-project integrity recheck — 2026-10-22

> Phase 32 pre-release evidence. The subsequent owner instruction authorizes
> commit/push/deployment; see the [Phase 32 release receipt](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md).

## Outcome

**Fresh verification passed within the tested scope. No new defect was found.**
One previously disclosed, unpatched development-only dependency advisory remains
under its exact-version, expiring policy. This is not an unconditional security
certification or a claim that the full raw npm audit is clean.

Verified the current `D:\HealthLink_V_1` working tree on `main`, HEAD
`89e89802a34a9e9f818649b301d6d96399b9eb98`, including unreleased Settings/theme and
dependency/CI work. Checks were rerun for this request, not copied from the
preceding remediation report. Application code, lockfiles, policy and existing
changes were not edited. This report is the only new source-document artifact.

The verification skill guided the complete story: citizen, doctor, lab and admin
UI → authenticated API → authorized database operation → response/rendered UI.
Authenticated journeys used newly seeded synthetic accounts on loopback only.

## Results

| Check | Fresh result |
| --- | --- |
| Full backend/PostgreSQL suite | **567 passed**, 110.49 seconds; no skipped tests |
| Frontend Vitest | **61 files / 298 tests passed** |
| Security-policy regression tests | **10 passed** |
| ESLint / TypeScript / optimized build | Passed; Node **24.20.0**, Next.js **16.4.2** |
| Optimized-build Edge acceptance | **14/14 passed**, 89.11 seconds; zero skipped, unexpected or flaky tests |
| Python runtime lock audit | Strict PyPI advisory/hash check: no known vulnerabilities |
| Python development lock audit | Strict PyPI advisory/hash check: no known vulnerabilities |
| Independent Python OSV check | **103 installed packages; zero flagged**, complete batch response |
| Frontend production dependency audit | **Zero flagged packages**, no exception |
| Frontend full dependency gate | Passed with the single disclosed dev-only exception below |
| Complete installed npm tree | Consistent; resolved lock sources are official npm registry URLs |
| Runtime/development lock reproduction | Both byte-for-byte identical using **uv 0.12.7**, generated into ignored copies; source locks untouched |
| Migration chain and QA database | Single head/current **0031_ai_conversations** |
| SQLAlchemy metadata drift | No new upgrade operations detected |
| QA database foreign keys | **57 validated; zero unvalidated** |
| Python dependency compatibility | `pip check`: no broken requirements |
| CI YAML / action pins / release contracts | Passed; immutable action pins, quality prerequisites and serialized release safeguards intact |
| Current-source/browser-bundle key patterns | No matching provider/GitHub key or private-key patterns |
| Secret/runtime path tracking | Checked paths remain ignored and untracked |
| Diff whitespace | Passed; existing CRLF normalization notices only |
| Anonymous production smoke | **9/9 passed** on `https://healthlink-sd.vercel.app/` |

One existing Starlette/httpx TestClient deprecation warning remains non-failing.
Local API, frontend and routing-proxy output showed no new error output during
the accepted browser journeys. This is local evidence, not production log review.

## Functional and authorization coverage

- Citizen → doctor → lab → citizen care journey: specialty/nearby discovery,
  appointments, chamber/queue persistence, unified clinical notes/prescription,
  previous prescriptions, generated PDF bytes, diagnostic request/report and
  finalized citizen results.
- Private AI conversation history, continued/reopened transcript, new chat,
  deletion, explicit record consent and separate-account isolation. Source checks
  retain citizen-owned conversations and finalized-only clinical AI context.
- Grants, scoped/revoked/expired access, draft exclusion, wrong-portal and
  cross-citizen denial, emergency profile, privacy/access history and existing
  manual reminder controls. No reminder scheduler was reintroduced.
- Synthetic facility updates, professional verification, practice hours and
  administrator identity detail; Settings role restrictions and session revocation.
- Responsive portal matrices, mobile focus/scroll behavior, browser-only display
  preferences and Light/Dark/System persistence, OS changes, cross-tab sync and
  light print behavior. Fresh dark Settings and AI-chat screenshots inspected.
- Backend negative/provider tests retain explanation-only AI safety, malformed
  output rejection, fail-closed provider errors/timeouts and clinical ownership
  enforcement. PDFs remain generated on demand with private/no-store responses.

## Known exception — unchanged, not patched

The full npm scan still contains five package entries tracing to **one advisory**:
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) in
`braces@3.0.3`, used by Next.js lint tooling. It is absent from the production
dependency graph. The policy accepts only that exact version/advisory in dev-only
entries through **2026-11-21**. Production exposure, another advisory, a changed
version, invalid/expired policy or failed/unrecognized scan blocks the gate.
Do not silently extend the exception or call the package fixed.

## Production and assurance limits

Production checks were anonymous and read-only: `/health`, `/`, three portal
login pages and four protected APIs. Public contracts passed; protected APIs
returned the expected `401` without redirects. No credentials, live AI request,
personal medical record or production database mutation was involved.

These probes do **not** prove current production DB connectivity, authenticated
workflow health, deployed dependency versions or deployment SHA. Local patches
remain unreleased. GitHub Actions was not dispatched; local equivalent checks,
workflow parsing and offline release/security contracts passed.

Live Groq behavior, production schema/data/backups/restoration, runtime logs,
monitoring and platform WAF/rate limits were not verified. The audit is not a
penetration test, exhaustive accessibility/cross-browser assessment, medical
safety certification or full Git-history/entropy secret audit. Browser AI used
the mock provider; no real records were transferred externally.

## Evidence and cleanup

- Fresh browser JSON: `.runtime/browser-qa/results.json`
- Fresh browser screenshots/report: `.runtime/browser-qa/results/` and
  `.runtime/browser-qa/report/index.html`
- Reproduced lock copies: `.runtime/lock-recheck-*` (ignored)
- Policy/maintenance: `security/npm-audit-policy.json` and
  `docs/DEPENDENCY_SECURITY.md`
- Earlier findings/fixes: `docs/PROJECT_INTEGRITY_AUDIT_2026_10_22.md` and
  `docs/DEPENDENCY_REMEDIATION_2026_10_22.md`

Temporary QA API, frontend, proxy and database processes started for this recheck
were stopped afterward. Synthetic records and artifacts were retained locally,
not deleted. No commit, push or deployment was performed.
