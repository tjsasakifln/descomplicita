# DescompLicita Frontend Specification

**Document Version:** 4.0
**Date:** 2026-03-09
**Author:** @ux-design-expert (Pixel)
**Phase:** Comprehensive Frontend Audit
**Previous Version:** 3.0 (by Vera, 2026-03-09)

---

## 1. Executive Summary

DescompLicita is a single-page application for searching and analyzing Brazilian public procurement bids (licitacoes) from official sources (PNCP, Compras.gov, Transparencia, Diarios Oficiais, TCE-RJ). Built with **Next.js 16 (App Router) + React 18 + TypeScript**, it features a 5-theme system, Mixpanel analytics, Sentry error monitoring, and a comprehensive design token architecture.

### Current State (v4.0 Audit)

The codebase has matured significantly since earlier audits. Key completions since v3.0:

- **LoadingProgress decomposed** into 5 sub-components (ProgressBar, StageList, UfGrid, CuriosityCarousel, SkeletonCards). The orchestrator is now 141 lines.
- **ThemeProvider refactored** from 30+ imperative `style.setProperty` calls to CSS cascade via `data-theme` attribute selectors in `globals.css`. ThemeProvider now only sets `data-theme` attr + `.dark` class (83 lines).
- **Carousel category colors** migrated to CSS custom properties (`--cat-{category}-bg/icon-bg/text`).
- **Ctrl+Enter keyboard shortcut** implemented for search submission.
- **NetworkIndicator** added for offline detection.
- **not-found.tsx** page created.
- **Setores loading state** added to SearchForm (spinner + "Carregando setores..." fallback).
- **SaveSearchDialog** now uses native `<dialog>` element with `showModal()`.
- **SavedSearchesDropdown** has full ARIA listbox pattern with keyboard navigation.
- **Polling upgraded** to exponential backoff (1s initial, 1.5x growth, 15s max).
- **Fallback setores** centralized in `constants/fallback-setores.ts`.
- **ItemsList + Pagination** added for paginated result browsing.
- **Test coverage** at ~68% statements (404+ assertions, 5 E2E specs).

### What Remains

- No shared Button or Spinner component abstractions
- 2 hardcoded color violations (SearchSummary badges, SourceBadges warning)
- Silent error swallowing in ItemsList pagination
- `ink-muted` contrast ratio borderline WCAG AA
- Broken `/termos` footer link
- Single `"use client"` page (no SSR for main content)
- No Storybook or documented design system beyond code

---

## 2. Technology Stack

### Runtime Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| next | ^16.1.4 | React framework (App Router, SSR, API routes) |
| react / react-dom | ^18.3.1 | UI library + DOM rendering |
| @sentry/nextjs | ^10.42.0 | Error monitoring and performance tracing |
| mixpanel-browser | ^2.74.0 | Product analytics (lazy loaded via dynamic import) |
| uuid | ^13.0.0 | Unique ID generation for saved searches |

### Dev Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| typescript | ^5.9.3 | Type safety |
| tailwindcss | ^3.4.19 | Utility-first CSS framework |
| postcss | ^8.5.8 | CSS processing pipeline |
| jest / @swc/jest | ^29.7.0 / ^0.2.29 | Unit testing with fast SWC transform |
| @testing-library/react | ^14.1.2 | Component testing utilities |
| @playwright/test | ^1.58.0 | End-to-end testing |
| @axe-core/playwright | ^4.11.0 | Automated accessibility auditing |
| msw | ^2.12.10 | API mocking for integration tests |

### Fonts

- **DM Sans** (body text) -- `--font-body`, `font-body` Tailwind class
- **Fahkwang** (display/headings) -- `--font-display`, `font-display` Tailwind class
- **DM Mono** (data/numbers) -- `--font-data`, `font-data` Tailwind class

All loaded via `next/font/google` with `display: "swap"` and CSS variable injection.

### Build Configuration

- `reactStrictMode: true`
- `output: 'standalone'` (Docker-optimized)
- Sentry webpack plugin with `hideSourceMaps: true`
- Node.js requirement: >=20.9.0

---

## 3. Component Inventory

### 3.1 Page-Level Components

| File | Purpose | Props | Dependencies | Test Coverage |
|------|---------|-------|--------------|---------------|
| `app/page.tsx` | Main search page orchestrator (209 lines) | None (default export) | 5 hooks, 6 static components, 4 dynamic imports | `page.test.tsx` |
| `app/layout.tsx` | Root layout (Server Component): fonts, metadata, providers | `{ children }` | DM_Sans, Fahkwang, DM_Mono, ThemeProvider, AnalyticsProvider, NetworkIndicator, theme-init.js | -- |
| `app/error.tsx` | Error boundary with Sentry reporting | `{ error, reset }` | @sentry/nextjs | `error.test.tsx` |
| `app/not-found.tsx` | 404 page (Server Component) | None | next/link | -- |

