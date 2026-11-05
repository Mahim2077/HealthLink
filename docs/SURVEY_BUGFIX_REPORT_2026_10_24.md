# Production-survey corrections — 2026-10-24

## Release status

Completed local implementation and verification follow-up to
[the 2026-10-22 production survey](PRODUCTION_LIVE_SURVEY_2026_10_22.md).
The original survey is historical evidence, not a statement that these fixes are
already deployed. **No commit, push, deployment or production data mutation is
part of this work.** No application migration is required by these changes.

## Confirmed findings addressed

| Finding | Local correction | Regression coverage |
| --- | --- | --- |
| L01 — hero overlap | Zero-minimum grid tracks and bounded text column; responsive heading and wrapping/shrinkable action buttons. | Real Edge checks at 320, 390, 768, 1024, 1280 and 1366 CSS pixels; desktop buttons remain inside the text column and are not covered by the image. |
| L02 — location focus escape | Body-portalled modal, inert background, contained forward/backward/programmatic focus, Escape, scroll lock and trigger restoration. | Component focus tests and real Edge Shift+Tab/Escape/restore before manual nearest-area search. |
| L03 — specialist wording | Explicit normalized specialty/practitioner aliases, preserving verification, active-facility and other search filters. No symptom inference or arbitrary fuzzy matching. | Alias unit matrix and database-backed Cardiology/Cardiologist equivalence plus eligibility/filter exclusions. |
| L04 — Mirsarai label | Correct Bengali catalog label to মীরসরাই; coordinates unchanged. | Catalog regression asserts English/Bengali pairing. |
| L05 — indistinguishable facilities | Citizen discovery, Doctor practice, booking and Admin assignment choices show public area/address/registration. Exactly matching metadata gets a labelled listing number and a confirmation-needed notice, never internal IDs/coordinates as display text. | Shared label tests and role component coverage. Production provenance and location backlog are deliberately not cleaned up. |
| L06 — filtered-empty registry | Separate “No matching facilities” from an actually empty registry; Clear search restores results. | Admin component cases and real Edge no-match/clear test. |
| L07 — silent unsaved replacement | Add/Edit transitions require confirmed discard when dirty; cancellation preserves input. Transitions are disabled while saving. | Component cancellation/confirmation cases plus real Edge dismiss/accept with unsaved capacity 19. Pending-disable behavior was reviewed in code, not separately exercised in an in-flight save test. |
| L08 — unfinished publication | Finalized-only Citizen prescription JSON/PDF and service reads, direct visit reads/list summaries and appointment prescription links. Authorized Doctor draft/history access remains under centralized clinical policy. | Actual Finish Appointment transition: own draft JSON/PDF/visit denied and link hidden; finalization restores access; foreign-owner denial remains; denied PDF never renders; author and authorized other-author history preserved. Browser care journey verifies structured denial before finishing and publication afterward. |
| L09 — empty chat clipping | Empty/new conversations scroll to top; actual messages still scroll to the bottom. Switching back from symptom guidance re-evaluates the visible transcript. | Chat component scroll tests and real Edge 390px initial scrollTop 0 with the whole welcome heading inside the transcript. |
| L10 — older encounter labelled today | Neutral “Current consultations” heading, actual appointment date and explicit older/future-open encounter context; the older-open banner includes a queue review link. No automatic close/finalization or hidden historical recovery. | Older-open backend DTO case preserves ACTIVE/BOOKED state; component date/banner tests and existing current-care browser journey. |
| L11 — Back loses history | History links carry an allowlisted return path with applied record type/date filters/page. Prescription Back restores it; direct entry retains Appointments fallback; Professional return behavior unchanged. | URL sanitization including external/disguised paths and page 1000/1001 boundary; timeline/PrescriptionPage tests; real Edge filtered-history round trip and native date Apply. |
| L12 — reminder promises | Dashboard/list/form now describe saved schedules and explicitly disclose disabled automatic delivery. Existing notices remain reviewable; activating a schedule does not promise alerts. | Copy regression and real Edge schedule form check. Removed GitHub reminder cron remains absent. |

