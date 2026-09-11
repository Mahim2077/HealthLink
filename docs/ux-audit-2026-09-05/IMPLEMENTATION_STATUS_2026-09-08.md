# HealthLink UX audit implementation status

Date: 2026-09-08
Baseline audit: `HealthLink_UX_Audit.md`
Scope: improvements to the existing Phase 0–14 product only. No Phase 15 capability was introduced.

## Outcome

This pass prioritizes clinical safety, queue correctness, the patient booking journey, persistent navigation, and privacy-sensitive administration. It intentionally does not add password-reset infrastructure, payments, a new longitudinal timeline, or unapproved legal/support content.

No database schema or API contract changed, so no Alembic migration or dependency-manifest update was required.

## Implemented

| Audit item | Result |
| --- | --- |
| F01 | Finish is disabled while clinical notes or prescription work is unsaved or saving. Both editors expose save state and warn before navigation or browser close; nothing is persisted in browser storage. A post-finish refresh failure no longer restores an editable finalized visit. |
| F02 | Chamber start now consumes the documented full session response and renders it directly. |
| F03 | Call-next correctly promotes the top-level acted queue entry when `next_current` is null, removes it from waiting, and cannot run while a patient is already current. |
| F04 | Chamber and booking dates use the Bangladesh civil date (`Asia/Dhaka`) while stored timestamps remain UTC. |
| F05 | Close chamber, skip, no-show, queue removal, and schedule deletion now require explicit review. Closing warns about current/waiting serials. The existing no-reopen business rule was not changed. |
| F06 | Saving an edited prescription invalidates and revokes the open PDF object URL. An older in-flight PDF response cannot overwrite a newer state. |
| F07 | Duplicate citizen shells were removed from doctor search, doctor profile, appointments, and booking. The citizen layout is the only shell owner. |
| F08 | Doctor search runs only from submitted filters, ignores stale responses, has distinct initial/loading/error/empty states, and clears without issuing a blank search. |
| F09 | Admin verification no longer silently chooses the first active facility; the reviewer must select one. |
| F10 | Booking no longer exposes editable doctor or facility UUIDs. It loads the chosen verified doctor and derives both identifiers from that record. A generic booking entry sends the citizen to doctor search. |
| F11 | Booking displays active practice weekdays, hours, facility, Bangladesh-time guidance, serial-queue expectations, and rejects dates outside the published practice schedule before submission. Backend availability remains authoritative. |
| F12 | Citizen Overview is now care-only. Identity remains in Profile, and the account-level `Add a professional role` action was moved there as well. |
| F13 | Doctor profiles emphasize availability and serial-queue expectations, remove submission/verification timestamps, use readable verification/availability labels, and suppress booking when no active practice day exists. |
| F17 | Homepage primary actions now lead to finding a verified doctor or managing citizen care. |
| F18 | Authenticated citizen, professional, and admin layouts provide persistent role-appropriate navigation with active-page state and sign-out. Professional navigation includes chamber and consultations. |
| F24 | The doctor dashboard presents chamber and consultations before weekly schedule maintenance. |
| F26 | Chamber has a refresh control, accurate current/waiting movement, no-show differentiation, clear empty/closed states, and guarded high-impact actions without widening patient data exposure. |
| F29 | The verification queue still defaults to pending work and now includes a local name/role/facility search, shown count, and readable status labels. |
| F30 | Facility management now includes local search, distinct success/error styling, readable active labels, and moves keyboard focus to the edit form when a row is selected. |
| F31 | Citizen identity support no longer fetches or displays 50 records on initial load. Search is explicitly filtered, list identifiers are masked, and retry repeats only the last submitted filter. Full values remain confined to deliberate detail review. |

## Partially implemented