### 3.2 UI Components

| File | Purpose | Props Interface | Dependencies | Test Coverage |
|------|---------|-----------------|--------------|---------------|
| `SearchHeader.tsx` | Sticky header: logo, saved searches, theme toggle | `{ onLoadSearch, onAnalyticsEvent }` | next/image, SavedSearchesDropdown, ThemeToggle | `SearchHeader.test.tsx` |
| `SearchForm.tsx` | Search mode toggle (setor/termos), sector dropdown, term chips | `SearchFormProps` (11 props) | types.Setor | `SearchForm.test.tsx`, `SearchForm.loading.test.tsx` |
| `UfSelector.tsx` | 27-state multi-select grid with region shortcuts | `UfSelectorProps` (6 props) | RegionSelector, constants/ufs | `UfSelector.test.tsx` |
| `RegionSelector.tsx` | 5 region quick-select buttons (Norte/Nordeste/etc.) | `{ selected, onToggleRegion }` | None | Indirect via UfSelector |
| `DateRangeSelector.tsx` | Date range picker (start/end date inputs) | `DateRangeSelectorProps` (5 props) | types.ValidationErrors | `DateRangeSelector.test.tsx` |
| `SearchSummary.tsx` | AI executive summary card with stats and highlights | `{ result: BuscaResult }` | SourceBadges | `SearchSummary.test.tsx` |
| `SourceBadges.tsx` | Expandable source attribution badges with status dots | `SourceBadgesProps` (4 props) | types.SourceStats | No dedicated test |
| `ItemsList.tsx` | Paginated procurement item list with client-side fetch | `{ jobId, totalFiltered }` | Pagination | `ItemsList.test.tsx` |
| `Pagination.tsx` | Page navigation with ellipsis and current page indicator | `PaginationProps` (5 props) | None | `Pagination.test.tsx` |
| `EmptyState.tsx` | Zero-results with filter breakdown and suggestions | `EmptyStateProps` (5 props) | types.FilterStats | `EmptyState.test.tsx` |
| `SearchActions.tsx` | Download Excel + Save Search action buttons | `SearchActionsProps` (8 props) | types.BuscaResult | `SearchActions.test.tsx` |
| `SaveSearchDialog.tsx` | Native `<dialog>` modal for naming saved searches | `SaveSearchDialogProps` (5 props) | None | `SaveSearchDialog.test.tsx` |
| `SavedSearchesDropdown.tsx` | ARIA listbox dropdown for saved search management | `{ onLoadSearch, onAnalyticsEvent? }` | useSavedSearches | `SavedSearchesDropdown.test.tsx`, `.aria.test.tsx` |
| `ThemeProvider.tsx` | Theme context: 5 themes via `data-theme` attribute + `.dark` class | `{ children }` | None (React Context) | `ThemeProvider.security.test.tsx` |
| `ThemeToggle.tsx` | Theme selector dropdown with preview swatches, full keyboard nav | None (uses useTheme) | ThemeProvider | `ThemeToggle.test.tsx` |
| `AnalyticsProvider.tsx` | Mixpanel lazy init + page_load/page_exit tracking | `{ children }` | mixpanel-browser (dynamic import) | Via `analytics.test.ts` |
| `NetworkIndicator.tsx` | Offline/online fixed banner with dismiss | None | None | `NetworkIndicator.test.tsx` |

### 3.3 Loading Progress Sub-Components

| File | Purpose | Props | Test Coverage |
|------|---------|-------|---------------|
| `loading-progress/ProgressBar.tsx` | Animated progress bar with ETA, percentage, status | `ProgressBarProps` (7 props) | `ProgressBar.test.tsx` |
| `loading-progress/StageList.tsx` | 5-stage indicator dots + mobile detail card | `StageListProps` (3 props) | `StageList.test.tsx` |
| `loading-progress/UfGrid.tsx` | Per-UF completion grid with pulse on active state | `UfGridProps` (4 props) | `UfGrid.test.tsx` |
| `loading-progress/CuriosityCarousel.tsx` | Rotating educational tips with category icons/colors | `{ curiosidade, isFading }` | `CuriosityCarousel.test.tsx` |
| `loading-progress/SkeletonCards.tsx` | Shimmer placeholder cards | None | `SkeletonCards.test.tsx` |
| `LoadingProgress.tsx` | Orchestrator composing all 5 sub-components (141 lines) | `LoadingProgressProps` (9 props) | `LoadingProgress.test.tsx` |

### 3.4 Data/Config Modules

| File | Purpose |
|------|---------|
| `components/carouselData.ts` | 52 curiosity items (4 categories), `shuffleBalanced()` round-robin algorithm |
| `constants/ufs.ts` | Canonical 27 UFs, `UF` type, `UF_NAMES` map, `DEFAULT_UFS` (SC/PR/RS) |
| `constants/fallback-setores.ts` | 7 fallback sectors for API unavailability |
| `app/types.ts` | All TypeScript interfaces: SearchParams, BuscaResult, Resumo, FilterStats, SourceStats, SearchPhase, etc. |
| `lib/savedSearches.ts` | localStorage CRUD for saved searches (max 10, uuid-based IDs) |
| `lib/backendAuth.ts` | Server-side JWT token acquisition/caching for API route authentication |

