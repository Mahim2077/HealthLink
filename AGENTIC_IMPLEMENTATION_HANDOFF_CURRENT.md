# HealthLink current agentic implementation handoff

> **Status date:** 2026-10-22
> **Read this file first.** It is the authoritative operational checkpoint for
> the current workspace. Older implementation prompts and handoffs remain useful
> for architecture/history, but this file supersedes their phase-start, storage,
> scheduler, route, and release-state statements wherever they conflict.

## 1. Resume point

```text
Workspace:              D:\HealthLink_V_1
Repository:             https://github.com/Mahim2077/HealthLink
Production:             https://healthlink-sd.vercel.app/
Branch:                 main
Released app commit:    21e94a5372f6cbf29d71f12fa85e4fa069930ea1
GitHub Actions run:     39398090813 (successful, 4m 29s)
Released DB head:       0031_ai_conversations
Released roadmap:       Original Phases 0-31; earlier Phase 32 saved-chat increment released
Current release:        Modern chat + private history committed, pushed and deployed to stable production
Local QA DB head:       0031_ai_conversations (synthetic loopback database only)
Implementation commit:  5de35ffb285b74535f2eece623a6c16310a3f68b
Local release scope:    Phase 32: Settings/themes + dependency/CI security + post-31 documentation
Release authority:      Owner explicitly authorized document/commit/push/deploy on 2026-10-22
Next work:              Complete authorized Phase 32 CI release and stable-origin verification
```

## Phase 32 designation and release authority

The owner designated **all post–Phase 31 continuation as Phase 32**: earlier
saved-chat/history, Settings/UI/themes, dependency/CI hardening, QA and handoff/
portability updates. See `docs/PHASE_32_POST_ROADMAP_UPGRADES.md`. Preserve dated
history and migration identifiers; `0031_ai_conversations` must not be renamed.

The same 2026-10-22 instruction authorizes this Phase 32 commit, push and release,
superseding earlier local holds below for this release only. Account restrictions,
clinical-data safety and CI safeguards remain mandatory. Release is pending until
confirmed in `docs/PRODUCTION_PHASE_32_RELEASE_2026_10_22.md`; push is not deployment.

Recent local and historical release context:

### Latest local continuation — dependency integrity fixes (unreleased)

After the full integrity audit, the owner authorized careful fixes, not a
release. See `docs/DEPENDENCY_REMEDIATION_2026_10_22.md` and
`docs/DEPENDENCY_SECURITY.md` for current commands and exact limits.

- Next.js/matching lint config now 16.4.2; Vitest 4.1.12, jsdom 30.1.3 and
  affected transitive packages updated. React and existing feature logic remain
  unchanged. Actual frontend verification used Node 24.20.0.
- Python runtime and development/tooling inputs/locks are separated. Both
  generated locks pin all versions and SHA-256 hashes with universal platform
  markers. The generator is uv 0.12.7, matching CI. Unaffected direct dependencies
  retain the tested versions; security floors patch certifi/PyJWT/Pillow/Mako/
  urllib3 and development pytest/pip. Runtime excludes test/security tools.
- Python runtime/dev advisory scans passed; an independent OSV check of all
  103 locally installed packages found zero matches. Frontend production audit
  has zero advisories. **The full npm scan is not completely clean:** one
  unpatched upstream dev-only `braces@3.0.3` advisory remains, inherited by five
  package entries. Its exact-version exception expires 2026-11-21. Do not call
  it patched or silently extend the exception. Production receives no exception.
- CI now verifies lock freshness, hash-enforced installs and fail-closed Python/
  npm advisory gates. Actions are immutable SHA-pinned; all checkouts disable
  persisted Git credentials. Release ordering, stale-head/account guards and
  non-cancelling migration-to-promotion lock are unchanged. No scheduled workflow.
- Fresh local QA: **567 backend tests**, **298 frontend tests**, **10 security-gate
  tests**, lint/typecheck/optimized build and **14/14 browser journeys**. Final
  release/security contracts also passed separately (15 tests). Migration head
  remains `0031_ai_conversations`, no schema drift. One pre-existing TestClient
  deprecation warning remains. Linux-target runtime resolution passed as a dry run.
- Prior Settings/theme/chat/clinical work is preserved. No migration, live AI
  call, production mutation, commit, push or deployment. GitHub Actions itself
  has not run on these local changes. Previous production operational assurance
  gaps remain gaps, not failures proved or fixed by dependency upgrades.

### Latest local continuation — Settings and UI upgrade (unreleased)

The owner requested a portal-wide UI inspection, Settings plan and implementation,
then explicitly approved automated Edge/Playwright QA with synthetic local data.
No release authorization was given for this new work. Do not interpret earlier
chat-release approval as permission to commit, push or deploy these changes.

- Citizen, professional and admin Settings now have Account, Security and Display
  sections. Citizen-only Privacy & sharing reuses existing grants/access history;
  verified doctors get Practice hours. Lab/pending/rejected roles cannot open the
  schedule editor. No permission expansion, new schema or migration.
- Citizen profile/identity and one-time NID confirmation remain intact inside
  Settings. `/citizen/profile` and `/citizen/privacy` redirect to their Settings
  sections. Professional verification status remains accessible from Account.
- Practice editor moved from the daily doctor dashboard, with a clear shortcut,
  corrected overview copy and an unsaved-changes guard.
- Settings exposes existing current/all-session sign-out with confirmations and
  retry feedback. Existing backend revocation remains authoritative.
- Display choices (Light/Dark/System theme, larger text, reduced motion, default desktop sidebar) are
  allowlisted, non-sensitive browser-only preferences, not account-synced. No
  medical records/tokens/identity drafts are persisted in browser storage.
