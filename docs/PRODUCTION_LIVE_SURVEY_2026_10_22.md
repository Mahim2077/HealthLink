# HealthLink production survey — 2026-10-22

**Completed bounded production survey.** Live observations were collected on
2026-10-22, 17:13–17:52:50 UTC / 23:13–23:52:50 Asia/Dhaka. This is a survey,
not a fix, release, penetration test or clinical certification.

## Executive result

The production application was reachable and all three supplied roles signed in.
The principal read/navigation journeys worked, but the survey identified **11
confirmed software/UX issues plus one production-data/choice-disambiguation review
item**. Including that review item, the register contains **12 findings: 1 P1,
8 P2 and 3 P3; no P0 was established**. Missing response security headers are an
additional hardening observation, outside these 12. No assertion of zero other
bugs is made.

The most important finding is **L08**: the Citizen can open a saved prescription
from an encounter that the Doctor still sees as in progress. Medical history and
the centralized access policy use finalized-only publication, but the appointment
link/direct prescription read do not. This is a publication-policy inconsistency,
not a demonstrated cross-patient disclosure. Resolve it before treating the
clinical publication flow as release-ready.

| ID | Priority | Finding | Classification |
| --- | --- | --- | --- |
| L08 | P1 | Unfinished prescription readable by its Citizen owner | Confirmed publication-policy inconsistency |
| L01 | P2 | Desktop landing image overlaps text/CTA | Confirmed responsive layout issue |
| L02 | P2 | Location modal lets keyboard focus reach underlying booking links | Confirmed accessibility/interaction issue |
| L03 | P2 | “cardiologist” misses the doctor found by “cardiology” | Confirmed search discoverability issue |
| L05 | P2 | Repeated, indistinguishable facility options | Confirmed data/UX condition; provenance needs owner review |
| L07 | P2 | Practice Edit replaces unsaved Add form without warning | Confirmed unsaved-work loss |
| L09 | P2 | Mobile empty chat starts below the welcome heading | Confirmed initial-scroll/layout issue |
| L10 | P2 | Older active encounter is presented as today's consultation | Confirmed date-context issue |
| L12 | P2 | Reminder screen implies delivery although delivery was intentionally disabled | Confirmed misleading capability copy |
| L04 | P3 | Mirsarai displays the wrong Bengali name | Confirmed catalog label issue |
| L06 | P3 | Zero search matches are described as an empty facility registry | Confirmed empty-state issue |
| L11 | P3 | Prescription Back goes to Appointments after entry from Medical history | Confirmed navigation-context issue |

No fixes, commits, pushes, deployments or test removal were performed. The only
application content deliberately created was the separately approved two-turn
General-mode QA conversation. Appearance preferences were restored.

## Scope and evidence rules

- Stable target: https://healthlink-sd.vercel.app/.
- Survey began 2026-10-22 17:13 UTC / 23:13 Asia/Dhaka.
- Fresh Vercel stable-host lookup: READY production deployment
  `dpl_3RyPMHxWh3BVG6pgsrEEfHQrUyGr`, application
  `6649931e29bdf19a9b085ec2b0641a79f97777b7`, approved healthlink-sd project.
- The supplied Citizen, Doctor and Admin accounts all signed in successfully.
  Credentials, government identifiers and medical text are deliberately omitted.
- Current-run browser screenshots/DOM observations are live evidence. Source
  review corroborates causes; source-only concerns are explicitly separate.
- No bookings/cancellations, clinical edits, chamber operations, verification
  decisions, facility saves, identity corrections, grants/revocations or deletions
  were authorized or performed. The owner separately approved two General-mode
  AI questions with records OFF and retaining the labelled QA conversation.
  Ordinary login/read audit events
  may be created by the product. Appearance and unsaved-form checks are local.
- Private screenshots: `.runtime/production-survey-2026-10-22/`, ignored by Git.
  Some contain the supplied test accounts' personal/clinical context. Keep local;
  do not publish/upload/commit the screenshot set without a privacy review.
- Responsive captures distinguish CSS viewport dimensions from image size.
  Immediate post-resize/still-loading captures are not accepted as app defects.
- Tests used the actual stable production website, not local fixtures or a
  development server. Supporting source review used the local checkout matching
  the released application code; it was not substituted for live reproduction.
- Browser: Codex in-app browser, desktop CSS widths 1280/1366, mobile 390×844,
  plus a bounded 320×844 Larger-text Settings check. This is not a multi-browser
  compatibility or full screen-reader audit. Screenshots are captures, not design
  mockups. Source locations below refer to this surveyed release.
- Severity: P1 high-impact publication/security/workflow issue; P2 functional or
  material usability/accessibility issue; P3 lower-impact copy/polish/data label.
  This prioritization is not a clinical risk assessment.

