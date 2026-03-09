# DescompLicita Frontend Specification

**Document Version:** 3.0
**Date:** 2026-03-09
**Author:** @ux-design-expert (Vera)
**Phase:** Brownfield Discovery Phase 3 - Frontend/UX Audit
**Previous Version:** 2.0 (by Pixel)

---

## 1. Executive Summary

DescompLicita is a single-page application for searching and analyzing public procurement bids (licitacoes) from Brazil's official sources (PNCP, Compras.gov, Transparencia, Diarios Oficiais, TCE-RJ). The frontend is built with **Next.js 16 + React 18 + TypeScript** and uses the App Router. It provides a search-oriented workflow where users select sectors or custom terms, choose Brazilian states (UFs), pick a date range, and receive AI-summarized results with Excel download capability.

### Current State

Since the v2.0 spec, significant refactoring has been completed:

- **Component decomposition is done.** The former 1,071-line `page.tsx` "god component" has been broken into 14 focused components and 5 custom hooks. The page is now 185 lines (orchestration only).
- **Accessibility improvements are in place.** Skip navigation, focus traps, ARIA dialog roles, Escape key handlers, screen reader announcements, keyboard menu navigation, `aria-pressed`/`aria-expanded`/`aria-describedby` throughout.
- **Dynamic imports** for heavy components (SaveSearchDialog, LoadingProgress, EmptyState).
- **UF constants centralized** in `app/constants/ufs.ts` (single source of truth).
- **Error boundary uses design tokens** via CSS custom properties (inline style fallbacks).
- **Logo self-hosted** from `public/logo-descomplicita.png` via Next.js `<Image>`.
- **Test coverage improved** to ~68% statements (up from ~49%).

### What Remains

- Single `"use client"` page (no SSR for main content)
- Term input tokenization prevents multi-word terms (space triggers token creation)
- ThemeProvider imperatively sets 30+ CSS custom properties
- LoadingProgress still 450+ lines (complex but functional)
- No Storybook, no documented design system beyond code
- Some hardcoded Tailwind colors in SearchSummary type badges and carouselData

---

## 2. Technology Stack

### Runtime Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| next | ^16.1.4 | React framework (App Router, SSR, API routes) |
| react | ^18.3.1 | UI library |
| react-dom | ^18.3.1 | DOM rendering |
| @sentry/nextjs | ^10.42.0 | Error monitoring and performance tracing |
| mixpanel-browser | ^2.74.0 | Product analytics and user event tracking |
| uuid | ^13.0.0 | Unique ID generation for saved searches |

### Dev Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| typescript | ^5.9.3 | Type safety |
| tailwindcss | ^3.4.19 | Utility-first CSS framework |
| postcss | ^8.5.6 | CSS processing pipeline |
| autoprefixer | ^10.4.23 | CSS vendor prefixing |
| jest | ^29.7.0 | Unit test runner |
| @swc/jest | ^0.2.29 | Fast TypeScript/JSX transform for Jest |
| jest-environment-jsdom | ^29.7.0 | Browser environment simulation |
| @testing-library/react | ^14.1.2 | Component testing utilities |
| @testing-library/jest-dom | ^6.1.5 | Custom Jest DOM matchers |
| @testing-library/user-event | ^14.5.1 | User interaction simulation |
| @playwright/test | ^1.58.0 | End-to-end testing |
| @axe-core/playwright | ^4.11.0 | Automated accessibility testing in E2E |

### Fonts

- **DM Sans** (body text) -- `--font-body`
- **Fahkwang** (display/headings) -- `--font-display`
- **DM Mono** (data/numbers) -- `--font-data`

All loaded via `next/font/google` with `display: "swap"` to prevent FOIT.

### Build Configuration

- `reactStrictMode: true`
- `output: 'standalone'` (Docker-optimized)
- Sentry webpack plugin with `hideSourceMaps: true`
- Node.js requirement: >=20.9.0
- Deployed on Railway

---

## 3. Project Structure

