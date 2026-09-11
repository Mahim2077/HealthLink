# HealthLink public landing page — design QA

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
