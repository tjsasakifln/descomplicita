# Frontend Specification -- Descomplicita

**Project:** Descomplicita (formerly Descomplicita) -- Brazilian Procurement Search Platform
**Date:** March 2026
**Version:** 2.0
**Status:** MVP -- Production-ready single-page application
**Documented by:** @ux-design-expert (Pixel)
**Audit scope:** Complete frontend codebase analysis

---

## 1. Overview

### Purpose and User-Facing Features

Descomplicita (DescompLicita) is a procurement opportunity discovery platform for Brazil. It searches official government procurement portals (PNCP, Compras.gov, Transparencia, Diarios Oficiais, TCE-RJ) and returns AI-summarized results with an Excel download.

**Core user workflow:**
1. Select search mode (Sector or Custom Terms)
2. Choose Brazilian states (UFs) from a visual grid
3. Set date range
4. Submit search -> background job with real-time progress polling
5. View AI-generated executive summary with highlights
6. Download filtered results as Excel spreadsheet
7. Optionally save search for later re-use

**Additional features:**
- 5-theme system (Light, Paperwhite, Sepia, Dim, Dark)
- Saved searches (up to 10, persisted in localStorage)
- Real-time loading progress with 5-stage pipeline visualization
- Curiosity carousel during loading (52 items across 4 categories)
- Background browser notifications on search completion
- Source transparency badges showing per-source statistics
- Empty state with filter rejection breakdown and actionable suggestions
- Mixpanel analytics integration

### Target Audience

Brazilian businesses and procurement professionals who participate in public tenders (licitacoes). Primary use case: companies that supply goods/services to government entities searching for new opportunities across multiple states.

### Current State

**MVP** -- Single-page application with full search-to-download flow. Production-deployed with Docker standalone output. The app is functional but operates as a monolithic single page with all UI in `page.tsx` (1,071 lines).

---

## 2. Technology Stack

### Framework Versions
| Technology | Version | Purpose |
|---|---|---|
| Next.js | ^16.1.4 | React meta-framework with App Router |
| React | ^18.3.1 | UI library |
| TypeScript | ^5.9.3 | Type safety |
| TailwindCSS | ^3.4.19 | Utility-first CSS |
| PostCSS | ^8.5.6 | CSS processing |
| Autoprefixer | ^10.4.23 | CSS vendor prefixing |

### Key Dependencies
| Package | Version | Purpose |
|---|---|---|
| mixpanel-browser | ^2.74.0 | Analytics event tracking |
| uuid | ^13.0.0 | Unique ID generation for saved searches |
| @types/uuid | ^10.0.0 | TypeScript types for uuid |

### Dev Dependencies
| Package | Version | Purpose |
|---|---|---|
| jest | ^29.7.0 | Unit test runner |
| @swc/jest | ^0.2.29 | SWC-based Jest transformer |
| jest-environment-jsdom | ^29.7.0 | Browser environment simulation |
| @testing-library/react | ^14.1.2 | React component testing |
| @testing-library/jest-dom | ^6.1.5 | Custom DOM matchers |
| @testing-library/user-event | ^14.5.1 | User interaction simulation |
| @playwright/test | ^1.58.0 | E2E browser testing |
| @axe-core/playwright | ^4.11.0 | Accessibility testing in E2E |

### Build Configuration
- **Output:** `standalone` (Docker-optimized)
- **Strict mode:** Enabled (`reactStrictMode: true`)
- **Dark mode:** Class-based (`darkMode: "class"`)
- **Node.js requirement:** >=20.9.0

---

## 3. Application Architecture

### App Router Structure

```
frontend/
  app/
    layout.tsx          -- Root layout (fonts, metadata, providers)
    page.tsx            -- Main (and only) page -- entire UI
    error.tsx           -- Error boundary
    globals.css         -- Design system tokens + animations
    types.ts            -- Shared TypeScript interfaces
    icon.svg            -- Favicon (still shows "B" from Descomplicita era)
    api/
      buscar/
        route.ts        -- POST: Submit search job
        status/
          route.ts      -- GET: Poll job status
        result/
          route.ts      -- GET: Fetch completed result
      download/
        route.ts        -- GET: Serve Excel file
      setores/
        route.ts        -- GET: Fetch available sectors
    components/
      AnalyticsProvider.tsx
      carouselData.ts
      EmptyState.tsx
      LoadingProgress.tsx
      RegionSelector.tsx
      SavedSearchesDropdown.tsx
      SourceBadges.tsx
      ThemeProvider.tsx
      ThemeToggle.tsx
  hooks/
    useAnalytics.ts
    useSavedSearches.ts
  lib/
    savedSearches.ts
  public/
    .gitkeep
    logo-descomplicita.png
```

### Component Tree / Hierarchy

```
RootLayout (layout.tsx)
  AnalyticsProvider
    ThemeProvider
      HomePage (page.tsx) -- "use client"
        header
          img (logo)
          SavedSearchesDropdown
          ThemeToggle
        main
          [Search Mode Toggle]
          [Sector Select / Terms Input]
          RegionSelector
          [UF Grid]
          [Date Range Inputs]
          [Search Button]
          [Save Search Button]
          LoadingProgress (conditional)
          [Error Display] (conditional)
          EmptyState (conditional)
          [Result Display] (conditional)
            SourceBadges
            [Download Button]
        footer
        [Save Search Dialog Modal] (conditional)
```

### Data Flow Patterns

