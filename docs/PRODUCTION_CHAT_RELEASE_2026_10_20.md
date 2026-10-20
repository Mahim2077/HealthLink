# Modern AI chat production release — 2026-10-20

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
