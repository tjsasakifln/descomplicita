# Story 0.0: Emergency Fixes -- Unblock CI and Establish Regression Baseline

**Sprint:** 0
**Epic:** Resolucao de Debitos Tecnicos
**Priority:** Critical
**Estimated Points:** 3
**Estimated Hours:** 3-5

## Objetivo

Fix currently broken backend unit tests and E2E tests caused by the BidIQ-to-Descomplicita rebrand. This is a prerequisite for all subsequent work -- without a green CI pipeline and passing E2E suite, there is no regression baseline to validate the Sprint 2 God component decomposition (TD-004).

## Debts Addressed

| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-054 | Broken backend test assertions -- tests assert `app.title == "BidIQ Uniformes API"` but codebase says `"Descomplicita API"` | 1-2 | Backend |
| TD-041 | E2E tests reference outdated class names -- `01-happy-path.spec.ts:64` asserts `bg-green-600` but UI uses `bg-brand-navy` | 2-3 | Frontend |

## Tasks

- [ ] Task 1: Update `backend/tests/test_main.py:24` -- change `assert app.title == "BidIQ Uniformes API"` to `assert app.title == "Descomplicita API"`
- [ ] Task 2: Update `backend/tests/test_main.py:238` -- fix any additional BidIQ title assertions in the same file
- [ ] Task 3: Update `backend/tests/test_pncp_client.py:75` -- fix User-Agent assertion that checks for "BidIQ" string
- [ ] Task 4: Search all test files for remaining "BidIQ" references and update to "Descomplicita"
- [ ] Task 5: Update `frontend/e2e/01-happy-path.spec.ts:64` -- change `bg-green-600` assertion to `bg-brand-navy`
- [ ] Task 6: Search all E2E spec files for outdated CSS class references (`bg-green-600`, etc.) and update to current design token classes
- [ ] Task 7: Run full backend test suite (`pytest`) and verify all tests pass
- [ ] Task 8: Run E2E test suite and verify happy-path test passes
- [ ] Task 9: Verify CI pipeline is green on the resulting commit

## Criterios de Aceite

- [ ] `pytest` runs with zero failures on backend test suite
- [ ] All assertions in `test_main.py` reference "Descomplicita" not "BidIQ"
- [ ] All assertions in `test_pncp_client.py` reference "Descomplicita" not "BidIQ"
- [ ] E2E happy-path test (`01-happy-path.spec.ts`) passes end-to-end
- [ ] No test file contains the string "BidIQ" (verified via grep)
- [ ] CI pipeline completes successfully (green status)

## Testes Requeridos

- [ ] Run `pytest` -- all backend unit tests pass
- [ ] Run `npx playwright test` -- E2E happy-path passes
- [ ] Run `grep -r "BidIQ" backend/tests/` -- returns zero matches
- [ ] Run `grep -r "bg-green-600" frontend/e2e/` -- returns zero matches

## Dependencias

- Blocked by: None (this is Sprint 0, the prerequisite for everything)
- Blocks: All subsequent stories (Story 1.0 through Story 5.0). Specifically critical for Story 2.0 (God component decomposition) which requires a regression baseline.

## Definition of Done

- [ ] Code reviewed
- [ ] All backend tests passing (pytest)
- [ ] E2E happy-path test passing (Playwright)
- [ ] CI pipeline is green
- [ ] No regressions introduced
- [ ] No "BidIQ" references remain in any test file