- Shared header/navigation is slimmer; mobile menu now traps/restores focus,
  makes its background inert and locks scrolling. Result tables are keyboard
  scrollable; wide report tables have a mobile scrolling hint.
- Audit found/fixed the admin citizen-identity detail route's synchronous use of
  Next.js async params. Browser regression now loads the correct synthetic user.
- AI chat, saved history/delete, explicit per-request record consent, specialist/
  nearby doctor search, hidden facility coordinates, merged diagnostics and
  generated-on-demand PDFs are preserved. No scheduled workflow was reintroduced.

Verified locally: **564 backend tests** (prior unchanged-backend baseline),
**61 frontend files / 298 tests**, lint/typecheck/optimized build, and
**14/14 optimized-build browser journeys**, including the full care journey in dark mode.
Baseline audit captured 38 screens at desktop/mobile sizes, followed by 53
post-change screens, final Settings/dashboard recaptures, and clinical editing
captures. Tested widths include 320/390/768/1366/1920 where applicable; larger text,
storage failures, role gates and all-session revocation have regression coverage.
No unexpected API/console errors or external browser requests in the final suite.
One pre-existing Starlette/httpx deprecation warning remains in backend tests.

The owner additionally requested light/dark mode. Settings → Display & accessibility
now provides **Light / Dark / Use system setting**. Light remains the compatible
default for existing users. Theme choice uses the same versioned browser-only
allowlist; saved theme is applied by a static trusted head bootstrap before body
paint. System mode follows live OS changes; other tabs synchronize through storage
events. Shared surfaces, role colors, statuses, native fields, validation and AI
chat are themed without image inversion or changing clinical behavior. Screen-only
dark styling leaves printing light; generated PDFs and APIs are unchanged.

Read `docs/UI_SETTINGS_AUDIT_2026_10_20.md` and the latest `design-qa.md` entry.
Raw synthetic screenshots/review sheets are ignored under
`.runtime/ui-settings-audit/`; browser results under `.runtime/browser-qa/`.
The optimized local preview uses Next on 3003 plus the loopback Services proxy on
3001 and mock API on 8001. The API uses QA PostgreSQL on 55433, not production.
Production remains the released modern-chat commit above. The pre-existing
production runtime-log/monitoring gap remains unresolved and out of this task.

**Released modern-chat continuation:** see `docs/AI_CONVERSATIONS_2026_10_19.md` and the
latest `design-qa.md` entry. The owner approved the hybrid conversation sidebar /
wide transcript / compact records control and explicitly requested private
account persistence with delete controls. This changes the earlier no-chat-storage
decision for the conversation UI only. Provider architecture, explanation-only
safety, finalized-record authorization and per-request consent remain unchanged.
The owner's separate 2026-10-20 “okay, proceed” authorized this release.
Migration `0031_ai_conversations`, staging, protected smoke, promotion and stable
smoke all passed. Modern chat is live at the stable production origin. A real
citizen login, two General-mode Groq answers, history after refresh/reopen, and
New conversation were verified without reading/sending personal medical records.
The provided Doctor and Admin logins and role dashboards also passed; no clinical
or administrative records were changed during those checks.
See `docs/PRODUCTION_CHAT_RELEASE_2026_10_20.md` for exact evidence and limits.

```text
fa07edf  feat(clinical): complete phases 15 through 17
6ca19f6  feat(clinical): complete phases 18 through 21
cb075e2  docs(phase-21): record production verification [skip ci]
c8d2f26  feat(platform): modernize discovery and clinical workflows
5de35ff  feat(platform): complete phases 22-31 with Groq AI and safe releases
2bb55b8  fix(ci): authenticate protected staged deployment smoke checks
```

The earlier baseline was released before the 2026-10-17 local continuation. The
later AI/dashboard/security work was unreleased at the start. On 2026-10-18 the owner explicitly
authorized commit, push and deployment, supplied a production Groq key and
requested private environment configuration. This supersedes the prior release
hold for this release only. See `docs/PRODUCTION_RELEASE_2026_10_18.md` for status.

### Account restriction — mandatory

Use only GitHub **Mahim2077**, repository **Mahim2077/HealthLink**, and the Vercel
**Mahim2077** connection, team **mahim2077's projects** (`mahim2077s-projects`),
project **healthlink-sd**. Never inspect/use another available account without
asking the owner. The linked project ID and team ID were verified through the
approved connection. An explicit-team connector query misleadingly returned 404;
account-level lookup returned the exact same project and team. No account switch
or replacement project was needed.

### Latest release result — deployed successfully, bounded checks passed

After the owner resumed Supabase, migration passed. The first staged smoke hit
Vercel Authentication, correctly preventing promotion. CI-only fix `2bb55b8` uses
the existing Vercel CLI identity for staged probes; the public stable-domain
probes remain anonymous. No protection downgrade or alternate account was used.

Actions **39058877324** succeeded: **555 backend tests**, **263 frontend tests**,
lint/typecheck/build, production migration `0030`, staged smoke, promotion and
stable smoke. Vercel stable-origin lookup confirms application `2bb55b8`, READY
deployment **dpl_AsYMM369iNxaNwbWdcij4zn4nQRA**. CI smoke passed 18 probes and an
independent stable-domain pass completed 9/9 probes. Source/log Groq-key-pattern
scans were clean; no key file or frontend variable was introduced.
Credential-free headless Edge also checked the public sign-in controls at four
widths with zero document overflow/browser exceptions; screenshot inspected.

