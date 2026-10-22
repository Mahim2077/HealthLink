# HealthLink project integrity audit — 2026-10-22

> Dated pre-fix evidence within [Phase 32](PHASE_32_POST_ROADMAP_UPGRADES.md), not current release state.

> Historical pre-fix findings below are retained. The owner subsequently
> authorized local remediation; see
> [remediation results](DEPENDENCY_REMEDIATION_2026_10_22.md) for current status,
> including the explicit unpatched development-only exception. No release occurred.

## Verdict

**Functional verification passed. Security/release clearance is withheld pending
dependency remediation.** No functional regression was found in the executed
backend, frontend and browser suites. This is a bounded audit, not a penetration
test, medical-safety certification or a guarantee that every possible defect is absent.

The inspected workspace is `D:\HealthLink_V_1`, branch `main`, HEAD
`89e89802a34a9e9f818649b301d6d96399b9eb98`, including the existing uncommitted
Settings, accessibility and Light/Dark/System work. That work remains unreleased.
The previously recorded production application commit is `21e94a5`; this audit
did not independently query the deployed commit identity.

Story checked: citizen, doctor, lab and admin interfaces → same-origin API →
authorized database operations → returned records/UI, including private AI chat
history and browser-only display preferences.

No application code, dependency versions, environment values, CI configuration
or production records were changed. No commit, push or deployment was performed.
This report is the only new tracked-source candidate created by the audit.
Synthetic fixtures and generated browser/build/test artifacts remain local.

## Fresh verification results

| Check | Result | Evidence |
| --- | --- | --- |
| Backend suite | PASS | 564 tests, 118.13 seconds; PostgreSQL integrations enabled on loopback QA DB |
| Frontend suite | PASS | 61 files, 298 tests |
| ESLint | PASS | `npm run lint` exited successfully |
| TypeScript | PASS | `npm run typecheck` and build-time checks passed |
| Optimized frontend build | PASS | Next.js compilation/static generation completed |
| Edge browser acceptance | PASS | 14/14, zero skipped, unexpected or flaky cases; 88.39 seconds |
| Migration head | PASS | Code and QA DB both `0031_ai_conversations` |
| Schema drift | PASS | Alembic: `No new upgrade operations detected.` |
| QA foreign-key validation | PASS | 57 public-schema foreign keys; zero unvalidated constraints |
| Python dependency consistency | PASS | `pip check`: `No broken requirements found.` |
| Diff whitespace | PASS | `git diff --check`; only existing CRLF normalization warnings |
| Credential-pattern scan | PASS within scope | No matching provider/GitHub key or private-key patterns in tracked content, frontend source or generated browser assets |
| Anonymous production smoke | PASS | 9/9 read-only checks against the stable production origin |
| Frontend dependency advisories | FAIL | 14 affected packages: 1 critical, 11 high, 2 moderate; production-only subset: 3 packages |
| Installed Python advisory check | FAIL | OSV version matches for 7 of 85 installed packages, including local tooling |

The backend suite emitted one existing Starlette/httpx TestClient deprecation
warning. It did not fail tests.

### Browser and permission coverage

- Full synthetic citizen → doctor → lab → citizen care journey, including
  specialty/nearby discovery, booking, chamber queue, consultation, diagnostics
  and finalized reports. The clinical journey also runs in dark mode.
- Unified clinical notes/prescription, previous prescriptions and on-demand PDF
  bytes; no stored PDF was introduced.
- Saved AI transcript, follow-up continuity, refresh/reopen, new conversation,
  deletion, separate-account ownership and explicit record-context consent.
- Existing grants, privacy/access history, emergency information and manual
  reminder controls. No scheduled reminder workflow exists in `.github/workflows`.
- Synthetic facility contact update preserving confirmed location, practice
  schedule editing and admin verification/identity detail.
- Settings role gates, legacy profile/privacy redirects, mobile menu focus
  trapping/restoration, larger text, storage failures and all-session revocation.
- Light/Dark/System persistence before body paint, cross-tab synchronization,
  live system-theme changes, explicit-choice precedence and light printing.
- Portal matrices at 390/768/1366/1920 pixels, plus narrower Settings checks.
  Fresh Settings, consultation, AI chat and mobile lab-edit screenshots were
  visually inspected. Browser assertions detected no unexpected API/console
  errors or nonlocal browser requests in the accepted journeys.

Backend negative tests additionally cover expired/tampered tokens, inactive and
wrong-role access, revoked/expired/scoped grants, draft exclusion, cross-citizen
denial, unsafe AI output, provider failures/timeouts and chat ownership/deletion
races. Source inspection confirmed per-request database authorization, memory-only
access tokens, HttpOnly refresh cookies, private authenticated responses and
generated-on-demand prescription PDFs.

### Production smoke scope

`/health`, `/`, and citizen/professional/admin login pages returned their expected
healthy/HTML contracts. Citizen/professional/admin overview and AI-status APIs
returned the expected unauthenticated `401`, without a redirect.

These probes used no account credentials and changed no production records.
They do not establish current production DB connectivity, authenticated workflow
health, deployed dependency versions or live AI behavior.

## Findings and recommended follow-up

### 1. P1 — Next.js dependency has critical/high upstream advisories

`frontend/package.json:21` and `frontend/package-lock.json` resolve Next.js
**16.3.0**. The read-only npm audit identifies Next.js as critical, plus production
packages **sharp 0.35.3** and **source-map-js 1.2.1** as high. The complete audit
also flags development dependencies including Vitest/Vite, undici and lint/glob
dependencies. Counts are affected packages, not distinct vulnerabilities.