```
frontend/
  app/
    layout.tsx              # Root layout (Server Component: fonts, metadata, providers)
    page.tsx                # Home page (Client Component: search orchestration, 185 lines)
    error.tsx               # Error boundary with Sentry reporting
    globals.css             # Design tokens, animations, base styles (209 lines)
    types.ts                # Shared TypeScript type definitions
    icon.svg                # App favicon
    constants/
      ufs.ts                # Brazilian states data (27 UFs, names, defaults)
    components/
      AnalyticsProvider.tsx  # Mixpanel initialization and page tracking
      carouselData.ts        # Loading screen curiosity/tip content (52 items, 4 categories)
      DateRangeSelector.tsx  # Date range picker (start/end date inputs)
      EmptyState.tsx         # Zero-results feedback with suggestions
      LoadingProgress.tsx    # Multi-phase loading indicator with ETA (452 lines)
      RegionSelector.tsx     # Geographic region toggle buttons (5 regions)
      SavedSearchesDropdown.tsx  # Saved searches management dropdown
      SaveSearchDialog.tsx   # Modal dialog for naming saved searches
      SearchActions.tsx      # Download + save buttons after results
      SearchForm.tsx         # Search mode toggle + sector/terms input
      SearchHeader.tsx       # Sticky header with logo, nav, theme toggle
      SearchSummary.tsx      # AI-generated results summary display
      SourceBadges.tsx       # Data source status indicators
      ThemeProvider.tsx      # Theme context (5 themes, localStorage persistence)
      ThemeToggle.tsx        # Theme picker dropdown with keyboard nav
      UfSelector.tsx         # State (UF) selection grid (27 buttons)
    hooks/
      useSaveDialog.ts       # Save search dialog state management
      useSearchForm.ts       # Form state, validation, sector fetching
      useSearchJob.ts        # Search execution, polling, download, notifications
    api/
      buscar/
        route.ts             # POST /api/buscar - Submit search job
        status/route.ts      # GET /api/buscar/status - Poll job status
        result/route.ts      # GET /api/buscar/result - Fetch results
      download/route.ts      # GET /api/download - Proxy Excel download
      setores/route.ts       # GET /api/setores - Fetch available sectors
  hooks/
    useAnalytics.ts          # Mixpanel event tracking hook
    useSavedSearches.ts      # Saved searches CRUD with localStorage
  lib/
    savedSearches.ts         # Saved searches storage logic (max 10, uuid IDs)
  __tests__/                 # Jest unit tests (22 test files)
  __mocks__/                 # Jest mocks (@sentry/nextjs)
  public/                    # Static assets (logo-descomplicita.png)
  sentry.client.config.ts   # Sentry client config (DSN, 10% trace sampling)
  sentry.server.config.ts   # Sentry server config
```

---

## 4. Pages and Routes

| Route | File | Type | Purpose |
|---|---|---|---|
| `/` | `app/page.tsx` | Client Component | Main search interface |
| `/api/buscar` | `app/api/buscar/route.ts` | API Route (POST) | Proxy search job submission to backend |
| `/api/buscar/status` | `app/api/buscar/status/route.ts` | API Route (GET) | Proxy job status polling |
| `/api/buscar/result` | `app/api/buscar/result/route.ts` | API Route (GET) | Proxy completed job results |
| `/api/download` | `app/api/download/route.ts` | API Route (GET) | Proxy Excel file download (binary stream) |
| `/api/setores` | `app/api/setores/route.ts` | API Route (GET) | Proxy available sectors list |

The root layout (`layout.tsx`) is a Server Component providing metadata (`lang="pt-BR"`, title, description), font CSS variables, and wrapping children in `AnalyticsProvider > ThemeProvider`. The home page is the only user-facing route. All API routes act as a BFF (Backend for Frontend) proxy to the Python/FastAPI backend.

---

## 5. Component Inventory

### 5.1 Page Orchestrator