Production-only Groq configuration is saved, but **authenticated production
journeys/live AI remain unconfirmed automatically**: the browser runtime and
secure-input path were unavailable. Do not weaken password input or transfer
real records to get a test to pass. Owner manual General-mode confirmation was
requested. Runtime-log access returned 403; zero drains were listed, so no clean
log review or monitoring guarantee is claimed. See
`docs/PRODUCTION_RELEASE_2026_10_18.md` for the receipt and exact limits. Earlier
blocked/unreleased statements in later historical sections are superseded here.

## 2. Mandatory reading order

1. This file.
   Latest release: `docs/PRODUCTION_RELEASE_2026_10_18.md`. The preceding audit/repair evidence is in `docs/PHASE_31_INTEGRITY_AUDIT_2026_10_17.md` and `docs/PHASE_31_LOCAL_RELEASE_REPORT.md`; their release blockers were corrected.
2. `frontend/AGENTS.md`.
3. `AGENTIC_IMPLEMENTATION_HANDOFF_PHASES_0_TO_14.md` for the historical base.
4. The end of `docs/implementation-progress.md` for Phases 15–21 and the latest
   product-release evidence.
5. The `HealthLink doctor discovery and nearby-location flow` section in
   `design-qa.md`.
6. `docs/implementation-assumptions.md` and
   `docs/VERCEL_GITHUB_ACTIONS_DEPLOYMENT.md` when touching infrastructure.
7. The complete current `git status --short` and `git diff` before editing.
8. The original Phase 15–31 continuation prompt for still-valid future roadmap,
   authorization, privacy, and quality rules. Do not follow its stale Phase-14
   resume point or its superseded PDF/reminder assumptions.

Secrets and production test credentials are intentionally absent. Obtain them
out of band only when the owner authorizes production work. Never write them to
source, documentation, fixtures, screenshots, commands that will be logged, or
handoff files.

## 3. Released system through Phase 21

### Phases 15–17

- Medical history is a paginated, derived timeline over authoritative visits,
  prescriptions, and diagnostic records; there is no duplicate history table.
- Doctors create structured diagnostic-test requests for the current patient.
- Verified lab technicians use role/facility/assignment-gated workflows.
- Finalized lab results are structured, immutable, citizen-readable, and feed
  unit-separated numeric trend tables.

### Phases 18–21

- Citizens own an emergency profile; current doctors receive a read-only view.
- Reminder schedules and durable in-app notifications exist as product data.
- Sensitive clinical reads/mutations create metadata-only audit entries; raw
  medical text and national identifiers are not copied into the audit log.
- Citizens can create, expire, and revoke scoped historical-read grants.
- `ClinicalReadPolicy` centralizes citizen-self, CURRENT-patient, authorship, and
  manual-grant reads. Read authorization never grants mutation.
- Production database and Vercel release are verified through migration
  `0029_access_grant_scopes`.

## 4. Released post-Phase-21 product improvements

### 4.1 Modern doctor discovery

The old analog doctor finder was replaced with a specialty-first hybrid design.

Implemented behavior:

- one unified name/specialty/facility search;
- six common specialty shortcuts and a complete normalized specialty catalog;
- weekday and facility filters;
- active-filter chips and a single clear action;
- five sort modes: best match, earliest practice, nearest, doctor name, facility name;
- meaningful specialization and qualification fields;
- responsive desktop results table and mobile result cards;
- existing booking and doctor-detail paths preserved.

Nearby behavior:

- Choosing `Nearest facility` opens an explicit location-choice modal before any
  browser geolocation request.
- Approximate browser coordinates are rounded before transport, remain only in
  component memory, and are never written to browser storage.
- Manual search uses the bundled bilingual Bangladesh dataset with 64 zila
  choices and dependent upazila choices.
- Distance is computed in backend logic and returned only as a human-readable
  distance. Exact coordinate fields are not present in public/admin DTOs.
- Near-exact matches display `Less than 1 km away`, not `0 km`.

Facility administration:

- Facility registration address remains a human-readable string.
- Only admins confirm the submitted address with zila/upazila and the backend
  geocoded match.
- A facility participates in nearest sorting only after confirmation.
- Latitude and longitude are private backend fields. Never expose them in user
  interfaces, API responses, logs, or documentation.

Primary files:

```text
backend/alembic/versions/0030_doctor_discovery_locations.py
backend/app/locations/
backend/app/facilities/geocoding.py
backend/app/facilities/{models,schemas,service}.py
backend/app/doctors/{repository,routes,schemas,service}.py
backend/app/admins/{routes,verification_schemas,verification_service}.py
backend/app/professionals/{constants,models,schemas,service}.py
frontend/src/components/citizen/doctor-search.tsx
frontend/src/components/admin/facility-manager.tsx
frontend/src/components/admin/professional-verification-detail.tsx
frontend/src/lib/doctors/
frontend/src/lib/locations/
```

Migration `0030_doctor_locations` adds:

- facility district/upazila codes;
- private latitude/longitude;
- PENDING/CONFIRMED location status, matched address, and confirmation time;
- location bounds/status constraints and area index;
- doctor specialization and qualification plus specialization index.

This migration passed the clean PostgreSQL CI gate and was applied to
production before the Vercel deployment was promoted.

### 4.2 Citizen diagnostics and lab results merged

The citizen now has one section named `Diagnostic tests` for:

- test requests and status;
- finalized result access;
- numeric result trends.

Compatibility is intentional:

```text
/citizen/lab-reports             -> /citizen/diagnostic-tests
/citizen/lab-reports/{test_id}   -> /citizen/diagnostic-tests/{test_id}
/citizen/lab-trends              -> /citizen/diagnostic-tests#result-trends
```

