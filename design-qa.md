# HealthLink public landing page — design QA

> Phase designation update, 2026-10-22: post–Phase 31 entries for saved chat,
> Settings/interface cleanup and Light/Dark/System are **Phase 32** evidence.
> Earlier entries keep their original scope; see `docs/PHASE_32_POST_ROADMAP_UPGRADES.md`.

## Comparison target

- Approved source mock: `C:/Users/User/.codex/generated_images/019fe7ac-e181-7140-b244-712ee417dcef/exec-12fca598-ef03-4d02-ac3b-4ae69d9ef5d6.png` (`1487 × 1058`).
- Final desktop implementation: `docs/landing-redesign-2026-09-09/implementation-chrome-desktop-1440x1024.png` (`1440 × 1024`).
- User-reported Chrome reference: `C:/Users/User/AppData/Local/Temp/codex-clipboard-1d360939-9c77-4ef1-9d2a-61f1e40d9acf.png` (`1885 × 918`).
- Final wide Chrome implementation: `docs/landing-redesign-2026-09-09/implementation-chrome-wide-1885x918-v2.png` (`1885 × 918`).

The source and implementation were normalized only for the combined comparison canvas. The standalone screenshots retain their native dimensions for breakpoint review.

## Evidence reviewed together

- Approved mock beside the final Chrome implementation: `docs/landing-redesign-2026-09-09/comparison-source-to-chrome-final.png`.
- User-reported wide Chrome state beside the corrected state: `docs/landing-redesign-2026-09-09/comparison-chrome-scaling-before-after.png`.
- Complete final page, including the editorial extension and footer: `docs/landing-redesign-2026-09-09/implementation-chrome-full-page-1440x2200.png`.
- Tablet verification: `docs/landing-redesign-2026-09-09/implementation-chrome-tablet-1024x768-v2.png`.
- Mobile verification was inspected at a true `390 × 844` CSS viewport in the in-app Chromium browser; the Chrome CLI has a 500-pixel minimum layout width, so `implementation-chrome-mobile-500x844-v2.png` is the faithful standalone Chrome capture.

## Findings

No actionable P0, P1, or P2 findings remain.

- [P3] The generated standalone hero artwork omits the mock's small handwritten decorative phrase. This avoids embedding hard-to-read text in a responsive raster asset and does not affect hierarchy or meaning.
- [P3] The standalone artwork's doctor crop differs slightly from the source mock at some ratios. The subject, clinical iconography, Dhaka skyline, and pale-aqua palette remain faithful, and the focal point stays visible at every checked breakpoint.

## Iteration history

### Pass 1 — landing implementation

- Replaced the portal chooser with the approved citizen-first landing page.
- Removed public admin access and consolidated sign-in destinations into one disclosure menu.
- Preserved the two primary citizen routes and the professional registration route.
- Used the supplied/generated doctor artwork with the existing HealthLink mark and Heroicons.

### Pass 2 — desktop fidelity corrections

- Corrected hero height, image crop, typography, and spacing against the approved source.
- Re-captured the implementation and reviewed it beside the source at the same effective proportions.

### Pass 3 — Chrome scaling corrections

- [P2] The hero was capped at 1440 pixels while the teal band spanned the window, leaving a disconnected white strip on wide Chrome windows.
- [P2] A fixed 650-pixel hero height made the next section feel clipped on shorter screens.
- [P2] The two-column layout activated at 1024 pixels, causing the large heading and second CTA to collide with the image.

Fixes applied:

- Made the header and hero fluid across the browser width.
- Replaced the fixed desktop height with a viewport-aware `clamp()`.
- Moved the split hero to the `xl` breakpoint so 1024-pixel layouts stack cleanly.
- Added fluid horizontal padding and responsive image sizing.
- Confirmed no horizontal overflow at `390 × 844`, `1024 × 768`, and `1885 × 918`.

### Pass 4 — editorial page depth

- Added a non-interactive purpose section, three editorial care principles, a closing statement, and a minimal footer.
- Added no new application feature, route, form, or duplicated CTA.
- Preserved the approved action hierarchy and all existing destinations.

## Required fidelity surfaces

- Typography: display hierarchy, weight, tracking, and line length remain aligned with the approved mock; mobile display text scales down without overflow.
- Spacing and layout: the header, hero, artwork, and teal process band now share one continuous responsive canvas. The 1024-pixel breakpoint stacks without clipping.
- Colors: white, ink, indigo, teal, and pale-aqua surfaces match the approved visual language and maintain readable contrast.
- Assets: the hero uses the local high-resolution doctor artwork and Next.js image optimization. Interface icons come from Heroicons; no placeholder, CSS-drawn, or inline SVG artwork was added.
- Content: added copy is general editorial context only. It does not claim or expose a new product capability.

