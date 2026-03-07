# Story 2.0: Frontend Architecture -- God Component Decomposition

**Sprint:** 2
**Epic:** Resolucao de Debitos Tecnicos
**Priority:** Critical
**Estimated Points:** 13
**Estimated Hours:** 31-45

## Objetivo

Decompose the monolithic `frontend/app/page.tsx` (1,071 lines, 23 useState calls, 4 useRef calls) into maintainable, testable modules. This is the single largest maintainability risk in the codebase, blocking all future feature work and making testing impractical. The target state is `page.tsx` under 150 lines acting as a thin orchestrator, with no extracted component exceeding 200 lines.

## Debts Addressed

| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-004 | God component -- page.tsx at 1,071 lines with 23 useState, 4 useRef | 28-40 | Frontend |
| TD-021 | Duplicate UFS constant definition (centralize during extraction) | 1-2 | Frontend |
| TD-028 | External logo dependency on Wix CDN (self-host during SearchHeader extraction) | 2-3 | Frontend |
| TD-045 | Unused public asset logo-descomplicita.png (consumed by TD-028) | 0 | Frontend |

## Tasks

### Phase 1: Extract Hooks (4-6 hours)

- [ ] Task 1: Create `frontend/app/hooks/useSearchJob.ts` -- extract polling logic, job phase state, job lifecycle management (start, poll, complete, error) from `page.tsx`
- [ ] Task 2: Create `frontend/app/hooks/useSearchForm.ts` -- extract form state management, validation logic, default values, sector/UF/date state from `page.tsx`
- [ ] Task 3: Write unit tests for `useSearchJob` hook (mock fetch, test polling lifecycle, test error states)
- [ ] Task 4: Write unit tests for `useSearchForm` hook (test validation, test defaults, test state transitions)

### Phase 2: Extract Leaf Components (8-12 hours)

- [ ] Task 5: Create `frontend/app/components/SaveSearchDialog.tsx` -- extract save-search modal with proper dialog role (prepares for TD-008 focus trap in Sprint 3)
- [ ] Task 6: Create `frontend/app/components/UfSelector.tsx` -- extract UF grid selection including RegionSelector as a child component
- [ ] Task 7: Create `frontend/app/components/SearchHeader.tsx` -- extract logo, dropdowns, theme toggle. Self-host logo via Next.js Image component (resolves TD-028).
- [ ] Task 8: Create `frontend/app/components/DateRangeSelector.tsx` -- extract date range picker UI and validation
- [ ] Task 9: TD-021 -- Create `frontend/app/constants/ufs.ts` with single canonical UFS definition. Update all imports to reference this file.
- [ ] Task 10: TD-045 -- Remove unused `public/logo-descomplicita.png` if TD-028 self-hosting uses a different asset, or verify it is now referenced.

### Phase 3: Extract Result Components (6-10 hours)

- [ ] Task 11: Create `frontend/app/components/SearchSummary.tsx` -- extract executive summary display, highlights rendering
- [ ] Task 12: Create `frontend/app/components/SearchActions.tsx` -- extract download button, save button, stats display
- [ ] Task 13: Create `frontend/app/components/SearchForm.tsx` -- extract mode toggle, sector select, terms input as a composed form component

### Phase 4: Wire and Test (8-12 hours)

- [ ] Task 14: Refactor `page.tsx` to thin orchestrator -- import all extracted components and hooks, wire props and callbacks. Target: under 150 lines.
- [ ] Task 15: Extract all user-facing strings to a constants file (recommended for future i18n, per UX review)
- [ ] Task 16: Write co-located unit tests for each extracted component (SaveSearchDialog, UfSelector, SearchHeader, DateRangeSelector, SearchSummary, SearchActions, SearchForm)
- [ ] Task 17: Run full E2E regression suite after each extraction phase to catch regressions early
- [ ] Task 18: Verify no component exceeds 200 lines

## Criterios de Aceite

- [ ] `frontend/app/page.tsx` is under 150 lines
- [ ] No extracted component exceeds 200 lines
- [ ] All 23 useState calls are distributed across hooks and components (none remain in page.tsx except orchestration state)
- [ ] All existing E2E tests pass without modification (regression-free extraction)
- [ ] Each extracted component has a co-located unit test file (`*.test.tsx`)
- [ ] UFS constant is defined in exactly one file (`frontend/app/constants/ufs.ts`)
- [ ] Logo is served from Next.js public assets or via next/image optimization, not from Wix CDN
- [ ] Frontend test coverage increases to >= 65% statements (from current ~49%)
- [ ] `page.tsx` reads as a clear orchestrator -- component composition is obvious at a glance

## Testes Requeridos

- [ ] Unit tests for `useSearchJob` hook: polling start, phase transitions, error handling, cleanup
- [ ] Unit tests for `useSearchForm` hook: validation, defaults, state management
- [ ] Unit tests for each extracted component: rendering, props, user interactions
- [ ] E2E regression: full happy-path test passes after each extraction phase
- [ ] E2E regression: search flow works end-to-end (form submit -> poll -> results -> download)
- [ ] Coverage check: `npx jest --coverage` shows >= 65% statements

## Dependencias

- Blocked by: Story 0.0 (E2E baseline must be established before decomposition begins)
- Blocks: Story 3.0 -- TD-008 (modal focus trap requires SaveSearchDialog extracted), TD-031 (focus management easier after extraction), TD-042 (code splitting requires separate components)

## Definition of Done

- [ ] Code reviewed (recommend incremental reviews per phase, not one massive PR)
- [ ] All existing tests passing
- [ ] All new component unit tests passing
- [ ] Coverage >= 65% statements
- [ ] E2E happy-path passes
- [ ] No regressions in functionality
- [ ] page.tsx < 150 lines verified
- [ ] No component > 200 lines verified