These are permanent redirects. The duplicate `Lab reports` navigation item was
removed. Do not create a second citizen results section again.

Primary files:

```text
frontend/src/components/diagnostics/
frontend/src/app/citizen/diagnostic-tests/
frontend/src/app/citizen/lab-reports/
frontend/src/app/citizen/lab-trends/page.tsx
frontend/src/components/auth/portal-navigation.tsx
```

### 4.3 Consultation notes merged with prescriptions

The doctor consultation workspace now treats the clinical record and
prescription as one unit:

- chief complaint, diagnosis, clinical notes, follow-up instructions,
  medicines, diagnostic information, advice, and notes share one form;
- one request atomically updates visit clinical fields and the structured
  prescription;
- medicines are optional;
- an entirely blank medicine row is ignored;
- partially completed medicine rows are rejected;
- the unified dirty/saving state blocks accidental appointment completion;
- finalized visit clinical fields remain immutable.

The current-patient history exposes prior prescriptions to doctors:

- the centralized clinical-read dependency still decides access;
- a current or otherwise authorized doctor can review past prescriptions;
- only the author doctor receives `can_edit=true`;
- non-author historical views are read-only;
- citizen self-access remains read-only.

Primary files:

```text
backend/app/prescriptions/{schemas,service,routes,repository,pdf,models}.py
frontend/src/components/prescriptions/prescription-panel.tsx
frontend/src/components/prescriptions/prescription-page.tsx
frontend/src/components/professional/consultation-workspace.tsx
frontend/src/components/medical-records/medical-history-timeline.tsx
frontend/src/lib/prescriptions/
```

### 4.4 Prescription PDFs are generated on demand

Current intended behavior:

```text
authorized GET /api/v1/prescriptions/{id}/pdf
    -> reload authoritative structured visit/prescription
    -> render fresh PDF bytes in memory
    -> stream with private/no-store semantics
    -> persist nothing
```

Do not restore the previous save/upload/document-pointer flow.

- `backend/app/prescriptions/storage.py` is deleted.
- `backend/tests/test_prescription_storage.py` is deleted and replaced by
  on-demand generation coverage in `test_prescriptions.py`.
- The Python Vercel Blob dependency and prescription-storage environment
  settings are removed.
- Response DTOs no longer expose PDF-availability/file metadata.
- The old `PrescriptionDocument` ORM and `prescription_documents` table remain
  only to keep the existing migration chain compatible. New code neither reads
  nor writes them.
- Existing production Blob objects/legacy rows have not been destructively
  removed. Cleanup would require a separate reviewed operation and explicit
  owner authorization.

### 4.5 GitHub reminder scheduler removed

`.github/workflows/reminders.yml` is deleted from `main`.

Reason: its five-minute `schedule` event created GitHub workflow-run records
before the job-level `REMINDERS_ENABLED` guard was evaluated, so disabled jobs
still cluttered the Actions history.

After release:

- no new scheduled reminder Action runs should be created;
- historical Actions entries remain unless separately deleted;
- citizen reminder configuration and existing data remain;
- no background worker is scheduled, so new in-app reminder notifications are
  not delivered automatically.

Do not recreate a reminder scheduler unless the owner explicitly requests it.

## 5. Authorization invariants that must not regress

- Portal sessions are isolated as CITIZEN, PROFESSIONAL, or ADMIN.
- A professional session selects one exact role-registration context.
- VERIFIED role state is required for clinical capability.
- Frontend guards are UX only; backend dependencies are authoritative.
- NID/BCN do not belong in JWTs, URLs, logs, public DTOs, PDFs, or AI prompts.
- CURRENT queue context grants temporary clinical access only to the exact
  doctor-role registration and patient.
- Manual grants extend historical reads; they never create CURRENT context and
  never authorize writes.
- Prescription read, prescription edit, and PDF generation are separate
  authorization decisions. Author-only edit remains strict.
- Lab assignment/role/facility gates and finalized immutability remain strict.
- Clinical audit entries contain access metadata, not copied clinical payloads.
- Coordinates are sensitive implementation details and must remain backend-only.

## 6. Verification and production release evidence

Latest complete local gates:

```text
Backend pytest:          285 passed, 38 skipped
Frontend Vitest:         52 files, 239 tests passed
ESLint:                  passed
TypeScript:              passed
Python AST parsing:      178 files passed
git diff --check:        passed; existing CRLF normalization warnings only
Next.js production build: passed
```

The 38 local backend skips are explicit environment-gated PostgreSQL suites,
not test failures. GitHub Actions subsequently ran the canonical clean
PostgreSQL migration and backend gates successfully.

Browser acceptance used synthetic local data only and verified:

- doctor discovery desktop layout at approximately 1440 × 1050;
- responsive mobile cards at 390 × 844 with no horizontal overflow;
- explicit approximate-location choice;
- Dhaka → Savar manual nearby search and distance ordering;
- no visible latitude/longitude/coordinate language;
- the unified consultation/prescription editor;
- previous-prescription navigation for the current patient;
- non-author read-only historical content;
- automatic freshly generated PDF preview;
- successful prescription and PDF API responses;
- no stored document row after regeneration;
- no Next.js error overlay.

Release commit `c8d2f26` passed GitHub Actions run `34915012756` in 4m 24s:
backend quality gates, frontend quality gates, production migration, Vercel
deployment, and deployment smoke tests all succeeded. The stable `/health`
endpoint returned `healthy` for the production environment.