## Functional and responsive checks

- Chrome screenshots verified at `1885 × 918`, `1440 × 1024`, `1024 × 768`, and `500 × 844`.
- A true `390 × 844` CSS viewport verified the mobile header, stacked hero, CTA width, artwork crop, editorial sections, and footer.
- The mobile sign-in disclosure opened without clipping and still exposed only Citizen and Professional sign-in.
- Browser console inspection returned no errors.
- Layout metrics reported no horizontal overflow at mobile, tablet, or wide desktop sizes.
- Focused landing-page tests: 2 passed.
- Full frontend suite: 42 files and 192 tests passed.
- TypeScript typecheck, ESLint, and the Next.js production build passed.

## Implementation checklist

- [x] Approved visual target preserved.
- [x] Wide Chrome scaling issue reproduced and corrected.
- [x] Tablet collision corrected.
- [x] True mobile layout and sign-in disclosure verified.
- [x] General below-fold content added without new features.
- [x] Source and implementation reviewed in combined comparison images.
- [x] No P0/P1/P2 visual findings remain.

final result: passed

---

# HealthLink doctor discovery and nearby-location flow — final design QA

## Comparison target

- Approved hybrid source mock: `C:/Users/User/.codex/generated_images/01a09161-a544-7292-8a25-323ccc9166b8/exec-36e033dd-57b1-4c78-82a6-75c21f70b1b7.png` (`1488 × 1058`).
- Browser-rendered implementation: `http://127.0.0.1:3000/citizen/doctors/search`.
- In-app browser captures were inspected at `1440 × 1050` for desktop fidelity and `390 × 844` for the responsive layout. The implementation URL is the reproducible screenshot target; captures were emitted inline by the Codex in-app browser rather than written to the repository.

## Evidence reviewed together

- Full view: approved source and browser-rendered implementation were compared for the heading, unified search, six specialty cards, day/facility/sort controls, active-filter chips, results table, and action hierarchy.
- Focused region: the source location modal was compared with the implemented approximate-location modal at desktop size, including the softened background, map-pin treatment, primary/secondary actions, privacy copy, and dismissal control.
- Focused region: the implementation's additional manual-area state was inspected separately because it extends the approved concept. It presents bilingual zila and upazila selectors without exposing coordinates.
- Responsive view: the `390 × 844` layout was checked separately because the approved source is desktop-only. It replaces the table with readable stacked result cards and keeps controls at touch-friendly sizes without horizontal overflow.

## Findings

No actionable P0, P1, or P2 visual differences remain.

- [P3] The production portal shell remains visible around the discovery surface instead of reproducing the mock's isolated canvas. This preserves the application's existing navigation and visual system.
- [P3] On mobile, specialty cards use a two-column grid and result rows become stacked cards. This is an intentional responsive adaptation of the desktop source.
- [P3] The manual nearby flow adds a second modal state that was not pictured in the source. It follows the same dimensions, hierarchy, controls, and teal/slate styling.

## Required fidelity surfaces

- Typography: the strong display heading, compact filter labels, doctor hierarchy, and restrained supporting copy align with the approved source and existing portal typography.
- Spacing and density: desktop preserves the source's search-first rhythm and compact results table; mobile increases vertical space and touch targets without clipping.
- Colors and effects: teal actions, pale-teal icon circles, slate text, white cards, subtle borders, modal dimming, and restrained shadows remain consistent.
- Assets: all interface symbols use the project's existing Heroicons dependency; no placeholder graphics, manually drawn SVGs, or low-resolution assets were introduced.
- Content: specialty, qualification, facility, area, next-practice, distance, verification, and action labels use real backend response fields. Coordinate values are absent from all user-facing responses and interface states.

## Interaction, privacy, and responsive checks

- Unified text search, six specialty shortcuts, day selection, facility filtering, and five sorting options are present and keyboard-addressable.
- Selecting `Nearest facility` opens an explicit location choice before browser geolocation is requested.
- Manual location exposes 64 bilingual zila options and their dependent upazila choices; Dhaka → Savar returned the expected distance-ordered doctors.
- Approximate GPS values are rounded before a `POST` search request, retained only in component memory, and never written to browser storage.
- Nearby results use human-readable distance labels; an exact/near-exact match reads `Less than 1 km away` rather than `0 km`.
- No `latitude`, `longitude`, or `coordinate` label appeared in the rendered doctor-search flow.
- The `390 × 844` document width remained within the viewport (`375px` content width inside a `390px` viewport), with no page-level horizontal overflow.
- Browser console warnings/errors: none.
- Focused doctor-search tests: 4 passed.
- Full frontend suite: 52 files and 238 tests passed.
- Focused backend location/doctor-discovery tests: 11 passed.
- TypeScript typecheck, ESLint, full backend suite, and the Next.js production build passed during this implementation pass.