### 3.5 Custom Hooks

| Hook | Location | Responsibility | Lines |
|------|----------|----------------|-------|
| `useSearchForm` | `app/hooks/useSearchForm.ts` | Form state, validation, sector fetching, UF selection, loadSearchParams | 210 |
| `useSearchJob` | `app/hooks/useSearchJob.ts` | Search execution, exponential backoff polling, download, tab notifications | 405 |
| `useSaveDialog` | `app/hooks/useSaveDialog.ts` | Save search dialog visibility, name input, error state | 69 |
| `useAnalytics` | `hooks/useAnalytics.ts` | Mixpanel lazy-loaded event tracking + user identification | 56 |
| `useSavedSearches` | `hooks/useSavedSearches.ts` | Saved search CRUD over localStorage with refresh | 148 |

---

## 4. Page Structure

### 4.1 Routes

| Route | Type | Description |
|-------|------|-------------|
| `/` | Page (Client Component) | Main search page -- single-page app |
| `/api/buscar` | API Route (POST) | Submits search job to backend |
| `/api/buscar/status` | API Route (GET) | Polls job progress (exponential backoff) |
| `/api/buscar/result` | API Route (GET) | Fetches completed search results |
| `/api/buscar/items` | API Route (GET) | Paginated item list for a completed job |
| `/api/download` | API Route (GET) | Proxies Excel download from backend |
| `/api/setores` | API Route (GET) | Fetches available sectors from backend |

### 4.2 Layout Hierarchy

```
RootLayout (layout.tsx) [Server Component]
  html[lang="pt-BR"][data-theme] + Google Font CSS variables
  head
    theme-init.js (beforeInteractive -- FOUC prevention)
  body
    Skip Link -> #main-content
    AnalyticsProvider [Client]
      ThemeProvider [Client]
        NetworkIndicator (fixed top banner when offline) [Client]
        HomePage (page.tsx) [Client]
          SearchHeader (sticky top, z-40)
            Logo (next/image, priority)
            SavedSearchesDropdown (ARIA listbox)
            ThemeToggle (ARIA menu)
          main#main-content
            h1 "Busca de Licitacoes"
            SearchForm (setor/termos mode)
            UfSelector > RegionSelector
            DateRangeSelector
            Submit Button (with aria-busy)
            LoadingProgress [dynamic import]
              ProgressBar + UfGrid + StageList + CuriosityCarousel + SkeletonCards
            Error Alert (role="alert")
            aria-live result announcement (sr-only)
            EmptyState [dynamic import]
            Results Section (animate-fade-in-up)
              SearchSummary > SourceBadges
              ItemsList > Pagination
              SearchActions
          SaveSearchDialog [dynamic import, SSR disabled]
          Footer
```

### 4.3 Navigation

Single-page experience. No client-side routing beyond root. Navigation points:
- Sticky header with logo (not linked)
- Footer: mailto link, `/termos` (not yet implemented -- see FE-008)
- External links to procurement sources in search results (`target="_blank"`)

---

## 5. Design System Audit

### 5.1 Theme Implementation

**Architecture: Excellent.** The theme system uses CSS cascade via `data-theme` attribute selectors in `globals.css`. The `ThemeProvider` only performs two DOM operations: `setAttribute("data-theme", themeId)` and `classList.add/remove("dark")`. All visual changes flow through CSS custom properties.

**FOUC Prevention:** `public/theme-init.js` is a 1-line IIFE loaded with `strategy="beforeInteractive"` that reads localStorage and sets `data-theme` + `.dark` class before React hydrates. This is the optimal approach.

**5 Themes:**

| Theme | Type | Canvas | Ink | Status |
|-------|------|--------|-----|--------|
| Light | Light | #ffffff | #1e2d3b | Full token coverage |
| Paperwhite | Light | #F5F0E8 | #1e2d3b | Partial overrides (canvas, surfaces, status-bg) |
| Sepia | Light | #EDE0CC | #2c1810 | Good overrides (canvas, ink, surfaces, semantic) |
| Dim | Dark | #2A2A2E | via .dark | Minimal overrides (canvas, surface-0 only) |
| Dark | Dark | #121212 | #e8eaed | Full token coverage via .dark |

**Key Observation:** Dim and Dark share identical ink, border, semantic, and category tokens (all via `.dark`). Only canvas/surface-0 differs. This makes Dim feel nearly identical to Dark.

### 5.2 Color Usage