The audit suggested Next.js 16.4.2; this is a candidate to validate, not an
automatic update approval. Upgrade the framework and matching lint configuration,
refresh transitive dependencies deliberately, review installed migration guidance,
then rerun the complete verification set. Do not use a blind force/downgrade fix.

Applicability matters: the Windows-hosted RCE advisory applies to affected
Windows servers; this audit's Windows preview was loopback-only. No `next/og`
ImageResponse usage was found. The current public image is a bundled PNG, not
attacker-supplied AVIF. Production exploitability was **not demonstrated**; these
conditions limit particular exploit paths but do not make the dependency scan clean.

Primary sources:

- [Next.js Windows-hosted RCE advisory](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36)
- [Next.js AVIF/image-optimization advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4)
- [Next.js ImageResponse advisory](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j)

### 2. P1 — Installed Python dependency set is not advisory-clean

A read-only OSV batch query matched these installed package versions:

| Package | Installed | Context |
| --- | --- | --- |
| certifi | 2026.7.22 | TLS trust bundle; critical compromised-CA advisory |
| PyJWT | 2.13.0 | Authentication dependency; multiple condition-specific advisories |
| pillow | 12.3.0 | Image/PDF dependency; image-decoder advisories |
| urllib3 | 2.7.0 | HTTP dependency; proxy/streaming advisories |
| Mako | 1.4.1 | Migration/template tooling; Windows path advisory |
| pytest | 8.4.2 | Test tooling; temporary-directory advisory |
| pip | 25.2 | Local package installer, not an application API |

These are local installed-version matches, **not confirmation of the production
environment's versions or successful application exploitation**. PyJWT's JWK/
asymmetric-key advisories do not automatically apply to HealthLink's fixed HS256
secret configuration. A bounded local malformed/nested JWT check returned `401`,
not `500`; it did not reproduce an authorization bypass and does not resolve all
listed advisories. No exploit or stress test was sent to production.

The certifi advisory is particularly relevant to outbound HTTPS, including the
httpx-based Groq provider. Rebuild and audit a controlled Python dependency set,
prioritizing a current CA bundle and supported patched libraries. Some fixes may
require revisiting existing version constraints rather than simply reinstalling.
The certifi maintainer advisory and OSV report slightly different patched dates;
select a release satisfying the current advisory database, not the old installed
bundle.

- [certifi maintainer advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
- [PyJWT nested-header advisory and applicability limits](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-8wjv-2p76-3863)

### 3. P2 — Dependency/security checks are not enforced by CI

`.github/workflows/ci-cd.yml` checks dependency consistency, tests, lint, types,
build, migration ordering and staged/stable smoke, but does not run npm/Python
vulnerability scans. The successful quality gates therefore coexist with the
findings above.

`backend/requirements.txt` contains broad version ranges and no committed Python
lock/constraints file. A fresh CI/deployment installation can differ from this
tested virtual environment; `pip check` verifies compatibility, not security or
reproducibility. The pytest range currently excludes the major version reported
as patched for its advisory.

Recommended: establish reviewed reproducible Python constraints/locking and add
read-only advisory gates with explicit, narrowly justified exceptions. Keep test
tooling distinguished from deployed runtime dependencies. Do not alter the
existing migration → stage → smoke → promote lock/order.

## Boundaries and remaining assurance gaps

- AI responses in browser QA used the backend mock provider. Groq request-shape,
  consent, timeout and fail-closed safety tests passed, but no fresh live Groq
  request or personal medical-record transfer was performed.
- Local DB/schema checks used synthetic loopback PostgreSQL only. Production
  schema/data integrity, backup restore and disaster recovery were not exercised.
- Current authenticated production journeys, runtime logs/alerts, WAF/rate-limit
  configuration and monitoring were not verified. The handoff's prior runtime-log
  access/monitoring gap remains unresolved, not a fresh clean-log result.
- No application-level login/AI throttling was found in the reviewed handlers;
  platform protection was not inspected, so effective production abuse limits
  remain unconfirmed. This warrants follow-up, not an asserted production bypass.
- Secret scanning was pattern-based over current tracked content and browser
  assets. It is not a full Git-history/entropy audit or proof that no credential
  was ever exposed. Ignored environment files were not printed or pulled.
- Edge desktop/mobile emulation is not Safari/Firefox, physical GPS, assistive
  technology, load testing or exhaustive accessibility certification.

The verification skill guided complete boundary checks and separation of local
and production evidence. Environment-safety guidance kept secrets out of output
and avoided production environment pulls. Neither required an application change.

## Evidence locations

- Browser JSON: `.runtime/browser-qa/results.json`
- Browser report: `.runtime/browser-qa/report/index.html`
- Fresh screenshots: `.runtime/browser-qa/results/`
- Existing Settings plan/handoff: `docs/UI_SETTINGS_AUDIT_2026_10_20.md` and
  `AGENTIC_IMPLEMENTATION_HANDOFF_CURRENT.md`

Temporary API, frontend, routing proxy and QA database processes started for this
audit were stopped afterward; synthetic fixtures were retained, not deleted.

All runtime evidence is local/ignored. Application source, lockfiles and the
pre-existing Settings/theme changes were preserved. Dependency fixes and any
commit/push/deployment require a subsequent owner instruction.