## Comparison history

### Pass 1 — hybrid discovery implementation

- Rebuilt doctor discovery around the approved unified search, specialty cards, compact filters, active chips, responsive results, and primary booking action.
- Added specialization and qualification data so search results are clinically meaningful instead of generic provider rows.

### Pass 2 — nearby-location implementation

- Added an explicit one-time approximate-location choice and bilingual manual zila/upazila alternative.
- Kept facility coordinates private and used them only for backend distance filtering and sorting.
- Added admin-only address/area confirmation before a facility becomes eligible for nearby calculations.

### Pass 3 — browser and regression QA

- Verified the desktop source hierarchy and location modal at `1440 × 1050`.
- Verified the responsive card layout at `390 × 844` and exercised Dhaka → Savar manual nearby search end to end.
- [P3] Replaced `About 0 km away` with `Less than 1 km away` and added a focused regression test.
- Confirmed no visible coordinate terminology and no browser console warnings or errors.

## Implementation checklist

- [x] Approved hybrid doctor-search design implemented.
- [x] Specialty-first discovery and five sorting options implemented.
- [x] Explicit approximate-GPS prompt implemented without browser persistence.
- [x] Manual bilingual zila/upazila search implemented.
- [x] Facility coordinates confined to backend location logic.
- [x] Facility location confirmation restricted to admins.
- [x] Desktop and mobile browser states verified.
- [x] Automated regression, type, lint, and production-build checks passed.

final result: passed

---

# HealthLink portal-theme consistency — final Phase 14 design QA

## Scope

This pass preserved the approved layouts, typography, content, interactions,
routes, and semantic status treatments. It corrected portal identity colors
only: Citizen teal/green, Professional sky/blue, and Admin indigo/purple.

## Findings and verification

No actionable P0, P1, or P2 finding remains.

- Public and authenticated shared shells declare an explicit `data-portal`
  theme scope.
- The compact account header, second-row text navigation, desktop icon rail,
  collapse/resize controls, mobile drawer, focus rings, and form accents inherit
  the active portal palette.
- Citizen Overview no longer carries indigo/purple supporting copy or arrows.
- The Professional chamber current-patient surface no longer carries a teal
  border/background while its professional blue label is active.
- Emerald success, amber warning, rose error, and slate neutral treatments were
  deliberately retained because they communicate state rather than identity.
- Full frontend verification passed: ESLint, TypeScript, 43 Vitest files / 199
  tests, and the optimized 22-route Next.js build.
- Local browser checks confirmed the Citizen login in teal/green, Professional
  login in sky/blue, and Admin login in indigo/purple with no feature changes.

## Implementation checklist

- [x] Previous portal palettes preserved.
- [x] Shared shell and navigation use one portal-aware token system.
- [x] Cross-portal accent remnants corrected.
- [x] Semantic state colors preserved.
- [x] No database, API, authorization, dependency, or Phase 15 change.

final result: passed

---

# HealthLink authenticated portals — second-row navigation design QA

## Comparison target

- Source visual truth: `C:/Users/User/.codex/visualizations/2026/08/09/019fe7ac-e181-7140-b244-712ee417dcef/healthlink-top-navigation-concepts.html`, with the approved `Second row` state selected.
- Baseline portal reference: `C:/Users/User/AppData/Local/Temp/codex-clipboard-93e74b28-32e3-4428-8a49-0794627c569c.png` (`1880 × 902`), showing the existing compact sidebar and account header that had to remain intact.
- Browser-rendered implementation: `http://127.0.0.1:3000`, captured inline in the current Codex in-app browser task for `/citizen/dashboard`, `/citizen/appointments`, `/professional/status`, and `/admin/dashboard`.
- Implementation screenshot locator: `cua://browser/1/tab/browser-use:64118f6d-6edd-471c-bdac-2045c0223bb7` (the selected browser connector emitted inline captures rather than a filesystem screenshot path).

## Viewport and state normalization