**HomePage** (`app/page.tsx`, 185 lines)
- Composes all components via props (controlled component pattern)
- Manages search submission, download, saved search loading
- Uses `useCallback` for all handler functions
- Focus management: auto-focuses results heading after search completes
- Screen reader: `aria-live="polite"` region announces result count
- Dynamic imports: `SaveSearchDialog` (ssr: false), `LoadingProgress` (with skeleton fallback), `EmptyState`

### 5.2 Component Details

| Component | File | Lines | Props Count | Dependencies |
|---|---|---|---|---|
| SearchHeader | `SearchHeader.tsx` | 40 | 2 | SavedSearchesDropdown, ThemeToggle, next/image |
| SearchForm | `SearchForm.tsx` | 156 | 10 | None (pure presentational) |
| UfSelector | `UfSelector.tsx` | 80 | 6 | RegionSelector, UFS/UF_NAMES constants |
| RegionSelector | `RegionSelector.tsx` | 53 | 2 | None |
| DateRangeSelector | `DateRangeSelector.tsx` | 62 | 5 | None |
| LoadingProgress | `LoadingProgress.tsx` | 452 | 9 | carouselData, useAnalytics |
| SearchSummary | `SearchSummary.tsx` | 76 | 1 | SourceBadges |
| SearchActions | `SearchActions.tsx` | 93 | 8 | None |
| EmptyState | `EmptyState.tsx` | 140 | 5 | None |
| SaveSearchDialog | `SaveSearchDialog.tsx` | 122 | 5 | None |
| SavedSearchesDropdown | `SavedSearchesDropdown.tsx` | 277 | 2 | useSavedSearches hook |
| SourceBadges | `SourceBadges.tsx` | 121 | 4 | None |
| ThemeProvider | `ThemeProvider.tsx` | 161 | 1 (children) | None (React Context) |
| ThemeToggle | `ThemeToggle.tsx` | 141 | 0 (uses useTheme) | ThemeProvider |
| AnalyticsProvider | `AnalyticsProvider.tsx` | 74 | 1 (children) | mixpanel-browser |

### 5.3 Props Interfaces

**SearchForm:** `searchMode`, `onSearchModeChange`, `setores: Setor[]`, `setorId`, `onSetorIdChange`, `termosArray: string[]`, `onTermosArrayChange`, `termoInput`, `onTermoInputChange`, `onFormChange`

**UfSelector:** `ufsSelecionadas: Set<string>`, `onToggleUf`, `onToggleRegion`, `onSelecionarTodos`, `onLimparSelecao`, `validationErrors: ValidationErrors`

**LoadingProgress:** `phase: SearchPhase`, `ufsCompleted`, `ufsTotal`, `itemsFetched`, `itemsFiltered`, `elapsedSeconds`, `onCancel`, `selectedUfs?: string[]`, `sectorId?: string`

**SaveSearchDialog:** `saveSearchName`, `onNameChange`, `onConfirm`, `onCancel`, `saveError: string | null`

**SearchActions:** `result: BuscaResult`, `rawCount`, `sectorName`, `downloadLoading`, `downloadError`, `isMaxCapacity`, `onDownload`, `onSaveSearch`

### 5.4 Reusability Assessment

| Rating | Components |
|---|---|
| **High** | DateRangeSelector, SaveSearchDialog, ThemeProvider, ThemeToggle, AnalyticsProvider |
| **Medium** | SearchForm, UfSelector, RegionSelector, EmptyState, SearchActions, SavedSearchesDropdown |
| **Low** | LoadingProgress, SearchSummary, SourceBadges, SearchHeader |

---

## 6. State Management

### Architecture

Pure React hooks -- no external state library. State is organized into 5 custom hooks:

| Hook | Location | Responsibility |
|---|---|---|
| `useSearchForm` | `app/hooks/useSearchForm.ts` (205 lines) | Form state, validation, sector fetching, UF selection |
| `useSearchJob` | `app/hooks/useSearchJob.ts` (363 lines) | Search execution, polling, download, notifications |
| `useSaveDialog` | `app/hooks/useSaveDialog.ts` (69 lines) | Save dialog visibility, name, errors |
| `useAnalytics` | `hooks/useAnalytics.ts` (66 lines) | Mixpanel event tracking, user identification |
| `useSavedSearches` | `hooks/useSavedSearches.ts` (148 lines) | Saved search CRUD over localStorage |

