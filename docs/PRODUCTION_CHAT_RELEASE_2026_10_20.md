# Modern AI chat production release — 2026-10-20

> Retrospectively the saved-chat increment of [Phase 32](PHASE_32_POST_ROADMAP_UPGRADES.md).
> This dated receipt remains intact; see the
> [subsequent Phase 32 release](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md) for Settings/theme/security.

> **Released successfully.** Commit `21e94a5` is READY and serves
> `https://healthlink-sd.vercel.app/`. Migration, staging, protected smoke,
> promotion and stable-domain smoke all passed. Preflight text below is historical.

## Final release receipt

- Application commit: `21e94a5372f6cbf29d71f12fa85e4fa069930ea1`.
- [GitHub Actions 39398090813](https://github.com/Mahim2077/HealthLink/actions/runs/39398090813):
  **success**, 4m 29s, authorized `main` commit and approved Vercel target.
- Deployment: `dpl_VJY17uPWnJQ1yKotXvTSv76SkCvs`, READY / production.
- Generated origin: `https://healthlink-4gjsbw4vw-mahim2077s-projects.vercel.app`.
- Stable origin: `https://healthlink-sd.vercel.app/`; deployment lookup of this
  origin returned the same deployment and application SHA after promotion.
- Production schema: **`0031_ai_conversations`**; CI migration logs confirmed head.
- Linux backend CI: **564 passed**, zero skipped. Frontend CI: **57 files / 266
  tests**, lint, typecheck and optimized build passed.
- Release smoke: **18 passed** (9 staged authenticated transport + 9 stable
  anonymous probes). Independent workstation stable-domain smoke: **9/9 passed**.

## Production acceptance and limits

The provided citizen test account signed in successfully. The new chat displayed
its sidebar, private history and compact records-off control. Two real Groq
General-mode questions about laboratory reference ranges returned educational,
non-diagnostic answers, including a context-dependent follow-up. A full page
refresh restored the session; reopening the saved conversation showed both
questions and answers. New conversation cleared the transcript/composer while
preserving previous saved history and defaulting to records off.

One harmless, two-turn conversation beginning “Release check:” remains in the
provided test account. No existing conversation was deleted. Production deletion
was not exercised; confirmation/ownership/hard-delete paths passed local synthetic
tests. No real clinical record was created/changed or sent to Groq, and no
record-aware model request was made during release verification.

The in-app browser supplied authenticated visual/AX evidence; the earlier release's
browser initialization limitation is no longer a blocker for this citizen check.
This limited sample does not certify clinical accuracy or provider privacy/terms.

The provided Doctor and Admin accounts also signed in successfully and rendered
their role-specific dashboards (Today's care overview / Operational overview).
No consultation, schedule, facility, verification, identity or access-grant change
was made. Test sessions were signed out after checks. This is production login /
dashboard acceptance, not a fresh production execution of the full clinical journey.

Runtime-log counts remain unavailable: the approved Vercel connection returned
**403** for a bounded error/fatal grouped query. Its project-scoped CLI fallback
stalled and was stopped after verifying exact approved project/team arguments;
no login, permission or account change was attempted. Project-scoped drain
inventory returned **zero drains**. No clean runtime-log scan or active external
error monitor is claimed; no new paid integration/alert was provisioned.

## Authority and target

The owner authorized proceeding with the remaining release/verification work
after being told the chat upgrade needed commit, push and deployment. This is
fresh approval for modern chat and private account history; it is not authority
to modify real clinical records, change provider privacy settings, create
unrelated infrastructure, or access another service account.

- GitHub: `Mahim2077/HealthLink`, `main`, authenticated account `Mahim2077`.
- Vercel: approved `Mahim2077` connection, `mahim2077s-projects`, `healthlink-sd`.
- Project: `prj_kQyhfaS1tFS7NXlUMYr9C0FA8W5f`.
- Team: `team_l9GeumDweBdowhhoxPfAS0yM`.
- Production: `https://healthlink-sd.vercel.app/`.
- Previous application: `2bb55b8`; previous production schema: `0030_doctor_locations`.

## Release contents

Approved sidebar / wide transcript / compact records control, private saved
conversations and deletion, bounded server-owned follow-up context, idempotent
retry, per-request record consent, and preserved explanation-only AI policy.
See `AI_CONVERSATIONS_2026_10_19.md` and `../design-qa.md` for implementation,
retention limits and synthetic local browser evidence.

Migration `0031_ai_conversations` adds two tables and indexes only. It does not
alter or delete existing clinical records. A rollback must not drop these tables
or erase newly saved conversations; any rollback requires a deliberate decision.

## Preflight / current state

- Approved GitHub identity and Vercel project/team reverified through the named
  connections. Remote main matches local baseline `ead76e4` before release.
- Fresh backend: **564 passed**, zero skipped; one existing upstream warning.
- Fresh frontend: **57 files / 266 tests**, lint, TypeScript and optimized build passed.
- Local Alembic head `0031_ai_conversations`; no metadata drift; `pip check` passed.
- Prior optimized-build browser acceptance: **9/9 Edge journeys**, synthetic
  local PostgreSQL and mock AI only.
- Secrets remain in existing private environments. No AI key/database password
  is being added to source/reports; no environment change is needed.

Production migration, deployment and promotion are **not yet confirmed** at this
preflight checkpoint. They must run through the existing CI lifecycle:
quality → approved-target/stale-head checks → migration → build/stage → protected
smoke → stale-head check → promotion → stable-domain smoke.

After promotion, record exact commit/run/deployment evidence and the real scope
of verification. A successful deployment does not itself prove a live AI answer,
authenticated patient workflow, clinical safety or clean runtime logs.
