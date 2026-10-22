# Phase 32 — post-roadmap product, interface and release hardening

The owner designated **all work after completion of the original Phase 31
roadmap as Phase 32** on **2026-10-22**, and authorized documenting, committing,
pushing and deploying the increment, now released as `6649931`. Follow the
[production receipt](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md) for actual status.

## Boundary and numbering

Phases 0–31 keep their original scope. Phase 32 consolidates the subsequent
continuation, not a rewrite of older features or historical receipts. Earlier
commits, migration identifiers and dated test results remain intact.

**Migration numbers are not phase numbers.** `0031_ai_conversations` belongs to
the Phase 32 saved-chat continuation; do not rename it. The released Settings/
theme/security increment adds no migration. Expected production head remains 0031.

## Complete Phase 32 scope

| Area | Included continuation |
| --- | --- |
| Release reliability | Post-roadmap rollout/verification, protected staged smoke transport (`2bb55b8`), approved-target/stale-head checks, serialized migration → stage → smoke → promotion, release receipts and handoffs |
| Modern AI conversations | Approved sidebar/wide transcript/pinned composer/compact records control, mobile drawer, saved account-private history, reopen/follow-up, new chat, deletion, copy/timestamps and pagination |
| Chat persistence/privacy | Migration 0031, server-owned bounded context, retry idempotency, turn cap, owner/role enforcement and concurrent-delete protection; fresh one-request record consent and General-mode history isolation |
| Portal Settings | Citizen/professional/admin Account, Security and Display; citizen Privacy & sharing; verified-doctor Practice hours; existing identity/grant/session/schedule controls reused; legacy redirects and unsaved-edit protection |
| Shared UI/accessibility | Slimmer navigation, mobile focus trap/restoration and scroll lock, responsive Settings, keyboard-scrollable diagnostic tables; admin identity-detail async-params correction |
| Light / Dark / System | Browser-only allowlisted appearance/text/motion/sidebar preferences, pre-paint initialization, OS following, cross-tab sync, readable role/status/form/chat surfaces; light printing and unchanged generated PDFs |
| Dependency/CI security | Next.js/matching lint 16.4.2 and patched transitives; Python security patches; separate universal hash-locked runtime/dev requirements; lock freshness, strict advisory gates, immutable action pins and credential-free checkouts |
| QA and portability | Full backend/PostgreSQL/frontend/security/browser checks, responsive/theme/privacy regressions, integrity audits/remediation/rechecks, new-PC setup and updated agentic handoffs |

The saved-chat increment was **already released** as `21e94a5` on 2026-10-20.
Its Phase 32 designation is retrospective; this release does not recreate the
tables or duplicate that implementation. Earlier release-hardening receipts
remain dated evidence, even when their original title refers to Phase 31 rollout.

Explanation-only AI safety remains authoritative: no diagnosis, prescribing,
treatment changes, booking or clinical-record writes. No raw record-context
snapshot is stored in chat history. Display preferences contain no identity or
medical data. No automatic AI record-consent setting was introduced.

## Preserved foundations — not newly attributed to Phase 32

Configurable Groq AI foundation; specialist/nearest doctor discovery; private
admin-confirmed facility coordinates and Bangladesh district/upazila fallback;
merged Diagnostic tests; unified clinical notes/prescription; previous records
and on-demand PDF regeneration; scoped grants and clinical auditing; emergency
profiles and manual reminders. The scheduled reminder workflow remains removed.

## Latest local verification before release

The same application working tree passed a fresh recheck immediately before this
designation. These classification edits change documentation only; CI must still
verify the exact release commit.

- 567 backend/PostgreSQL, 298 frontend (61 files) and 10 security-gate tests.
- Lint, TypeScript and optimized build; Node 24.20.0 / Next.js 16.4.2.
- 14/14 optimized-build Edge journeys, including care, privacy, chat, Settings
  and responsive/Light/Dark/System checks.
- Both Python lock scans clean; all 103 installed packages clean against OSV;
  frontend production scan clean; byte-identical lock reproduction.
- Alembic head 0031/no drift; 57 validated foreign keys; 9 anonymous production probes.

One TestClient deprecation warning remains non-failing. The full npm scan retains
**one unpatched dev-only `braces@3.0.3` advisory**, inherited by five package
entries, with an exact-version exception through **2026-11-21**. Production has
no exception. Changed exposure/version, new findings, expired/invalid policy or
failed scan blocks the gate. Do not call this patched or silently extend it.

## Evidence index

- [Current handoff](../AGENTIC_IMPLEMENTATION_HANDOFF_CURRENT.md) and
  [Phase 32 production receipt](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md).
- [Saved chat](AI_CONVERSATIONS_2026_10_19.md) and
  [earlier chat release](PRODUCTION_CHAT_RELEASE_2026_10_20.md).
- [Settings/theme audit](UI_SETTINGS_AUDIT_2026_10_20.md) and [design QA](../design-qa.md).
- [Original audit](PROJECT_INTEGRITY_AUDIT_2026_10_22.md),
  [remediation](DEPENDENCY_REMEDIATION_2026_10_22.md) and
  [fresh recheck](PROJECT_INTEGRITY_RECHECK_2026_10_22.md).
- [Dependency maintenance](DEPENDENCY_SECURITY.md),
  [new-PC setup](NEW_PC_DEVELOPMENT_SETUP.md) and [progress](implementation-progress.md).

## Authority and completion

The owner's 2026-10-22 instruction supersedes earlier local release holds for
this Phase 32 release only. Use **Mahim2077/HealthLink**, `main`, and the approved
Mahim2077 Vercel connection, **mahim2077s-projects / healthlink-sd**. No alternate
account/project, secret rotation, permission downgrade or real clinical-data
mutation is authorized by this release.

Production completion is recorded in the linked receipt: application `6649931`,
successful Actions run `39808112467`, READY production deployment and independently
verified stable origin. No medical safety, provider privacy, backup or monitoring
certification is implied by the tests; the receipt records actual acceptance limits.