## Role and journey coverage

“Working” below means the stated bounded interaction succeeded, not that every
mutation, exception or security case in that subsystem passed.

| Role / journey | What was actually operated | Result and boundary |
| --- | --- | --- |
| Public availability | Homepage, three sign-in routes, health and anonymous protected-route checks | Working; fresh anonymous smoke 9/9. Landing desktop issue L01; settled mobile hero reflow worked. |
| Citizen sign-in / overview | Supplied account sign-in, dashboard and care links | Working; no credential changes. Reminder capability discrepancy L12. |
| Citizen doctor discovery | Free-text query, specialty/facility controls, nearest chooser, manual Zilla/Upazila choice, result/profile and booking-form entry | Four unfiltered verified results; manual Raozan nearest result worked with approximate distance and hidden coordinates. Issues L02–L05. No booking or GPS request. |
| Citizen appointments / prescription | Existing appointment cards, saved in-progress prescription link, finalized prescription view | Read flow worked but exposed L08. No cancellation, consultation mutation or citizen draft PDF request. |
| Citizen medical history | All six finalized items, prescriptions-only filter to three items, Reset, prescription entry and Back | Type filter worked; L11 return destination. Native date-input result inconclusive, not counted as a bug. |
| Citizen diagnostics / trends | Combined requests/results and numeric-trend sections | Both empty states worked. No available finalized lab detail or nonempty trend dataset. |
| Citizen emergency profile | Existing profile view | Rendered; no personal or emergency details edited or copied into this report. |
| Citizen reminders | Delivery copy and schedule form entry | Rendered; L12. No reminder created, changed or marked read. |
| Citizen AI | Existing history, New conversation, exactly two approved General questions, refresh/reopen, delete UI then Cancel | Both answers and two-turn persistence worked; records remained OFF. Mobile initial-scroll issue L09. No deletion or record-aware request. |
| Citizen Settings | Account, Security, Display, Privacy/access history and sharing form/doctor lookup | Loaded; 320px Larger-text view had no horizontal overflow. Original preferences restored. No grant, revoke, session revocation or identity update. |
| Legacy Citizen links | `/citizen/profile`, `/citizen/privacy`, `/citizen/lab-reports`, `/citizen/lab-trends` | Redirected to Settings, Settings/Privacy, Diagnostic tests and Diagnostic tests `#result-trends`, respectively; destination sections loaded. Anchor auto-scroll positioning was not separately certified. |
| Doctor overview / Chamber | Today's dashboard and dated Chamber view | Loaded with no session for the current date. Consultations used a pre-existing older active encounter: L10. No session start/end or queue advance. |
| Doctor Consultations | Existing current-patient workspace, history, read-only historical prescription by another author, PDF regeneration control | Structured history worked. Regeneration produced a Download PDF blob link; embedded preview compatibility unresolved. No clinical text, medicine or status changed. |
| Doctor Diagnostics / Shared records | List/empty states | Loaded empty for this account; no report creation or grant-detail access could be exercised. |
| Doctor Settings / Practice | Account, Security, Display, active weekly windows, unsaved Add→Edit transition, Cancel | Loaded; L07 reproduced locally without saving. Mobile 390px pages/menu reflowed. |
| Admin overview / facilities | Registry totals, facility list, unmatched search then clear, location-confirmation backlog | Loaded; L05/L06. No facility/location save or creation. |
| Admin professional verification | Pending filter, Verified filter, name search and existing Doctor decision detail | Pending was empty; Verified had 26 entries and name search narrowed to one. Read worked; no Verify/Reject decision. |
| Admin Citizen records | Supplied test-citizen lookup, masked result and detail route | Correct account detail loaded. No identity correction or reason submitted. |
| Admin Settings / mobile navigation | Account, Security, Display, dark synchronization, mobile menu keyboard traversal and close | Loaded; menu contained/restored focus. Light restored. No security/session mutation. |

## Confirmed live observations

### L01 — Desktop landing hero can occlude content (P2)

At the desktop layout the image paints over the right edge of the left column.
The initial default-width capture visibly clips heading/paragraph/doctor CTA;
the 1366 CSS-pixel check still clips the second CTA's right edge. Evidence:
`01-public-landing-default`, `02-public-landing-desktop-1366`; independent settled
end-of-survey recaptures `71` and `72` reproduced the issue. The first immediate
mobile resize capture (`03`) was unsettled and is rejected. Replacement `73`
shows the stacked mobile hero without this overlap at 390px.

Source-supported layout mechanism: `frontend/src/app/page.tsx:128` defines a 48.5%/51.5% desktop grid;
left padding at 129 reduces available width while the buttons at 148/154 require
278px each plus a 16px gap. At 1366 the required 572px exceeds the left content
space. Recommended fix: allow wrapping/shrinking or stack CTAs earlier, contain
the text column and verify nearby breakpoints/larger text without masking content.