- Desktop layout viewport: approximately `1200 × 750` CSS pixels at `devicePixelRatio 1.2`; emitted browser capture measured `1188 × 743` pixels after the in-app browser viewport chrome and scrollbar were excluded.
- Mobile layout viewport: `390 × 844` CSS pixels at density `1`; citizen appointments drawer open.
- Source reference density: `1880 × 902` pixels. The comparison was structural rather than pixel-for-pixel because the approved source is an interactive navigation concept layered over the earlier portal reference, not a full-page replacement mock.
- Authenticated desktop states: citizen overview and appointments, professional restricted role-status view, and admin overview.
- Active-route state, desktop overflow, mobile fallback, and browser console output were checked separately so the comparison did not confuse responsive behavior with visual drift.

## Evidence reviewed together

- Full view: the approved second-row concept and the browser-rendered citizen, professional, and admin pages were reviewed as one navigation-system comparison.
- Focused region: the sticky header, identity cluster, second navigation row, active underline, and preserved icon rail were compared directly. A separate crop was unnecessary because each inline capture kept the full header labels readable.
- Mobile state: the second row was confirmed hidden at `390 × 844`; the existing drawer displayed the complete citizen destination set and the active appointments state without horizontal overflow.

## Findings

No actionable P0, P1, or P2 differences remain.

- [P3] The second row intentionally starts at the content edge rather than centering its links across the full header. This preserves the approved scalable navigation behavior and gives future links predictable overflow space.
- [P3] Professional users with a pending role can see destinations that remain authorization-protected. This matches the sidebar's existing information architecture; protected routes retain their current backend/frontend guards.

## Required fidelity surfaces

- Fonts and typography: the existing HealthLink type scale is preserved. Navigation labels use the established small semibold UI style, remain on one line, and do not truncate.
- Spacing and layout rhythm: the identity row is reduced to a compact `80px` minimum height and the navigation row uses a consistent `56px` minimum height. Both align to existing responsive page gutters.
- Colors and visual tokens: the row reuses the portal's white, slate, and teal tokens. Active links use teal text plus a two-pixel underline; inactive links retain the established slate-to-teal hover treatment.
- Image quality and asset fidelity: no images, logos, or decorative assets were added or altered. The existing HealthLink mark and Heroicons remain unchanged.
- Copy and content: every text link reuses the existing sidebar label and route definition, preventing navigation terminology from drifting between the two surfaces.

## Functional and responsive checks

- The shared component renders the complete route set for Citizen, Professional, and Admin portals.
- Citizen doctor-detail routes continue to highlight `Find a doctor` through the existing nested-route rule.
- Clicking `Appointments` from the citizen second row navigated to `/citizen/appointments` and moved `aria-current="page"` to the correct link.
- Desktop navigation remained a single horizontal row with no page-level overflow.
- Mobile navigation hid the second row and preserved the full existing drawer flow.
- The resizable/collapsible desktop sidebar and account identity controls remain present.
- Citizen, professional, and admin browser sessions produced no console warnings or errors during the checked states.
- Focused component tests: 5 passed.
- Full frontend suite: 43 files and 195 tests passed.
- TypeScript typecheck, ESLint, and the Next.js production build passed.

## Comparison history

### Pass 1 — shared second-row implementation

- Added one shared text-navigation component backed by the existing role-specific route map.
- Inserted it below the account header for every authenticated portal page through the shared shell.
- Preserved the icon rail, resize controls, responsive drawer, route authorization, and page content.

### Pass 2 — browser and responsive verification

- No P0/P1/P2 visual mismatch was found, so no corrective visual iteration was required.
- Confirmed route-active styling across citizen, professional, and admin states.
- Confirmed the mobile drawer remains the only navigation surface below the desktop breakpoint.

## Implementation checklist

- [x] Shared second row added to every authenticated portal page.
- [x] Existing sidebar route definitions reused as the single source of truth.
- [x] Active state and nested doctor-route behavior preserved.
- [x] Long-term link growth handled with a single-line horizontally scrollable row.
- [x] Mobile drawer retained without duplicate on-screen navigation.
- [x] Accessibility, tests, lint, typecheck, build, and live browser flows verified.

final result: passed

---

# HealthLink citizen role-onboarding placement — final Phase 14 design QA

## Comparison target

- Source visual truth remains the approved citizen Overview/Profile system
  recorded in `docs/ui-design-audit-2026-09-08/`, together with the approved
  second-row navigation concept documented above.
- This was a placement refinement, not a redesign: the existing typography,
  spacing, colors, icon style, sidebar, header, and route behavior were kept.

## Findings and verification

