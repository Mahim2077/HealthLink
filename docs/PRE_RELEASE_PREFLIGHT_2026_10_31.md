# HealthLink pre-release preflight — 2026-10-31

> The blocker described here was resolved locally on 2026-11-03 with a minimal
> stack-preserving dependency adapter. See
> [the subsequent fix report](MINIMAL_LINT_DEPENDENCY_FIX_2026_11_03.md).
> This preflight remains historical evidence; publication is still held.

## Result: held, not released

The owner authorized a fresh pre-release check, commit, push and deployment using
Mahim2077 GitHub and its associated approved Vercel account. No commit, push,
deployment, production migration or credential change has been performed in this
preflight. The October 24 survey fixes and the narrow Python security patch
described below remain in the working tree.

## Verified account and source-control context

- GitHub plugin authenticated as **Mahim2077**, profile ID `141449518`.
- Repository access includes admin/push for **Mahim2077/HealthLink**, default
  branch `main`. The non-interactive Git dry-run used the explicitly selected
  Mahim2077 credential and succeeded without exporting credentials.
- Local and remote main remain `70059d3df275be7cabfd92a24d963f1d0b4849cd`.
  Latest application workflow remains successful run `39808112467` for
  `6649931e29bdf19a9b085ec2b0641a79f97777b7`; the later documentation commit
  skipped CI. These are old-release facts, not CI evidence for the pending fixes.
- Only the Vercel connection labelled **Mahim2077** was used. It authenticates as
  `mahimchow2077-3904`, user ID `cVbkvkuEmlfmpf5VSqhZCcvY`, and identifies
  approved team `team_l9GeumDweBdowhhoxPfAS0yM` / `mahim2077s-projects`.
- **Vercel access resolved after the owner clarified its account scope.**
  Account-default plugin reads (omitting the explicit team selector) return
  existing project `healthlink-sd`, ID `prj_kQyhfaS1tFS7NXlUMYr9C0FA8W5f`,
  owned by the same approved team `team_l9GeumDweBdowhhoxPfAS0yM`.
  Its domain list confirms verified `healthlink-sd.vercel.app`. Production-host
  lookup returns READY deployment `dpl_3RyPMHxWh3BVG6pgsrEEfHQrUyGr`, application
  SHA `6649931e29bdf19a9b085ec2b0641a79f97777b7`.
- Earlier plugin requests with explicit team ID/slug returned 404/empty lists;
  those results did not establish that the account lacked project permission.
  The successful account-default lookup corrects the earlier access conclusion.
  Use that working plugin read path and validate returned project/owner IDs.
  This does not establish a CLI scoping defect or authorize changing CI guards.
  No token/reconnection, alternate account, replacement project, project relink,
  CI-secret edit or production mutation was necessary. Local CLI remains signed
  out, but the authenticated plugin can inspect the approved project.

## Fresh local checks completed

| Check | Result |
| --- | --- |
| Frontend tests | 343 passed, 64 files, Node 24.20.0 |
| TypeScript / ESLint | Passed |
| Security-gate behavior tests | 10 passed |
| Optimized build | Passed: clean-cache and warm-cache confirmation, 44 static pages each |
| Python / package consistency | Python 3.13.7; `pip check` passed |
| Fresh backend / PostgreSQL suite | Final patched environment: 601 passed, zero skipped, 66.54 seconds |
| Migration / metadata drift | Head `0031_ai_conversations`; no new upgrade operations |
| Complete local Edge suite | 18/18 passed in 1.8 minutes; synthetic records and mock AI |
| Landing browser quick check | HTTP 200, meaningful content, six links, no page errors or framework overlay |
| Git whitespace | Passed |
| Changed/new file credential-pattern scan | 70 files scanned; no matches |
| Strict Python runtime / development audits | Both passed, zero known vulnerabilities after patch |
| Python locks / installation | Byte-identical uv 0.12.7 reproduction; hash-enforced install and `pip check` passed |
| Fresh npm production audit | Zero advisories |
| Fresh npm full/development audit | Blocked; see below |

The resumed PostgreSQL start succeeded. Backend tests used a newly created
`healthlink_release_da172ead7b6a` database on loopback port 55433. The browser suite
used separately seeded unique fixtures in `healthlink_phase27_qa`, with real local
API/database responses and mock AI. Citizen, Doctor, Lab and Admin journeys,
saved chat/privacy, finalized publication, Settings/themes, responsive layouts and
survey regressions passed. Landing, mobile empty chat and secondary-facility
screenshots were visually inspected. No production records or live model calls
were used. The API, frontend and exact PostgreSQL cluster started for this check
were stopped afterward. Synthetic databases and ignored evidence are retained.

Initial browser launch failed inside the Windows sandbox, then the external Edge
process could not reach the sandboxed frontend. Running the approved local
frontend and Edge harness in the same accessible environment resolved these
setup failures; assertions were not weakened. The post-browser optimized build
then reported a Turbopack PostCSS worker exiting before its IPC handshake, both
inside and outside the sandbox, including with child-process Node 24 pinned.
The old generated `.next` output was preserved under ignored
`.runtime/next-build-before-f442cb009c8e4287b1c7e3a6c82b3048`. The unchanged
Turbopack production build then passed from a clean cache and passed a warm-cache
confirmation, generating all 44 pages each time. This associates the failure with
the prior generated state; its exact corruption/race mechanism is unproven. No
application, bundler or dependency configuration was changed to bypass it.
Production route types were restored. Generated heading-only `AGENTS.md` noise
was removed without changing its instructions.

