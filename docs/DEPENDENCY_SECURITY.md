# Reproducible dependencies and security checks

Part of [Phase 32](PHASE_32_POST_ROADMAP_UPGRADES.md); its
[release receipt](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md) records deployment state.

Use Python 3.13 and Node 24 (at least 24.15). Do not copy a production `.env`
into tests, print credentials or install packages from an unreviewed mirror.

## Python installation

`backend/requirements.in` records reviewed runtime/migration inputs and security
floors. `backend/requirements.txt` is the generated complete runtime lock, with
exact versions, platform markers and SHA-256 distribution hashes. Vercel continues
to use the conventional `requirements.txt`; no project/framework migration is needed.

`backend/requirements-dev.in` adds test/security tooling, constrained to the
runtime lock. Its generated `requirements-dev.txt` includes that exact runtime
set plus pytest, pip-audit and the pinned installer. Test/security tools are not
included in the runtime lock or production migration install.

From the repository root:

```powershell
# Development/test environment (also installs runtime packages):
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check

# Production/runtime-only environment, when separately authorized:
python -m pip install --require-hashes --only-binary=:all: -r backend/requirements.txt
```

Do not edit generated locks by hand or replace them with a workstation `pip
freeze`. Use **uv 0.12.7**, matching CI, from the repository root:

```powershell
uv pip compile backend/requirements.in --universal --python-version 3.13 --generate-hashes --no-header --output-file backend/requirements.txt
uv pip compile backend/requirements-dev.in --universal --python-version 3.13 --generate-hashes --no-header --output-file backend/requirements-dev.txt
```

Review input changes first. For an intentional transitive update, add
`--upgrade-package NAME` to the relevant compile invocation; do not indiscriminately
upgrade or relax security floors. Regenerate runtime before development, review
the resulting diff and rerun all quality gates. Universal markers/hashes retain
Windows development and Linux CI/deployment compatibility. New wheels or metadata
may require a reviewed lock refresh even without a version change.

CI recompiles both locks with the pinned tool and rejects a diff, installs with
hash enforcement/binary-only distributions, then audits **both** locks:

```powershell
.\.venv\Scripts\python.exe -m pip_audit --strict --disable-pip --require-hashes -s pypi -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pip_audit --strict --disable-pip --require-hashes -s pypi -r backend/requirements-dev.txt
```

No Python advisory is suppressed. Advisory-service or dependency-collection
failures close the gate. A passing `pip check` alone is not a security scan.

## Frontend installation and checks

```powershell
Set-Location frontend
npm.cmd ci --ignore-scripts
npm.cmd run test:security
npm.cmd run audit:security
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

Next.js and its lint configuration are kept at the same reviewed version.
`package-lock.json` pins transitive packages and integrity digests. Install-time
lifecycle scripts are not needed by the verified build and are disabled locally
and in the frontend CI quality gate. The workstation may have a newer system
Node; ensure the actual npm process, not just a PATH label, runs under Node 24.

`audit:security` runs production and full npm audits. The production graph has
**no advisory exceptions**. Full-tree exceptions must match a reviewed advisory
ID, package, exact version, development-only lock entry and unexpired policy.
Unknown formats, contradictory totals/exit statuses, missing advisory chains,
offline/failed scans and all other advisories fail closed. Regression tests cover
these failure modes; no general severity threshold suppresses findings.

### Explicit unresolved upstream limitation

`braces@3.0.3`, pulled through Next.js ESLint → fast-glob → micromatch, has
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
(deep-pattern recursion / denial of service). No patched upstream release was
available on 2026-10-22. It is not in the production dependency graph; HealthLink
does not feed application-user glob patterns into this tooling. Lint quality
jobs have no production credentials. Untrusted code should still be handled in
an isolated checkout/CI runner, never executed with production secrets.

`security/npm-audit-policy.json` temporarily accepts **only this advisory for
this exact dev-only version**, through **2026-11-21**. Five inherited npm package
entries trace to this one advisory; they are not five accepted vulnerabilities.
This is a transparent, time-limited risk exception, not a patched package or a
claim that the raw full npm audit is clean. New advisories in braces still fail.
Recheck upstream and remove the exception when a supported fix is available;
do not silently extend its date or alias incompatible replacement packages.

## Release boundary

Dependency checks strengthen the existing backend/frontend prerequisites. The
non-cancelling release lock, approved account/project guard and stale-head checks
remain intact: migration → stage without domains → protected smoke → promote →
stable smoke. No new schedule or reminder workflow is introduced.

Local fixes do not patch the deployed application until the owner separately
authorizes commit, push and deployment. Real-provider behavior, production logs,
backups and platform abuse protections require separate operational verification.