### L02 — Location modal does not contain keyboard focus (P2)

Citizen → Find a doctor → Nearest facility → location chooser. Shift+Tab from
Close moved focus to an underlying doctor's Book appointment link while the modal
remained open. DOM evidence: active element A, `inDialog=false`; browser AX also
identified the underlying Book appointment. This is not just an inferred risk.
Screenshot `10-location-dialog-desktop` establishes the open modal state.

`doctor-search.tsx:94` only focuses Close/handles Escape; the modal at 110 lacks
focus containment/background inertness. Use the same robust focus/restore/inert
pattern as the portal menu. Do not allow hidden background booking/navigation
controls into the modal's keyboard traversal. No booking was activated.

### L03 — Common specialist wording misses an available doctor (P2)

With no specialty/day/facility/area filter, query `cardiology` returned one
verified Cardiology doctor; changing only the query to `cardiologist` returned
zero. Evidence: `13-search-cardiology-one-result`,
`14-search-cardiologist-no-result`; both states verified in the live DOM.

`backend/app/doctors/repository.py:123` substring-matches normalized enum codes
without specialty aliases. Add an explicit, tested specialty synonym map rather
than widening arbitrary fuzzy medical text. This is a discovery issue, not proof
that every specialty or doctor is unsearchable. Pagination beyond 50 is separate
and has not been reached in this four-result production dataset.

### L04 — Mirsarai has the wrong Bengali label (P3)