## Additional deterministic risks corrected

These were source-only risks in the original production survey. They are not
retroactively described as production reproductions; synthetic tests establish
the corrected behavior locally.

- **Admin qualification validation (R2):** whitespace validation happens before
  entering the Saving state. The Doctor decision controls remain usable after an
  invalid qualification, and a corrected value can proceed.
- **Doctor result limit (R3):** explicit 50-item paging uses the existing total
  and offset contract. Paging preserves the submitted query/filter/location;
  unsent text does not change a page request. New searches reset the offset,
  controls are disabled while pending, and stale responses are suppressed.
- **Secondary-facility booking (R4):** the booking form intersects active public
  facilities with active published practice windows. It defaults to the primary
  only when eligible, otherwise a scheduled secondary facility. Selecting a
  different facility clears the date, retains the reason, and updates windows,
  weekday validation, published capacity and the submitted facility. Remaining
  capacity is still checked by the backend, not invented by the UI.
- **GPS error placement (R5):** denied/unavailable GPS feedback is visible within
  the location dialog, where the manual-area fallback remains available.
- **Catalog failures (R6):** facility, area and doctor requests settle
  independently. A failed optional catalog no longer hides available doctors;
  each failed catalog has a targeted retry, including manual-area recovery inside
  the modal. Pending/failed controls are labelled and unavailable where needed.
- **Historical PDF metadata (R7):** regenerated facility comes from the stored
  encounter facility, not the Doctor's current assignment. Age and the printed
  date use the encounter timestamp in Bangladesh time, not the regeneration date.
  Naive persisted timestamps follow the existing UTC convention; a corrected DOB
  after an encounter shows age unavailable rather than a negative number. PDFs
  remain generated on demand and are not stored. Names, qualifications and
  subsequent facility-name corrections still use canonical structured values;
  no new immutable demographic/credential snapshot schema was introduced.
- **Response hardening:** frontend and API add nosniff, SAMEORIGIN framing,
  same-origin referrers, self-only geolocation/disabled camera and microphone,
  and a baseline CSP restricting base URI, form actions and frame ancestors.
  Same-origin PDF previews, Next scripts/styles and optional GPS remain enabled.
  This is not a full nonce/hash script CSP or a security certification.

The secondary-booking browser test also exposed an additional follow-through
issue: its saved facility ID was correct, but Citizen appointment cards displayed
the Doctor's primary submitted facility name. **Corrected:** the list now derives
canonical names from stored appointment facility IDs in one batched query. The
regression includes cancellation, inactive historical facilities, an outdated
submitted primary label, ordering/status preservation and one-query behavior.
The real Edge secondary booking now reaches the correct hospital name in history.

## Verification receipts

Final checks ran together on the completed working tree, not only on independent
agent branches:

| Check | Final result |
| --- | --- |
| Full backend / PostgreSQL suite | **601 passed, zero skipped**, 118.16 seconds. Fresh dedicated migrated database `healthlink_survey_9c9afc6f1b57` on loopback port 55433. |
| Full frontend suite | **343 passed across 64 files**, 8.99 seconds. |
| TypeScript | Passed, no errors. |
| ESLint | Passed, no errors/warnings. |
| Optimized Next build | Passed after all code changes; all 44 static pages generated and dynamic routes compiled. |
| Dependency-gate behavior | **10 offline security-gate tests passed**; no dependencies or advisory exceptions changed. This is not a fresh external advisory scan. |
| Complete Edge acceptance suite | **18/18 passed**, 2.4 minutes. Local development frontend, real loopback API/PostgreSQL, mock AI, no mocked API responses. |
| Whitespace and evidence links | Final diff check and local evidence-target checks passed. |

The final browser pass covers the care journey, on-demand PDF Blob signature,
private saved chat/follow-up/consent, four-viewport role matrix, synthetic
schedule/facility/verification operations, Settings/session/theme behavior and
the four added survey scenarios. Every passing case also checks no browser
exceptions, unexpected API errors or off-loopback requests. The publication test
explicitly allows its expected denied draft request; that 404 is not hidden as an
unexpected error. Native date inputs retained their values and Apply returned
200 for the requested date filter, resolving the old automation ambiguity in
this normal-Edge local environment without inventing a date-filter code fix.

