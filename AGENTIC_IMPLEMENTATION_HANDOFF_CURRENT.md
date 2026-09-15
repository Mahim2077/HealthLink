# HealthLink current agentic implementation handoff

> **Status date:** 2026-09-15
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
Local HEAD:             cb075e21b652fd7d17d7f104fb1a30656ea57b44
origin/main at handoff: cb075e21b652fd7d17d7f104fb1a30656ea57b44
Released DB head:       0029_access_grant_scopes
Pending local DB head:  0030_doctor_locations
Released roadmap:       Phases 15–21
Next roadmap phase:     Phase 22, only after the pending release is healthy
```

Relevant released commits:

```text
fa07edf  feat(clinical): complete phases 15 through 17
6ca19f6  feat(clinical): complete phases 18 through 21
cb075e2  docs(phase-21): record production verification [skip ci]
```

The current worktree is intentionally dirty. Recent owner-approved changes are
implemented and verified locally but have **not** been committed, pushed,
migrated, or deployed. Do not discard them.

## 2. Mandatory reading order

1. This file.
2. `frontend/AGENTS.md`.
3. `AGENTIC_IMPLEMENTATION_HANDOFF_PHASES_0_TO_14.md` for the historical base.
4. The end of `docs/implementation-progress.md` for Phases 15–21 release
   evidence and the pending prescription consolidation.
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

## 4. Pending owner-approved work in the dirty tree

### 4.1 Modern doctor discovery

The old analog doctor finder was replaced with a specialty-first hybrid design.

Implemented behavior:

- one unified name/specialty/facility search;
- six common specialty shortcuts and a complete normalized specialty catalog;
- weekday and facility filters;
- active-filter chips and a single clear action;
- five sort modes: relevance, earliest availability, experience, name, nearest;
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

This migration is local/pending and has not been applied to production.

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

`.github/workflows/reminders.yml` is deleted in the working tree.

Reason: its five-minute `schedule` event created GitHub workflow-run records
before the job-level `REMINDERS_ENABLED` guard was evaluated, so disabled jobs
still cluttered the Actions history.

After the deletion is committed and pushed:

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

## 6. Verification evidence for current dirty tree

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

The 38 backend skips are explicit environment-gated PostgreSQL suites, not test
failures. Before production release, run the available PostgreSQL migration and
concurrency gates as appropriate for migration `0030`.

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

The reminder-workflow deletion and handoff-document updates occurred after the
code gates; they are YAML/Markdown-only and passed `git diff --check`.

## 7. Current source tree cautions

Expect both modified and untracked files. Important untracked source includes:

```text
backend/alembic/versions/0030_doctor_discovery_locations.py
backend/app/facilities/geocoding.py
backend/app/locations/
backend/tests/test_locations.py
frontend/src/app/citizen/diagnostic-tests/[test_id]/
frontend/src/components/citizen/doctor-search.test.tsx
frontend/src/lib/doctors/specializations.ts
frontend/src/lib/locations/
```

Important intended deletions include:

```text
.github/workflows/reminders.yml
backend/app/prescriptions/storage.py
backend/tests/test_prescription_storage.py
```

Do not confuse any of these with disposable generated files.

Local ignored `.runtime`, `.env`, and `.vercel` material may exist. Preserve it,
do not enumerate or expose secrets unnecessarily, and never commit it.

## 8. Release procedure when explicitly authorized

The owner previously required commit/push/deploy to be a separate explicit
prompt. Until that instruction arrives, stop before all external mutations.

When authorized:

1. Re-read the current diff and verify no credential or coordinate leakage.
2. Run focused tests for any final edits.
3. Run full backend/frontend gates, including migration checks and available
   PostgreSQL-specific coverage.
4. Confirm `0030_doctor_locations` is the single Alembic head and metadata
   matches migrations.
5. Commit the complete coherent pending work without dropping unrelated owner
   changes.
6. Push `main` to `Mahim2077/HealthLink` only with explicit approval.
7. Observe the configured HealthLink CI/CD workflow through completion.
8. Confirm production migration reaches `0030_doctor_locations`.
9. Verify `https://healthlink-sd.vercel.app/`, `/health`, Citizen/Doctor/Admin
   login routing, doctor search, admin facility confirmation, diagnostic
   compatibility redirects, consultation, prior prescription access, and fresh
   PDF generation.
10. Confirm no new `Deliver in-app reminders` runs are scheduled after the
    workflow deletion reaches the default branch.
11. Record the release commit, Actions run, deployment, migration head, smoke
    results, and known limitations in `docs/implementation-progress.md`.

Do not include secret values in the commit, output, logs, or verification notes.

## 9. Next roadmap work: Phase 22

Phase 22 has not started. Do not write AI code before planning and before the
pending release is stable.

Minimum Phase-22 design constraints:

- consult current official OpenAI API documentation rather than remembered SDK
  behavior;
- server-side `OPENAI_API_KEY` only; never create a `NEXT_PUBLIC_` AI key;
- one provider abstraction and centralized timeout/error handling;
- mock provider calls in all tests and CI; no real model spending in CI;
- authorize every record-aware request before data retrieval;
- send only the minimum structured, authorized context;
- remove NID, BCN, passwords, tokens, direct identity data, unrelated address,
  and unrelated record history;
- treat user text and all stored medical text as untrusted prompt data;
- validate model output with strict Pydantic schemas;
- log/audit metadata only, never raw PHI prompts or responses;
- AI output remains explanatory and cannot diagnose, prescribe, alter clinical
  truth, or perform medical actions.

Plan Phase 22 first and present the architecture, authorization, privacy,
failure-mode, test, and browser-acceptance plan to the owner before coding.

## 10. Superseded statements in older documents

Interpret these older statements as historical:

```text
Start/continue from Phase 15
    -> Phases 15–21 are released; finish the pending release, then Phase 22.

Phase-14 is the current production baseline
    -> Phase 21 is the released baseline.

Alembic head is 0023_prescription_documents
    -> Production is 0029; pending local head is 0030.

Prescription PDFs use private Vercel Blob and document pointers
    -> New PDFs are regenerated in memory and are not persisted.

PDF availability/file metadata is part of the response contract
    -> Those fields are removed from the pending implementation.

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

- what is already released versus merely local;
- why migration `0030` is pending;
- why facility coordinates never reach DTOs/UI;
- why grants and current-patient access are different;
- why previous prescriptions may be readable but not editable;
- why PDF regeneration must not create a stored object or document row;
- why old diagnostic routes redirect rather than disappear;
- why deleting the reminder workflow stops future history clutter only after a
  push;
- which tests already passed and which PostgreSQL gates remain release work;
- which external operations require fresh owner authorization.

If any answer is unclear, stop, search the repository, and update the internal
ledger before editing.