No actionable P0, P1, or P2 differences remain.

- Citizen Overview now contains only doctor discovery and
  appointment/prescription navigation; it does not render `Add a professional
  role` or national-identity content.
- Citizen Profile displays `Add a professional role` as an account-level action
  beside `Back to dashboard`, retaining the exact `/professional/onboard`
  destination.
- The action group stacks on compact widths and aligns horizontally when space
  permits, using existing responsive tokens and accessible focus styles.
- Focused component tests passed, followed by the full 43-file / 196-test
  frontend suite, lint, typecheck, and the 22-route optimized build.
- An isolated authenticated local browser flow verified Dashboard → Profile →
  Professional onboarding. Browser console warnings/errors: none.

## Implementation checklist

- [x] Approved visual system preserved.
- [x] Care and account actions separated without duplicating links.
- [x] Existing route and authorization behavior preserved.
- [x] Automated and real-browser coverage passed.
- [x] No Phase 15 feature introduced.

final result: passed

---

# Approved modern AI chat — 2026-10-19 local implementation

## Source and rendered evidence

- Source visual truth: `C:/Users/User/.codex/generated_images/01a09161-a544-7292-8a25-323ccc9166b8/exec-68a89dfa-1d2c-41f2-a96b-92573beb9fb1.png`.
  An unchanged local QA copy is `D:/HealthLink_V_1/.runtime/chat-design-qa/approved-reference.png`.
- Implementation: `http://127.0.0.1:3001/citizen/ai-assistant`, optimized Next
  build behind the existing loopback Services proxy; synthetic PostgreSQL and mock AI only.
- Final desktop capture: `D:/HealthLink_V_1/.runtime/chat-design-qa/implementation-desktop.png`.
- Full-view combined comparison: `D:/HealthLink_V_1/.runtime/chat-design-qa/full-comparison.png`.
- Focused composer combined comparison: `D:/HealthLink_V_1/.runtime/chat-design-qa/composer-comparison.png`.
- Additional evidence: `D:/HealthLink_V_1/.runtime/chat-design-qa/implementation-mobile-320.png`
  and `D:/HealthLink_V_1/.runtime/chat-design-qa/record-consent.png`.
- Desktop CSS viewport: 1487 × 1058; deviceScaleFactor 1. Source: 1487 × 1058 px.
  Full-page implementation: 1487 × 1059 px (one extra page-layout pixel).
  Both are 1× density; contact sheets scale each image equally to fit 890 × 635
  without stretching. Composer crops use corresponding content regions at equal scale.
- State: authenticated citizen, collapsed existing portal rail, two real synthetic
  general question/answer turns, empty composer, records off. Source has seven
  illustrative conversations and short fictional answers; implementation has one
  genuine saved conversation and the existing mock's deliberately generic answer
  plus clinician questions. No fake history was inserted to copy the mock.
- Responsive captures: 320, 390, 768 and 1280 px at height 900. Broader portal
  regression also covers 1366 and 1920 px.

## Comparison history / findings and fixes

### First visual pass — blocked pending adjustments

- [P2] The history column was 44 px narrower than the reference, shifting the chat
  start from approximately x418 to x374 and making history titles too cramped.
  Fixed desktop sidebar width from 290 to 334 px; retain narrower tablet rules.
- [P2] Transcript/composer text and send affordance were undersized compared with
  the reference. Increased desktop transcript to 17 px, composer input to 16 px,
  context chip to 14 px, heading to 28 px and send target to 52 px. Mobile retains
  appropriate compact spacing and a minimum 44 px send target.
- [P2] Send glyph used an upward arrow rather than the reference's paper-plane
  affordance. Replaced it with the existing Heroicons paper-plane asset.
- Initial evidence was the first dev capture opened in this turn; the first
  combined contact sheet confirmed the undersized composer before the second
  typography/icon adjustment. Final paths above contain the revised captures.

### Final visual pass — passed

Opened the final full-view and focused composer contact sheets together with
the final mobile and consent captures. No actionable P0/P1/P2 difference remains.

Required fidelity surfaces:

- **Fonts/typography:** existing locally bundled Inter retained, with strong compact
  heading hierarchy and readable transcript/input sizes. Long questions wrap,
  sidebar titles clamp instead of widening the layout, and small timestamps stay
  secondary. The compact context utility no longer dominates the chat.
- **Spacing/layout:** final history/chat boundary aligns with the reference;
  white transcript, right-aligned pale-teal user bubbles, unboxed assistant text,
  and bottom composer follow the approved hierarchy. Longer structured answers
  scroll inside the message region; earlier bubbles may be above the current
  scroll position, not discarded. Existing portal header is approximately 14 px
  taller than the illustrative reference and is intentionally preserved.