1. **Search initiation:** `page.tsx` -> POST `/api/buscar` -> backend `/buscar` -> returns `job_id`
2. **Status polling:** `setInterval` (2s) -> GET `/api/buscar/status?job_id=` -> updates progress state
3. **Result fetch:** On status=completed -> GET `/api/buscar/result?job_id=` -> sets result state
4. **Download:** Click -> GET `/api/download?id=` -> blob -> programmatic anchor click
5. **Sectors:** On mount -> GET `/api/setores` -> fallback hardcoded list on failure

All API routes in `/api/*` are **proxy routes** that forward requests to the Python backend (`BACKEND_URL` env var, default `http://localhost:8000`).

### State Management Approach

**Pure React state** -- no external state management library. All state lives in `HomePage` component via `useState` hooks. The component manages 20+ state variables including:
- Form state (UFs, dates, search mode, terms)
- Loading/error state
- Polling state (phase, UFs completed, items fetched, elapsed time)
- Result state
- Download state
- Save search dialog state

Refs are used for:
- Polling interval (`pollingRef`)
- Current job ID (`jobIdRef`)
- Search start time (`searchStartTimeRef`)
- Original document title (`originalTitleRef`)

---

## 4. Component Inventory

### HomePage (page.tsx)
- **Path:** `frontend/app/page.tsx`
- **Purpose:** Entire application UI -- search form, results display, download, save search
- **Lines:** 1,071
- **Props:** None (root page component)
- **Dependencies:** All other components, both hooks, types
- **Responsive:** Yes -- grid adjustments at `sm:` breakpoint, responsive typography
- **Accessibility:** aria-pressed on UF buttons, aria-busy on search button, role="alert" on errors, aria-live="polite" on loading
- **Issues:** God component -- 1,071 lines with 20+ state variables, all business logic, and UI rendering in one file

### LoadingProgress
- **Path:** `frontend/app/components/LoadingProgress.tsx`
- **Purpose:** Multi-stage loading visualization with progress bar, UF grid, curiosity carousel, skeleton cards
- **Lines:** 415
- **Props Interface:**
  ```typescript
  interface LoadingProgressProps {
    phase: SearchPhase;
    ufsCompleted: number;
    ufsTotal: number;
    itemsFetched: number;
    itemsFiltered: number;
    elapsedSeconds: number;
    onCancel: () => void;
    selectedUfs?: string[];
    sectorId?: string;
  }
  ```
- **Dependencies:** useAnalytics hook, carouselData, types
- **Responsive:** Stage labels hidden on mobile (`hidden sm:block`), mobile-specific detail card (`sm:hidden`)
- **Accessibility:** `role="progressbar"` with `aria-valuenow/min/max`, `aria-hidden` on decorative icons

### carouselData
- **Path:** `frontend/app/components/carouselData.ts`
- **Purpose:** Pure data module with 52 curiosity items across 4 categories, category config, and balanced shuffle algorithm
- **Lines:** 368
- **No React -- pure TypeScript data**
- **Exports:** `CURIOSIDADES`, `CATEGORIA_CONFIG`, `shuffleBalanced`, types

### SavedSearchesDropdown
- **Path:** `frontend/app/components/SavedSearchesDropdown.tsx`
- **Purpose:** Dropdown for managing saved searches -- load, delete, clear
- **Lines:** 250
- **Props Interface:**
  ```typescript
  interface SavedSearchesDropdownProps {
    onLoadSearch: (search: SavedSearch) => void;
    onAnalyticsEvent?: (eventName: string, properties?: Record<string, any>) => void;
  }
  ```
- **Dependencies:** useSavedSearches hook, SavedSearch type
- **Responsive:** "Buscas Salvas" label hidden on small screens (`hidden sm:inline`), dropdown width responsive (`w-80 sm:w-96`)
- **Accessibility:** `aria-label`, `aria-expanded`, `aria-hidden` on backdrop

### EmptyState
- **Path:** `frontend/app/components/EmptyState.tsx`
- **Purpose:** Informative empty state when search returns 0 results, with filter rejection breakdown and suggestions
- **Lines:** 140
- **Props Interface:**
  ```typescript
  interface EmptyStateProps {
    onAdjustSearch?: () => void;
    rawCount?: number;
    stateCount?: number;
    filterStats?: FilterStats | null;
    sectorName?: string;
  }
  ```
- **Dependencies:** FilterStats type
- **Responsive:** No specific responsive adjustments (relies on parent container)
- **Accessibility:** No explicit ARIA attributes

### ThemeProvider
- **Path:** `frontend/app/components/ThemeProvider.tsx`
- **Purpose:** Context provider for 5-theme system. Manages theme persistence in localStorage and applies CSS custom properties
- **Lines:** 122
- **Exports:** `ThemeProvider` component, `useTheme` hook, `THEMES` constant, `ThemeId` type
- **Dependencies:** None (pure React context)
- **Approach:** Imperatively sets CSS custom properties on `document.documentElement` via `applyTheme()` function

### SourceBadges
- **Path:** `frontend/app/components/SourceBadges.tsx`
- **Purpose:** Displays per-source search statistics with colored badges and expandable detail view
- **Lines:** 120
- **Props Interface:**
  ```typescript
  interface SourceBadgesProps {
    sources: string[];
    stats: Record<string, SourceStats>;
    dedupRemoved: number;
    truncatedCombos?: number;
  }
  ```
- **Responsive:** Margin adjustments (`mt-4 sm:mt-6`)
- **Accessibility:** No ARIA attributes on expandable section