Intermediate failures were investigated rather than omitted:

- The first broad backend command mistakenly enabled PostgreSQL-only tests with
  an in-memory SQLite URL and also encountered a Windows temporary-directory
  ACL. Those failures were test setup, not a product regression; a fresh migrated
  loopback PostgreSQL DB and unique workspace scratch directory resolved them.
- One new exact-label browser locator did not match a select that was present in
  the accessibility snapshot. Role-based selection corrected the test; focused
  and full final reruns passed. No assertion was removed to manufacture a pass.
- The secondary-booking test then found the real appointment-list name bug;
  code and backend regression coverage were added before its successful rerun.

One existing non-failing Starlette TestClient deprecation warning remains. Edge
prints a non-failing NO_COLOR/FORCE_COLOR tooling warning. No test failures or
skips remain in the final backend/frontend/browser receipts.

- Two fully synthetic historical PDFs were rendered with Poppler and their PNGs
  inspected: date/age/facility, table wrapping and corrected-DOB text fit without
  clipping. Artifacts remain ignored under `.runtime/survey-fixes/tmp/pdfs/`.

### Selected local visual evidence

These are synthetic/local screenshots, not production records. Runtime artifacts
are Git-ignored and may be replaced by a later harness run; they are not bundled
into a fresh clone.

- [Landing 1280 — no image-covered actions](../.runtime/browser-qa/results/healthlink-Survey-regressi-363c2-d-baseline-response-headers/survey-landing-1280.png)
- [Mobile empty chat — heading starts at the top](../.runtime/browser-qa/results/healthlink-Survey-regressi-7f522-chat-and-truthful-reminders/survey-mobile-empty-chat-top.png)
- [Admin facility no-match state](../.runtime/browser-qa/results/healthlink-Survey-regressi-1da9b-cility-filtered-empty-state/survey-facility-no-match.png)
- [Selected secondary facility and capacity](../.runtime/browser-qa/results/healthlink-Survey-regressi-43f35-secondary-practice-facility/survey-secondary-facility-booking.png)

## Safety, data and remaining boundaries

- Production credentials, provider keys and the production database were not
  needed. No production writes or real AI calls were performed. Local browser
  requests are restricted to loopback; the backend uses explicit mock AI settings.
- Browser fixtures are uniquely named synthetic records in
  `127.0.0.1:55433/healthlink_phase27_qa`. Backend regression tests use a separate
  newly created database. Existing accounts are not overwritten. The seed now
  also pins application settings before importing models, excluding developer
  `.env` fallback.
- No tests were removed. Existing tests were retained/strengthened to reflect
  the deliberate finalized-only Citizen publication rule.
- Facility provenance, duplicate records and the location-confirmation backlog
  still need the owner's reviewed data decision. UI disambiguation is not data
  deletion or certification of those records.
- No new schema migration or production backfill is required. Newly returned
  facility metadata and current-encounter date are additive API fields, but the
  finalized-only publication change is an intentional behavior correction.
- In-app PDF preview compatibility from the original survey is not declared
  universally fixed: the normal Edge journey validates returned PDF bytes and
  generated Blob, while the synthetic PDF rendering verifies document layout.
- This is bounded local verification, not a replacement for an approved
  post-deployment smoke on the stable production link or a complete clinical,
  penetration, screen-reader, load or cross-browser certification.
- Temporary local API/frontend and the PostgreSQL cluster started for this QA
  were stopped after the checks. Synthetic fixtures/test databases and ignored
  evidence are retained for reproduction; no existing database was deleted.

## Handoff

Keep the original survey and this correction report together. Commit/push/deploy
remain separate owner actions. After an approved release, retest the stable
production link with read-only flows and a separately approved disposable
pre/post-finalization encounter; do not alter an existing patient encounter to
manufacture that check.