The fresh runtime and development audits found four advisories in
`pyasn1==0.6.4`: CVE-2026-119196, CVE-2026-119194, CVE-2026-119197 and
CVE-2026-119195. Official PyPI provides non-yanked universal-wheel patch `0.6.5`,
within the parent's supported `>=0.6.1,<0.7.0` range. A narrow
`pyasn1>=0.6.5,<0.7.0` input floor was added, and both locks were regenerated
using pinned uv 0.12.7. Only pyasn1's version/hashes and its provenance comments
changed; all unrelated versions and hashes were preserved.

Hash-enforced installation changed only pyasn1 and `pip check` passed. Fresh
strict PyPI runtime **and** development lock audits now report zero known
vulnerabilities, without exceptions. Both patched locks reproduce byte for byte
with uv 0.12.7. A fresh isolated database `healthlink_release_patch_995911bc2afb`
is at head 0031 with no metadata drift. Its full patched-environment backend run
passed **601 tests, zero skipped, in 66.54 seconds**. The initial pre-patch run
also passed 601 tests in 86.95 seconds. Two non-failing warnings remain: the
existing Starlette TestClient deprecation and an anyio assertion-rewrite warning
caused by the explicit pre-import validation wrapper. The complete Edge pass
preceded the pyasn1 installation; application/UI code did not change afterward.

## New security blocker

The fresh full npm audit reports 16 moderate inherited package entries rooted in
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249), published
after the previous survey-fix verification. The advisory lists minimatch
`<11.0.1` as affected and `11.0.1` as patched. The locked development graph
contains `3.1.5` and `10.2.6`; the production audit is clean.

The fail-closed gate reports an incomplete advisory chain while traversing npm's
cyclic ESLint inheritance graph. This is a blocked result, not a clean audit.
The documented amplification requires optimization level 2; the located local
v10 consumer uses `{dot:true}` and its default level 1, while v3 lacks that
preprocessing function. That bounded reachability observation does not clear the
advisory or authorize a new exception.

Older lint consumers call minimatch as a function/default export. Globally
forcing v11, or accepting npm's suggested ancient ESLint/config downgrades, is not
a verified compatible fix. Current patched-parent/backport research requires an
approved read-only registry query. The initial escalation was declined; no other
tool bypassed that denial. The owner subsequently instructed the agent to
continue after being asked to retry registry reads and synthetic PostgreSQL
testing. The registry queries then succeeded.

Official npm metadata still provides no compatible patched v3/v10 backport:
`legacy-v3` remains `3.1.5`; latest v10 remains `10.2.6`; v11 reaches `11.0.3`.
Latest ESLint/config-array/typescript-estree parents still require minimatch v10,
while the current import/accessibility/React plugins and eslintrc require v3.
`eslint-config-next@16.4.3` retains those parent families. ESLint 10 also falls
outside the current plugins' supported peer ranges. Neither a forced major
override nor a broader parent upgrade is a supported fix for this graph.

A subsequent registry recheck requested by the owner confirmed the same versions
and constraints across all nine packages above. No compatible upstream patch had
appeared, so no dependency update or policy change was applied. The selected
release hold remains in effect unless the owner explicitly changes that decision.

No frontend dependency, lock, audit exception or quality threshold was changed.
Production remains clean; the full development gate remains blocked. Releasing
would require either an upstream compatible patch or an explicit owner-reviewed
risk decision and separately tested policy implementation. The current policy
only accepts one exact-version dev-only braces exception; it does not authorize
this new minimatch advisory or a traversal bypass for cyclic reports.

## Owner decision — release held for an upstream fix

The owner explicitly selected **“Keep release held for an upstream fix”** after
reviewing the preflight results. Do not commit, push or deploy this release while
the gate remains blocked. Preserve the existing audit policy; no minimatch
exception, gate bypass or incompatible override is authorized. Resume with a
compatible upstream fix and fresh affected checks. No background monitoring or
automatic retry was requested.

The following alternative was presented for review and **was not selected**.
It would require a new explicit owner decision to accept a temporary
development-only risk, followed by implementation and verification. The concrete
bounded proposal is this advisory/package only, exact versions `3.1.5` and
`10.2.6`, expiry **2026-11-07**, and no automatic renewal. Every accepted lock node
must exist, match minimatch and one of those exact versions, and have `dev ===
true`. Production never accepts an exception. The existing braces exception and
its 2026-11-21 expiry stay unchanged. This proposal is **not approved or applied**.

The current scalar-version policy cannot express both versions under one unique
advisory ID. A reviewed implementation would need an exact version allowset and
safe resolution of npm's cyclic advisory graph. It must reject missing/malformed
references, cycles without reachable concrete advisories, and every reachable
unapproved advisory. Simply skipping visited nodes or accepting cycles is unsafe.
Negative tests must cover runtime/mixed nodes, unsupported versions, expiry,
production mode, missing references, rootless cycles and cycles reaching another
unapproved advisory. Fresh install/audits and affected quality checks must pass
before any commit/push/release. No such gate or policy change was made here.

## Resume conditions

1. Vercel target verification is complete through the Mahim2077 plugin's working
   account-default scope. Keep the returned existing project/owner IDs and stable
   production domain pinned; do not ask for tokens or relink the project.
2. Follow the owner's selected hold: resolve the new dependency blocker with a
   compatible, supported upstream update. No new risk exception is authorized;
   do not widen the existing braces-only exception.
3. Local functional checks, Python remediation and bounded diff review are
   complete. After resolving the npm gate, refresh affected checks and review the
   final intended diff/secrets, then commit/push using Mahim2077.
4. Preserve the existing CI lifecycle and account/stale-head guards: quality
   gates → production migration → staged build without domains → protected
   smoke → promotion → stable-domain smoke. Do not bypass a failed gate.

Installing a plugin, authenticating an account and accessing a particular project
are distinct checks. All three now pass for Vercel. The unresolved development
dependency security gate, not Vercel access, holds this release. No new CI run or
production deployment exists for this working tree.