**Token System:** 40+ CSS custom properties organized into semantic groups:
- Canvas/Ink hierarchy (5 levels)
- Brand (navy, blue, blue-hover, blue-subtle)
- Surfaces (0, 1, 2, elevated)
- Semantic (success, error, warning + subtle)
- Status badges (bg, text, border, dot per status)
- Category tokens (4 categories for carousel)
- Borders (3 levels: default, strong, accent)
- Focus ring

**Consistency Violations:**
1. `SearchSummary.tsx` uses hardcoded Tailwind classes (`bg-blue-100`, `text-blue-800`, `bg-purple-100`, `text-purple-800`) for licitacao/ata type badges. These bypass the theme system entirely.
2. `SourceBadges.tsx` uses `text-amber-600 dark:text-amber-400` for truncated combos warning instead of the `warning` semantic token.

### 5.3 Typography

**Font Stack:**
- Body: DM Sans (`--font-body`) -- clean, readable sans-serif
- Display: Fahkwang (`--font-display`) -- distinctive for headings/section titles
- Data: DM Mono (`--font-data`) -- monospace for numbers, timestamps, technical data

**Base Size:** `clamp(14px, 1vw + 10px, 16px)` with 1.6 line-height. Good responsive scaling.

**Type Scale:** Consistent Tailwind text-size usage (xs through 4xl). Display font correctly reserved for headings. Tabular numbers via `.tabular-nums` for data alignment.

### 5.4 Spacing Patterns

Tailwind config declares 4px-base grid comment but does not override defaults. In practice, spacing is consistent through standard Tailwind utilities. No custom magic numbers observed. Content max-width is `max-w-4xl` (896px) with `px-4 sm:px-6` horizontal padding.

### 5.5 Border Radius Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `rounded-input` | 4px | Form inputs, selects |
| `rounded-button` | 6px | Buttons |
| `rounded-card` | 8px | Cards, panels, alerts |
| `rounded-modal` | 12px | Modal dialogs |

Consistently applied across all components.

### 5.6 Component Reuse vs Duplication

**Good Reuse:**
- LoadingProgress decomposed into 5 focused sub-components
- RegionSelector properly extracted from UfSelector
- SourceBadges separated from SearchSummary
- Shared hooks (useAnalytics, useSavedSearches) in `hooks/`
- Constants centralized in `constants/`

**Duplication (Technical Debt):**
- SVG spinner markup repeated in SearchForm, SearchActions -- no shared `Spinner` component
- Primary/secondary/danger button styles repeated as inline Tailwind class strings across 7+ components -- no shared `Button` component
- Form input styling (`w-full border border-strong rounded-input px-4 py-3 text-base bg-surface-0 text-ink focus:...`) repeated in 4 places

---

## 6. Accessibility Audit

### 6.1 ARIA Usage -- Excellent

- `aria-pressed` on UF toggle buttons
- `aria-expanded` + `aria-haspopup` on all dropdowns
- `aria-live="polite"` regions for search results and loading state
- `role="alert"` on all error messages and validation errors
- `role="progressbar"` with `aria-valuenow/min/max` on progress bar
- `aria-labelledby` on save search dialog
- `role="listbox"` + `role="option"` + `aria-activedescendant` on SavedSearchesDropdown
- `role="menu"` + `role="menuitem"` with roving tabindex on ThemeToggle
- `aria-label` on all icon-only buttons and navigation landmarks
- `aria-describedby` linking term input to help text
- `aria-busy` on submit button during loading
- `aria-current="page"` on active pagination button
- `aria-hidden="true"` on decorative SVG icons
- `role="group"` with `aria-label` on UF grid
- `role="status"` on empty saved searches and result announcements

### 6.2 Keyboard Navigation -- Strong

- **Skip link:** "Pular para o conteudo principal" -> `#main-content`
- **Ctrl+Enter:** Global shortcut to submit search form
- **Escape:** Closes ThemeToggle and SavedSearchesDropdown, returns focus to trigger
- **Arrow keys:** Full roving focus in ThemeToggle (menu) and SavedSearchesDropdown (listbox)
- **Home/End:** Supported in both dropdown menus
- **Enter on save dialog input:** Submits the form
- **Backspace in empty term input:** Removes last term
- **Focus management after search:** Results heading receives focus via `requestAnimationFrame` + `scrollIntoView`
- **Focus trap in SaveSearchDialog:** Native `<dialog>` `showModal()` provides built-in focus trap

### 6.3 Screen Reader Compatibility

- `sr-only` headings: "Formulario de Busca" and "Resultados"
- `aria-live="polite"` region announces result count ("X resultados encontrados" / "Nenhum resultado encontrado")
- All interactive elements have accessible names
- Loading state communicated via aria-live region wrapping LoadingProgress
- Status messages use `role="status"` for polite announcements

### 6.4 Color Contrast

