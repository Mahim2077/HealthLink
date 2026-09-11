# HealthLink portal redesign — design QA

## Comparison target

- Source: `docs/ui-design-audit-2026-09-08/selected-citizen-overview.png`
  (`1487 × 1058` pixels).
- Implementation: authenticated Citizen overview at `/citizen/dashboard`, with
  the navigation rail collapsed, captured in the Codex in-app browser at a
  `1280 × 720` CSS viewport and `1280 × 720` output pixels.
- Normalization: the source was proportionally reduced to 1280 pixels wide and
  top-cropped to 720 pixels. This avoids treating the source image's larger
  canvas as a product defect.

Pragmatic note: exact responsive reflow in the source cannot be inferred from
a single static mock, so the comparison evaluates the selected visual scheme,
hierarchy, proportions, and interaction state rather than false pixel-level
precision.

## Evidence reviewed together

- Full composition: `docs/ui-design-audit-2026-09-08/design-qa-comparison.png`
- Focused header and primary action:
  `docs/ui-design-audit-2026-09-08/design-qa-focused-header-actions.png`
- Latest implementation capture:
  `docs/ui-design-audit-2026-09-08/implementation-citizen-overview.png`
- Responsive evidence:
  `docs/ui-design-audit-2026-09-08/implementation-mobile-profile.png`

The focused comparison was necessary because it makes the account control,
brand mark, type hierarchy, CTA scale, icon treatment, and top-of-page spacing
readable at the same time.

## Findings

No actionable P0, P1, or P2 findings remain.

- [P3] The implemented collapsed rail is intentionally a little narrower than
  the proportion shown in the generated mock. This gives the application more
  working space at common laptop widths while preserving the approved dark-teal
  icon-rail treatment. The rail can be expanded and resized from 224 to 340
  pixels, so this does not reduce usability or hide a required control.
- [P3] A small amount of vertical-position drift in the normalized comparison
  comes from scaling the taller source canvas to the browser's 1280-pixel
  capture width. The implementation's native 96-pixel header and content rhythm
  are internally consistent and do not create overflow.

## Iteration history

### Pass 1 — blocked

- [P2] The header account control stacked its secondary action and used a
  forward chevron; the source uses one compact inline identity group.
- [P2] The sidebar brand treatment did not provide the source's white-tile
  contrast on dark teal.
- [P2] An authenticated footer added visual weight absent from the selected
  dashboard design.
- [P2] The primary doctor action was vertically compressed and its supporting
  copy had a noticeably different measure.
- [P2] Several secondary pages still used text arrow glyphs instead of the
  project's icon system.

### Fixes applied

- Rebuilt the account affordance as an inline avatar, name, action, and
  disclosure group.
- Used the shared Heroicons set for the sidebar mark and navigation/back/forward
  affordances.
- Removed the authenticated footer while retaining the public-portal footer.
- Increased the doctor CTA's icon and button scale and constrained the copy to
  the approved two-line measure.
- Re-captured the implementation and regenerated both comparison images.

### Pass 2 — passed

The revised capture contains no broken layout, clipped persistent control,
missing primary action, or moderate-or-higher fidelity mismatch.

## Required fidelity surfaces

- Fonts and typography: self-hosted Inter Variable is applied globally. The
  weight, tracking, line height, truncation, and display/body hierarchy closely
  follow the source; small labels retain sufficient optical weight.
- Spacing and layout rhythm: the sticky 96-pixel portal header, restrained page
  width, pale-teal action band, section spacing, 48-pixel minimum targets,
  rounded corners, and low elevation produce the approved quiet clinical
  rhythm. No horizontal overflow was observed.
- Colors and tokens: the dark-teal rail, pale-teal action surface, white header,
  ink text, muted indigo copy, subtle borders, and semantic portal accents map
  consistently to the selected palette with accessible contrast.
- Image quality and asset fidelity: the target contains no photography or
  raster illustration. The implementation uses the installed Heroicons library
  for interface icons and the existing HealthLink brand component on public
  screens; there are no placeholder images or raster-scaling artifacts.
- Copy and content: the approved welcome, doctor-discovery, and appointments
  copy is preserved. National ID information is absent from the overview and
  remains available only in the protected profile workflow. Professional-role
  onboarding moved to Profile as an account action without changing its copy or
  destination.

## Functional and responsive checks

- Citizen registration and sign-in reached the authenticated overview against
  an isolated local PostgreSQL database.
- Citizen overview, doctor search, appointments, and profile routes loaded.
- Professional onboarding/login and admin login routes loaded.
- Desktop navigation expands, collapses, and resizes with the keyboard.
- Mobile navigation opens as a modal drawer and closes with Escape.
- Browser console inspection returned no warnings or errors.
- Automated typecheck, lint, 192 unit/component tests, and the production build
  all passed after the final changes.

## Final Phase 14 refinement

- Citizen Overview no longer displays `Add a professional role`, leaving the
  page focused on care discovery and appointments.
- Citizen Profile presents the same action in its responsive header action
  group beside `Back to dashboard`, using the established pale-sky account
  accent and 44-pixel minimum control height.
- The route remains `/professional/onboard`; no workflow, authorization, form,
  or backend behavior changed.
- Focused component tests and the full 43-file / 196-test frontend suite passed.
  An authenticated local browser flow verified Overview → Profile →
  Professional onboarding with no console warnings or errors.

## Portal-theme consistency closeout (2026-09-11)

- The selected design and all existing interactions remain unchanged. The
  shared public/authenticated shell and second-row navigation now inherit
  portal-scoped tokens: Citizen teal/green, Professional sky/blue, and Admin
  indigo/purple.
- The account avatar/action, desktop rail, collapse and resize controls, mobile
  drawer, active navigation, focus rings, and form accents follow the current
  portal without duplicating shell components.
- The remaining indigo accents were removed from Citizen Overview, and the
  remaining teal current-patient surface was changed to sky in the Professional
  chamber.
- Emerald success, amber warning, rose error, and slate neutral treatments are
  intentionally unchanged because they communicate status rather than portal
  identity.
- ESLint, TypeScript, 43 Vitest files / 199 tests, and the optimized 22-route
  build passed. Local visual checks confirmed all three login palettes.
- No route, feature, workflow, API, authorization rule, schema, migration, or
  dependency changed, and no Phase 15 behavior was introduced.

## Implementation checklist

- [x] Selected visual target resolved and preserved in project documentation.
- [x] Shared shell applied to Citizen, Professional, and Admin portals.
- [x] Existing role, authorization, API, and workflow behavior preserved.
- [x] Desktop and mobile navigation interactions verified.
- [x] Source and implementation reviewed in combined comparison images.
- [x] All P0/P1/P2 visual findings fixed and re-captured.
- [x] Citizen, Professional, and Admin portal identity colors are consistent.

final result: passed