### AnalyticsProvider
- **Path:** `frontend/app/components/AnalyticsProvider.tsx`
- **Purpose:** Initializes Mixpanel and tracks page_load/page_exit events
- **Lines:** 74
- **Dependencies:** mixpanel-browser, next/navigation
- **Issues:** Uses deprecated `performance.timing.navigationStart` API

### ThemeToggle
- **Path:** `frontend/app/components/ThemeToggle.tsx`
- **Purpose:** Dropdown button to switch between 5 themes
- **Lines:** 73
- **Dependencies:** ThemeProvider (useTheme, THEMES)
- **Responsive:** Theme label hidden on small screens (`hidden sm:inline`)
- **Accessibility:** `aria-label`, `aria-expanded`

### RegionSelector
- **Path:** `frontend/app/components/RegionSelector.tsx`
- **Purpose:** Quick-select buttons for Brazilian geographic regions (Norte, Nordeste, Centro-Oeste, Sudeste, Sul)
- **Lines:** 53
- **Props Interface:**
  ```typescript
  interface RegionSelectorProps {
    selected: Set<string>;
    onToggleRegion: (ufs: string[]) => void;
  }
  ```
- **Accessibility:** `aria-label` on each region button

### useAnalytics (Hook)
- **Path:** `frontend/hooks/useAnalytics.ts`
- **Purpose:** Wraps Mixpanel tracking with error handling. Provides trackEvent, identifyUser, trackPageView
- **Lines:** 66
- **Dependencies:** mixpanel-browser

### useSavedSearches (Hook)
- **Path:** `frontend/hooks/useSavedSearches.ts`
- **Purpose:** React hook wrapping localStorage-based saved searches with CRUD operations
- **Lines:** 148
- **Dependencies:** lib/savedSearches

### savedSearches (Library)
- **Path:** `frontend/lib/savedSearches.ts`
- **Purpose:** Pure localStorage CRUD operations for saved searches (max 10, sorted by lastUsedAt)
- **Lines:** 99
- **Dependencies:** uuid

---

## 5. Design System Analysis

### Documented Design System

The project has a well-documented design system at `frontend/.interface-design/system.md` with clear rationale for decisions.

### Color Palette

**Brand Colors:**
| Token | Light | Dark | Purpose |
|---|---|---|---|
| `--brand-navy` | #0a1e3f | #0a1e3f | Primary action, authority |
| `--brand-blue` | #116dff | #116dff | Interactive accent |
| `--brand-blue-hover` | #0d5ad4 | #0d5ad4 | Hover state |
| `--brand-blue-subtle` | #e8f0ff | rgba(17,109,255,0.12) | Highlight backgrounds |

**Canvas & Ink:**
| Token | Light | Dark |
|---|---|---|
| `--canvas` | #ffffff | #121212 |
| `--ink` | #1e2d3b | #e8eaed |
| `--ink-secondary` | #3d5975 | #a8b4c0 |
| `--ink-muted` | #808f9f | #6b7a8a |
| `--ink-faint` | #c0d2e5 | #3a4555 |

**Surfaces:**
| Token | Light | Dark |
|---|---|---|
| `--surface-0` | #ffffff | #121212 |
| `--surface-1` | #f7f8fa | #1a1d22 |
| `--surface-2` | #f0f2f5 | #242830 |
| `--surface-elevated` | #ffffff | #1e2128 |

**Semantic:**
| Token | Light | Dark |
|---|---|---|
| `--success` | #16a34a | #22c55e |
| `--error` | #dc2626 | #f87171 |
| `--warning` | #ca8a04 | #facc15 |

### Typography

| Role | Font | Variable | Usage |
|---|---|---|---|
| Body | DM Sans | `--font-body` | All body text, labels, buttons |
| Display | Fahkwang | `--font-display` | Headings (matches Descomplicita brand) |
| Data | DM Mono | `--font-data` | Numbers, statistics, timestamps |

All fonts loaded via `next/font/google` with `display: "swap"` for performance.

**Font size:** `clamp(14px, 1vw + 10px, 16px)` responsive base with `line-height: 1.6`.

### Spacing System

Base: 4px (Tailwind default). Custom comment in config references 4px base but no custom values defined -- relies on Tailwind's default spacing scale.

### Border Radius Scale
| Token | Value | Usage |
|---|---|---|
| `rounded-input` | 4px | Form inputs |
| `rounded-button` | 6px | Buttons |
| `rounded-card` | 8px | Cards, panels |
| `rounded-modal` | 12px | Modals |

### Depth Strategy

**Borders-only** -- no box shadows. All depth conveyed through 1px borders with low-opacity values:
- `--border`: rgba(0,0,0,0.08) / rgba(255,255,255,0.08)
- `--border-strong`: rgba(0,0,0,0.15) / rgba(255,255,255,0.15)
- `--border-accent`: rgba(17,109,255,0.3) / rgba(17,109,255,0.4)

Exception: `shadow-lg` used on save search dialog and `shadow-sm` on theme dropdown.

### Dark/Light Theme Implementation

5 themes managed via `ThemeProvider`:

| Theme | isDark | Canvas | Ink |
|---|---|---|---|
| Light | No | #ffffff | #1e2d3b |
| Paperwhite | No | #F5F0E8 | #1e2d3b |
| Sepia | No | #EDE0CC | #2c1810 |
| Dim | Yes | #2A2A2E | #e0e0e0 |
| Dark | Yes | #121212 | #e0e0e0 |

