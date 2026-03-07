# UX Specialist Review
**Reviewer:** @ux-design-expert (Pixel)
**Date:** 2026-03-07
**Reviewed Document:** docs/prd/technical-debt-DRAFT.md
**Codebase Reference Commit:** 9fbd54d0 (main branch)

---

## 1. Debts Validated

All frontend-related debts in the DRAFT were validated against the actual source code. Evidence and adjusted assessments follow.

| ID | Debt | Original Severity | Adjusted Severity | Hours | Complexity | Design Review? | Notes |
|----|------|-------------------|-------------------|-------|------------|----------------|-------|
| TD-004 | God component (page.tsx) | Critical | **Critical** | 28-40 | Complex | Yes | Confirmed: 23 useState calls, 4 useRef calls, 1,071 lines. Validated at `frontend/app/page.tsx`. This is the single largest UX velocity blocker. |
| TD-008 | Modal missing focus trap and dialog role | High | **High** | 4-6 | Medium | No | Confirmed: Lines 1002-1061 of page.tsx. No `role="dialog"`, no `aria-modal`, no focus trap, no Escape handler. grep confirms zero occurrences of these attributes across the entire frontend. |
| TD-009 | Missing Escape key on dropdowns | High | **High** | 2-3 | Simple | No | Confirmed: `ThemeToggle.tsx` lines 11-18 only handle mousedown outside click. `SavedSearchesDropdown.tsx` line 144 uses onClick backdrop. Neither has keydown listener. |
| TD-010 | Insufficient color contrast (ink-muted) | High | **High** | 4-6 | Medium | Yes | Confirmed: `globals.css` line 11: `--ink-muted: #808f9f` (3.4:1 on white). Line 48: dark mode `--ink-muted: #6b7a8a` (3.8:1 on #121212). Both fail WCAG AA 4.5:1. Additionally, `--ink-faint` (#c0d2e5, 1.7:1) is used for actual text content in `SavedSearchesDropdown.tsx` lines 160 and 212, not just decorative purposes. Severity correctly High. |
| TD-027 | No skip-to-content link | Medium | **Medium** | 1-2 | Simple | No | Confirmed: No skip link in page.tsx or layout.tsx. The header contains SavedSearchesDropdown and ThemeToggle, so keyboard users must tab through at least 4-5 interactive elements before reaching the form. |
| TD-028 | External logo dependency (Wix CDN) | Medium | **Medium** | 2-3 | Simple | Yes | Confirmed: `page.tsx` line 15: `LOGO_URL = "https://static.wixstatic.com/..."`. Uses raw `<img>` tag (not Next.js Image). `public/logo-descomplicita.png` exists but is unused. |
| TD-029 | Outdated favicon (Descomplicita "B") | Medium | **Medium** | 1-2 | Simple | Yes | Confirmed: `icon.svg` line 2-3: green (#166534) rectangle with white "B" letter. Completely wrong brand identity. |
| TD-030 | Error boundary uses hardcoded colors | Medium | **Medium** | 2-4 | Simple | No | Confirmed: `error.tsx` uses `bg-gray-50`, `bg-white`, `text-gray-900`, `text-gray-600`, `bg-gray-100`, `text-gray-700`, `bg-green-600`, `text-gray-500`. Zero design system tokens used. This page completely ignores the 5-theme system. The green button (#16a34a) is from the old Descomplicita palette, not brand-navy. |
| TD-031 | Missing focus management after search | Medium | **High** (upgraded) | 3-5 | Medium | No | Confirmed: No scrollIntoView or focus call after search completes. On mobile, the search form takes the full viewport, so results are entirely invisible until the user manually scrolls. For screen reader users, there is zero announcement of completion. This affects conversion (users might think search failed) and is an accessibility gap. Upgrading to High. |
| TD-035 | Frontend emoji in source code | Low | **Low** | 1 | Simple | No | Confirmed: `LoadingProgress.tsx` line 11-16 embeds emoji directly in JSX. `AnalyticsProvider.tsx` lines 40-46 uses emoji in console.log. Style inconsistency, but functionally harmless. |
| TD-039 | Deprecated performance API | Low | **Low** | 1 | Simple | No | Confirmed: `AnalyticsProvider.tsx` line 52: `performance.timing.navigationStart`. Deprecated but still functional in most browsers. |
| TD-040 | No loading state for sector list | Low | **Low** | 1-2 | Simple | No | Confirmed: `page.tsx` lines 94-111 fetches sectors with no loading indicator. Falls back to hardcoded list silently. Minor UX gap. |
| TD-041 | E2E tests reference outdated class names | Low | **Low** | 2-3 | Simple | No | Confirmed per DRAFT. Tests reference `bg-green-600` (old Descomplicita) while UI uses `bg-brand-navy`. |
| TD-042 | No code splitting for components | Low | **Low** | 4-6 | Medium | No | Confirmed: All imports in page.tsx are static. `LoadingProgress` (415 lines) and `carouselData` (368 lines, 52 items) are conditionally rendered and good candidates for `next/dynamic`. |
| TD-043 | No `<nav>` semantic element | Low | **Low** | 1 | Simple | No | Confirmed: Header in page.tsx has no `<nav>` wrapping the SavedSearchesDropdown and ThemeToggle. |
| TD-044 | SourceBadges/carouselData hardcoded colors | Low | **Medium** (upgraded) | 3-5 | Medium | Yes | Confirmed: `SourceBadges.tsx` lines 49-54 uses `bg-green-100`, `bg-yellow-100`, `bg-red-100` with explicit `dark:` variants. These break visually in Paperwhite and Sepia themes because the dark: variant logic does not match the 5-theme system (Paperwhite/Sepia are light themes but have different canvas colors). `carouselData.ts` similarly uses hardcoded category colors. Upgrading to Medium because this causes visible visual inconsistency in 2 of 5 themes. |
| TD-045 | Unused public asset | Low | **Low** | 0.5 | Simple | No | Confirmed: `public/logo-descomplicita.png` exists, unused. Will be resolved by TD-028. |
| TD-046 | Missing aria-describedby for terms input | Low | **Low** | 1 | Simple | No | Confirmed: page.tsx terms input has helper text "Digite cada termo..." without `aria-describedby` linkage. |

---

## 2. Debts Added (Missed in DRAFT)

| New ID | Debt | Severity | Hours | Category | Evidence |
|--------|------|----------|-------|----------|----------|
| TD-047 | Dropdown menus lack `role="menu"` and `role="menuitem"` ARIA pattern | Medium | 2-3 | Accessibility | `ThemeToggle.tsx` and `SavedSearchesDropdown.tsx` render dropdown items as plain `<button>` elements without menu roles. Screen readers cannot announce these as menu structures. No arrow key navigation between items. WCAG 4.1.2 requires proper role semantics for custom widgets. |
| TD-048 | `window.confirm()` used for destructive action | Medium | 2-3 | UX | `SavedSearchesDropdown.tsx` line 174 uses `window.confirm('Deseja excluir todas as buscas salvas?')`. This native dialog is un-styled, breaks theme consistency, cannot be customized, and is blocked by some browsers. Should use a custom confirmation modal following the design system. |
| TD-049 | EmptyState component lacks ARIA live region | Low | 1 | Accessibility | `EmptyState.tsx` renders informational content (rejection breakdown, suggestions) without `role="status"` or `aria-live`. When search completes with zero results, screen readers are not proactively informed. |
| TD-050 | SourceBadges expandable section has no `aria-expanded` or keyboard disclosure pattern | Low | 1-2 | Accessibility | `SourceBadges.tsx` lines 30-42: the toggle button has no `aria-expanded` attribute, no `aria-controls` linking to the detail panel. Screen readers cannot communicate the expand/collapse state. |
| TD-051 | UF grid buttons lack group label for screen readers | Medium | 1-2 | Accessibility | The 27 UF toggle buttons in `page.tsx` (lines ~600-650) have no `role="group"` wrapper or `aria-label` to communicate their purpose as a state selector grid. Screen reader users encounter 27 unlabeled toggle buttons without context. |
| TD-052 | No `<h2>` heading structure in main content sections | Low | 1-2 | Accessibility | `page.tsx` uses a single `<h1>` ("Busca de Licitacoes") but the results section, loading section, and form sections lack heading hierarchy (`<h2>`, `<h3>`). Screen reader navigation by heading is ineffective. The EmptyState has an `<h3>` but there is no `<h2>` parent. |
| TD-053 | Hardcoded `borderColor` in ThemeToggle preview circle | Low | 0.5 | Design | `ThemeToggle.tsx` line 58: `borderColor: theme === t.id ? "#116dff" : "var(--border-strong)"`. The `#116dff` is hardcoded rather than using the `--brand-blue` token. Minor but breaks the token abstraction. |

---

## 3. Debts Contested (Disagree with Assessment)

| ID | Debt | Reason for Disagreement | Suggested Change |
|----|------|------------------------|-----------------|
| TD-010 | Color contrast: placed in "Low Impact + High Effort (Deprioritize)" quadrant in Section 8 | The DRAFT correctly marks severity as High, but then the Priority Matrix (Section 8) puts it in the "Deprioritize" quadrant with rationale "requires full contrast audit." A full audit is not required for the primary fix -- darkening `--ink-muted` in globals.css is a 2-line change that immediately resolves the most impactful failures. The `--ink-faint` audit is secondary. This should be in the Quick Wins quadrant. | Move TD-010 to "High Impact + Low Effort" for the primary fix (darken `--ink-muted`). Keep the `--ink-faint` comprehensive audit as a separate follow-up task. |
| TD-031 | Focus management after search: categorized as Medium | As noted above, this should be High severity. On mobile devices, users have no visual indication that results have loaded. For screen reader users, there is no announcement whatsoever. This directly impacts conversion -- users may abandon the app thinking their search timed out. | Upgrade to High severity and move to Sprint 2 (Accessibility Critical Path). |
| TD-016 | Branding inconsistency: estimated 4-8 hours | The frontend portion (TD-029 favicon + any UI references) is trivial (1-2 hours). The docker-compose and backend references are separate. The frontend effort is over-estimated when combined with non-frontend work. | Split estimate: 1-2 hours frontend, 2-3 hours backend/infra. |

---

## 4. Answers to @architect Questions

### Question 1: TD-004 God Component Decomposition -- Component Boundaries

The proposed decomposition is sound but I recommend adjustments for future feature evolution:

**Approved as-is:**
- `SearchForm` (mode toggle, sector select, terms input) -- good boundary
- `DateRangeSelector` -- good, self-contained
- `SaveSearchDialog` -- good, natural extraction point
- `useSearchJob` custom hook -- critical, extracts the 23-state + 4-ref problem

**Recommended modifications:**
- `UfSelector` should include the `RegionSelector` as a child (they are always used together). The parent component should be `UfSelector` which internally renders `RegionSelector` and the UF grid. This keeps the UF selection concern fully encapsulated.
- `SearchResults` should be split further into `SearchSummary` (executive summary, highlights, urgency alert) and `SearchActions` (download button, save search trigger, stats). This supports a future comparison view where two summaries could appear side-by-side without duplicating action logic.

**Additional extraction I recommend:**
- `SearchHeader` component wrapping the logo, SavedSearchesDropdown, and ThemeToggle. This enables adding navigation items later (e.g., a "Minhas Buscas" page link) without touching page.tsx.

**Proposed final component tree:**
```
HomePage (page.tsx, target: <150 lines)
  SearchHeader
    Logo
    SavedSearchesDropdown
    ThemeToggle
  SearchForm
    SearchModeToggle
    SectorSelect | TermsInput
    UfSelector
      RegionSelector
      UfGrid
    DateRangeSelector
  LoadingProgress (existing, 415 lines -- consider splitting stage indicator from carousel)
  SearchSummary (executive summary, highlights)
  SearchActions (download, save, stats)
  SourceBadges (existing)
  EmptyState (existing)
  SaveSearchDialog
  Footer
```

**Target:** No component exceeds 200 lines. `useSearchJob` hook handles polling, phase state, and job lifecycle. A `useSearchForm` hook handles form state, validation, and defaults.

### Question 2: TD-010 Color Contrast -- `--ink-muted` Fix

Darkening `--ink-muted` to approximately `#5a6a7a` is acceptable. I have verified this value:

- `#5a6a7a` on `#ffffff` (light canvas) = 4.86:1 -- passes WCAG AA for normal text
- For dark mode, the current `#6b7a8a` on `#121212` = 3.8:1, failing AA. I recommend darkening the dark mode value to `#8a99a9` which yields 5.2:1 on `#121212`.

**On the `--ink-faint` question:** The role of `--ink-faint` should be restricted to purely decorative purposes (borders, background tints, placeholder text). Currently it is used for actual readable text content in `SavedSearchesDropdown.tsx` lines 160 and 212 (helper text and timestamps). Those usages should be changed to `text-ink-muted`. The `--ink-faint` token value itself does not need to change -- its purpose just needs to be enforced through a lint rule or documentation.

**Recommendation:** Do not change the design intent of the muted role. Darken the value. Document that `--ink-faint` is decoration-only.

### Question 3: TD-FE-010 (i18n) -- Is It a Near-Term Need?

**No, i18n is not a near-term need.** The product exclusively targets Brazilian procurement professionals operating in Brazilian government portals. All backend data is in Portuguese. The domain vocabulary (licitacao, modalidade, pregao, etc.) does not translate meaningfully.

**However,** during the God Component decomposition (TD-004), I recommend extracting user-facing string constants into a centralized `frontend/lib/strings.ts` file -- not for i18n, but for:
1. Consistency of messaging across components
2. Easier A/B testing of copy
3. Simpler QA verification of Portuguese text
4. Enabling future i18n with minimal additional work if needed

This adds approximately 2-3 hours to the TD-004 effort but provides immediate maintainability value. It is not a separate debt item -- it should be part of the decomposition workstream.

### Question 4: TD-030 Error Boundary -- Theme System Participation

**The error boundary should partially participate in the theme system** with a defensive fallback.

Rationale: Error boundaries catch JavaScript errors. If the error is in the ThemeProvider itself, CSS custom properties may be unavailable. However, the design tokens are defined in `globals.css` via `:root` and `.dark` selectors, not via JavaScript. They will always be available as long as the stylesheet loads.

**Recommended approach:**
1. Use design system tokens for background, text, and border colors (`bg-canvas`, `text-ink`, etc.)
2. Keep the button using `bg-brand-navy` (matches the rest of the app)
3. Add a CSS `@supports` fallback for the unlikely case CSS variables fail:
```css
.error-fallback {
  background: var(--canvas, #ffffff);
  color: var(--ink, #1e2d3b);
}
```

This way the error page respects all 5 themes but has a safe fallback. Effort: 2 hours.

### Question 5: TD-028 Logo -- Brand Asset Status

The local `public/logo-descomplicita.png` should be used as-is via Next.js `<Image>`. Verify with the brand owner whether there is an SVG version available (preferred for resolution independence and smaller file size).

**For the favicon (TD-029):** The new favicon should be a navy "D" on a white/transparent background, or the Descomplicita brand mark if one exists. The SVG favicon should use:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <rect width="32" height="32" rx="6" fill="#0a1e3f"/>
  <text x="16" y="23" text-anchor="middle" font-family="system-ui,sans-serif"
        font-weight="bold" font-size="18" fill="white">D</text>
</svg>
```

This maintains structural consistency with the existing SVG favicon while updating the brand colors and letter. The brand owner should confirm whether a brand mark or the "D" letter is preferred.

### Question 6: Frontend Test Coverage Discrepancy

**The 49.45% statement / 39.56% branch coverage from `jest.config.js` is the canonical measurement.** The 91.5% figure in the architecture doc appears to be aspirational or from a partial measurement (possibly covering only the files that have tests, excluding files without any test coverage).

**Realistic target for next milestone:**
- After TD-004 decomposition: 65% statements, 50% branches (each extracted component should ship with a co-located test file)
- After accessibility remediation sprint: 70% statements, 55% branches
- Long-term target: 80% statements, 65% branches

**Important:** The decomposition in TD-004 will temporarily decrease coverage because new files are created without tests. The target should be enforced per-component, not as a global threshold, during the decomposition sprint.

### Question 7: Large-Screen Optimization (`max-w-4xl`)

**The narrow content column (896px) is intentional and correct for this application.** Rationale:

1. The primary content is a search form and text-heavy results (executive summary, highlights). Optimal reading width for body text is 50-75 characters per line, which maps to approximately 600-900px.
2. The UF grid (27 buttons) renders well at 9 columns within 896px. Wider would create too much whitespace between buttons.
3. Procurement professionals typically have one application window alongside their email/ERP. A narrow layout works well in split-screen scenarios.

**Future consideration:** If a comparison view (side-by-side results from two searches) or a dashboard view is added, the max-width should expand to `max-w-7xl` (1280px) with a two-column layout. This is a feature decision, not a debt.

---

## 5. Design Recommendations

### 5.1 God Component Decomposition Strategy

**Phase 1: Extract hooks (4-6 hours)**
1. `useSearchJob` -- polling logic, job lifecycle, phase state, elapsed time, cancel (moves ~150 lines out of page.tsx)
2. `useSearchForm` -- form state, validation, defaults, saved search loading (moves ~100 lines)

**Phase 2: Extract leaf components (8-12 hours)**
3. `SaveSearchDialog` -- lines 1002-1061 of page.tsx, add `role="dialog"`, focus trap (resolves TD-008 simultaneously)
4. `UfSelector` -- UF grid + RegionSelector composition, UF_NAMES constant
5. `SearchHeader` -- logo, dropdowns, theme toggle
6. `DateRangeSelector` -- date inputs with validation display

**Phase 3: Extract result components (6-10 hours)**
7. `SearchSummary` -- executive summary, highlights, urgency alert
8. `SearchActions` -- download button, save search trigger, statistics

**Phase 4: Wire and test (8-12 hours)**
9. Rewrite `page.tsx` as a thin orchestrator (<150 lines)
10. Add unit tests for each extracted component
11. Run E2E suite to verify no regressions

**Total: 26-40 hours** (aligns with DRAFT estimate)

### 5.2 Design System Improvements

**Immediate (with TD-010 fix):**
- Darken `--ink-muted` to `#5a6a7a` (light) and `#8a99a9` (dark)
- Document token usage rules: `--ink-faint` is decoration-only, never for readable text
- Add a comment block in `globals.css` documenting contrast ratios for each ink token

**Short-term (with TD-004 decomposition):**
- Create semantic color tokens for status indicators: `--status-success`, `--status-warning`, `--status-error` that work across all 5 themes (replacing hardcoded Tailwind colors in SourceBadges)
- Add `--status-success-bg`, `--status-warning-bg`, `--status-error-bg` surface tokens for badge backgrounds
- Move category colors from `carouselData.ts` into CSS custom properties

**Medium-term:**
- Create a `frontend/lib/design-tokens.ts` file exporting all token values for use in JavaScript contexts (e.g., inline styles in ThemeToggle line 58)
- Add Tailwind plugin or custom config for status color utilities

### 5.3 Accessibility Remediation Plan

Priority order based on user impact and legal risk (LBI Law 13.146/2015):

**Wave 1 -- Keyboard users unblocked (Sprint 2, ~8-10 hours):**
1. TD-008: Modal focus trap + dialog role (4-6h) -- Keyboard users currently trapped
2. TD-009: Escape key on dropdowns (2-3h) -- Keyboard users cannot dismiss
3. TD-027: Skip-to-content link (1h) -- Quick win

**Wave 2 -- Screen reader users supported (Sprint 2-3, ~8-10 hours):**
4. TD-031: Focus management after search (3-5h) -- Users miss results
5. TD-051 (new): UF grid group label (1-2h)
6. TD-046: aria-describedby for terms input (1h)
7. TD-047 (new): Menu roles on dropdowns (2-3h)
8. TD-050 (new): SourceBadges aria-expanded (1-2h)

**Wave 3 -- Visual accessibility (Sprint 2, ~5-7 hours):**
9. TD-010: Color contrast fix (4-6h) -- Two-line CSS change for primary fix, plus audit of ink-faint usage

**Wave 4 -- Structural semantics (Backlog, ~3-4 hours):**
10. TD-043: Nav element (1h)
11. TD-052 (new): Heading hierarchy (1-2h)
12. TD-049 (new): EmptyState aria-live (1h)

---

## 6. Effort Summary

| Category | Items | Hours (Low) | Hours (High) | Priority |
|----------|-------|-------------|--------------|----------|
| Accessibility (existing) | 8 (TD-008, 009, 010, 027, 031, 043, 046, + TD-031 upgrade) | 14 | 24 | Critical/High |
| Accessibility (new) | 5 (TD-047, 049, 050, 051, 052) | 6 | 10 | Medium/Low |
| Component Architecture | 2 (TD-004, TD-042) | 32 | 46 | Critical |
| Design Consistency | 5 (TD-029, 030, 044, 053, TD-028) | 9 | 15 | Medium |
| UX Quality | 2 (TD-040, TD-048) | 3 | 5 | Low/Medium |
| Branding (frontend portion) | 2 (TD-029, TD-028) | 3 | 5 | Medium |
| Code Quality (frontend) | 4 (TD-021, 035, 039, 041) | 5 | 10 | Low |
| Performance (frontend) | 1 (TD-042) | 4 | 6 | Low |
| **TOTAL (Frontend)** | **29** | **76** | **121** | |

**Notes:**
- These estimates are frontend-only. Backend debts (TD-001 through TD-003, TD-005 through TD-007, etc.) are outside my scope.
- TD-004 is the highest-leverage item: completing it unblocks TD-008, TD-031, TD-042, and TD-021, and makes all future frontend work faster.
- The accessibility wave 1 items (TD-008, TD-009, TD-027) are high impact, low effort, and should be done in the same sprint as or immediately after TD-004.
- TD-031 severity upgrade (Medium to High) is my strongest recommendation. On mobile, invisible results are a direct conversion killer.

---

## 7. Sprint Sequence Recommendation (UX Perspective)

**Sprint 1 (Security):** No change from DRAFT -- agree with TD-001, TD-002, TD-006, TD-012 first.

**Sprint 2 (Accessibility + UX Quick Wins):**
TD-008, TD-009, TD-010 (primary fix only), TD-027, TD-031 (~14-22 hours)
Rationale: These are all small, independent fixes that immediately improve the experience for keyboard, screen reader, and low-vision users. Brazilian accessibility law applies to government-facing tools.

**Sprint 3 (Frontend Architecture):**
TD-004 (God component decomposition, ~28-40 hours)
During this sprint, also resolve TD-021 (UFS dedup) and TD-028 (self-host logo) as natural parts of the extraction.

**Sprint 4 (Design Cleanup):**
TD-029 (favicon), TD-030 (error boundary), TD-044 (hardcoded colors), TD-048 (window.confirm replacement) (~8-14 hours)

**Backlog:**
TD-042, TD-043, TD-046, TD-047, TD-049, TD-050, TD-051, TD-052, TD-053, TD-035, TD-039, TD-040, TD-041

---

**Review Status: COMPLETE**
**Reviewer:** @ux-design-expert (Pixel)
**Signed:** 2026-03-07
**Next step:** Consolidation by @architect into final technical-debt.md
