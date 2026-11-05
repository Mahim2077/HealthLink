# Minimal lint dependency fix — 2026-11-03

## Result

The minimatch audit blocker is resolved **locally** while retaining Next.js
16.4.2, React 19.2.8, TypeScript 5.9.3, ESLint 9.39.2 and the existing Next lint
configuration. No replacement linter, new security exception or audit-gate change
was introduced. Commit, push and deployment remain held.

This supersedes the unresolved local blocker in the
[October 31 preflight](PRE_RELEASE_PREFLIGHT_2026_10_31.md). That report and its
earlier registry/QA results remain dated evidence. This continuation is Phase 32.

## Narrow implementation

The old minimatch 3/10 copies are replaced by the official, integrity-locked
`minimatch@11.0.4` engine under the explicit `minimatch-engine` npm alias. A private
project-owned development adapter exposes the callable/default and named API
needed by the existing seven lint consumers. It does not copy a glob algorithm
or pretend to be an upstream legacy release.

- `frontend/tooling/minimatch-compat` contains the small CommonJS/ESM adapter.
- `frontend/package.json` uses npm's dependency-reference override.
- `frontend/.npmrc` sets `install-links=true` so clean installs pack the local
  package and do not depend on pre-existing symlinks.
- Seven adapter/integration tests join the ten existing security-gate tests in
  `test:security`; the existing CI already runs that command.

The adapter deliberately supports the pinned lint callers, rather than promising
general minimatch 3 compatibility. Their legacy `makeRe()` use only requires a
`.test()` method; it delegates to the patched engine's non-regex matcher and
does not return a RegExp. Tests exercise the actual import-plugin caller.
Changes to the seven consumer versions/set or any runtime use fail the new
guards and require review. Remove this adapter when the lint stack natively
supports the patched engine.

All retained unrelated lock records, including runtime dependencies and platform
constraints, are unchanged. The lock only changes the root development
declaration and adapter, removes the old matcher/helper subtree, and adds the
patched engine/helper subtree. Existing survey and Python changes were preserved.

## Verification

Checks used Node 24.20.0. Lock generation and clean installation used npm 11.17.0.

| Check | Result |
| --- | --- |
| Clean project `npm ci --ignore-scripts` | Passed, 448 packages |
| Production and full dependency gates | Both passed: zero flagged entries, zero exceptions used |
| Security / adapter tests | 17 passed: existing 10 plus 7 compatibility/integration cases |
| Frontend regression suite | 343 passed across 64 files, 9.33 seconds |
| TypeScript | Passed |
| ESLint file/rule comparison | All 239 original files retain identical effective rule maps; only the two adapter entry points are added, for 241 files total |
| ESLint diagnostics | Zero errors and warnings; the application's 86 enabled rules remain intact |
| Optimized Next build | Passed: all 44 static pages and dynamic routes compiled |
| Lock reproduction | Second npm lock generation is byte-stable in the clean verification project |
| Dependency tree | `npm ls minimatch minimatch-engine --all` passed; all seven consumers use the adapter and official 11.0.4 engine |
| Final diff / credential patterns | Whitespace check passed; 80 changed/new files scanned with no credential-pattern matches |

Thirty one-off compatibility comparisons also matched the original implementation
for globstar, dotfiles, braces, negation/extglob, matchBase/case options, Windows
paths, partial directory traversal and helpers. Persistent tests verify those
contracts, CJS/ESM exports, genuine patched-engine identity, development-only use,
and live Next/React Hooks/TypeScript/accessibility rule failures.

Intermediate issues were resolved rather than bypassed. Relative local override
paths and stale npm metadata initially failed in scratch installs. The final
minimal lock was assembled from npm-generated patched records and the original
unrelated records, then canonicalized by npm and verified by clean installation,
repeated lock generation and audits. A broad fresh resolution that upgraded
unrelated dependencies was discarded. npm 10's unrelated platform-metadata churn
was also discarded. The final lock retains the original platform records.

One test fixture initially expected a parent-directory glob to match. The original
minimatch 3.1.5 and the patched engine both returned false; the fixture was
corrected after checking an isolated original-version reference. No matching
behavior or assertion was disabled. The original reference remains ignored under
`.runtime`, outside the project's dependency graph.

The existing ESLint support/deprecation notice is not changed by this scoped fix.
The old braces policy entry is unchanged and expires on 2026-11-21; neither audit
needed it in this pass. No exception was extended or added.

## Release boundary

No application behavior, backend code, migration, clinical data or live AI call
was changed for this dependency fix. The previous October 31 backend/browser
receipts remain historical; they are not described as fresh November 3 runs.
Linux GitHub Actions and production acceptance remain pending a later authorized
release. The existing account, stale-head, migration/staged-smoke/promotion guards
remain unchanged. No commit, push or deployment was performed.