Implementation uses inline `<script>` in `<head>` to prevent flash of unstyled content (FOUC), reading from localStorage before React hydrates. The `ThemeProvider` then takes over with `applyTheme()` which sets all CSS custom properties imperatively.

### Component Consistency

The design system is **well-defined but inconsistently applied**:
- `error.tsx` uses hardcoded Tailwind colors (`bg-gray-50`, `bg-green-600`, `text-gray-900`) instead of design tokens
- The `icon.svg` still shows "B" (from Descomplicita) with green background (`#166534`) instead of brand navy
- Some hardcoded Tailwind color classes in `SourceBadges.tsx` (`bg-green-100`, `bg-red-100`, etc.) instead of semantic tokens
- `carouselData.ts` uses hardcoded Tailwind colors (`bg-blue-50`, `bg-green-50`, etc.) for category styling

### Responsive Breakpoints

Uses Tailwind's default breakpoints:
- `sm:` (640px) -- primary responsive breakpoint used throughout
- `md:` (768px) -- used only for UF grid columns (`md:grid-cols-9`)
- No `lg:` or `xl:` usage

---

## 6. UX Patterns

### User Flows

**Primary Flow: Search -> Results -> Download**
1. User lands on page, sees search form with defaults (SC/PR/RS, last 7 days, Vestuario sector)
2. User can switch to "Termos Especificos" mode for custom keyword search
3. User selects states via grid or region quick-select buttons
4. User adjusts date range
5. User clicks "Buscar [Sector Name]"
6. Loading screen shows: progress bar, 5-stage indicator, UF grid, curiosity carousel, skeleton cards
7. On completion: executive summary, highlights, statistics, source badges
8. User clicks "Baixar Excel" to download
9. Optionally saves search for later

**Secondary Flow: Saved Searches**
1. Click "Buscas Salvas" dropdown in header
2. See list of up to 10 saved searches sorted by last used
3. Click to load parameters into form, or delete individual searches

### Loading States

**Excellent loading UX** with multi-layered feedback:
- 5-stage pipeline indicator (Queued -> Fetching -> Filtering -> Summarizing -> Generating Excel)
- Real progress bar with percentage based on actual backend phase
- UF visual grid showing completed/in-progress/pending states
- ETA calculation based on per-UF timing
- Elapsed time counter
- Curiosity carousel rotating every 6 seconds (sector-aware content)
- Skeleton result cards previewing upcoming layout
- Document title updates during background tab: progress % shown
- Browser notification on completion (if permission granted)
- Cancel button available at all times

### Error States

- **API errors:** Red card with error message + "Tentar novamente" button
- **Download errors:** Red card below download button
- **Validation errors:** Inline red text below affected fields with `role="alert"`
- **Error boundary:** Full-page error with "Ops! Algo deu errado" message
- **Backend unavailable:** Handled with 503 status and user-friendly message
- **Polling timeout:** 10-minute deadline with specific timeout message

### Empty States

Rich empty state component with:
- Contextual messaging based on raw count and filter stats
- Filter rejection breakdown (keyword, value range, state mismatch)
- Actionable suggestions (expand dates, add states, change sector)
- "Ajustar criterios de busca" button scrolls to top

### Feedback Mechanisms

- Button states: enabled/disabled/loading with visual changes
- UF buttons: pressed state via `aria-pressed` and bg-brand-navy
- Search mode toggle: segmented control with active state
- Form validation: real-time inline errors
- Download: loading spinner animation during download

### Notifications

- Browser Notification API (permission requested after first search)
- Document title change when tab is in background
- Title restored when user returns to tab

---

## 7. API Integration

### Frontend API Routes

| Route | Method | Purpose | Backend Proxy |
|---|---|---|---|
| `/api/buscar` | POST | Submit search job | `POST /buscar` |
| `/api/buscar/status` | GET | Poll job status | `GET /buscar/{job_id}/status` |
| `/api/buscar/result` | GET | Fetch completed result | `GET /buscar/{job_id}/result` |
| `/api/download` | GET | Serve Excel file | N/A (filesystem) |
| `/api/setores` | GET | List available sectors | `GET /setores` |

### Backend Communication Patterns

- **Proxy pattern:** All API routes proxy to Python backend via `BACKEND_URL` env var
- **Job-based async:** Search is async -- POST returns `job_id`, frontend polls status every 2s
- **File handling:** Result route saves base64-encoded Excel to tmp filesystem, download route serves it
- **TTL cleanup:** Downloaded files auto-expire after 1 hour (`DOWNLOAD_TTL_MS`)

### Error Handling in API Routes

Each route handles:
- Missing/invalid parameters (400)
- Backend unavailable (503)
- Backend errors (forwarded status)
- Network errors (catch blocks)
- Job not found (404)

### Polling Mechanism

```
POST /api/buscar -> { job_id }
  |
  v (every 2s via setInterval)
GET /api/buscar/status?job_id= -> { status, progress }
  |
  v (when status === "completed" or "failed")
GET /api/buscar/result?job_id= -> { resumo, download_id, ... }
```

- Polling interval: 2 seconds
- Timeout: 10 minutes
- On network error: silently retry next interval
- On completion: stop polling, fetch result, update UI

---

## 8. Performance Analysis

### Bundle Size Considerations

**Positive:**
- Minimal dependencies (only mixpanel-browser and uuid beyond React/Next.js)
- `output: 'standalone'` for optimized Docker builds
- Google Fonts via `next/font` (self-hosted, no external requests)
- `display: "swap"` on all fonts prevents blocking render