- **Colors/tokens:** existing #00695f / #0f766e teal, #f8fbfa neutral surface,
  #dbe6e3 borders and dark foreground are preserved. Selected history and user
  bubbles use restrained pale teal. Disabled send is deliberately muted, unlike
  the mock's active-looking empty send button.
- **Image quality/assets:** no raster artwork is called for. Existing HealthLink
  brand and Heroicons are reused; no generated decorative assets, hand-drawn SVG,
  emoji substitutes or placeholder artwork were introduced.
- **Copy/content:** real account data replaces illustrative identity/history.
  Conversation titles are first-question-derived without an extra model call.
  Original structured clinician questions, source labels and safety reminders are
  preserved instead of hiding product information to imitate short mock answers.
  A small provider-processing warning and private-history/delete notice are
  intentional safety additions. AI remains explanation-only.

## Interaction and implementation checklist

- [x] Actual send → authenticated API → PostgreSQL persistence → transcript rendering.
- [x] Two-turn transcript, reload/reopen, New conversation and delete confirmation.
- [x] One-request record consent, reset after editing/sending, General default.
- [x] Pending controls, failed-question preservation and idempotent retry covered.
- [x] Mobile history drawer, keyboard input, bounded internal scrolling, visible
  composer and no horizontal viewport overflow at tested sizes.
- [x] Symptom guidance and existing citizen/doctor/lab/admin journeys preserved.
- [x] Browser console/page exceptions, unexpected API failures and external browser
  requests checked by the acceptance harness: none in the final passing run.
- [x] Full backend 564 tests; frontend 57 files / 266 tests; lint, TypeScript and
  optimized build passed. Final optimized-build Edge browser suite: 9/9 passed.
- [x] Local migration upgrade and Alembic schema-drift check passed.
- [x] Separate release approval required; no commit, push or deployment performed.

## Expected differences and remaining limits

The existing portal chrome, real history count, dynamic content, optional
clinician questions and safety/privacy disclosures explain the remaining layout
differences. These are intentional product constraints, not missing mock content.
The in-app browser could not reconnect to loopback; the previously authorized
local Edge harness supplied authenticated rendered evidence. Live-provider answer
quality and production authenticated behavior were not retested in this UI task.
No P3 refinement is required before local owner review.

final result: passed

---

# Role-aware Settings and shared UI cleanup — 2026-10-20 (local, unreleased)

## Source, target and evidence

User asked to inspect the entire app, plan Settings, then implement it. The target
is an evolution of the existing HealthLink application, not a new visual identity
or pixel-identical clone. User approved local automated Edge/Playwright QA using
synthetic records; no production record changes or release were requested.

Fresh source truth: `.runtime/ui-settings-audit/before/manifest.json`, 38 numbered
routes at desktop/mobile sizes. Numbered audit and plan:
`docs/UI_SETTINGS_AUDIT_2026_10_20.md`. Current-run clinical source evidence came
from the 9/9 baseline browser journeys before UI edits. Initial admin detail
capture was blocked by a real async-params bug; its saved error screen is in
`before-detail/`. It was not accepted as a healthy detail screen.

Implementation evidence:

- `.runtime/ui-settings-audit/after/manifest.json`: 53 route states / 106 captures.
- `.runtime/ui-settings-audit/after-final/manifest.json`: 14 final Settings states.
- `.runtime/ui-settings-audit/after-final-dashboard/manifest.json`: four dashboards.
- `.runtime/browser-qa/results/`: final optimized-build care/Settings journeys,
  including doctor consultation, lab editing/finalization, mobile large-text menu,
  cross-session revocation and repaired admin detail. Browser report/result JSON
  under `.runtime/browser-qa/` is generated/ignored, not a release artifact.

Opened and inspected saved contact sheets and focused full-size screens. Source
and implementation were put together in the same comparison inputs, not compared
from memory:

- `comparisons/doctor-desktop.png`: full-view top region, daily work hierarchy.
- `comparisons/account-mobile.png`: mobile account navigation/form hierarchy.
- `comparisons/privacy-desktop.png`: existing access history vs reorganized section.
- `comparisons/citizen-header.png`: shared navigation/header proportions.
- `comparisons/navigation-focused.png`: unscaled, readable navigation detail.

All comparison paths above are under `.runtime/ui-settings-audit/`. Raw files are
local synthetic QA evidence only. Account names, IDs, fixture counts and activity
timestamps differ between isolated seed runs; they are not fidelity targets.