### Data Flow

```
page.tsx (orchestrator)
  |-- useSearchForm() -> form state, validation, sectors
  |-- useSearchJob(trackEvent) -> search lifecycle, polling, results
  |-- useSaveDialog({form, saveNewSearch, trackEvent}) -> dialog state
  |-- useAnalytics() -> event tracking
  |-- useSavedSearches() -> saved search persistence
```

All state flows down to components via props. No prop drilling issues due to flat component hierarchy (page -> components, max 2 levels deep).

### Persistence Layer

- **Theme:** `localStorage.getItem('descomplicita-theme')` -- string (ThemeId)
- **Saved Searches:** `localStorage.getItem('descomplicita_saved_searches')` -- JSON array, max 10 items, sorted by `lastUsedAt`

---

## 7. API Integration

### BFF (Backend for Frontend) Pattern

The frontend never communicates directly with the Python backend. All requests go through Next.js API routes:

```
Browser -> Next.js API Route -> Python Backend (FastAPI @ BACKEND_URL)
```

This provides:
- Backend URL abstraction (`BACKEND_URL` env var, default `http://localhost:8000`)
- API key injection (`BACKEND_API_KEY` via `X-API-Key` header)
- Error normalization (backend errors mapped to user-friendly Portuguese messages)
- Response transformation (extracting/reshaping fields)
- Binary file proxying (Excel download)

### Async Search Pattern

```
1. POST /api/buscar         -> { job_id }
2. GET /api/buscar/status   -> { status, progress } (every 2s via setInterval)
3. GET /api/buscar/result   -> { resumo, download_id, ... } (when status=completed)
4. GET /api/download?id=X   -> binary Excel file
```

- **Polling interval:** 2 seconds (fixed)
- **Timeout:** 10 minutes
- **On network error:** Silently retry next interval
- **User cancellation:** Available at any time via cancel button

### Error Handling

| Scenario | HTTP Code | User-Facing Message |
|---|---|---|
| Missing parameters | 400 | "Selecione pelo menos um estado" / "Periodo obrigatorio" |
| Backend unreachable | 503 | "Backend indisponivel em [URL]: [error]" |
| Backend error | Forwarded | Backend's `detail` field or "Erro no backend" |
| Job not found | 404 | "Job not found" |
| Download expired | 404 | "Arquivo expirado. Faca uma nova busca..." |
| Internal error | 500 | "Erro interno do servidor" |

---

## 8. Styling Architecture

### Design Token System

A comprehensive CSS custom property system in `globals.css` (55 variables in `:root`, mirrored in `.dark`):