| Audit item | Completed in this pass | Remaining |
| --- | --- | --- |
| F14 | Completed/past appointment groups sort newest first; upcoming remains chronological. | Add user-selectable status/date filtering or pagination if appointment history becomes large. |
| F16 | Blood-group editing now uses the same controlled choices as registration, and profile edits receive an unsaved-change warning. | A richer before/after identity review presentation can be added without changing the exact `CONFIRM` rule. |
| F19 | Citizen, professional, and admin password fields have accessible show/hide controls. | Password reset and real support details require an approved recovery workflow and operational contact. |
| F20 | The citizen doctor-search and booking journey preserves a validated same-portal return destination after sign-in. External, cross-portal, encoded-slash, auth-loop, and traversal targets fall back safely. | Extend return destinations to every guarded professional/admin deep link if product owners want universal deep-link restoration. |
| F22 | Professional verification uses readable “Under review”, “Verified”, and “Not approved” labels and preserves rejection reasons. | Add approved operational next steps/contact text for pending and rejected applicants. Unsupported future roles remain outside Phase 14. |
| F23 | Unverifiable generic privacy promises were replaced with factual role/session descriptions. | Publish only approved privacy/help content and real contacts. |
| F25 | Schedule removal confirmation and clearer consequences were added. | A denser weekly timetable and facility autocomplete can follow if the eligible-facility list grows. |
| F27 | No-active-patient links to the chamber, notes/prescription show coordinated save state, and finish is safely gated. | A sticky desktop action rail or further density work needs cross-device design validation. |
| F28 | Prescription save state and stale-PDF handling are explicit. | Compact medicine-row layout and field-level error placement can be refined; no drug catalog or AI suggestion was added. |
| F32–F34 | Engineering-heavy copy was reduced, raw labels were humanized, portal navigation has active state, controls retain 44px targets, and the root declares smooth-scroll behavior for correct Next.js navigation handling. | Continue page-title and copy review as new routes are added; perform a dedicated screen-reader pass. |
| F35 | Regression coverage was added for Dhaka midnight, queue response shapes, finish gating, PDF invalidation, safe return paths, password visibility, destructive confirmations, and admin privacy. A real local browser/API flow was exercised. | Establish production telemetry and measured performance budgets before claiming performance improvements. |

## Deferred by documented scope or missing product authority

- F15: no new Phase 15 longitudinal visit timeline was created. Existing appointment/prescription access remains in place.
- F21: the registration flow was not structurally redesigned in this reliability-focused pass.
- Password-reset infrastructure, payments, AI recommendations, drug catalogs, and new support/legal claims were not introduced.

## Verification evidence

- Frontend TypeScript: passed.
- Frontend ESLint: passed.
- Frontend Vitest: 41 files, 189 tests passed.
- Frontend optimized Next.js build: passed; all 22 static-generation entries completed.
- Backend pytest: 202 passed, 34 PostgreSQL-only tests skipped when the dedicated test URL was not supplied.
- All existing Alembic migrations applied successfully to a fresh isolated PostgreSQL database.
- Browser/API path verified locally with synthetic data: citizen login with validated return destination → filtered doctor search → verified doctor profile → booking screen. The page showed one citizen shell, persistent navigation, readable schedule data, and no UUID inputs. Browser console errors: none. API responses for login, search, and doctor profile: HTTP 200.

The browser verification did not create a real appointment because the UI check used disposable synthetic data and the booking mutation was already covered by automated API/component tests.

## Final Phase 14 design closeout (2026-09-11)

- The shared authenticated shell now carries scalable role-specific text links
  in a dedicated second header row while retaining the resizable/collapsible
  desktop sidebar and existing mobile drawer.
- Citizen Overview contains only doctor discovery and appointment/prescription
  navigation. `Add a professional role` now appears in Citizen Profile beside
  the account and identity controls and continues to open the existing
  `/professional/onboard` flow.
- Focused regression tests cover the new placement. The full closeout passed
  43 frontend files / 196 tests, lint, typecheck, the 22-route production build,
  207 backend tests with 34 PostgreSQL-only skips, and a clean authenticated
  local browser flow.
- No feature from Phase 15 or later was introduced.

## Portal-theme consistency closeout (2026-09-11)

- Preserved the approved interface and corrected color scope only: Citizen
  teal/green, Professional sky/blue, and Admin indigo/purple.
- Shared `PortalShell` and second-row navigation now use one portal-aware token
  system for the header identity control, desktop rail, mobile drawer,
  collapse/resize controls, active links, focus rings, and form accents.
- Removed isolated indigo accents from Citizen Overview and an isolated teal
  surface from the Professional chamber. Semantic success, warning, error, and
  neutral colors remain intentionally shared.
- Local quality gates passed: ESLint, TypeScript, 43 frontend test files / 199
  tests, and the optimized 22-route build. Visual checks confirmed each portal
  login uses its intended existing palette.
- This was a presentation-only Phase 14 closeout. No database, migration,
  backend, API, authorization, dependency, workflow, or Phase 15 behavior
  changed.