### Dimensions and normalization

Desktop CSS viewport 1440×1000, mobile 390×844, device scale factor 1. Full-page
source profile mobile: 390×2282; final profile mobile: 390×2390. Source doctor
dashboard: 1440×1944; final: 1440×1207 (practice configuration intentionally moved).
Final display desktop: 1440×1000; security mobile: 390×1163.
Full-view comparisons crop equal 1440×1000 or 390×844 top regions before equal
downsampling (desktop to 720 px wide; mobile remains 390 px). Focused navigation
uses identical x=84..1200, y=0..145 crops without downsampling, stacked together.
Production-build captures omit Next's development indicator; that is not a
product difference. Full-page modal screenshots can show content below the
viewport; actual modal focus/scroll locking was checked in the 390×844 viewport.

## Iteration history and findings

### Initial pass — blocked pending refinements

- [P2] Mobile Settings/account header repeated the citizen eyebrow and explanatory
  copy, pushing editable fields too far down. Evidence: first `after/24-...-mobile`
  capture versus source `before/22-...-mobile`. Removed repeated eyebrow/copy and
  redundant Back to dashboard button in embedded mode, compacted mobile heading
  spacing, retained visible email and Add a professional role. Post-fix evidence:
  `after-final/01-citizen-settings-mobile.png` and final `account-mobile.png`.
- [P2] All-session revocation initially looked like a neutral action because
  utility classes lost to the shared button rule. Added an explicit danger style.
  Evidence: `after/25-citizen-settings-security-mobile.png` versus
  `after-final/02-citizen-settings-security-mobile.png`.
- [P2] Doctor overview still said "schedule below" after moving that editor.
  Changed the sentence to link directly to Settings → Practice hours. Final
  evidence: `after-final-dashboard/02-doctor-dashboard-desktop.png` and combined
  `doctor-desktop.png`; daily clinical actions remain in the workspace.
- [P2] Wide result columns lacked an explicit mobile scroll cue/keyboard region.
  Added a mobile hint and focusable labelled report/trend scroll regions. Final
  care journey/table tests pass and final citizen report capture was inspected.
- [P1, functional audit] Admin identity detail requested `undefined` due to
  synchronous access to async Next.js params. Awaited params; final synthetic
  identity detail renders correctly and has a browser regression.

### Final comparison — passed

Reopened the combined source/final comparison inputs, final Settings sheets and
individual mobile/desktop/clinical captures after fixes. No actionable P0/P1/P2
visual finding remains in the tested states.

Required fidelity surfaces:

- Fonts/typography: existing locally bundled Inter retained; clear h1/section/
  field hierarchy, readable labels, wrapping email and responsive section names.
  Larger text is functional and does not hide controls at tested widths.
- Spacing/layout: slimmed shared chrome from 136 to 120 CSS px on desktop;
  preserved icon rail, resizing and familiar text navigation. Settings uses an
  anchored desktop section list and wrapping mobile grid. Mobile account header
  is intentionally compact; doctor dashboard is shorter without removing tools.
- Colors/tokens: existing citizen teal, professional blue, admin indigo, neutral
  surfaces and border tokens retained. Selected sections use role-tinted surfaces;
  destructive session revocation is visibly distinct. Screenshot review does not
  assert full contrast/WCAG compliance.
- Image quality/assets: existing brand/hero assets and Heroicons remain. No new
  raster art was needed; no custom SVG, emoji or CSS-art replacements were added.
- Copy/content: no fictitious password/2FA/notification features. Display settings
  explicitly say browser-only/shared-device scope. Session revocation clearly
  includes this session/other portals. AI remains an explainer, never a diagnosis
  or prescription; records require explicit per-request consent in the chat.

## Interaction and verification checklist

- [x] Settings entry from account header and navigation in citizen/doctor/lab/admin.
- [x] Existing profile saves, masked identity and irreversible NID confirmation retained.
- [x] Legacy profile/privacy URLs redirect; existing verification route remains usable.
- [x] Verified-doctor-only practice editor; lab/pending/rejected role denial covered.
- [x] Existing schedule saves/reloads, with an unsaved-edits warning on navigation.
- [x] Display allowlist, corrupt/blocked storage, cross-tab updates, reset and reload.
- [x] Mobile focus containment, inert background, scroll locking, Escape and focus restore.
- [x] Current/all-session sign-out confirmation/error handling; two same-account
  sessions revoked while another synthetic account remains signed in.