Read-only production browser acceptance verified Citizen, Doctor, and Admin
login/routing, specialty-first doctor search, all five sort options, explicit
nearest-location choice, 64 bilingual zila choices with dependent upazila,
unified Diagnostic tests plus the legacy redirect, the combined consultation
and prescription editor, prior-prescription navigation, and a fresh `blob:` PDF
URL after reloading the historical record. No coordinate label/value appeared
in the Citizen or Admin interface, and the browser console contained no warnings
or errors.

## 7. Current source tree cautions

Release commit `c8d2f26` intentionally deleted:

```text
.github/workflows/reminders.yml
backend/app/prescriptions/storage.py
backend/tests/test_prescription_storage.py
```

These deletions are released product decisions, not files to restore.

Local ignored `.runtime`, `.env`, and `.vercel` material may exist. Preserve it,
do not enumerate or expose secrets unnecessarily, and never commit it.

## 8. Release procedure for future changes

The latest release is complete. For every future external release, obtain fresh
owner authorization, run the full quality/migration gates, let GitHub Actions
apply production migrations before Vercel promotion, verify the stable domain,
and record exact evidence without including secret values.

## 9. Phases 22–27 local implementation and next work

Phases 22–27 are implemented locally but are not yet committed, pushed,
deployed, or enabled in production. Do not describe them as released. The owner
authorized parallel development through Phase 27, not an external release.

Implemented foundation:

- `app/ai/` provides one provider protocol, a deterministic mock, a native
  Google GenAI adapter, and a direct GroqCloud strict-JSON adapter;
- provider selection is environment-driven through `AI_PROVIDER`; no provider
  key or vendor name is coupled to a route;
- `POST /api/v1/citizens/me/ai/guidance` is citizen-self only and requires the
  caller to explicitly set `use_my_health_records: true`;
- record context includes only bounded finalized visits, prescriptions, and
  diagnostic reports plus the citizen's emergency profile and coarse age band;
- direct identity/address/contact/database-key fields are omitted; common
  NID/BCN-like numbers, emails, phones, UUIDs and known citizen identity terms
  embedded in free text are redacted. This reduces identity exposure but does
  not guarantee anonymization of arbitrary medical free text;
- stored medical text and the citizen question are delimited as untrusted data;
- output is schema-validated and scanned for diagnosis, prescribing, and
  treatment-change language before it can reach the caller;
- every retrieved AI context creates a metadata-only `AI_ACCESS` audit event;
  prompts, questions, record text, and model responses are never logged;
- timeouts, provider failures, and rate limits are centrally mapped to safe API
  errors without exposing SDK or provider detail;
- CI explicitly keeps AI disabled and uses no external model calls or spending.

Configuration is disabled by default:

```text
AI_ENABLED=false
AI_PROVIDER=groq
AI_API_KEY=
AI_MODEL=qwen/qwen3.8-27b
AI_RECORD_CONTEXT_ENABLED=false
AI_TIMEOUT_SECONDS=20
AI_MAX_INPUT_CHARACTERS=12000
AI_MAX_CONTEXT_RECORDS=10
```

`AI_API_KEY` is server-only and redacted from settings representation. Never
create a `NEXT_PUBLIC_` AI secret. Provider adapters are cached on app state,
not instantiated ad hoc per route. Groq's HTTP clients are cancellation-safe
per-request resources; the native Gemini client is reused by its adapter.