**Adequate:**
- `ink` (#1e2d3b) vs `canvas` (#ffffff): ~12.7:1 (AAA)
- `ink-secondary` (#3d5975) vs `canvas`: ~6.4:1 (AA)

**Borderline:**
- `ink-muted` (#5a6a7a) vs `canvas` (#ffffff): ~4.1:1 -- **below WCAG AA 4.5:1** for normal text. Used extensively for hints, timestamps, metadata.

**Dark mode needs verification:**
- `ink-muted` (#8a99a9) vs `surface-1` (#1a1d22) should be checked
- Category token text colors in dark mode may have insufficient contrast

### 6.5 Focus Management

- `:focus-visible` global style: 2px solid `var(--ring)` with 2px offset
- Ring color adapts per theme (#116dff light, #3b8bff dark)
- Skip link visible on focus with proper styling
- Native `<dialog>` focus trap in SaveSearchDialog
- Focus returns to trigger on dropdown close
- Minimum 44px touch targets enforced globally

### 6.6 Reduced Motion

`@media (prefers-reduced-motion: reduce)` sets all animation/transition durations to `0.01ms`. This is comprehensive and correctly covers all custom animations (fadeInUp, fadeIn, shimmer) and transitions.

### 6.7 Overall A11y Grade: **A-**

The application demonstrates deliberate, above-average accessibility. ARIA patterns, keyboard navigation, focus management, and screen reader support are thorough. Main deduction: `ink-muted` contrast ratio and incomplete theme contrast audit.

---

## 7. Performance Assessment

### 7.1 Bundle Size Strategy

**Dynamic Imports (next/dynamic):**
- `SaveSearchDialog` -- SSR disabled, loaded on demand
- `LoadingProgress` -- with inline skeleton fallback
- `EmptyState` -- lazy loaded
- `ItemsList` -- lazy loaded

**Lazy-loaded SDK:**
- Mixpanel loaded via `import('mixpanel-browser')` -- ~40KB savings from initial bundle

**Production dependencies:** next, react, react-dom, @sentry/nextjs, mixpanel-browser (lazy), uuid

### 7.2 Lazy Loading Usage

4 components use `next/dynamic`. `LoadingProgress` has a proper skeleton fallback. `EmptyState` and `ItemsList` have no fallback (minor gap -- see FE-009).

### 7.3 Image Optimization

- Logo: `next/image` with explicit `width={140} height={67}`, `priority` flag, `className="h-10 w-auto"` -- correctly optimized for LCP
- App icon: SVG in `app/icon.svg` -- optimal format
- No other images in the application

### 7.4 Client vs Server Components

**Server Components:** `layout.tsx` (font loading, metadata), `not-found.tsx` (static content)
**Client Components:** Everything else (`"use client"` on all interactive components)

Given the SPA-like interactive nature, this split is reasonable. The main page could theoretically SSR the form shell for better initial paint, but the complexity tradeoff is not justified for this use case.

### 7.5 Polling Strategy

Exponential backoff: 1s initial, 1.5x growth factor, 15s max interval, 10-minute timeout. Pattern: 1s -> 1.5s -> 2.25s -> 3.375s -> 5s -> 7.6s -> 11.4s -> 15s (max). Reduces poll requests by 60-80% vs fixed interval. Well-documented in code with future SSE migration noted.

### 7.6 Build Output

`output: 'standalone'` produces a self-contained server for Docker deployment. Combined with Sentry's `hideSourceMaps: true`, this is production-ready.

---

## 8. State Management

### 8.1 Architecture

Pure React hooks with no external state library. All state originates in `page.tsx` and flows down via props.

```
page.tsx (orchestrator)
  |
  +-- useSearchForm(clearResult)
  |     State: setores, setorId, searchMode, termosArray, termoInput,
  |            ufsSelecionadas (Set), dataInicial, dataFinal, validationErrors
  |     Side effects: fetch /api/setores on mount
  |
  +-- useSearchJob(trackEvent)
  |     State: loading, error, result, rawCount, searchPhase,
  |            ufsCompleted, ufsTotal, itemsFetched, itemsFiltered,
  |            elapsedSeconds, downloadLoading, downloadError
  |     Side effects: POST /api/buscar, poll status, fetch result, download
  |
  +-- useSaveDialog({ form, saveNewSearch, trackEvent, hasResult })
  |     State: showSaveDialog, saveSearchName, saveError
  |
  +-- useSavedSearches()
  |     State: searches, loading, isMaxCapacity
  |     Storage: localStorage
  |
  +-- useAnalytics()
        State: mixpanelInstance (module-level singleton)
        Side effects: lazy load mixpanel-browser
```

### 8.2 Context Providers

| Provider | Scope | Purpose | Consumers |
|----------|-------|---------|-----------|
| `ThemeContext` | `ThemeProvider` | Theme ID, setter, config | ThemeToggle (via `useTheme()`) |
| `AnalyticsProvider` | Root | Mixpanel init, page tracking | Children (passive -- no context exposed) |

### 8.3 Patterns

- **Lifting state up:** All form/search state in page.tsx, passed as props (max 2 levels deep)
- **useCallback memoization:** All handlers wrapped for referential stability
- **Set for multi-select:** `ufsSelecionadas` uses `Set<string>` for O(1) toggle/has
- **Refs for non-UI state:** pollingRef, jobIdRef, searchStartTimeRef avoid unnecessary re-renders
- **Reactive validation:** `validateForm()` via `useCallback` + `useEffect` recomputes on dependency change

---

## 9. UX Patterns

### 9.1 Loading States

| Context | Implementation |
|---------|----------------|
| Sectors dropdown | Spinner + "Carregando setores..." with `aria-busy`, fallback to hardcoded list |
| Search in progress | Full LoadingProgress: progress bar, 5-stage indicator, UF grid, carousel, skeletons, cancel button |
| Pagination | "Carregando..." centered text |
| Download | Spinner in button + "Preparando download..." label |
| Dynamic import | Inline skeleton for LoadingProgress; no fallback for EmptyState/ItemsList |

### 9.2 Error Handling

| Scenario | Implementation |
|----------|----------------|
| Network offline | NetworkIndicator: fixed top banner with dismiss button |
| Search failure | Alert card (`role="alert"`) with error message + "Tentar novamente" button |
| Download failure | Inline alert card below action buttons |
| Save search error | Inline error in dialog |
| Pagination failure | Silent -- **no user feedback** (see FE-005) |
| Global unhandled error | error.tsx: Sentry report + "Ops! Algo deu errado" with retry |
| Polling timeout | "A consulta excedeu o tempo limite" message after 10 minutes |
| Backend unavailable | 503 with "Backend indisponivel em [URL]: [error]" |

### 9.3 Empty States

| Context | Implementation |
|---------|----------------|
| No saved searches | Icon + "Nenhuma busca salva" + hint text in dropdown |
| Zero search results | Rich EmptyState with filter breakdown, suggestions, stats, "Ajustar criterios" button |
| Zero filtered items | Contextual messaging based on rawCount vs filtered count |

### 9.4 Form Validation

| Field | Validation | Display |
|-------|------------|---------|
| UF selection | At least 1 state required | `role="alert"` below grid |
| Date range | End date >= start date | `role="alert"` below dates |
| Terms mode | At least 1 term required | Submit button disabled |
| Save search name | Required, max 50 chars | Live character counter, disabled submit |
| Submit guard | `canSearch` boolean | Button disabled + aria-busy when loading |
| Ctrl+Enter | Respects `canSearch` and `!loading` | No visual indicator (keyboard shortcut) |

### 9.5 Responsive Design

| Breakpoint | Changes |
|------------|---------|
| Base (mobile) | Single column, 5-col UF grid, hidden labels, mobile stage detail card |
| `sm:` (640px) | Two-column dates, 7-col UF grid, visible labels, hidden mobile card |
| `md:` (768px) | 9-col UF grid |

**Touch targets:** Global 44px minimum via CSS. **Content width:** `max-w-4xl` (896px). **Fluid typography:** `clamp(14px, 1vw + 10px, 16px)`.

### 9.6 Notifications

- **Tab title:** Updates to show result count when search completes while tab is backgrounded
- **Browser notifications:** Requested on completion; sent when tab is hidden (permission-gated)
- **Analytics:** Comprehensive Mixpanel event tracking: search_started, search_completed, search_failed, search_cancelled, loading_stage_reached, loading_abandoned, download_started/completed/failed, saved_search_created/loaded/deleted

---

## 10. Test Coverage

### 10.1 Jest Unit Tests

**Coverage thresholds (jest.config.js):**
- Statements: 65% (current: ~67.93%)
- Lines: 65% (current: ~66.30%)
- Functions: 57% (current: ~59.89%)
- Branches: 50% (current: ~52.74%)

**~585 test assertions** across 30+ test files:

| Category | Files | Scope |
|----------|-------|-------|
| Component tests | 18 files | All major components + accessibility + loading states |
| Hook tests | 3 files | useSearchForm, useSearchJob, useSearchJob.polling |
| API route tests | 4 files | buscar, buscar-result, buscar-status, download |
| Integration | 1 file | Full search flow with MSW handlers |
| Page-level | 2 files | page.tsx, error.tsx |
| Library tests | 2 files | analytics, savedSearches |
| Security | 1 file | Security headers |

### 10.2 E2E Tests (Playwright)

5 specs with axe-core:
1. `01-happy-path.spec.ts` -- full search -> results -> download flow
2. `02-llm-fallback.spec.ts` -- LLM/AI summary failure handling
3. `03-validation-errors.spec.ts` -- form validation error states
4. `04-error-handling.spec.ts` -- backend error scenarios
5. `05-accessibility.spec.ts` -- automated accessibility audits

### 10.3 Test Gaps

| Component | Risk Level |
|-----------|------------|
| RegionSelector (no direct test) | Low -- tested indirectly via UfSelector |
| SourceBadges (no dedicated test) | Medium -- complex conditional rendering |
| not-found.tsx (no test) | Low -- static content |

---

## 11. Technical Debt Items

### FE-001: Hardcoded Colors in SearchSummary Badges

- **Description:** `SearchSummary.tsx` uses `bg-blue-100 text-blue-800 border-blue-200` and `bg-purple-100 text-purple-800 border-purple-200` for licitacao/ata type badges. These bypass the theme system and use `dark:` prefix variants that do not cover paperwhite, sepia, or dim themes.
- **Severity:** High
- **Impact on UX:** Visual inconsistency across non-light themes; badges may be illegible in sepia/paperwhite.
- **Estimated Effort:** 1 hour
- **Recommendation:** Define `--badge-licitacao-{bg,text,border}` and `--badge-ata-{bg,text,border}` CSS custom properties per theme in globals.css, similar to the category token pattern.

### FE-002: Hardcoded Color in SourceBadges Warning

- **Description:** `SourceBadges.tsx` uses `text-amber-600 dark:text-amber-400` for truncated combos warning instead of the `warning` semantic token.
- **Severity:** Low
- **Impact on UX:** Minor inconsistency in paperwhite, sepia, dim themes.
- **Estimated Effort:** 0.5 hours
- **Recommendation:** Replace with `text-warning`.

### FE-003: UUID Dependency for ID Generation

- **Description:** `uuid` v13 is a production dependency used only in `lib/savedSearches.ts`. `crypto.randomUUID()` is available in all target browsers and Node 19+.
- **Severity:** Low
- **Impact on UX:** None directly; ~3KB gzipped bundle overhead.
- **Estimated Effort:** 0.5 hours
- **Recommendation:** Replace with `crypto.randomUUID()` and remove the dependency.

### FE-004: Missing Spinner Component

- **Description:** SVG spinner markup (circle + arc path with opacity animation) is duplicated in SearchForm (setores loading) and SearchActions (download button). No shared component exists.
- **Severity:** Medium
- **Impact on UX:** Inconsistency risk if spinner styles diverge.
- **Estimated Effort:** 1 hour
- **Recommendation:** Extract `<Spinner size="sm" | "md" />` component.

### FE-005: Silent Error Swallowing in ItemsList

- **Description:** `ItemsList.tsx` has an empty `catch {}` block when fetching paginated items. Errors are silently discarded with no user feedback, retry mechanism, or error logging.
- **Severity:** High
- **Impact on UX:** Users see perpetual "Carregando..." or stale data with no indication of failure. No way to recover without page reload.
- **Estimated Effort:** 2 hours
- **Recommendation:** Add error state with inline message and retry button. Log to Sentry.

### FE-006: Missing Button Component Abstraction

- **Description:** Primary/secondary/danger/ghost button styles are duplicated as inline Tailwind class strings across 7+ components. Strings like `bg-brand-navy text-white py-3 rounded-button font-semibold hover:bg-brand-blue-hover...` repeat verbatim.
- **Severity:** Medium
- **Impact on UX:** Risk of style drift; difficulty enforcing consistent hover/focus/disabled states.
- **Estimated Effort:** 3 hours
- **Recommendation:** Create `<Button variant="primary" | "secondary" | "danger" | "ghost" size="sm" | "md" | "lg" />`.

### FE-007: ink-muted Contrast Below WCAG AA

- **Description:** `--ink-muted` (#5a6a7a) against white (#ffffff) yields ~4.1:1 contrast ratio, below WCAG AA (4.5:1) for normal text. This color is used extensively for metadata, timestamps, and hints.
- **Severity:** Medium
- **Impact on UX:** Accessibility barrier for low-vision users.
- **Estimated Effort:** 1 hour
- **Recommendation:** Darken to ~#4d5d6d (achieving ~5:1 ratio).

### FE-008: Broken /termos Footer Link

- **Description:** Footer links to `/termos` but no route exists. Clicking shows 404 page.
- **Severity:** Medium
- **Impact on UX:** Broken link on every page view.
- **Estimated Effort:** 2 hours
- **Recommendation:** Create `app/termos/page.tsx` or remove the link until content is ready.

### FE-009: Missing Error Fallback for Dynamic Imports

- **Description:** `EmptyState` and `ItemsList` dynamic imports have no `loading` or error fallback. Chunk load failures (network issues) result in blank sections.
- **Severity:** Low
- **Impact on UX:** Rare scenario but silent failure.
- **Estimated Effort:** 1 hour
- **Recommendation:** Add loading skeletons and error boundaries.

### FE-010: Missing Test for RegionSelector

- **Description:** No direct test file. Partial/full selection visual states not explicitly verified.
- **Severity:** Low
- **Impact on UX:** None directly; testing gap.
- **Estimated Effort:** 1.5 hours
- **Recommendation:** Add `RegionSelector.test.tsx`.

### FE-011: Missing Test for SourceBadges

- **Description:** Complex conditional rendering (status colors, expandable detail, dedup stats, truncation) with no dedicated test.
- **Severity:** Medium
- **Impact on UX:** None directly; regression risk.
- **Estimated Effort:** 2 hours
- **Recommendation:** Add `SourceBadges.test.tsx`.

### FE-012: Dim Theme Incomplete Token Coverage

- **Description:** `html[data-theme="dim"]` only overrides `--canvas` and `--surface-0`. All other tokens (surfaces 1/2/elevated, borders) inherit from `.dark`, making dim visually near-identical to dark.
- **Severity:** Low
- **Impact on UX:** Dim theme may feel indistinguishable from dark.
- **Estimated Effort:** 2 hours
- **Recommendation:** Add `surface-1: #32323a`, `surface-2: #3a3a42`, `surface-elevated: #2e2e34` to dim theme.

### FE-013: SavedSearchesDropdown Returns null During Loading

- **Description:** When `useSavedSearches` is loading, the entire dropdown renders null, causing a brief layout shift in the header.
- **Severity:** Low
- **Impact on UX:** Brief layout shift on initial page load.
- **Estimated Effort:** 0.5 hours
- **Recommendation:** Return a disabled skeleton button instead of null.

### FE-014: page.tsx Is a Monolithic Client Component

- **Description:** The entire main page (209 lines) is a single `"use client"` component managing all state. Any state change re-renders the entire page.
- **Severity:** Low
- **Impact on UX:** No visible impact currently due to React's efficient diffing. Will become relevant as features grow.
- **Estimated Effort:** 4 hours
- **Recommendation:** Consider splitting into `SearchFormSection` and `ResultsSection` with `React.memo` boundaries when scope expands.

---

## 12. Summary

### Strengths

1. **Well-architected theme system** with CSS cascade, FOUC prevention, 5 coherent themes, and comprehensive design tokens (40+ properties)
2. **Strong accessibility** (A- grade): skip link, ARIA patterns, keyboard navigation, focus management, reduced motion, screen reader announcements
3. **Excellent loading UX**: multi-stage progress, per-UF grid, educational carousel with sector-aware content, ETA estimation, skeleton placeholders
4. **Efficient polling**: exponential backoff reducing requests 60-80%
5. **Good component decomposition**: LoadingProgress into 5 sub-components, RegionSelector extracted, hooks properly separated
6. **Comprehensive analytics**: full search lifecycle tracking, loading abandonment, download metrics
7. **Dynamic imports** for heavy components reduce initial bundle
8. **Solid test coverage**: ~68% statements, 585+ assertions, 5 E2E specs with axe-core
9. **Consistent typography**: 3-font system (body/display/data) with fluid scaling
10. **Native `<dialog>`** for modal with built-in focus trap

### Priority Remediation

| Priority | Items | Total Effort |
|----------|-------|--------------|
| High | FE-001 (hardcoded colors), FE-005 (silent pagination error) | 3 hours |
| Medium | FE-004, FE-006, FE-007, FE-008, FE-011 | 9 hours |
| Low | FE-002, FE-003, FE-009, FE-010, FE-012, FE-013, FE-014 | 10 hours |

**Total estimated remediation effort: ~22 hours**

### Changes Since v3.0 Spec

| v3.0 Issue | v4.0 Status |
|------------|-------------|
| UXD-001: Multi-word terms impossible | Still open (space triggers token) |
| UXD-002: No setores loading state | **RESOLVED** -- spinner + text + aria-busy |
| UXD-003: No 404 page | **RESOLVED** -- not-found.tsx created |
| UXD-004: No keyboard shortcut | **RESOLVED** -- Ctrl+Enter implemented |
| UXD-005: SavedSearchesDropdown not ARIA listbox | **RESOLVED** -- full listbox pattern |
| UXD-006: SaveSearchDialog not native dialog | **RESOLVED** -- uses `<dialog>` showModal() |
| UXD-008: Mixpanel unconditionally imported | **RESOLVED** -- lazy loaded via dynamic import |
| UXD-010: ThemeProvider 30+ imperative style.setProperty | **RESOLVED** -- CSS cascade via data-theme |
| UXD-011: FOUC script may drift from ThemeProvider | **RESOLVED** -- both use same mechanism (data-theme + .dark) |
| UXD-012: No offline/network indicator | **RESOLVED** -- NetworkIndicator component |
| UXD-016: LoadingProgress 450+ lines | **RESOLVED** -- decomposed to 141-line orchestrator + 5 sub-components |
| UXD-017: Hardcoded fallback sectors | **RESOLVED** -- centralized in constants/fallback-setores.ts |
| UXD-019: carouselData hardcoded colors | **RESOLVED** -- migrated to CSS custom properties (--cat-* tokens) |
