# Phase 32 production release — 2026-10-22

**Released: committed, pushed, staged, verified and promoted to stable production.**
The exact application release and remaining verification limits are recorded below.

## Authority and verified target

The owner requested consolidating all post–Phase 31 work into Phase 32, documenting
it, then committing, pushing and deploying it. See
[Phase 32 scope](PHASE_32_POST_ROADMAP_UPGRADES.md).

- GitHub: approved **Mahim2077**, **Mahim2077/HealthLink**, `main`.
- Vercel: approved **Mahim2077**, **mahim2077s-projects**, **healthlink-sd**.
- Team: `team_l9GeumDweBdowhhoxPfAS0yM`.
- Project: `prj_kQyhfaS1tFS7NXlUMYr9C0FA8W5f`; Services / Node 24.x.
- Stable production: `https://healthlink-sd.vercel.app/`.
- Matching preflight remote/local HEAD: `89e89802a34a9e9f818649b301d6d96399b9eb98`.
- Previous application receipt: `21e94a5`, schema `0031_ai_conversations`.

Approved identities/project were reverified. Push access was checked using the
explicitly selected Mahim2077 Git credential, without exporting/printing credentials.
No other account/project or secret configuration was used or changed.

## Deployment increment

Role-aware Settings, shared UI/accessibility cleanup, Light/Dark/System themes,
dependency patches, hash-locked runtime/dev dependencies, CI security gates and
Phase 32 documentation. The already released modern-chat/history increment is
included in the Phase 32 umbrella without being reimplemented.

No new migration: CI upgrades to the existing expected head `0031_ai_conversations`.
No clinical records or provider credentials are changed by this release.

## Preflight evidence and limitations

567 backend, 298 frontend, 10 security-gate tests; lint/types/build; 14 optimized
browser journeys; clean Python/frontend production scans; exact lock reproduction;
head 0031/no drift; 57 validated foreign keys and 9 anonymous production probes.
See [fresh recheck](PROJECT_INTEGRITY_RECHECK_2026_10_22.md).

One unpatched dev-only braces advisory is accepted for the exact version through
2026-11-21. No production exception is added/extended. One existing TestClient
warning remains non-failing. Monitoring/log-access limits are detailed below.

## Completed release sequence

Commit → push approved main → backend/frontend/security CI → target/stale-head
checks → migration → production build → stage without domains → protected smoke →
stale-head check → promote tested build → stable smoke.

- Application commit: `6649931e29bdf19a9b085ec2b0641a79f97777b7`.
- Commit subject: `feat(phase-32): consolidate settings, themes and release hardening`.
- Approved `main` push and remote commit match verified.
- [GitHub Actions run 39808112467](https://github.com/Mahim2077/HealthLink/actions/runs/39808112467):
  **completed / success**, exact application SHA; completed 2026-10-22 at 15:52 UTC.
- Both backend and frontend quality jobs passed, including Linux lock reproduction,
  advisory gates, tests, lint/types/build and schema checks.
- Production job passed approved-target/stale-head checks, database upgrade,
  both-service build, staging without live-domain changes, protected staged smoke,
  promotion and stable-domain smoke. Schema remains `0031_ai_conversations`.
- Deployment: `dpl_3RyPMHxWh3BVG6pgsrEEfHQrUyGr`, **READY**, production target.
- Immutable origin: `healthlink-k17q6mhyv-mahim2077s-projects.vercel.app`.
- Vercel lookup of `healthlink-sd.vercel.app` resolved to this deployment, the
  expected `healthlink-sd` project and the exact application commit.
- Independently reran all **9 anonymous stable-origin smoke probes** after CI;
  all passed (health, public/sign-in pages and protected API denial contracts).

## Production browser acceptance and limits

- The provided citizen test account signed in at the stable production origin.
  Settings exposed Account, Security, Display & accessibility and Privacy & sharing.
- Display controls exposed Light/Dark/System, text size, motion and sidebar choices.
  Dark mode rendered correctly and remained selected after refresh/session restore.
  The original Light preference was restored. Security showed current-session and
  all-session controls without offering unsupported password/2FA features.
- Local ignored screenshot: `.runtime/phase32-production-qa/citizen-display-dark.png`.
  It contains the appearance screen, not clinical records. No screenshot or browser
  credentials are included in Git.
- The ordinary sign-out confirmation stalled browser automation; dismissal/sign-out
  and tab closure could not be confirmed. Do not claim session cleanup succeeded.
  All-session revocation was deliberately not used. Doctor/admin workflows retain
  the local synthetic acceptance evidence; they were not re-tested in production
  during this release. No clinical data, grants, schedules or chats were edited.
- No live Groq call or new transfer of medical record context was made. Existing
  private production provider configuration was retained, not printed or changed.
- Fresh approved-project drain inventory returned **zero drains**. A bounded,
  deployment-scoped error/fatal runtime-log query returned **403 forbidden**.
  No alternate account or unverified local CLI credential was used to work around
  access. Therefore this is **not** a verified clean runtime-error window or
  continuous monitoring, backup/restore, provider-privacy or clinical certification.

The follow-up documentation-only receipt commit uses `[skip ci]` after this run
completed. It does not replace the application SHA above or trigger another release.
