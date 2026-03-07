# Story 3.0: Frontend Quality + Accessibility Compliance

**Sprint:** 3
**Epic:** Resolucao de Debitos Tecnicos
**Priority:** High
**Estimated Points:** 13
**Estimated Hours:** 29-47

## Objetivo

Complete WCAG 2.1 AA accessibility compliance across all frontend components and align the design system for consistency across all 5 themes. After the Sprint 2 decomposition, extracted components are now individually testable and modifiable. This sprint addresses 13 accessibility debts, design token consistency, code splitting for performance, and brand asset updates. Brazilian accessibility law (LBI -- Law 13.146/2015) requires digital accessibility for government-facing tools.

## Debts Addressed

| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-008 | Modal missing focus trap, dialog role, Escape close | 4-6 | Frontend |
| TD-031 | Missing focus management after search (scroll, focus, aria-live) | 3-5 | Frontend |
| TD-029 | Outdated favicon (Descomplicita "B") | 1-2 | Frontend |
| TD-030 | Error boundary uses hardcoded colors instead of design tokens | 2-4 | Frontend |
| TD-042 | No code splitting (dynamic imports for heavy components) | 4-6 | Frontend |
| TD-043 | No `<nav>` semantic element in header | 1 | Frontend |
| TD-044 | SourceBadges/carouselData hardcoded colors break in Paperwhite/Sepia themes | 3-5 | Frontend |
| TD-046 | Missing aria-describedby for terms input | 1 | Frontend |
| TD-047 | Dropdown menus lack ARIA menu pattern (role="menu", role="menuitem") | 2-3 | Frontend |
| TD-048 | window.confirm() used for destructive action (not accessible, not themed) | 2-3 | Frontend |
| TD-049 | EmptyState component lacks ARIA live region | 1 | Frontend |
| TD-050 | SourceBadges lacks aria-expanded attribute | 1-2 | Frontend |
| TD-051 | UF grid buttons lack group label (role="group", aria-label) | 1-2 | Frontend |
| TD-052 | No heading hierarchy in main sections (h2/h3 structure) | 1-2 | Frontend |
| TD-053 | Hardcoded borderColor in ThemeToggle component | 0.5 | Frontend |

## Tasks

### Accessibility -- Critical/High

- [ ] Task 1: TD-008 -- Add focus trap to SaveSearchDialog component (extracted in Sprint 2). Implement: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, focus trap cycling (Tab/Shift+Tab), Escape key closes and returns focus to trigger element.
- [ ] Task 2: TD-031 -- After search results load: scroll to results section, set focus on results heading, add `aria-live="polite"` region that announces "X resultados encontrados" (or error message). Critical for mobile users where results are below the fold.
- [ ] Task 3: TD-047 -- Add ARIA menu pattern to all dropdown components: `role="menu"` on container, `role="menuitem"` on items, `aria-haspopup="true"` on trigger, arrow key navigation between items.
- [ ] Task 4: TD-048 -- Replace `window.confirm()` in delete/destructive actions with a custom confirmation modal using the same dialog pattern as SaveSearchDialog (focus trap, dialog role, themed).

### Accessibility -- Medium/Low

- [ ] Task 5: TD-043 -- Wrap header navigation elements in `<nav aria-label="Navegacao principal">` in SearchHeader component.
- [ ] Task 6: TD-046 -- Add `aria-describedby` linking the terms input to its help text / character count hint.
- [ ] Task 7: TD-049 -- Add `aria-live="polite"` and `role="status"` to EmptyState component so screen readers announce when no results are found.
- [ ] Task 8: TD-050 -- Add `aria-expanded="true|false"` to SourceBadges toggle/expand trigger.
- [ ] Task 9: TD-051 -- Wrap UF grid in `role="group"` with `aria-label="Selecionar Unidades Federativas"`. Each region sub-group also gets `role="group"` with region name as label.
- [ ] Task 10: TD-052 -- Establish heading hierarchy: h1 for page title, h2 for major sections (Search Form, Results, Summary), h3 for subsections. Verify no heading levels are skipped.

### Design System Alignment

- [ ] Task 11: TD-029 -- Replace favicon files in `frontend/public/` with Descomplicita brand favicon. Update `frontend/app/layout.tsx` metadata if needed.
- [ ] Task 12: TD-030 -- Refactor error boundary component to use CSS custom properties (`var(--ink-base)`, `var(--surface-base)`) with hardcoded CSS fallback values for when themes fail to load.
- [ ] Task 13: TD-044 -- Create semantic status CSS custom properties: `--status-success`, `--status-warning`, `--status-error` with values defined for all 5 themes. Update SourceBadges and carouselData to use these tokens instead of `bg-green-100`, `bg-yellow-100`, `bg-red-100`.
- [ ] Task 14: TD-053 -- Replace hardcoded `borderColor` in ThemeToggle component with CSS custom property `var(--border-base)`.

### Performance

- [ ] Task 15: TD-042 -- Add dynamic imports with `next/dynamic` for heavy components: LoadingProgress, carouselData/SourceBadges, SaveSearchDialog. Add loading fallbacks (skeleton or spinner).

## Criterios de Aceite

- [ ] Zero WCAG AA critical/serious violations when running axe-core against all page states (empty, loading, results, error)
- [ ] SaveSearchDialog has working focus trap (Tab cycles within dialog, Escape closes)
- [ ] After search completes, focus moves to results section and screen reader announces result count
- [ ] All dropdown menus implement full ARIA menu pattern with keyboard navigation (Arrow keys, Enter, Escape)
- [ ] window.confirm() is no longer called anywhere in the codebase
- [ ] Favicon displays Descomplicita brand (not "B" for Descomplicita)
- [ ] SourceBadges renders correctly in all 5 themes (Default Light, Default Dark, Paperwhite, Sepia, High Contrast) using semantic status tokens
- [ ] Error boundary is styled correctly even when theme CSS fails to load
- [ ] Code splitting reduces initial bundle size (measured before/after with `next build`)
- [ ] All heading levels follow correct hierarchy (h1 > h2 > h3, no skips)

## Testes Requeridos

- [ ] Unit test: SaveSearchDialog focus trap -- Tab cycles, Shift+Tab reverse cycles, Escape closes
- [ ] Unit test: Focus management after search -- focus moves to results heading
- [ ] Unit test: ARIA menu pattern on dropdowns -- correct roles, keyboard navigation
- [ ] Unit test: Custom confirmation modal -- renders, focuses, closes on confirm/cancel
- [ ] Unit test: SourceBadges uses CSS custom properties (no hardcoded color classes)
- [ ] E2E test with axe-core integration: zero critical/serious WCAG violations on all page states
- [ ] E2E test: Keyboard-only navigation through entire search flow (tab through form, submit, navigate results)
- [ ] Visual regression: SourceBadges in all 5 themes
- [ ] Bundle size check: `next build` output shows reduced initial JS

## Dependencias

- Blocked by: Story 2.0 -- TD-008 requires SaveSearchDialog extracted, TD-031 requires clean component boundaries, TD-042 requires separate components for dynamic imports
- Blocks: None directly. Sprint 4 (backend) is independent.

## Definition of Done

- [ ] Code reviewed
- [ ] All tests passing (unit + E2E)
- [ ] axe-core E2E gate passes with zero critical/serious violations
- [ ] Coverage >= 70% statements (incremental increase from Sprint 2's 65%)
- [ ] No regressions in functionality or visual appearance
- [ ] Tested in all 5 themes
- [ ] Documentation updated (accessibility patterns documented for future components)
