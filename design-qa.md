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