**Token Categories:**
- Canvas/Ink: `--canvas`, `--ink`, `--ink-secondary`, `--ink-muted`, `--ink-faint`
- Brand: `--brand-navy` (#0a1e3f), `--brand-blue` (#116dff), `--brand-blue-hover`, `--brand-blue-subtle`
- Surfaces: `--surface-0` through `--surface-elevated`
- Semantic: `--success`, `--error`, `--warning` (+ `-subtle` variants)
- Status badges: 12 tokens for success/warning/error (bg, text, border, dot)
- Borders: `--border`, `--border-strong`, `--border-accent` (opacity-based)
- Focus: `--ring`

All tokens are mapped to Tailwind classes in `tailwind.config.ts`, enabling usage like `bg-canvas`, `text-ink-secondary`, `border-status-success`.

### Theme System

5 themes managed via `ThemeProvider`:

| Theme | Type | Canvas | Ink |
|---|---|---|---|
| Light | Light | #ffffff | #1e2d3b |
| Paperwhite | Light | #F5F0E8 | #1e2d3b |
| Sepia | Light | #EDE0CC | #2c1810 |
| Dim | Dark | #2A2A2E | #e0e0e0 |
| Dark | Dark | #121212 | #e0e0e0 |

Implementation: `applyTheme()` imperatively sets CSS custom properties on `document.documentElement`. FOUC prevented by inline `<script>` in `<head>` that reads localStorage before React hydrates.

### Typography

- Body: DM Sans, `line-height: 1.6`
- Display: Fahkwang (headings)
- Data: DM Mono (numbers, timestamps)
- Base size: `clamp(14px, 1vw + 10px, 16px)` (fluid)
- Tabular numbers: `font-variant-numeric: tabular-nums` via `.tabular-nums` utility

### Border Radius Scale

| Token | Value | Usage |
|---|---|---|
| `rounded-input` | 4px | Form inputs |
| `rounded-button` | 6px | Buttons |
| `rounded-card` | 8px | Cards, panels |
| `rounded-modal` | 12px | Modals |

### Responsive Design

- Mobile-first with breakpoints at `sm:` (640px) and `md:` (768px)
- UF grid: 5 cols -> 7 (sm) -> 9 (md)
- Date inputs: stacked -> side-by-side (sm)
- Text scaling: `text-sm sm:text-base`, `text-2xl sm:text-3xl`
- Padding scaling: `px-4 sm:px-6`, `py-3 sm:py-4`
- Max content width: `max-w-4xl` (896px)
- Hidden on mobile: header tagline, loading stage labels, theme label, "Buscas Salvas" text

### Animations

- `animate-fade-in-up`: Entrance with 12px upward slide (0.4s)
- `animate-fade-in`: Opacity fade (0.3s)
- `animate-shimmer`: Skeleton loading shimmer (1.5s infinite)
- Stagger classes: `.stagger-1` through `.stagger-5` (50ms increments)
- `prefers-reduced-motion`: All animations reduced to 0.01ms

### Touch Targets

Global minimum 44px height on buttons and form inputs via CSS, meeting WCAG 2.5.8.

---

## 9. Performance Analysis

### Strengths

- **Dynamic imports:** `SaveSearchDialog` (ssr: false), `LoadingProgress` (with skeleton fallback), `EmptyState` -- reduces initial bundle
- **Font optimization:** `next/font/google` with `display: "swap"` and self-hosting
- **`output: 'standalone'`** for optimized Docker builds
- **`useCallback` usage:** All hook callbacks wrapped for referential stability
- **Logo with `priority`:** LCP optimization for above-fold image
- **Theme FOUC prevention:** Inline script applies theme before React hydrates

### Concerns

| Concern | Impact | Mitigation |
|---|---|---|
| Entire page is `"use client"` | No SSR benefit for SEO or initial paint | Acceptable for SPA; could SSR the form shell |
| `carouselData.ts` (52 items, 369 lines) bundled eagerly | ~15KB of data only needed during loading | Move to dynamic import within LoadingProgress |
| Fixed 2s polling interval | Unnecessary requests for long searches | Implement exponential backoff |
| Mixpanel SDK loaded unconditionally (~40KB gzipped) | Bundle bloat when analytics disabled | Conditional dynamic import based on token presence |
| Sentry SDK adds bundle weight | Always imported even when DSN empty | Conditional import (complex with Next.js plugin) |
| No ISR/SSG for sectors list | Extra API call on every page load | Could use `getStaticProps` with revalidation |

---

## 10. Testing Coverage

### Unit Tests (Jest)

**Coverage (from jest.config.js thresholds):**
- Statements: ~68% (threshold: 65%)
- Functions: ~60% (threshold: 57%)
- Branches: ~53% (threshold: 50%)
- Lines: ~66% (threshold: 65%)

**Test Files (22 files):**

| Category | Test Files | Description |
|---|---|---|
| Components | SearchForm, UfSelector, DateRangeSelector, SearchHeader, SearchSummary, SearchActions, LoadingProgress, EmptyState, SaveSearchDialog, SavedSearchesDropdown, ThemeToggle, accessibility | All major components tested |
| Hooks | useSearchForm, useSearchJob | Core logic hooks tested |
| API Routes | buscar, buscar-result, buscar-status, download | All API proxy routes tested |
| Integration | page, error | Full page rendering and error boundary |
| Libraries | analytics, savedSearches | Analytics tracking and storage |

**Quality Assessment:**
- Dedicated accessibility test file (`accessibility.test.tsx`) with focus trap, ARIA, semantic, and contrast tests
- API route tests mock `fetch` to verify proxy behavior
- Hook tests validate state transitions and side effects
- Testing Library used correctly (queries by role, not CSS selectors)

### E2E Tests (Playwright)

**4 test scenarios:**

| File | Scenario |
|---|---|
| `01-happy-path.spec.ts` | Complete search -> results -> download flow |
| `02-llm-fallback.spec.ts` | AI summary degradation handling |
| `03-validation-errors.spec.ts` | Form validation error states |
| `04-error-handling.spec.ts` | Backend error handling |

**Configuration:** Chromium-only, 60s timeout, sequential execution, screenshots/video on failure, traces on first retry. `@axe-core/playwright` installed for automated a11y.

### Test Gaps

| Gap | Impact |
|---|---|
| No tests for ThemeProvider (theme switching, persistence, CSS property application) | Theme bugs undetected |
| No tests for AnalyticsProvider (Mixpanel init, page tracking) | Analytics regressions |
| No tests for RegionSelector (region toggle logic) | Region selection bugs |
| No tests for carouselData (shuffleBalanced algorithm) | Shuffle bias undetected |
| No visual regression tests | Design drift undetected |
| No performance/Lighthouse CI tests | Performance regressions |
| E2E tests require live backend | No CI-friendly mock server |

---

## 11. UX Debt Inventory

| ID | Description | Severity | Effort |
|---|---|---|---|
| UXD-001 | **Multi-word terms impossible.** Space triggers token creation in term input, so "camisa polo" becomes two separate tokens. Need quote support or alternative delimiter. | **High** | Medium (3h) |
| UXD-002 | **No loading state for sector fetch.** `useSearchForm` fetches sectors on mount but shows no indicator. Dropdown appears empty momentarily if backend is slow. | Medium | Small (1h) |
| UXD-003 | **No 404 page.** Missing `not-found.tsx` for invalid routes. | Low | Small (1h) |
| UXD-004 | **No keyboard shortcut for search.** Enter key in date fields does not submit. No Ctrl+Enter or similar. | Low | Small (1h) |
| UXD-005 | **SavedSearchesDropdown uses div backdrop.** Not native `<dialog>` or proper ARIA listbox pattern. | Medium | Medium (3h) |
| UXD-006 | **SaveSearchDialog uses div, not native `<dialog>`.** Manual focus trap works but native element preferred. | Medium | Medium (2h) |
| UXD-007 | **No wrapping `<form>` element.** Prevents native form submission and browser autofill. | Medium | Small (2h) |
| UXD-008 | **Mixpanel imported unconditionally.** ~40KB even without token. Should use dynamic import. | Low | Small (1h) |
| UXD-009 | **No confirmation before page unload during search.** User can navigate away during long search without warning. | Low | Small (1h) |
| UXD-010 | **ThemeProvider applies 30+ CSS properties imperatively.** Could use data attribute + CSS rules for maintainability. | Low | Large (8h) |
| UXD-011 | **FOUC script in `<head>` duplicates ThemeProvider logic.** Subset handling may drift from full ThemeProvider. | Medium | Medium (3h) |
| UXD-012 | **No offline/network indicator.** Fetch failures show generic errors. No dedicated connectivity state. | Medium | Medium (4h) |
| UXD-013 | **Footer lacks meaningful content.** Single branding line, no links (privacy, terms, help). | Low | Small (1h) |
| UXD-014 | **SourceBadges text missing Portuguese diacritics.** "combinacoes" should be "combinacoes" with proper accents. | Low | Trivial (15min) |
| UXD-015 | **No color contrast audit for all 5 themes.** Sepia and Paperwhite themes not verified against WCAG AA. | Medium | Medium (4h) |
| UXD-016 | **LoadingProgress is 450+ lines.** Handles progress bar, ETA, stages, UF grid, carousel, skeletons, analytics. Should decompose. | Medium | Large (6h) |
| UXD-017 | **Hardcoded fallback sectors.** 7 sectors in `useSearchForm.ts` could become stale if backend changes. | Low | Small (1h) |
| UXD-018 | **Hardcoded Tailwind colors in SearchSummary.** Type badges use `bg-blue-100`, `bg-purple-100` instead of design tokens. Break in Sepia/Paperwhite themes. | Low | Small (1h) |
| UXD-019 | **carouselData uses hardcoded Tailwind category colors.** `bg-blue-50`, `bg-green-50`, etc. Not token-aware. | Low | Medium (2h) |
| UXD-020 | **No form `noValidate` attribute.** Native browser validation may conflict with custom validation. | Low | Trivial (5min) |

---

## 12. Design System Assessment

### What Exists (Strengths)

1. **Comprehensive CSS custom property token system** with 55+ variables covering canvas, ink, brand, surface, semantic, status, border, and focus categories.
2. **Full dark mode support** with `.dark` class override pattern and 5 theme variants.
3. **Tailwind integration** maps all tokens to utility classes for consistent usage.
4. **Three font families** with clear purpose (body, display, data).
5. **Border radius scale** (input: 4px, button: 6px, card: 8px, modal: 12px).
6. **Animation system** (fadeInUp, fadeIn, shimmer) with stagger utilities.
7. **Global touch target minimum** (44px buttons/inputs).
8. **`prefers-reduced-motion` support** disabling all animations.
9. **Consistent button visual pattern** (brand-navy primary, surface-0 secondary).

### What Is Missing

1. **No component library or Storybook** -- components only documented in code.
2. **No documented color palette** with contrast ratios per theme.
3. **No icon system** -- 8+ unique SVGs are inline throughout components, duplicated across files.
4. **No formal button variants** -- primary/secondary/ghost/danger patterns exist but are ad-hoc class strings.
5. **No form field component** -- input styling (`w-full border border-strong rounded-input px-4 py-3 text-base bg-surface-0 text-ink focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue transition-colors`) is repeated verbatim in 4 places.
6. **No spacing documentation** -- relies on Tailwind defaults.
7. **No typography scale documentation** beyond font family assignment.

### Consistency Issues

- **SearchSummary** type badges use hardcoded `bg-blue-100 text-blue-800` and `bg-purple-100 text-purple-800` instead of design tokens. These break in Sepia/Paperwhite themes.
- **carouselData** category configs use hardcoded Tailwind colors (`bg-blue-50 dark:bg-blue-950/30`, etc.) -- partially dark-mode aware via `dark:` prefix but not token-based.
- **Input styling** repeated verbatim in SearchForm (sector select), SearchForm (terms input wrapper), DateRangeSelector (2 date inputs), SaveSearchDialog (name input).

### Recommendations

1. **Extract a `<TextInput>` component** to eliminate repeated styling classes.
2. **Extract a `<Button>` component** with `variant` prop (primary, secondary, ghost, danger, disabled).
3. **Create a shared icons module** (`app/components/icons.tsx`) exporting named SVG components.
4. **Set up Storybook** for visual documentation and isolated component development.
5. **Audit contrast ratios** for all 5 themes against WCAG AA (4.5:1 text, 3:1 UI).
6. **Migrate hardcoded colors** in SearchSummary and carouselData to design tokens.
7. **Document the design system** in a dedicated `DESIGN_SYSTEM.md` with color, typography, spacing, and component guidelines.

---

## 13. Accessibility (A11y) Assessment

### Strengths (Implemented)

- **Skip navigation link** (`"Pular para o conteudo principal"`) in root layout
- **`lang="pt-BR"`** on `<html>` element
- **`aria-pressed`** on UF toggle buttons
- **`aria-live="polite"`** regions for search results and loading states
- **`role="alert"`** on all error messages (validation, search, download)
- **`aria-expanded`** and **`aria-haspopup`** on dropdown triggers
- **`aria-busy`** on search button during loading
- **`aria-label`** on region buttons, navigation, and icon-only buttons
- **`aria-describedby`** linking term input to help text
- **`role="group"`** with **`aria-label`** on UF grid
- **`role="dialog"`** with **`aria-modal`** and **`aria-labelledby`** on save dialog
- **Focus trap** implementation in SaveSearchDialog (Tab cycling, Escape to close)
- **`role="progressbar"`** with `aria-valuenow`/`min`/`max` on progress bar
- **`role="menu"`** / **`role="menuitem"`** with full keyboard navigation on theme toggle (ArrowUp/Down, Home/End, Escape)
- **Focus management** after search results (auto-focus heading + scroll into view)
- **Screen-reader-only result count announcement** via `aria-live` region
- **Hidden "Resultados" heading** (`tabIndex={-1}`) as focus target
- **`prefers-reduced-motion`** respected globally
- **44px minimum touch targets** on all interactive elements
- **Escape key handlers** on both ThemeToggle and SavedSearchesDropdown

### Weaknesses

| Issue | Impact | Fix Effort |
|---|---|---|
| No `aria-required` on mandatory form fields | Screen readers do not announce required state | Trivial |
| Delete confirmation in SavedSearchesDropdown uses timeout (3s auto-cancel) | Confusing for screen reader users | Small |
| Color alone distinguishes UF selected/unselected (mitigated by `aria-pressed`) | Visual-only users with color blindness | Small |
| No contrast audit for Sepia/Paperwhite themes | Possible WCAG AA failures | Medium |
| Region partial selection count only conveyed visually | Screen readers miss "(2/4)" indication | Small |

### Overall A11y Grade: **B+**

The application demonstrates deliberate, above-average accessibility attention for a POC. The main gaps are around edge cases in non-standard themes, missing `aria-required`, and some visual-only state indicators. The foundational patterns (ARIA roles, focus management, keyboard navigation, screen reader announcements) are solid.

---

## 14. Summary of Key Findings

### What Changed Since v2.0

| Previous Issue (v2.0) | Current Status |
|---|---|
| God component (page.tsx 1,071 lines) | **RESOLVED** -- Decomposed to 185 lines + 14 components + 5 hooks |
| Missing Escape key on dropdowns | **RESOLVED** -- Both ThemeToggle and SavedSearchesDropdown handle Escape |
| Modal missing focus trap and dialog role | **RESOLVED** -- SaveSearchDialog has full focus trap, role="dialog", aria-modal |
| No skip-to-content link | **RESOLVED** -- Added in root layout |
| No `<nav>` semantic element | **RESOLVED** -- Header nav has `aria-label="Navegacao principal"` |
| No focus management after search | **RESOLVED** -- Auto-focus results heading with scroll |
| External logo from Wix CDN | **RESOLVED** -- Self-hosted via next/image with priority |
| Error boundary uses hardcoded colors | **RESOLVED** -- Uses CSS custom properties with fallbacks |
| Duplicate UFS array | **RESOLVED** -- Centralized in `app/constants/ufs.ts` |
| Test coverage ~49% | **IMPROVED** -- Now ~68% statements |

### Top Priorities for Next Phase

1. **UXD-001 (High):** Fix multi-word term input -- critical UX bug preventing legitimate search terms
2. **UXD-015 (Medium):** Audit contrast ratios across all 5 themes for WCAG AA compliance
3. **UXD-016 (Medium):** Decompose LoadingProgress into smaller sub-components
4. **Design System:** Extract shared form input and button components to eliminate 4x duplication
5. **Testing:** Add tests for ThemeProvider, RegionSelector, carouselData; target 75% coverage