**Concerns:**
- `mixpanel-browser` (^2.74.0) adds significant bundle weight (~80KB minified)
- Entire page is `"use client"` -- no server-side rendering benefit for the main content
- Logo loaded from external Wix CDN (`static.wixstatic.com`) -- not self-hosted
- No dynamic imports or code splitting for components
- `carouselData.ts` (52 items, 368 lines) loaded eagerly even when not searching

### Image Optimization

- Logo: External URL via `<img>` tag, not using Next.js `<Image>` component (eslint disable comment present)
- `logo-descomplicita.png` exists in `/public/` but is not used -- logo comes from Wix CDN
- `icon.svg` is outdated (shows "B" in green, from Descomplicita era)

### Code Splitting

**None.** All components are imported statically. The entire UI loads as a single client-side bundle. Given it is a single-page app, this is acceptable for now but will become a concern as features grow.

### SSR vs CSR Patterns

- `layout.tsx` is a **server component** (renders HTML shell, fonts, metadata)
- `page.tsx` is `"use client"` -- the entire page is client-rendered
- All components are `"use client"`
- API routes are server-side (Next.js Route Handlers)
- No server-side data fetching for the main page

### Loading Performance

- **Font loading:** Optimized via `next/font/google` with `display: "swap"`
- **Theme FOUC prevention:** Inline script in `<head>` applies theme before paint
- **Animations:** CSS-based with `prefers-reduced-motion` support
- **Body background:** CSS-only radial gradients (no image assets)

---

## 9. Accessibility Audit

### ARIA Labels/Roles

**Present (27 occurrences across 6 files):**
- `aria-pressed` on UF toggle buttons
- `aria-busy` on search button during loading
- `aria-live="polite"` on loading progress container
- `aria-expanded` on dropdown triggers (ThemeToggle, SavedSearches)
- `aria-label` on buttons (theme toggle, region buttons, saved searches, download, remove term)
- `aria-hidden="true"` on decorative SVGs and backdrop
- `role="alert"` on error messages and urgency alerts
- `role="progressbar"` with `aria-valuenow/min/max` on progress bar

### Keyboard Navigation

**Partial implementation:**
- All interactive elements are `<button>` or `<input>` (focusable by default)
- `:focus-visible` styling defined globally (2px solid ring)
- Theme dropdown closes on outside click but **no Escape key handler**
- SavedSearchesDropdown closes on outside click but **no Escape key handler**
- Tag input supports Backspace (remove last) and Enter (add term)
- **No focus trap** in save search modal dialog
- **No keyboard navigation** within dropdown menus (arrow keys)

### Color Contrast