The Google Gemini API is technically compatible. However, its
[current terms](https://ai.google.dev/gemini-api/terms), reviewed 2026-10-02,
say not to submit sensitive/confidential/personal information to unpaid services
and prohibit clinical-practice/medical-advice use. User consent or removing a
name alone does not resolve these restrictions. A paid account changes data-use
terms but does not remove the medical-use restriction. Keep real patient data
out of Gemini free-tier testing. Review the informational scope, age restrictions,
provider terms and health-data obligations before enabling a production provider.
All verification uses synthetic data and deterministic mocks/in-memory HTTP,
not external model requests.

Historical Phase-22-only evidence (superseded by the complete Phase-27 gates):

```text
Focused Phase-22/config tests: 18 passed
Complete backend suite:        297 passed, 38 PostgreSQL-only skipped
Python bytecode compilation:   passed
pip dependency check:          passed
Gemini structured config:      constructed successfully with google-genai 1.75.0
```

No database model or migration changed. The existing clinical audit table stores
the new `AI_ACCESS` metadata.

Complete Phase-27 + Groq local verification (2026-10-02):

```text
Complete backend suite:        437 passed, zero skipped (local PostgreSQL 17.6)
Focused Groq/config suite:     53 passed (HTTPX in-memory transport only)
Frontend suite:                55 files / 252 tests passed
Frontend lint/typecheck/build: passed before backend-only Groq changes
Alembic head/check:            0030_doctor_locations / no metadata drift
pip check / compileall:        passed
git diff --check:              passed
Live external model calls:     zero
```

Browser acceptance used an isolated synthetic citizen/records and mock AI:
general/record-aware chat, per-request consent reset, symptom guidance and its
narrow emergency safeguard, optional history summary, prescription explanation,
and finalized diagnostic explanation passed. Original medicines/results/ranges
remained visible and authoritative. Metadata-only AI_ACCESS records were confirmed
for context/prescription/report reads; no console errors or narrow-viewport
horizontal overflow occurred. The temporary ignored QA launcher on port 8001
forces mock settings; use normal `app.main:app` plus `backend/.env` and restart
the backend for a future approved Groq synthetic-data check. Actual key validity,
model access/quota, Bangla/medical response quality and real-data suitability are
not verified. The local virtual environment's missing declared Gemini dependency
was installed (google-genai 1.75.0) before the clean final test run. The suite
reported one upstream Starlette/httpx deprecation warning, not a test failure.

### Phases 23–27

- Phase 23: `POST /api/v1/ai/prescriptions/{id}/explain` uses the existing
  prescription-read policy. Recorded medicine instructions are assembled by the
  server, not invented by the model. Missing medicine-specific purpose is stated
  as missing and referred to a clinician/pharmacist. AI cannot update records.
- Phase 24: `POST /api/v1/ai/lab-reports/{report_id}/explain` requires an
  authorized FINALIZED report. Results/ranges/units/flags remain server-owned;
  the model must explain each supplied parameter exactly once. Citizen detail
  URLs use the diagnostic-test ID, but this API takes the report ID.
- Phase 25: `POST /api/v1/ai/medical-history/summary` requires citizen-self
  consent. `/ai/patients/{citizen_id}/medical-history/summary` also supports
  current doctors or a valid FULL_MEDICAL_HISTORY grant through ClinicalReadPolicy.
  Context is bounded and output source-labelled, never saved as a clinical record.
- Phase 26: `/citizen/ai-assistant` and `POST /api/v1/ai/chat` have explicit
  GENERAL and RECORD_AWARE modes. GENERAL loads zero clinical records.
  RECORD_AWARE requires per-request opt-in and uses only the authenticated
  citizen's finalized records. No client-supplied patient/resource scope is trusted.
- Phase 27: `POST /api/v1/ai/symptom-guidance` loads no clinical records and
  returns structured informational guidance/red flags/next steps/urgency.
  It is not a diagnostic or medically validated triage tool.
- At this historical checkpoint AI responses were component-memory only.
  The separately approved 2026-10-19 chat upgrade now stores conversations
  privately in the database with delete controls. It still introduces no browser
  chat storage, stored PDF or automatic clinical write.
- UI places AI explanations below authoritative prescription/lab content;
  optional summary stays secondary to the medical-history timeline.
- Deterministic schema/safety checks are defence in depth, not proof of clinical
  accuracy. Source-category checks cannot prove every model statement true.

See `docs/AI_LOCAL_DEVELOPMENT.md` for safe local configuration and known limits.
At this historical checkpoint the next work was Phase 28. The owner subsequently
authorized local continuation through the remaining phases, while withholding
deployment approval. See section 9.1 for the latest state.

### GroqCloud selected and implemented locally (2026-10-02)

After discussing Llama and Qwen 3.8, the owner explicitly requested configuring
GroqCloud. `AI_PROVIDER=groq` and `AI_MODEL=qwen/qwen3.8-27b` are now the disabled
defaults/templates. Mock/Gemini remain replaceable alternatives. `AI_API_KEY`
remains server-only; no real key/account settings have been read or changed.

`GroqAIProvider` uses existing HTTPX directly, a fixed HTTPS endpoint, separate
system/user messages, strict nested/nullable JSON schemas, one bounded completion,
no retries/redirects/environment proxies/tools, cancellation-safe HTTP cleanup,
and shared Pydantic/safety/grounding checks. Qwen thinking is disabled. A model
override must support Groq strict-schema mode; no unsafe automatic fallback.
When AI is disabled the factory still returns the no-network mock. Backend/UI
contracts, consent scopes, identity reduction and audit metadata are unchanged.

Qwen is currently a preview model. Real key/model access, free-tier quota,
real-model behaviour and medical accuracy are unverified. Tests use in-memory
HTTP interception only. Groq's medical-use/PHI terms and account-level data
controls need review before any real-patient rollout. No external model
requests, agreement acceptance, production enablement or release occurred.

Sources reviewed 2026-10-02:
[model catalog](https://console.groq.com/docs/models),
[structured outputs](https://console.groq.com/docs/structured-outputs),
[data controls](https://console.groq.com/docs/your-data),
[service agreement](https://console.groq.com/docs/legal/services-agreement).

### Latest owner clarification: explanation-only AI (2026-10-02)

The AI must explain medical information and recorded conditions/prescriptions,
not diagnose, prescribe or replace a doctor. Canonical system policy is
`backend/app/ai/policy.py`, used by both Groq and Gemini. Requests for medicines,
new schedules or treatment changes must be refused; general education remains
allowed. No model may infer a patient's diagnosis from medicine choices or guess
why their doctor selected a medicine.

Prescription requests include the authorized visit's recorded condition and
optional provider `medicine_education` keyed to existing item numbers. Reject
duplicate/foreign medicine numbers. The server still owns medicine names,
original instructions and unknown per-medicine rationale; the UI separates
general knowledge from confirmed doctor intent. No clinical writes or migrations.

The Phase 21–27 integrity review found a diagnosis/prescribing bypass in the old
name-list guards. The owner's clarification authorized policy/guard fixes and
regression tests. Latest **476 backend tests passed, zero skipped** on isolated
PostgreSQL; **55 frontend files / 252 tests**, lint, TypeScript, production build
and whitespace checks passed. One upstream Starlette/httpx warning remains.
Fresh browser acceptance of this latest UI change is **pending** because the
controller timed out twice binding the existing mock-preview tab. Earlier
browser results above are historical. Live Groq/Gemini quality, especially
medical/Bangla behaviour, remains unverified. Conservative text checks can have
false positives and cannot guarantee semantic safety.

No live provider requests, real patient data transfer, commit, push, deploy or
production enablement occurred. The continuation below supersedes this earlier
Phase-28 starting point; fresh browser/release acceptance remains outstanding.

## 9.1 Phases 28–31 local continuation (2026-10-17)

The owner requested upgrading/fixing through the final phase without replacing
the approved product novelties. They explicitly deferred production deployment.
No commit, push, production migration, live model request or deployment occurred.

Implemented locally:

- `backend/app/dashboards/` and `frontend/src/components/dashboards/` add real,
  bounded citizen/doctor/lab/admin overview data within the existing design.
  Backend portal/selected-role/active-admin checks remain authoritative.
  Citizen projections are self-only and link finalized prescriptions/reports;
  doctor chambers show serial/count metadata, not patient narrative/identity.
  Lab projections require exact assignment and active facility, with no chamber.
- Dashboard waiting/current projections exclude cancelled appointments and
  doctor/facility/date mismatches. Completed sessions cannot report waiting work.
  Existing chamber/consultation/schedule workflows are not changed by reads.
- Diagnostic queues are paginated with `page`, `page_size`, `has_next`, stable
  ordering and UI previous/next controls. Assignment updates preserve metadata.
- CURRENT-patient access now explicitly requires matching selected doctor,
  BOOKED appointment, ACTIVE session, coherent facility/date and CURRENT entry.
- Login/refresh and authenticated responses use private/no-store; API nosniff
  remains set. Validation inputs and SQL bound values are redacted from relevant
  error representations. The admin UI searches identities using a POST body;
  the deprecated GET remains for compatibility and still needs access-log review.
- Session-keyed dashboard subtrees and effect cleanup prevent stale role/session
  responses from rendering. Retry states do not fabricate zero counts.
- `backend/tests/test_release_journey.py` adds synthetic HTTP/database acceptance
  through care/report finalization, source dashboard links, trends, private PDF
  regeneration, role isolation and authorized mock explanations. It is not a
  browser test and makes no external model calls.
- `scripts/smoke_release.py` and the existing Actions workflow prepare future
  read-only checks of both the generated URL and stable production domain. They
  are not run against production in this continuation.

Operational documents:

- `docs/SECURITY_PERMISSION_MATRIX.md`: formal authority/resource/logging matrix,
  corresponding regression files, input caps and explicit production limitations.
- `docs/PHASES_28_31_RELEASE_READINESS.md`: exact phase state, preserved features,
  automated versus historical browser evidence, pending acceptance, release and
  rollback checklist. Read this before resuming QA or proposing a release.

Fresh automated evidence is recorded at the end of `docs/implementation-progress.md`.
The new backend has no model/migration changes; head remains
`0030_doctor_locations`, with no Alembic metadata drift.

Fresh 2026-10-17 gates: **514 backend tests passed, zero skipped** (including
isolated local PostgreSQL cases); **56 frontend files / 261 tests passed**;
frontend lint/typecheck/production build, Alembic check, pip check and bytecode
compilation passed. One upstream Starlette/httpx deprecation warning remains.
The first backend run hit a Windows temp-directory permission error after 513
passes; a complete rerun with a new ignored workspace temp root passed all 514.
Use `-p no:cacheprovider` and a fresh `PYTEST_DEBUG_TEMPROOT` if stale host temp
permissions recur. Do not delete or change ACLs on the user's global temp tree.

Phase 30 is **not fully signed off**. Native browser tooling failed, but the owner
authorized headless Playwright through the working terminal. Fresh Edge QA on
2026-10-17 completed: **6 passed, 1 failed, zero skipped** (46 seconds), with
synthetic local accounts, actual frontend/API/database requests and mock AI only.
Citizen/doctor/lab/admin journeys, finalization, privacy/consent and four viewport
sizes ran; the failed final case reproduces two application defects:

- Opening a chamber commits before first-patient promotion; response shows
  CURRENT but the next request sees WAITING. Refresh + Call next is a tested
  workaround, not a fix. Keep activation/promotion in one locked transaction.
- Record-sharing doctor picker matches first/last names separately and misses a
  displayed full name. Unique-surname search works; add safe full-name matching.

No application code was changed during this testing request. Added repeatable
`scripts/browser-qa/`; report, reproduction/source evidence, limitations and
release implications are in `docs/BROWSER_QA_2026_10_17.md`. Ignored HTML/PNG/JSON
evidence lives in `.runtime/browser-qa/`. Historical runtime-blocker statements
above are superseded by this successful alternative runtime, not by clean QA.
Fix the defects with regression coverage before claiming browser sign-off.

Phase 31 is **release preparation only**, not a completed production release.
The owner subsequently authorized a temporary live Groq check with synthetic
local records. Authentication and configured Qwen availability passed; four UI
chat cases succeeded (English, Bangla, prescribing refusal and record awareness).
The fifth request received HTTP 429, so remaining live cases were not run. The
key was supplied only through a no-echo prompt into the backend environment,
never saved to files, and its process was terminated; mock mode was restored.
The owner then requested all remaining cases: injection refusal, lab explanation
and the deterministic emergency safeguard passed; history summary and prescription
explanation each failed with safety-rejection HTTP 502. No further throttling.
Across both runs seven distinct cases passed, two failed; six successful cases
were actual Groq generations. Rejected prose/rule was not captured, so do not
assume a false positive or weaken the guard without investigation. Temporary key
process terminated again and mock restored; no application source changes.
See `docs/GROQ_LOCAL_LIVE_QA_2026_10_17.md`. No credential belongs in this handoff.
Broader live Groq quota/safety and medical/Bangla quality, provider/health-data review,
production logs and stable-domain authenticated smoke remain separate gates.
Both AI enable flags remain false by default. Do not erase these limitations or
restore removed PDF storage/reminder scheduling to make an old prompt appear met.

## 9.2 Final local repairs and release-readiness gate (2026-10-17)

The owner authorized continuing development/fixes through Phase 31, not a commit,
push or deployment. **All four known issues are repaired and retested locally.**
This section supersedes the earlier failed/pending Phase-30 and live-QA states.

- Chamber activation and first CURRENT promotion commit together under the queue
  advisory lock. Reopening retains the existing patient/start time. Fresh-session,
  concurrent-open and failure-rollback PostgreSQL regressions pass.
- Sharing search matches displayed full names with case-insensitive/whitespace
  normalization and wildcard escaping; existing verification/role filters remain.
- Live metadata-only diagnostics traced the two AI 502s to model-echoed medication
  schedules. Summary/chat and prescription model input now omit structured dosing
  directions; names/authorized facts remain. Canonical/task prompts explicitly
  forbid repeating even recorded directions in generated fields. Original
  instructions are still rendered unchanged by the server/UI. Safety validation
  was not relaxed. No raw prompts/model prose were logged for diagnosis.
- Added the missing accessible prescription-page h1 without changing capabilities
  or visible layout. No schema/migration/dependency change for these repairs.

Fresh final gates:

```text
Backend:                 532 passed, zero skipped (PostgreSQL 17.6 enabled)
Frontend:                57 files / 263 tests passed
Lint / TypeScript:       passed
Production build:        passed
Real Edge acceptance:    8 passed, zero failed/skipped, 29.6 seconds
Live Groq AI/UI:         9 passed (8 model generations + deterministic emergency safeguard)
Alembic head/check:      0030_doctor_locations / no drift
pip check / compileall:  passed
Whitespace/secret check: passed (no Groq-key-shaped content in checked source/bundles/evidence)
```

Browser acceptance ran against the built production frontend plus actual local
API/database through a loopback Services-routing proxy, not response mocks. It
uses no chamber/surname workaround. Four roles at four widths passed, plus real
synthetic schedule edit, location-preserving facility contact update and admin
verification. The live pass was paced, synthetic-only, and had no rate limits or
browser errors. Key-bearing process terminated and mock backend restored; no
secret file or production-setting change. Default AI flags remain false.

Read `docs/PHASE_31_LOCAL_RELEASE_REPORT.md` for exact scope, artifacts and limits.
Phase 30 scoped local acceptance passed; Phase 31 local preparation is complete,
but **Phase 31 production release is not complete**. No commit/push/CI dispatch,
production migration, deployment, alias change or production AI enablement ran.
Production logs/permissions, Linux CI/Vercel packaging, stable-domain acceptance,
provider/health-data review and comprehensive manual accessibility/GPS checks
remain separate explicit gates. One upstream Starlette/httpx warning remains.

## 9.3 Independent integrity audit through Phase 31 (2026-10-17)

Fresh verification: **532 backend tests**, **57 files / 263 frontend tests**,
lint/typecheck, optimized production build and **8/8 production-build Edge cases**
(31.54 seconds) passed. PostgreSQL regression coverage was enabled; no skipped
tests. Alembic remains `0030_doctor_locations` with no drift; dependencies,
compilation and changed tracked whitespace passed. Default AI flags remain false;
bounded source/bundle Groq-key-pattern scans were clean. Existing upstream warning
and historical Markdown trailing spaces are not new regressions.

**New P1 finding:** `.github/workflows/ci-cd.yml` locks migration and deployment
as individual jobs, not a complete release. An older run with slower quality
checks can migrate/deploy after a newer run and replace its release. There is no
stale intended-commit guard. Correct and test whole-release ordering before
clearing Phase 31; preserve in-progress migrations and avoid self-blocking nested
concurrency groups. No workflow fix was made in this verification-only request.

Read `docs/PHASE_31_INTEGRITY_AUDIT_2026_10_17.md` for evidence, precise source
locations and a qualified post-deployment-smoke hardening advisory. The previous
9/9 live AI sample was **not rerun**. No application/CI source edit, external
release action or production inspection occurred. Temporary preview servers were
stopped and port 3001 development restored against the synthetic mock backend.
Earlier local-readiness statements are qualified by this new release blocker.

## 10. Superseded statements in older documents

Interpret these older statements as historical:

```text
Start/continue from Phase 15
    -> Phases 15–21/improvements are released; Phases 22–29 code plus Phase 30 automated QA and Phase 31 preparation remain local.

Phase-14 is the current production baseline
    -> Phase 21 is the released baseline.

Alembic head is 0023_prescription_documents
    -> Production is at 0030_doctor_locations.

Prescription PDFs use private Vercel Blob and document pointers
    -> New PDFs are regenerated in memory and are not persisted.

PDF availability/file metadata is part of the response contract
    -> Those fields are removed from the released implementation.

GitHub reminder scheduling is disabled with REMINDERS_ENABLED
    -> The scheduled workflow is deleted; no scheduler is requested.

Lab reports are a separate citizen navigation section
    -> Results and trends are merged into Diagnostic tests.
```

Still preserve Vercel Services, Supabase PostgreSQL, same-origin `/api/v1`, and
GitHub Actions CI/CD. Removing PDF Blob usage does not authorize changing the
database provider or deployment architecture.

## 11. Definition of a successful handoff continuation

A fresh agent is ready to act only when it can explain:

- what is released, what Phases 22–29 add locally, and why AI is disabled by default;
- why migration `0030` stores location fields privately;
- why facility coordinates never reach DTOs/UI;
- why grants and current-patient access are different;
- why previous prescriptions may be readable but not editable;
- why PDF regeneration must not create a stored object or document row;
- why old diagnostic routes redirect rather than disappear;
- why deleting the reminder workflow stopped future scheduled-run clutter;
- which local and CI tests passed for the release;
- what fresh Phase 30 acceptance covers and why Phase 31 production sign-off remains held;
- which external operations require fresh owner authorization.

If any answer is unclear, stop, search the repository, and update the internal
ledger before editing.