The live Chattogram Upazila options show `Mirsarai — সরাইল`.
`backend/app/locations/all-upazila.json:1802` contains that label. The correct
name is মীরসরাই, as shown by the
[official Chattogram district list](https://chittagong.gov.bd/pages/static-pages/6991007335ce18e1c0732888)
and [Upazila government portal](https://mirsharai.chittagong.gov.bd/pages/notices).
Only the display-name defect is established; coordinate accuracy was not mapped.
Review source-data labels systematically and add representative name assertions,
while retaining attribution and hidden coordinate behavior.

### L05 — Production registry contains test-like duplicated facility labels (P2 data/UX)

Admin overview reports 25 active facilities, 24 needing location confirmation.
Citizen facility options and Doctor practice options expose repeated `PG Booking
Facility`, `PG Chamber Facility`, `PG Queue Facility`, and a PostgreSQL-named
facility. Many identically named choices cannot be distinguished in the select.
Admin verified queue also exposes numerous corresponding PG-named accounts.

The labels/duplicates are confirmed; whether these records are intentionally
retained fixtures is an owner decision, not proved by their names. Do not delete
them automatically. Reconcile provenance/linked records and use a reviewed test
data policy; disambiguate legitimate same-name facilities by area/registration.
Evidence: live search/practice/registry DOM, `09`, `22`, `27` and `30` screens.

### L06 — Facility zero-match search claims the entire registry is empty (P3)

Admin → Facilities → Search facilities → deliberately unmatched
`zz-survey-no-match-20261022`. The UI says “No facilities yet” and “Create the
first facility before verifying a professional,” despite 25 active facilities.
Clearing the local query restores records. Evidence:
`25-admin-facility-no-match-message`.

`facility-manager.tsx:109,137` reuses the registry-empty state after filtering.
Distinguish “No matching facilities” (with clear-search action) from an actually
empty registry. No facility was created/changed.

### L07 — Practice Edit silently replaces an unsaved form (P2)

Doctor → Settings → Practice hours. In Add weekly window, change Max patients
from 20 to 19 without publishing. Select an existing window's Edit. The form
immediately becomes Edit weekly window with Max patients 20; no confirmation.
The live DOM verified the 19→20 transition. Evidence: `27`, `28`, `29` captures
(DOM provides the exact numeric transition; screenshot framing varies).

`practice-schedule-editor.tsx:169` clears dirty state and overwrites the form in
beginEdit. Guard this in-page transition as well as navigation. No Save/Publish/
Remove action was used; Cancel edit discarded only local unsaved UI state.

### L08 — Citizen can read the saved prescription before encounter finalization (P1)

**Reproduced in a fresh Citizen-only session**, after the earlier mixed-role
guard result was discarded as prescription evidence. My appointments → the
existing Booked card for the supplied Doctor's active encounter → View
prescription. The clinical summary and medicine directions rendered for the
same prescription identified by the Doctor's in-progress consultation. Screen
`47-citizen-saved-in-progress-prescription`, compared with Doctor `21`/`45` and
appointment `20`. The record/encounter remained unchanged throughout the survey.

This conflicts with the newer finalized-only centralized policy and Medical
history behavior. It is a premature-publication/policy inconsistency, **not
evidence of cross-citizen access**. The old prescription test explicitly expects
an own-citizen read before finishing, so this requires a deliberate coordinated
policy/test correction, not just hiding a button.

Source: appointment DTO `backend/app/appointments/service.py:306–338` maps
prescriptions without finalization; appointments page `:145` exposes the link;
citizen prescription dependency `backend/app/prescriptions/dependencies.py:56`
and service `:391` check ownership only. Central policy `app/access/policy.py:54`
and medical-history repository `:154` require finalized records. Legacy test
`test_prescriptions.py:673` preserves the old rule. PDF dependency shares the
gap, but a Citizen draft-PDF request was not separately executed in this run.

If finalized-only publication is retained, enforce it at every citizen structured
record/PDF boundary, suppress premature links, and test pre/post-finalization,
author access and cross-owner denial. Preserve authorized Doctor draft access.

### L09 — New/empty AI conversation starts scrolled below its heading on mobile (P2)

At 390×844, fresh AI navigation and New conversation show only the trailing
“understand?” of the welcome heading. Live DOM measurement: transcript top
235.39px, heading top 197.39px, scrollTop 126px, clientHeight 313px, scrollHeight
439px. Evidence `48-ai-assistant-mobile-records-off` and
`50-ai-mobile-empty-heading-clipped`. This is a settled page, not the earlier
post-resize capture artifact.

`chat-workbench.tsx:53` unconditionally bottom-scrolls even an empty conversation;
the welcome at 149 lives in the same constrained transcript (`.module.css:31`,
mobile sizing 90–91). Keep new/empty conversations at the top, and bottom-scroll
only actual messages/output. Re-test fresh navigation, New conversation and
larger-text mobile layouts without breaking follow-up scrolling.

### L10 — An older active encounter is presented as today's consultation (P2)

During the same live role survey, the Doctor dashboard and Chamber reported no
session for the current Dhaka date, while Consultations presented an already
active encounter tied to a September appointment, titled “Today's consultations.”
Its encounter banner showed facility/serial/status but no encounter date. Evidence
`18`, `20`, `21`, `23`, `43` and `45`.

Dashboard selection is today-bound (`dashboards/service.py:77`), Chamber sends
careDate (`chamber-queue.tsx:61,98`), but current-patient selection accepts the
latest CURRENT row from any ACTIVE session (`visits/repository.py:125–136`).
The response omits appointment/session date (`visits/schemas.py:102`), and the
UI title is unconditional (`professional/visits/page.tsx:196`).

This establishes misleading/missing date context, not that historical recovery
must be forbidden. Add the encounter date and an explicit older-open-encounter
banner/resume path, then resolve stale workflow state deliberately. Do not
automatically finish, delete, hide or close production encounters as an audit fix.

### L11 — Prescription Back loses the history entry point (P3)

Citizen → Medical history → an existing finalized prescription → Back navigates
to Appointments, not Medical history. The destination was followed and verified,
not inferred solely from source. Evidence `57`, `59`, `60` and route observation.
`prescription-page.tsx:76` hardcodes the citizen Back destination. Preserve a
safe allowlisted return context, including applied history filters/page, while
retaining a sensible direct-link fallback. Browser Back remains a workaround.

### L12 — Reminder copy implies automatic delivery despite intentional removal (P2 copy/trust)

The dashboard explicitly says automatic reminder delivery is not enabled. The
Reminders page instead promises that due medicine reminders/booked appointment
notices appear there and only says notices “may arrive late”; its form refers to
changes applying to future reminders. Evidence `07`/fresh dashboard DOM, `63`,
`64`. No reminder or notification state was changed.

The delivery scheduler was intentionally removed at the owner's request; this
is **not** an unexpected scheduler outage and must not be “fixed” by restoring
GitHub cron. State the disabled-delivery limitation on this page/form, use saved
schedule terminology, and make any future activation an explicit product decision.

## Additional live checks

- Exactly two separately approved General-mode AI questions were sent in one
  labelled `QA survey 2026-10-22...` conversation. They contained general terms,
  no patient details. Both answers were educational; the follow-up correctly
  retained the reference-range topic without diagnosing/prescribing. Records off
  remained visible; no record-consent control was enabled. Screens `50`–`53`.
- After refresh, the saved conversation reopened with exactly two Question and
  answer articles; the pre-existing conversation was still present. New conversation
  reset the composer but retained history. The delete UI was opened then Cancelled,
  never confirmed. Its inline non-modal alertdialog legitimately permits leaving
  focus; screenshot `54` is **not** evidence of a modal-focus bug. `55`, `56` show
  the reset state and unselected Use my records control. MAIN/skip target exists.
- Doctor historical prescription structured view and regeneration returned a
  fresh Download PDF blob link. The embedded preview was blank in this in-app
  browser (`34`); cross-browser PDF viewing/file-content validation is outstanding.
  Do not claim a broken generator from the blank embedded frame alone.
- Medical history showed six finalized items, filtering to three prescriptions.
  Native From/To date-input automation produced inconclusive results: both DOM
  values were observed populated before Apply, then cleared while record-type
  filtering remained correct. The cause was not independently established.
  Two attempts only; source handlers/tests do not
  explain a reset. Requires manual native-date reproduction before classifying
  as an app defect. Screen `58` is not accepted proof of date-range validation.
- Citizen diagnostics/trends, Doctor diagnostics and Doctor shared grants were
  empty for these accounts; empty-state rendering worked, but finalized lab detail,
  nonempty numeric trends and an existing grant detail could not be tested.
- Staff Account/Security/Display sections loaded with correct role labels. Dark
  preference synchronized across tabs, and Light was restored. Mobile Admin menu
  trapped focus (last control Tab wrapped to the first link) and restored focus
  on close. The mobile Doctor menu exposed all clinical destinations after its
  asynchronous role lookup; its brief first-open minimal list was not a missing-link
  bug. Doctor mobile consultation/practice pages reflowed within 390px. `36`–`46`.
- Citizen Display at 320×844 with Larger text had document width 320px, with
  wrapping Settings tabs and no horizontal overflow (`69`). Standard text and
  Light were restored; motion stayed System and sidebar stayed Compact. This
  does not certify every route at 320px, system-theme detection or all motion.
- The bounded final Citizen browser error/warning read returned no entries;
  bounded Doctor/Admin reads likewise yielded no useful errors. This is not a
  full network trace, proof of no server errors or substitute for runtime logs.
- Admin test-citizen identity search returned the expected masked match; its detail
  route loaded the correct account. No identity value/reason/decision was changed.
- Fresh runtime error/fatal query scoped to this deployment returned 403 at
  23:28 Dhaka. No alternate service account or unverified CLI credential was used.
  Thus no clean-runtime-error-window claim is possible from this survey.

- Fresh anonymous smoke, 23:19:19–23:19:32 Dhaka: 9/9 passed. Health/public/login
  routes healthy; anonymous Citizen/Professional/Admin overviews and AI status
  correctly denied with 401. Not an authenticated cross-account security test.
- Public GET headers at 23:20:09–23:20:10: HSTS present. Homepage lacks CSP,
  X-Frame-Options, nosniff, Referrer-Policy and Permissions-Policy; health has
  nosniff but lacks the other policies. This is a defense-in-depth hardening gap,
  not an exploited XSS/clickjacking claim. Frontend next.config.ts has no policy.
- Search had four verified doctors; manual Chattogram→Raozan returned one with
  an approximate distance (about 1.2km), not raw coordinates. No GPS permission
  or precise location was requested. Screens `11`, `12`.
- Doctor profile and booking form agree on its primary-facility Tuesday/Friday
  windows. Booking was not submitted. Screens `16`, `19`.
- Doctor consultation currently exposes an already active in-progress encounter
  and previous-prescription links. No draft was opened/started or edited by QA.
- A Citizen tab reload after another-role login correctly showed “Citizen Portal
  access required / This session belongs to another HealthLink portal.” This is
  role isolation, not a prescription denial result. Screen `24` must not be used
  as proof of draft prescription visibility. Sequential role testing is required
  because this browser's latest refresh session belongs to its latest login.

## Source-only risks — not yet live-confirmed

1. The citizen structured prescription gap is now confirmed as L08. Its matching
   PDF dependency and direct citizen visit-read variant remain source-corroborated,
   not independently exercised. No cross-patient access claim is made.
2. Admin whitespace-only verified qualification sets saving before returning,
   leaving Verify/Reject disabled. No pending applications existed, and no real
   decision was submitted to manufacture a reproduction.
3. Doctor search requests limit 50 with no next-page control. Four results do
   not reproduce the scale defect.
4. Secondary-facility-only schedules may produce an enabled booking CTA but a
   booking form hardcoded to the primary facility. No production schedule was
   created/changed to test this.
5. GPS denial feedback is on the underlying page rather than in the modal.
   GPS permission/denial was not tested; no permission change is implied.
6. Areas/facilities catalog failures may block search and incomplete retry paths.
   No network fault injection was performed.
7. Historical PDF regeneration uses current age/author facility. No demographic
   or facility change was made to test a historical rewrite.

## Prioritized correction and retest plan

These are recommendations, not changes performed by this survey. Preserve all
existing Phase 32 functionality and tests; add focused regression coverage.

| Order | Scope | Minimum acceptance / retest |
| --- | --- | --- |
| 1 | L08 publication policy | Deliberately align the legacy prescription contract with finalized-only history. Test Citizen structured read, appointment link, PDF and direct visit boundary before/after finalization; author draft access; other-owner denial; no accidental loss of authorized Doctor history. Live mutation tests need a disposable encounter and explicit approval. |
| 2 | L02 keyboard modal | Contain forward/backward focus, make background inert, support Escape, restore the trigger and keep location errors inside the dialog. Verify no background Book link can receive focus while open. Retest mouse/touch/manual area flow. |
| 3 | L07 dirty practice state | Warn or preserve an unsaved Add/Edit form when selecting another existing window; Cancel in the proposed discard-confirmation dialog must preserve input, and confirmed discard must be explicit. Verify save/delete/unsaved-route guards with synthetic schedules, not real production windows. |
| 4 | L10 encounter context | Show the actual encounter/session date and distinguish today's queue from resumed older-open care. Choose recovery rules deliberately; preserve historical access without silently ending, hiding or changing the old encounter. |
| 5 | L01 + L09 responsive layout | At 320/390/768/1024/1280/1366 and larger text, no image-covered CTA/text and no initial chat-heading clipping. Keep empty chat top-aligned and actual message follow-ups scrolled appropriately; composer/history remain reachable. |
| 6 | L03 + L04 discovery catalog | Test common specialty noun/practitioner aliases and representative Bangla/English area labels. “cardiology” and “cardiologist” must find the same eligible doctor without bypassing active/verified filters; correct Mirsarai label without exposing coordinates. |
| 7 | L05 production data | Owner reconciles named/duplicate records and location backlog using provenance and references. Do not delete by name. Disambiguate legitimate facilities by locality/registration; test same-name selections. Any cleanup is a separate approved data operation. |
| 8 | L12 reminders | Make disabled automatic delivery explicit on dashboard, list and form. Saved schedules must not promise an operating delivery service. Do not reintroduce the removed GitHub reminder workflow. |
| 9 | L06 + L11 polish | Distinguish no-match from empty registry; clear query restores results. Preserve an allowlisted return context for history→prescription→Back, including filters/page where supported, and provide a safe direct-link fallback. |
| 10 | Hardening + source-only risks | Verify response policies on HTML/API and PDF compatibility in a normal browser. Add approved synthetic cases for pending Admin qualification validation, multi-facility booking, >50 search results, failed location catalogs and historical PDF snapshots. Do not declare these live-fixed before reproducing them. |

## Evidence index and interpretation

All **73 local capture files** are under
`D:\HealthLink_V_1\.runtime\production-survey-2026-10-22`. They were saved during
this run; the relevant accepted screenshots were visually inspected, alongside
live AX/DOM state. The folder is Git-ignored (explicitly checked). File names
are capture-time labels, not independent truth: `21` contains a pre-existing
current patient despite its filename; `24` is a role guard, not successful draft
access; `40` is desktop despite “narrow”; `54` is a non-modal inline confirmation,
not a modal-focus failure; `58` does not prove invalid-date validation.

Links below are **private local evidence**, not published attachments. A clone
of the repository will not contain them. Some display identifiers or clinical
context; review/redact before sharing outside this machine. An evidence link
does not authorize publication of the image.

| Evidence | Purpose / limitation |
| --- | --- |
| [71 — landing 1280](../.runtime/production-survey-2026-10-22/71-public-landing-settled-1280.png), [72 — landing 1366](../.runtime/production-survey-2026-10-22/72-public-landing-settled-1366.png), [73 — mobile 390](../.runtime/production-survey-2026-10-22/73-public-landing-settled-390.png) | L01 reproduced at desktop; settled mobile comparison. Earlier 01/02 corroborate, 03 rejected as unsettled. |
| [09 — doctor results](../.runtime/production-survey-2026-10-22/09-doctor-search-loaded-desktop.png), [10 — location dialog](../.runtime/production-survey-2026-10-22/10-location-dialog-desktop.png) | L02 open-dialog context and L05 facility choices; live focus traversal supplies the escape proof. 08 was a loading capture. |
| [11 — manual area](../.runtime/production-survey-2026-10-22/11-manual-area-choice.png), [12 — nearest results](../.runtime/production-survey-2026-10-22/12-nearest-manual-results.png) | Manual Zilla/Upazila nearest flow; no precise GPS. L04 label came from live options/official corroboration, not the selected Raozan label. |
| [13 — cardiology](../.runtime/production-survey-2026-10-22/13-search-cardiology-one-result.png), [14 — cardiologist](../.runtime/production-survey-2026-10-22/14-search-cardiologist-no-result.png) | L03 equivalent user wording changes 1 result to 0. |
| [20 — Citizen appointments](../.runtime/production-survey-2026-10-22/20-citizen-appointments.png), [45 — Doctor consultation](../.runtime/production-survey-2026-10-22/45-doctor-consultation-mobile.png), [47 — Citizen in-progress prescription](../.runtime/production-survey-2026-10-22/47-citizen-saved-in-progress-prescription.png) | L08 sequential-role comparison. Private clinical context; not for publication. 24 is excluded from L08 proof. |
| [18 — Doctor dashboard](../.runtime/production-survey-2026-10-22/18-doctor-dashboard.png), [23 — Chamber](../.runtime/production-survey-2026-10-22/23-doctor-chamber-current-date.png) | L10 contrast with the older open encounter in 21/45. No clinical state changed. |
| [22 — Admin overview](../.runtime/production-survey-2026-10-22/22-admin-overview.png), [25 — facility no match](../.runtime/production-survey-2026-10-22/25-admin-facility-no-match-message.png) | L05 registry/backlog context, L06 misleading filtered-empty message. |
| [27 — original practice](../.runtime/production-survey-2026-10-22/27-doctor-practice-original.png), [29 — overwritten Edit form](../.runtime/production-survey-2026-10-22/29-doctor-practice-overwrite-to-20.png) | L07 form states. Live DOM, not framing of 28, establishes unsaved 19→20 replacement. |
| [26 — empty pending queue](../.runtime/production-survey-2026-10-22/26-admin-pending-queue-empty.png), [30 — verified search](../.runtime/production-survey-2026-10-22/30-admin-verified-filter-search.png), [32 — recorded decision](../.runtime/production-survey-2026-10-22/32-admin-test-doctor-recorded-decision.png), [35 — Citizen identity](../.runtime/production-survey-2026-10-22/35-admin-test-citizen-identity.png) | Admin read-only coverage; pending mutation unavailable. 35 is identifier-sensitive. |
| [31 — shared records](../.runtime/production-survey-2026-10-22/31-doctor-shared-records.png), [33 — Doctor diagnostics](../.runtime/production-survey-2026-10-22/33-doctor-diagnostics-empty.png), [34 — PDF UI](../.runtime/production-survey-2026-10-22/34-doctor-historical-prescription-pdf.png) | Empty datasets and historical prescription regeneration UI; blank frame is inconclusive about PDF contents. |
| [41 — Admin dark/mobile](../.runtime/production-survey-2026-10-22/41-admin-display-dark-mobile.png), [42 — Admin menu](../.runtime/production-survey-2026-10-22/42-admin-mobile-navigation.png), [44 — Doctor menu](../.runtime/production-survey-2026-10-22/44-doctor-mobile-navigation.png), [46 — mobile practice](../.runtime/production-survey-2026-10-22/46-doctor-practice-mobile.png) | Role Settings and mobile navigation/reflow. Other staff account/security/display captures: 36–40; dashboard 43. |
| [50 — clipped empty chat](../.runtime/production-survey-2026-10-22/50-ai-mobile-empty-heading-clipped.png), [52 — two General turns](../.runtime/production-survey-2026-10-22/52-ai-two-general-turns-mobile.png), [53 — reopened history](../.runtime/production-survey-2026-10-22/53-ai-history-restored-two-turns-desktop.png), [55 — New conversation](../.runtime/production-survey-2026-10-22/55-ai-new-conversation-retains-history.png) | L09 and approved AI test/persistence. 48/49/51/54/56 provide adjacent state/consent context; delete was cancelled. |
| [57 — finalized history](../.runtime/production-survey-2026-10-22/57-citizen-finalized-history.png), [59 — prescription filter](../.runtime/production-survey-2026-10-22/59-history-prescriptions-filter.png), [60 — Back link](../.runtime/production-survey-2026-10-22/60-citizen-finalized-prescription-back-link.png) | History/type filtering and L11. 58 excluded as proof of date validation. |
| [61 — combined diagnostics](../.runtime/production-survey-2026-10-22/61-citizen-diagnostic-tests-and-trends.png), [70 — legacy destination](../.runtime/production-survey-2026-10-22/70-legacy-trends-consolidated-diagnostics.png) | Empty combined diagnostics/trends and legacy route resolution; no finalized lab record available. |
| [63 — reminder copy](../.runtime/production-survey-2026-10-22/63-reminders-delivery-copy.png), [64 — unsaved reminder form](../.runtime/production-survey-2026-10-22/64-reminder-form-unsaved.png) | L12; no reminder save. Compare dashboard 07. |
| [65 — Citizen account](../.runtime/production-survey-2026-10-22/65-citizen-account-settings.png), [66 — privacy history](../.runtime/production-survey-2026-10-22/66-citizen-privacy-access-history.png), [67 — sharing form](../.runtime/production-survey-2026-10-22/67-sharing-full-name-search-no-grant.png), [68 — security](../.runtime/production-survey-2026-10-22/68-citizen-security-settings.png), [69 — 320px Larger text](../.runtime/production-survey-2026-10-22/69-citizen-display-320-larger.png) | Citizen Settings coverage; no sharing or session mutation. Emergency profile 62 is private and not reproduced in this report. |

Sign-in/profile/booking-entry captures 04–06, 15–17 and 19 are supporting journey
context. Captures 05/06 are not accepted as validation-success proof. Excluded,
loading or misleadingly named captures were retained for traceability, not counted
as findings. A failed full-page screenshot attempt at 320px was a capture-tool
limitation; the settled viewport screenshot and DOM width were obtained instead.

## Production write ledger and cleanup

- **Retained by approval:** one Citizen conversation titled
  `QA survey 2026-10-22: Explain what a laboratory reference range means in general`,
  containing exactly two user questions and two educational answers. First asked
  what a laboratory reference range means, explicitly excluding personal records
  and treatment; second asked how it differs from a diagnosis. Both succeeded.
  After refresh, two Question-and-answer articles remained. No record consent was
  enabled, and no medical data was intentionally transmitted to the AI provider.
- The delete confirmation was inspected and **Cancelled**. This conversation
  was not deleted and must not be removed without the owner's confirmation.
- Authentication and ordinary read/access audit events were generated by using
  the supplied accounts. The privacy history visibly recorded Doctor read/PDF
  activity. The audit did not purge or modify those events.
- Dark/Light and Larger/Standard display checks changed only device preferences;
  original Light/Standard were restored. Motion System and Compact navigation
  remained unchanged; the temporary viewport override was reset. Unsaved practice
  form changes were discarded via Cancel without any API save.
- No appointments, medicines, clinical notes, encounter status, schedules,
  facility records, identifiers, verification decisions or grants were saved or
  removed. No production database credentials or provider keys were used or read.
- **Session cleanup limitation:** ordinary sign-out uses a browser-native
  confirmation which the available in-app automation has previously been unable
  to complete reliably. It was not forced; no all-session revocation workaround
  was used. Do not assume QA login sessions have been revoked. The owner can
  perform ordinary sign-out manually if cleanup is needed. Temporary audit tabs
  are not a guarantee of server-side session revocation.
- Local deliverables: this Markdown report plus ignored private screenshots.
  No application source/test change, commit, push, workflow change or deployment.

## Gaps and confidence limits

The reproduction evidence supports the exact findings above. It does **not**
establish complete security, clinical safety, accessibility or end-to-end release
certification. In particular:

- No new booking/cancellation, clinical draft/finalization, queue/session mutation,
  facility change, identity correction, approval/rejection or grant/revoke cycle.
  These require synthetic/disposable data or separate approval.
- No arbitrary other-patient identifier probes, account lockout/invalid-password
  campaigns, CSRF/XSS exploit testing, CAPTCHA completion or privileged bypass.
  The anonymous 401 smoke and mixed-role guard are useful checks, not a complete
  authorization matrix.
- Exactly two General AI questions only. No record-aware AI request, symptom
  triage, prescribing challenge, prompt-injection campaign, provider-outage,
  concurrency, rate-limit or long-history stress test. Educational answers here
  do not establish safety for all possible prompts.
- No real GPS permission/denial, precise-location tracking or coordinate accuracy
  survey. Manual nearest-area choice worked for the stated example only.
- Finalized lab reports/trends, existing shared grants and pending verification
  forms were unavailable in these supplied account datasets. Empty states are
  covered, not the full populated workflows.
- Native history date filtering needs manual confirmation; embedded PDF preview
  needs ordinary-browser/file-content validation. Neither is counted as a
  confirmed defect or successful PDF-layout validation.
- No full browser/device matrix, screen-reader audit, measured WCAG contrast
  certification, Core Web Vitals benchmark, load test or exhaustive breakpoint
  sweep. Dark mobile/staff and narrow Citizen Settings are bounded samples.
- Runtime logs were unavailable with the approved Vercel connection (403).
  No alternate account was used. No backups/restores, infrastructure operations,
  database consistency audit or full local unit/integration suite rerun was part
  of this live survey.

**Handoff recommendation:** review and agree the L08 publication-policy correction
first, then implement the focused fixes and regression tests in the order above.
Keep production-data cleanup and any consequential live write tests separately
approved. Nothing in this report authorizes those operations.

## Implementation follow-up — 2026-10-24

The owner subsequently requested the fixes. The local implementation and
verification are tracked separately in
[the survey correction report](SURVEY_BUGFIX_REPORT_2026_10_24.md). This survey
retains the original live findings; it is not a post-deployment retest or a claim
that the corrected working tree is already on production.