**Generally good** due to dark ink on light canvas:
- `--ink` (#1e2d3b) on `--canvas` (#ffffff) = 12.6:1 ratio (AAA)
- `--ink-secondary` (#3d5975) on `--canvas` = 6.0:1 (AA for normal text)
- `--ink-muted` (#808f9f) on `--canvas` = 3.4:1 (FAILS AA for normal text)
- `--ink-faint` (#c0d2e5) on `--canvas` = 1.7:1 (FAILS all levels)

**Dark mode concerns:**
- `--ink` (#e8eaed) on `--canvas` (#121212) = 14.5:1 (AAA)
- `--ink-muted` (#6b7a8a) on dark canvas = 3.8:1 (FAILS AA for normal text)

### Screen Reader Support

- Page language set to `pt-BR` in `<html lang="pt-BR">`
- `<h1>` present ("Busca de Licitacoes")
- Semantic HTML used (header, main, footer, section)
- `<label>` elements properly associated with inputs via `htmlFor`
- Error messages use `role="alert"` for live announcements
- Decorative SVGs use `aria-hidden="true"`

**Missing:**
- No skip-to-content link
- No `<nav>` element for header navigation
- UF grid has no group label for screen readers
- No announcement when search completes (only `aria-live` on loading)
- Save search dialog missing `role="dialog"` and `aria-modal`

### Focus Management

- **No focus management** after search completes (results may be below viewport)
- **No focus trap** in modal dialog
- Focus ring visible via `:focus-visible` global style
- Minimum touch target 44px enforced via global CSS (`button { min-height: 44px }`)

### Form Accessibility

- Labels associated via `htmlFor` on date inputs and save search name input
- Sector select has `id="setor"` but label uses wrapper `<label>` without `htmlFor`
- Terms input has `id="termos-busca"` but no visible `<label>` element (only wrapper label for section)
- Validation errors displayed with `role="alert"`

---

## 10. Responsive Design

### Mobile Layout (< 640px)

- Single-column layout
- UF grid: 5 columns (`grid-cols-5`)
- Stage labels hidden; mobile-specific detail card shown
- Smaller text (`text-sm` for most elements, `text-2xl` for headings)
- "Buscas Salvas" label hidden, only icon + count shown
- Theme label hidden, only color preview circle shown
- Smaller padding on result cards (`p-4`)
- Dropdown width: 320px (`w-80`)

### Tablet Layout (640px - 768px)

- Date inputs side-by-side (`sm:grid-cols-2`)
- UF grid: 7 columns (`sm:grid-cols-7`)
- Larger text and padding
- Stage labels visible
- Header tagline visible

### Desktop Layout (768px+)

- UF grid: 9 columns (`md:grid-cols-9`)
- Max content width: `max-w-4xl` (896px)
- Centered layout with `mx-auto`

### Breakpoint Usage

| Breakpoint | Occurrences | Primary Use |
|---|---|---|
| `sm:` (640px) | ~50+ | Typography, padding, grid, visibility |
| `md:` (768px) | 1 | UF grid columns only |
| `lg:` / `xl:` | 0 | Not used |

**Gap:** No large-screen optimization. Content is capped at 896px (`max-w-4xl`). On wide displays, there is significant whitespace with no additional density or layout changes.

---

## 11. Testing Coverage

### Test File Inventory

**Unit Tests (Jest):** 11 files, 3,726 lines total

| Test File | Lines | Tests |
|---|---|---|
| `page.test.tsx` | 601 | UF selection, dates, validation, polling, results, edge cases |
| `analytics.test.ts` | 449 | Mixpanel integration, event tracking |
| `savedSearches.test.ts` | 333 | CRUD operations, capacity limits |
| `components/LoadingProgress.test.tsx` | 311 | Phase rendering, progress, cancel |
| `error.test.tsx` | 237 | Error boundary rendering, reset |
| `api/buscar.test.ts` | 175 | POST validation, job creation, error handling |
| `api/download.test.ts` | 149 | File serving, expiration, cleanup |
| `api/buscar-result.test.ts` | 133 | Result fetching, status handling |
| `components/ThemeToggle.test.tsx` | 135 | Theme switching UI |
| `components/EmptyState.test.tsx` | 93 | Empty state rendering, filter stats |
| `api/buscar-status.test.ts` | 75 | Status polling endpoint |
| `setup.test.ts` | 37 | Jest setup verification |

**E2E Tests (Playwright):** 4 files, 998 lines total

| Test File | Lines | Scenarios |
|---|---|---|
| `01-happy-path.spec.ts` | 307 | Full user journey, UI elements, search, download |
| `02-llm-fallback.spec.ts` | 245 | LLM fallback behavior |
| `03-validation-errors.spec.ts` | 198 | Form validation scenarios |
| `04-error-handling.spec.ts` | 248 | Error states, backend failures |

### Coverage Metrics

From `jest.config.js` thresholds (last recorded):
- **Statements:** 49.45%
- **Branches:** 39.56%
- **Functions:** 41.98%
- **Lines:** 51.01%

**Note:** The claimed 91.5% coverage likely refers to a different measurement or was aspirational. Actual thresholds in config are significantly lower.

### Coverage Gaps

**Components without dedicated tests:**
- `RegionSelector` -- no unit test
- `SavedSearchesDropdown` -- no dedicated unit test (tested indirectly via page)
- `SourceBadges` -- no unit test
- `AnalyticsProvider` -- no unit test
- `ThemeProvider` -- no unit test
- `carouselData` -- no unit test for `shuffleBalanced` algorithm

**Hooks without dedicated tests:**
- `useAnalytics` -- tested via analytics.test.ts but not as hook
- `useSavedSearches` -- no dedicated hook test

### E2E Test Patterns

- Playwright configured for Chromium only
- API mocking via `page.route()` for deterministic tests
- Some E2E tests reference outdated class names (e.g., `bg-green-600` instead of `bg-brand-navy`)
- axe-core dependency installed but not visibly used in current test files
- Sequential execution (`fullyParallel: false`) for stability

---

## 12. Frontend Technical Debt

### TD-FE-001: God Component (page.tsx)
- **Description:** The main page component is 1,071 lines with 20+ state variables, all business logic, form handling, polling logic, download logic, save search logic, and complete UI rendering. This violates single responsibility and makes testing, maintenance, and modification extremely difficult.
- **File:** `frontend/app/page.tsx`
- **Severity:** Critical
- **Category:** Code Quality
- **Impact:** Any change to the UI or business logic requires touching a massive file. Testing individual features in isolation is impossible. New developers face a steep learning curve.

### TD-FE-002: Missing Escape Key Handling on Dropdowns
- **Description:** ThemeToggle and SavedSearchesDropdown close on outside click but do not respond to Escape key. This is a WCAG 2.1 requirement for dismissible content.
- **Files:** `ThemeToggle.tsx`, `SavedSearchesDropdown.tsx`
- **Severity:** High
- **Category:** Accessibility
- **Impact:** Keyboard-only users cannot dismiss dropdowns without clicking elsewhere.

### TD-FE-003: Modal Missing Focus Trap and Dialog Role
- **Description:** The save search modal dialog does not trap focus, does not have `role="dialog"` or `aria-modal="true"`, and does not return focus to the trigger element on close.
- **File:** `frontend/app/page.tsx` (lines 1002-1061)
- **Severity:** High
- **Category:** Accessibility
- **Impact:** Screen reader users may not know they are in a modal. Keyboard users can tab behind the modal overlay.

### TD-FE-004: Insufficient Color Contrast for Muted Text
- **Description:** `--ink-muted` (#808f9f) on white canvas has only 3.4:1 contrast ratio, failing WCAG AA for normal text (requires 4.5:1). `--ink-faint` (#c0d2e5) at 1.7:1 is decorative-only but used for text content in some places.
- **Files:** globals.css, multiple components using `text-ink-muted` and `text-ink-faint`
- **Severity:** High
- **Category:** Accessibility
- **Impact:** Low-vision users may struggle to read muted text labels, timestamps, and helper text.

### TD-FE-005: No Skip-to-Content Link
- **Description:** There is no skip navigation link for keyboard users to bypass the header and jump to main content.
- **File:** `frontend/app/page.tsx`
- **Severity:** Medium
- **Category:** Accessibility
- **Impact:** Keyboard users must tab through header elements on every page load.

### TD-FE-006: External Logo Dependency
- **Description:** The logo is loaded from `static.wixstatic.com` instead of being self-hosted. This creates a runtime dependency on an external CDN, potential CORS issues, and privacy concerns (third-party tracking).
- **File:** `frontend/app/page.tsx` (LOGO_URL constant)
- **Severity:** Medium
- **Category:** Performance / Reliability
- **Impact:** Logo may fail to load if Wix CDN is down. Not using Next.js `<Image>` means no optimization.

### TD-FE-007: Outdated Favicon
- **Description:** `icon.svg` displays a green "B" (from Descomplicita era). Should show Descomplicita branding.
- **File:** `frontend/app/icon.svg`
- **Severity:** Medium
- **Category:** Design
- **Impact:** Brand inconsistency. Users see outdated branding in browser tabs.

### TD-FE-008: Error Boundary Uses Hardcoded Colors
- **Description:** `error.tsx` uses hardcoded Tailwind colors (`bg-gray-50`, `bg-green-600`, `text-gray-900`) instead of the design system tokens, breaking theme consistency.
- **File:** `frontend/app/error.tsx`
- **Severity:** Medium
- **Category:** Design
- **Impact:** Error page does not respect dark mode or custom themes.

### TD-FE-009: Duplicate UFS Array Definition
- **Description:** The `UFS` array is defined in both `app/types.ts` (with `as const` for type inference) and `app/page.tsx` (as plain array). `UF_NAMES` mapping only exists in `page.tsx`.
- **Files:** `frontend/app/types.ts`, `frontend/app/page.tsx`
- **Severity:** Medium
- **Category:** Code Quality
- **Impact:** Maintaining two copies risks divergence. UF-related constants should be centralized.

### TD-FE-010: No Internationalization (i18n) Infrastructure
- **Description:** All user-facing strings are hardcoded in Portuguese throughout the codebase. There is no i18n framework or string extraction.
- **Files:** All component files
- **Severity:** Medium
- **Category:** Code Quality
- **Impact:** If the app needs to support other languages (English, Spanish), every component would need manual refactoring. Even for Portuguese-only, centralized strings would improve consistency.

### TD-FE-011: Deprecated API Usage in AnalyticsProvider
- **Description:** Uses `performance.timing.navigationStart` which is deprecated in favor of `performance.timeOrigin`.
- **File:** `frontend/app/components/AnalyticsProvider.tsx` (line 52)
- **Severity:** Low
- **Category:** Code Quality
- **Impact:** Will eventually break in future browsers. Easy fix.

### TD-FE-012: No Loading State for Sector List
- **Description:** The sectors dropdown has no loading indicator while fetching from `/api/setores`. If the backend is slow, the dropdown appears empty or shows fallback data without indication.
- **File:** `frontend/app/page.tsx`
- **Severity:** Low
- **Category:** UX
- **Impact:** Minor confusion if sectors take time to load.

### TD-FE-013: E2E Tests Reference Outdated Class Names
- **Description:** E2E tests check for `bg-green-600` CSS class (old Descomplicita theme) but the actual UI uses `bg-brand-navy`. These tests likely fail or are not being run.
- **File:** `frontend/__tests__/e2e/01-happy-path.spec.ts` (line 64)
- **Severity:** Low
- **Category:** Code Quality
- **Impact:** False test failures or skipped E2E tests.

### TD-FE-014: Missing Focus Management After Search
- **Description:** When search completes, results appear below the form but focus remains on the search button. Users on large forms may not notice results have loaded.
- **File:** `frontend/app/page.tsx`
- **Severity:** Medium
- **Category:** UX / Accessibility
- **Impact:** Screen reader users may not know results are available. Visual users on mobile must scroll to see results.

### TD-FE-015: No Code Splitting for Components
- **Description:** All components are statically imported. The LoadingProgress component (415 lines), carouselData (368 lines with 52 items), and SavedSearchesDropdown could be dynamically imported.
- **File:** `frontend/app/page.tsx`
- **Severity:** Low
- **Category:** Performance
- **Impact:** Larger initial bundle. These components are conditionally rendered and could benefit from `React.lazy()` or Next.js `dynamic()`.

### TD-FE-016: No `<nav>` Semantic Element
- **Description:** The header uses a `<header>` element but lacks `<nav>` for the navigation area (saved searches, theme toggle).
- **File:** `frontend/app/page.tsx`
- **Severity:** Low
- **Category:** Accessibility
- **Impact:** Screen readers cannot announce navigation landmark.

### TD-FE-017: SourceBadges and carouselData Use Hardcoded Colors
- **Description:** These components use raw Tailwind color classes (`bg-green-100`, `bg-red-100`, `bg-blue-50`, etc.) instead of design system tokens. These colors do not respond to theme changes beyond basic dark: variants.
- **Files:** `SourceBadges.tsx`, `carouselData.ts`
- **Severity:** Low
- **Category:** Design
- **Impact:** Visual inconsistency in non-standard themes (Paperwhite, Sepia).

### TD-FE-018: Unused Public Asset
- **Description:** `public/logo-descomplicita.png` exists but is not referenced anywhere in the codebase. The logo comes from an external Wix URL.
- **File:** `frontend/public/logo-descomplicita.png`
- **Severity:** Low
- **Category:** Code Quality
- **Impact:** Unused asset increases repository size. Should either be used (replacing Wix URL) or removed.

### TD-FE-019: Missing `aria-describedby` for Terms Input
- **Description:** The custom terms tag input has helper text below it ("Digite cada termo...") but no `aria-describedby` linking the input to the description.
- **File:** `frontend/app/page.tsx`
- **Severity:** Low
- **Category:** Accessibility
- **Impact:** Screen reader users do not hear the input instructions.

### TD-FE-020: Test Coverage Below Target
- **Description:** Jest coverage thresholds show statements at 49.45% and branches at 39.56%, well below the stated 91.5% target. Multiple components lack dedicated unit tests.
- **Files:** `jest.config.js`, test files
- **Severity:** Medium
- **Category:** Code Quality
- **Impact:** Low confidence in refactoring. Changes to untested components may introduce regressions.

---

## 13. Recommendations

### Priority 1: Critical (Sprint 1)

1. **Decompose page.tsx into feature modules** (TD-FE-001)
   - Extract `SearchForm` component (mode toggle, sector select, terms input)
   - Extract `UfSelector` component (grid, region selector, select/clear)
   - Extract `DateRangeSelector` component
   - Extract `SearchResults` component (summary, highlights, download)
   - Extract `SaveSearchDialog` component
   - Extract polling logic into a `useSearchJob` custom hook
   - Target: No component exceeds 200 lines

2. **Fix modal accessibility** (TD-FE-003)
   - Add `role="dialog"` and `aria-modal="true"`
   - Implement focus trap (lock focus inside modal)
   - Return focus to trigger button on close
   - Close on Escape key

3. **Add Escape key handling to all dropdowns** (TD-FE-002)
   - ThemeToggle: close on Escape
   - SavedSearchesDropdown: close on Escape

### Priority 2: High (Sprint 2)

4. **Fix color contrast issues** (TD-FE-004)
   - Darken `--ink-muted` to meet 4.5:1 ratio (e.g., #5a6a7a)
   - Audit all uses of `text-ink-faint` for non-decorative text
   - Review dark mode muted contrast

5. **Self-host logo and update favicon** (TD-FE-006, TD-FE-007)
   - Use the existing `public/logo-descomplicita.png` via Next.js `<Image>`
   - Update `icon.svg` with Descomplicita branding (navy "D" or brand mark)
   - Remove Wix CDN dependency

6. **Add skip-to-content link** (TD-FE-005)
   - Add visually-hidden link before header: "Ir para conteudo principal"
   - Target the `<main>` element with `id="main-content"`

7. **Fix focus management after search** (TD-FE-014)
   - After results load, scroll to and focus the results section
   - Use `ref` and `scrollIntoView({ behavior: "smooth" })`

### Priority 3: Medium (Sprint 3)

8. **Migrate error.tsx to design tokens** (TD-FE-008)
   - Replace hardcoded gray/green Tailwind classes with design system tokens
   - Ensure error page works correctly in all 5 themes

9. **Centralize UFS/UF_NAMES constants** (TD-FE-009)
   - Move to `lib/constants.ts` or expand `types.ts`
   - Single source of truth for all UF-related data

10. **Increase test coverage** (TD-FE-020)
    - Add unit tests for RegionSelector, SourceBadges, SavedSearchesDropdown
    - Add hook tests for useAnalytics and useSavedSearches
    - Target: 70% statements, 55% branches
    - Enable axe-core accessibility checks in E2E tests

11. **Fix E2E test assertions** (TD-FE-013)
    - Update class name assertions from `bg-green-600` to `bg-brand-navy`
    - Verify all E2E tests pass against current UI

### Priority 4: Low (Backlog)

12. **Add code splitting** (TD-FE-015) -- Dynamic import for LoadingProgress and carouselData
13. **Replace deprecated performance API** (TD-FE-011)
14. **Migrate hardcoded colors in SourceBadges/carouselData** (TD-FE-017)
15. **Add `<nav>` landmark** (TD-FE-016)
16. **Add `aria-describedby`** for terms input (TD-FE-019)
17. **Clean up unused assets** (TD-FE-018)
18. **Evaluate i18n framework** (TD-FE-010) -- Consider next-intl if multi-language becomes a requirement
19. **Add sector loading indicator** (TD-FE-012)

---

## Appendix: Source File Line Counts

| File | Lines |
|---|---|
| `app/page.tsx` | 1,071 |
| `app/components/LoadingProgress.tsx` | 415 |
| `app/components/carouselData.ts` | 368 |
| `app/components/SavedSearchesDropdown.tsx` | 250 |
| `hooks/useSavedSearches.ts` | 148 |
| `app/components/EmptyState.tsx` | 140 |
| `app/components/ThemeProvider.tsx` | 122 |
| `app/components/SourceBadges.tsx` | 120 |
| `app/types.ts` | 114 |
| `lib/savedSearches.ts` | 99 |
| `app/api/buscar/result/route.ts` | 98 |
| `app/api/download/route.ts` | 76 |
| `app/components/AnalyticsProvider.tsx` | 74 |
| `app/components/ThemeToggle.tsx` | 73 |
| `app/layout.tsx` | 72 |
| `app/error.tsx` | 70 |
| `hooks/useAnalytics.ts` | 66 |
| `app/api/buscar/route.ts` | 60 |
| `app/components/RegionSelector.tsx` | 53 |
| `app/api/buscar/status/route.ts` | 41 |
| `app/api/setores/route.ts` | 25 |
| **Total source lines** | **3,505** |
| **Total test lines** | **4,724** |
