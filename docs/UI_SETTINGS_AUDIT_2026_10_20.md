# Portal UI audit and Settings plan — 20 October 2026

> Phase 32 evidence. Earlier local-only checkpoints are historical; the owner
> authorized consolidated release on 2026-10-22. See
> [scope](PHASE_32_POST_ROADMAP_UPGRADES.md) and
> [release state](PRODUCTION_PHASE_32_RELEASE_2026_10_22.md).

Scope: existing HealthLink application; local synthetic data only. No production
record writes, account changes, commit, push or deployment authorized for this work.
Captured 38 screens at 1440×1000 and 390×844 with Edge/Playwright, plus the full
9-journey clinical/responsive baseline (9 passed). Fresh source evidence is in
`.runtime/ui-settings-audit/before/manifest.json` and its numbered PNGs/contact
sheets; clinical editing evidence is in `.runtime/browser-qa/results/`.

## Findings and implementation plan

1. Public entry, role sign-in and registration — healthy. Clear role boundaries,
   responsive forms and consistent identity. Retain layout and brand assets.
2. Citizen overview/navigation — needs cleanup. Ten destinations compete in the
   horizontal strip and icon rail; profile/privacy are separate from account
   management. Consolidate account utilities into Settings; retain care tools,
   emergency profile, reminders and the familiar text navigation.
3. Discovery, booking and appointments — healthy. Preserve specialization chips,
   nearest/manual Bangladesh area selection, serial queue rules and booking flow.
4. Medical history, prescription, diagnostics and trends — healthy. Preserve
   unified diagnostic section, merged consultation/prescription and regenerated
   PDFs. Add clearer keyboard-focus treatment/scroll cues to shared UI, not a
   clinical workflow redesign.
5. AI chat — healthy. Preserve private saved conversations, delete controls,
   compact record selector and explicit per-request record consent. Settings may
   explain/link these controls, but must not silently enable record access.
6. Emergency profile/reminders — healthy functional care tools. Keep accessible
   in main navigation; do not recreate the removed scheduled GitHub workflow.
7. Citizen account/privacy/sharing — needs organization. Reuse existing editable
   profile, protected identity and one-time NID confirmation. Put these under
   Account; group access history and sharing under Privacy & sharing.
8. Doctor dashboard — needs separation of concerns. Weekly practice editor is
   embedded below daily work and makes the dashboard long. Move editor to verified
   doctor Settings → Practice hours, with a dashboard shortcut.
9. Chamber/consultation/shared records — healthy, including empty states. Baseline
   clinical journey verifies merged clinical note/prescription and previous record
   access; preserve all care permissions and actions.
10. Lab workload/diagnostic report — healthy. Retain draft/finalized distinction,
    immutability and role gates. No doctor-only settings for lab staff.
11. Admin overview/verification/facilities/identity search — healthy. Operational
    registries remain workspace tools, not personal Settings. Facility coordinate
    logic remains internal. The identity-detail capture exposed a real route bug:
    the page read Next.js asynchronous params synchronously, requesting `undefined`.
    Fix by awaiting params; add a successful browser detail regression before handoff.
12. Shared mobile navigation — improvement required. Add focus containment,
    background inertness, scroll locking, Escape close and focus restoration.
    Replace the account link's misleading dropdown chevron with a Settings affordance.

## Settings structure

- Account: citizen profile/identity/onboarding; professional selected-role and
  verified facility details; administrator account summary. No invented account
  editing endpoints or password/2FA toggles.
- Security: current-session sign-out and existing all-account-sessions revocation,
  explicit confirmations, pending/error feedback. Never display access tokens.
- Display & accessibility: Light/Dark/System theme, standard/larger text, system/reduced motion and compact/
  expanded default sidebar. Non-sensitive device-only preferences, accurately
  labelled, validated and recoverable if browser storage is unavailable.
- Citizen Privacy & sharing: record grants, recorded access and AI privacy links.
- Verified-doctor Practice hours: existing schedule editor, same backend permissions.

Use existing Inter typography, teal/blue/indigo portal tokens and Heroicons.
Settings gets one heading, responsive section navigation, clear section descriptions
and focused forms. Existing bookmarked profile/privacy/status URLs continue working.
No new database table or migration is needed for this UI reorganization.

## Audit limits

Synthetic data is not representative of all production volumes. Some audit lists
contain many previous synthetic fixtures. Screenshots alone do not establish WCAG
compliance; keyboard, focus, text scaling and flow tests are required after edits.
No claim of medical accuracy or production runtime-log verification is made.

## Implemented and verified

All planned Settings sections are implemented with existing role/API boundaries.
The original routes remain usable. The audit's admin-detail failure was reproduced,
fixed with awaited Next.js params, and verified by the optimized browser suite.
The mobile profile header was compacted after a before/after comparison; destructive
session revocation is visually distinct. Practice-hour navigation now warns about
unsaved edits. Lab report/trend regions accept keyboard focus for sideways scrolling.

1. Public entry/sign-in/registration — healthy, retained.
2. Citizen navigation/overview — healthy, account utilities consolidated.
3. Doctor discovery/booking — healthy, specialist and nearest flows retained.
4. History/prescriptions/diagnostics/trends — healthy, no duplicate report section.
5. AI chat — healthy, persistence/delete/consent and explanation-only behavior retained.
6. Emergency/reminder tools — healthy, existing capabilities retained, scheduler absent.
7. Citizen account/privacy/sharing — healthy, reorganized without identity-rule changes.
8. Doctor overview/practice configuration — healthy, daily work separated from Settings.
9. Clinical consultation/chamber/history — healthy, full synthetic care journey passed.
10. Lab draft/finalized reports — healthy, permissions and immutability retained.
11. Admin verification/facility/identity — healthy; detail route regression fixed.
12. Mobile menu/display/session management — healthy in tested keyboard/viewport states.

Evidence: initial manifest `before/`, post-change 53-screen manifest `after/`, final
14-section Settings manifest `after-final/`, four dashboards `after-final-dashboard/`
and combined source/final comparisons in `.runtime/ui-settings-audit/comparisons/`.
The capture directories are local/ignored, not production-data artifacts or Git assets.

Final gates: backend **564 passed** (one existing deprecation warning); frontend
**61 files / 298 tests**; lint, typecheck, optimized build; **14/14 browser cases
on the optimized local Services preview**. Browser suite checks unexpected API/
console failures and external browser requests; none in final passing run.
Settings widths 320/390/768/1366; existing portal matrix also covers 1920. Larger
text covers Settings and citizen discovery/history/diagnostics/chat/emergency routes.

Storage and security boundaries: profile changes use the existing citizen API;
display preferences store only four allowlisted UI choices on this browser;
sign-out uses the existing session mutation barrier and logout/logout-all endpoints.
Two sessions of one synthetic account were revoked while another account remained
signed in. No fake password, 2FA, notification or always-on AI record-consent switch.

No commit, push, deployment, production database write or provider-key change.
Local preview: `http://127.0.0.1:3001`; it is a mock/synthetic QA environment, not
the production site. Full visual comparisons and limitations are in `design-qa.md`.

### Color-theme follow-up

Owner requested Light/Dark mode after the initial Settings upgrade. Color theme
now offers Light, Dark and Use system setting. Legacy/missing preferences keep
Light. Theme applies across public/auth and all role portals, including AI chat,
with no image inversion. Static head bootstrap applies the saved theme before
body paint; OS-change and cross-tab updates are covered. Dark styling is screen-only,
so browser printing stays light and prescription PDFs are unchanged. No new
database/env/provider configuration or release operation was required.