- [x] Key clinical workflows, AI history/delete/consent, on-demand PDFs, manual
  Bangladesh area/nearest search and admin facility-coordinate privacy preserved.
- [x] Final backend 564 tests; frontend 60 files / 291 tests; lint, typecheck and
  optimized build passed. Final optimized Edge suite: 12/12 passed (53.2 s).
- [x] No unexpected API/console errors, external browser requests or document
  overflow in asserted states. Settings widths 320/390/768/1366; portal regression
  matrix also 1920; larger-text smoke includes main citizen care/AI screens.
- [x] Changed-file secret-pattern scan and `git diff --check` clean. No commit,
  push, deployment, production database write, schema migration or API-key change.

Limits: synthetic local data, mock AI and bounded viewport/keyboard testing only;
not a screen-reader certification, all-browser guarantee, live-provider evaluation
or production QA. Existing production runtime-log access gap is unchanged.
No required P3 refinement remains for local review. Fresh approval required before
any release operation.

final result: passed

---

# Light/Dark/System theme follow-up — 2026-10-20 (local only)

Requested addition: Color theme in Settings → Display & accessibility. This is
an extension of the existing approved Settings layout, not a new visual direction.
Light remains the default; Dark and Use system setting are persisted on this
browser only. OS changes and other-tab changes update live. Static trusted head
initialization applies the saved theme before body paint; missing/corrupt/blocked
storage safely falls back to Light. Hydration suppression is limited to the html
attributes intentionally changed by that bootstrap.

Evidence from this follow-up's actual optimized Edge run:

- `.runtime/browser-qa/results/healthlink-Light-dark-Syst-8c363-hanges-and-synchronize-tabs/`:
  `settings-dark-desktop.png`, `settings-dark-mobile.png`,
  `settings-light-mobile.png` and dark public/auth/validation captures.
- `.runtime/browser-qa/results/healthlink-Dark-portal-mat-a56c8-records-chat-and-workspaces/`:
  desktop/mobile dark Settings, dashboards, medical history, diagnostics, doctor
  discovery, AI transcript/composer, practice editor and admin registries.
- The complete citizen → doctor → lab → citizen care journey now also runs in
  Dark: clinical editing, previous prescriptions, PDFs, lab draft/finalize and
  result/AI explanation. Those captures remain in the care-journey result folder.
- `.runtime/theme-qa/themes-1.jpg` through `themes-4.jpg`: current-run review sheets.
- `.runtime/theme-qa/light-dark-mobile.png`: Light and Dark together at identical
  390×844 CSS-pixel viewport crops, scale factor 1, no resampling, with a 40-pixel
  label strip. Both states use the same fixture/layout; only selected theme differs.
  Desktop Settings uses 1366×900 viewport/full-page capture. Long clinical and
  registry pages have additional full-page evidence; review sheets crop top regions.

Opened the saved combined comparison, all four review sheets, full desktop
Settings, AI transcript/composer and consultation captures. Readability fixes from
the first pass: stronger native-field boundaries, retained pink invalid-field
borders/feedback, transparent inactive navigation borders and original role-brand
fills under the white logo mark. No image inversion or replacement artwork.

Fidelity surfaces:

- Typography: same Inter, weights, hierarchy, wrapping and layout in both modes.
- Spacing: color-only adaptation; theme selector uses the existing setting row.
- Tokens: dark canvas #0b111b, raised surfaces #131e2c, readable neutral text,
  teal/blue/indigo role links and distinct semantic warning/error/success surfaces.
  Solid action fills keep white text; original brand contrast is preserved.
- Assets: original logo/hero/Heroicons retained without invert filters.
- Copy: Light/Dark/Use system setting labels, device-only scope and privacy notices
  remain explicit. AI consent and medical behavior are unchanged.

Verification: **61 frontend files / 298 tests**, lint/typecheck/optimized build and
**14/14 browser journeys** passed. Coverage includes saved theme at first body
insertion (before hydration), refresh, live OS changes, cross-tab updates,
explicit-theme precedence, corrupt/blocked storage, error-field focus, print media,
all four roles and mobile overflow. Dark styling is screen-only; printing remains
light and generated PDFs/API/provider behavior are untouched. Browser harness
readiness was tightened to await hydrated legacy redirects and observable viewport/
media settling; no auth policy or production setting was weakened.

Backend source unchanged from the preceding 564-test baseline. All evidence is
synthetic/local and ignored; no live-provider or production claim. No exhaustive
WCAG/screen-reader certification. No commit, push or deployment; fresh release
approval still required.

final result: passed
