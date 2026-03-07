# QA Review -- Technical Debt Assessment
**Reviewer:** @qa (Shield)
**Date:** 2026-03-07
**Reviewed Document:** docs/prd/technical-debt-DRAFT.md
**Codebase Commit:** 9fbd54d0 (main branch)

---

## Gate Status: APPROVED WITH CONDITIONS

The DRAFT is well-structured, thorough, and ready for final consolidation -- provided the conditions listed at the end of this review are addressed. The assessment correctly identifies the most critical issues and proposes a reasonable execution plan.

---

## 1. Coverage Investigation

### 1.1 Frontend Coverage Analysis

**Configured coverage (jest.config.js):**
- Statements threshold: 49%
- Branches threshold: 39%
- Functions threshold: 41%
- Lines threshold: 50%

The `jest.config.js` comments explicitly document the discrepancy: "target: 60% per CLAUDE.md, current: 49.45%". The thresholds are set to the current measured values, not aspirational targets.

**Actual measured coverage:** ~49.45% statements, ~39.56% branches (per config comments -- these are the last-run values baked into the threshold floor).

**The 91.5% claim is incorrect.** The system-architecture.md (Section 13.2) states "91.5% frontend test coverage" but this is contradicted by the project's own jest.config.js. The 91.5% figure likely originated from an early draft or was aspirational. The DRAFT correctly flags this discrepancy in Section 9 and Appendix C.

**Components without dedicated unit tests:**
- `RegionSelector.tsx` -- no unit test
- `SavedSearchesDropdown.tsx` -- no dedicated test (only indirect via page.test.tsx)
- `SourceBadges.tsx` -- no unit test
- `AnalyticsProvider.tsx` -- no unit test
- `ThemeProvider.tsx` -- no unit test
- `carouselData.ts` -- no unit test for `shuffleBalanced` algorithm

**Hooks without dedicated tests:**
- `useSavedSearches` -- no dedicated hook test
- `useAnalytics` -- tested via analytics.test.ts but not as an isolated hook

**Verdict:** The DRAFT's characterization of a major coverage gap is **confirmed**. The 91.5% figure must be corrected in the final document. Realistic current coverage is ~49% statements.

### 1.2 Backend Coverage Analysis

**Configured coverage (pyproject.toml):**
- `fail_under = 70.0` (CI threshold)
- Branch coverage enabled
- Source includes all backend files, excludes tests/ and venv/

**Claim validity: PARTIALLY VALID but needs qualification.**

The 99.2% claim is plausible given the test infrastructure:
- 26 test files with a total of **1,028 test function definitions** (counted via `def test_` pattern matching). The architecture doc claims 226+ tests, which significantly undercounts the actual number.
- Every backend module has a corresponding test file.
- Coverage runs in CI with `--cov=.` and uploads to Codecov.

However, several important qualifications:

1. **The CI coverage check uses `continue-on-error: true`** (tests.yml line 76). This means even if coverage drops below 70%, the pipeline still passes. This weakens the enforcement of the threshold.

2. **Integration tests are skipped.** `test_pncp_integration.py` has `@pytest.mark.skip(reason="Integration test - requires real API access")`. The integration-tests CI job prints a placeholder message: "Integration tests will be implemented in issue #27".

3. **Tests heavily use mocks.** The `conftest.py` and `mock_helpers.py` create mock orchestrators. While this is appropriate for unit tests, there is no end-to-end backend pipeline test that exercises POST /buscar -> poll -> result with even partially real components.

4. **Test-to-source naming inconsistency detected.** `test_main.py:24` asserts `app.title == "BidIQ Uniformes API"` but `main.py:59` now sets `title="Descomplicita API"`. This test is **currently failing** or was patched locally. This is a concrete branding debt artifact that the DRAFT should flag more prominently.

5. **Test files also use deprecated patterns.** `test_main.py:124` uses `datetime.utcnow()`, `test_concurrency.py:222` uses `asyncio.get_event_loop()`. When TD-015 and TD-024 are fixed, these test files will also need updates.

**Untested or lightly tested modules:**
- `config.py` -- `test_config.py` exists (23 tests) -- appears adequate
- `sources/comprasgov_source.py`, `querido_diario_source.py`, `tce_rj_source.py` -- tests exist for disabled sources (good for when they are re-enabled)

**Verdict:** The 99.2% line coverage claim is plausible but the **quality** of that coverage is moderate. High line coverage does not equal high confidence when integration tests are absent and CI enforcement uses `continue-on-error`.

---

## 2. Gaps Identified

| # | Gap | Area | Risk Level | Recommendation |
|---|-----|------|------------|----------------|
| G-01 | **Failing backend test not flagged** -- `test_main.py` asserts `app.title == "BidIQ Uniformes API"` but main.py says `"Descomplicita API"`. At least 2 tests are currently broken. | Code Quality | High | Add as sub-item of TD-016 or new TD item. Fix immediately since it masks CI failures. |
| G-02 | **CI coverage check is non-blocking** -- `continue-on-error: true` on the coverage threshold step means coverage regressions pass silently | Maintainability | Medium | Remove `continue-on-error` once coverage stabilizes, or add a separate required status check |
| G-03 | **No Sentry or APM integration** -- `.env.example` has a SENTRY_DSN placeholder but no actual Sentry SDK is installed in requirements.txt or package.json | Observability | Medium | Add as a new debt item (TD-047). The system-architecture.md mentions it in recommendations but it is missing from the debt inventory. |
| G-04 | **`termos_busca` input not length-limited** -- while regex injection is mitigated via `re.escape()`, there is no max length validation. A user could submit a megabyte-long string. | Security | Medium | Add length validation to `BuscaRequest.termos_busca` (e.g., `max_length=500`) |
| G-05 | **Debug/diagnostic endpoints in production** -- `/cache/stats`, `/cache/clear`, `/debug/pncp-test` are exposed without auth | Security | Medium | Should be gated behind auth or disabled in production. Add as security debt item. |
| G-06 | **E2E tests do not use axe-core despite it being installed** -- `@axe-core/playwright` is in dependencies but `grep -r "axe" __tests__/e2e/` returns zero matches | Testing | Low | Document in test improvement plan |
| G-07 | **Postgres service in CI is unused** -- tests.yml provisions a postgres:15 service for integration tests that are skipped. Wasted CI resources. | Infrastructure | Low | Remove or actually implement integration tests |
| G-08 | **CORS comment still references `bidiq-uniformes.vercel.app`** -- main.py:73 has a comment with the old domain name | Branding | Low | Include in TD-016 branding cleanup |
| G-09 | **Backend tests also use deprecated APIs** -- TD-015 and TD-024 remediation must include updating test files that use the same deprecated patterns | Maintainability | Low | Note as dependency in TD-015 and TD-024 |
| G-10 | **No health check dependency validation** -- `/health` returns OK without verifying PNCP or OpenAI reachability. A "healthy" backend may have no working external connections. | Observability | Medium | Add as new debt item or sub-item of observability recommendations |

---

## 3. Risk Assessment

### 3.1 Security Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Wildcard CORS exploitation (TD-001) | High -- already exploitable | High -- any site can abuse the API | Sprint 1 quick fix; 1-2 hours |
| Root container escape (TD-002) | Low (requires kernel vuln) | Critical -- full host access | Sprint 1 quick fix; 1-2 hours |
| Resource exhaustion via no auth (TD-003) | High -- no barrier to entry | High -- 10 job slots monopolized | Backlog is risky; at minimum, deploy TD-006 (rate limiting) in Sprint 1 |
| Debug endpoints exposed (G-05) | Medium -- requires knowledge | Medium -- cache clear could disrupt service | Gate behind env-based feature flag |
| Unbounded `termos_busca` (G-04) | Low -- unlikely accidental | Medium -- memory pressure | Add `max_length` validation |

**Security Risk Assessment:** The DRAFT correctly identifies TD-001, TD-002, and TD-003 as Critical/High. However, I flag a concern with the execution plan: **TD-003 (authentication) is placed in the Backlog, which means the system will remain fully unauthenticated through 6 sprints.** At minimum, a simple API key (Phase 1 of TD-003) should be elevated to Sprint 1 or 2. Without it, TD-006 (rate limiting by IP) is easy to bypass via IP rotation.

### 3.2 Regression Risks

| Debt Resolution | Regression Risk | Mitigation |
|-----------------|-----------------|------------|
| TD-004 (God component decomposition) | **HIGH** -- 1,071-line refactor touches all UI features | Establish E2E baseline before refactor; run full Playwright suite after each extraction; keep feature parity checklist |
| TD-005 (Redis migration) | **MEDIUM** -- changes job lifecycle | Dual-write strategy (in-memory + Redis) during transition; comprehensive job lifecycle tests |
| TD-011 (requests -> httpx migration) | **MEDIUM** -- changes HTTP behavior | Compare response counts between old and new implementations on same query; regression test with known-good query producing N results |
| TD-013 (DI refactor) | **MEDIUM** -- touches all module initialization | Run full backend test suite; verify startup behavior in Docker |
| TD-010 (color contrast fix) | **LOW** -- visual only | Before/after screenshots across all 5 themes; visual regression test |
| TD-016 (branding cleanup) | **LOW** -- string replacements | Search-and-replace audit; ensure no functional code depends on old names |

### 3.3 Integration Risks

| Risk | Components Affected | Mitigation |
|------|---------------------|------------|
| TD-007 + TD-023 (file delivery refactor) | Backend result endpoint, frontend result route, frontend download route, frontend download button | End-to-end download test must pass on both old and new paths during migration |
| TD-005 + TD-026 (Redis introduction) | Backend startup, job store, cache, Docker compose, Railway config | Add Redis to docker-compose.yml; validate Railway supports Redis add-on; run full test suite with Redis backend |
| TD-004 (frontend decomposition) + frontend tests | All component tests reference `page.tsx` imports | Tests must be migrated alongside component extraction; test files that import from `page.tsx` will break |
| TD-014 (lifespan migration) + TD-013 (DI) | Backend startup, cleanup tasks, global singletons | These should be done together to avoid double-refactoring `main.py` startup logic |

---

## 4. Dependency Validation

### Proposed Sprint Order: NEEDS MINOR ADJUSTMENT

The 6-sprint plan in Section 8 is fundamentally sound. The dependency map in Section 7 is accurate. However, I identify the following adjustments:

**Issue 1: TD-003 in Backlog is too late.**
Authentication (even API-key-only) should move to Sprint 2 at latest. Without auth, rate limiting (TD-006) is ineffective against determined abuse. The DRAFT correctly notes "TD-003 REQUIRES TD-001" but then places TD-003 in the Backlog while TD-001 is Sprint 1. The dependency chain is satisfied by Sprint 2.

**Issue 2: TD-013 and TD-014 should be combined in one sprint.**
The DRAFT places them together in Sprint 4, which is correct. The dependency map notes TD-013 ENHANCES TD-014 -- these are tightly coupled and should be done by the same developer in the same PR.

**Issue 3: TD-004 (Sprint 3) regression risk needs E2E baseline.**
Sprint 2 includes accessibility work but the E2E tests are currently broken (TD-041 references `bg-green-600`). TD-041 should be moved to Sprint 2 or early Sprint 3 as a prerequisite for TD-004. You cannot validate a major refactor against a broken test suite.

**Issue 4: Hidden dependency -- backend test fixes (G-01) block CI.**
If `test_main.py` is asserting `app.title == "BidIQ Uniformes API"` and the app title is now `"Descomplicita API"`, CI may already be red. This must be fixed before any other work.

**Revised Sprint Suggestions:**

| Sprint | Change | Reason |
|--------|--------|--------|
| Sprint 0 (immediate) | Fix broken test assertions (G-01), fix E2E class name assertions (TD-041) | Unblock CI and E2E validation |
| Sprint 1 | Add TD-003 Phase 1 (API key auth, ~4-8 hours) alongside TD-001, TD-002, TD-006, TD-012 | Meaningful security posture |
| Sprint 2 | No change -- accessibility sprint | Fine as-is |
| Sprint 3 | No change -- God component decomposition | Fine, but requires Sprint 0 E2E fixes |
| Sprint 4 | Combine TD-013 + TD-014 in same PR | Tightly coupled |
| Sprint 5 | No change | Fine |
| Sprint 6 | No change | Fine |

---

## 5. Answers to @architect Questions (Section 9)

### Q1 (TD-041): Are E2E tests currently passing in CI?

**No.** The E2E test `01-happy-path.spec.ts` line 64 asserts `await expect(spButton).toHaveClass(/bg-green-600/)` but the actual UI uses `bg-brand-navy` for selected UF buttons (confirmed in `page.tsx` lines 587, 598). This assertion **will fail** against the current codebase.

The CI workflow (`tests.yml`) does run E2E tests (lines 147-304) with a full backend+frontend stack. However, the E2E job depends on unit tests passing first. If the backend unit tests are also failing (due to the `app.title` assertion mismatch at `test_main.py:24`), the E2E tests may never execute.

**Recommendation:** Fix both `test_main.py` title assertions and E2E class name assertions as Sprint 0.

### Q2 (TD-020): Frontend coverage discrepancy investigation

**Finding:** The 91.5% figure in `system-architecture.md` Section 13.2 is factually wrong. The canonical measurement is in `jest.config.js`, which records 49.45% statements. The comments in `jest.config.js` explicitly track the progression: "Progress: 31% -> 49.45% (+18.45% from test additions)".

There are no additional test suites that could account for the difference. Playwright E2E tests are excluded from Jest coverage (`testPathIgnorePatterns: ['/__tests__/e2e/']`). There is no separate coverage tool configured.

**Recommendation:** Correct the architecture doc to state actual coverage. Set a realistic target of 60% statements for next milestone (as the jest.config.js comments already suggest).

### Q3: Testing strategy for TD-004 (God Component decomposition)

**Recommended strategy:**

1. **Before decomposition:** Fix E2E tests (TD-041) to establish a passing baseline. Run and record full Playwright suite results.
2. **During decomposition:** Extract one component at a time. After each extraction:
   - Run existing `page.test.tsx` (601 lines) to verify no regression
   - Run full E2E suite
   - Add unit tests for the extracted component
3. **After decomposition:** Each extracted component should have its own test file. The `page.test.tsx` should shrink proportionally.
4. **Feature parity checklist:** Create a manual QA checklist covering: search submission, UF selection, date range, sector switching, custom terms, polling, result display, Excel download, save search, load saved search, theme switching, region selector. Verify each after the refactor.

### Q4: Accessibility testing with axe-core

**Finding:** `@axe-core/playwright` (v4.11.0) is listed as a dev dependency in `package.json` but is **not imported or used** in any E2E test file. Zero matches for "axe" in the `__tests__/e2e/` directory.

**Recommendation:** Yes, implement axe-core checks in E2E tests and gate PRs on zero critical/serious violations. Add to at least the happy-path E2E test:
```typescript
import AxeBuilder from '@axe-core/playwright';
// After page loads:
const results = await new AxeBuilder({ page }).analyze();
expect(results.violations.filter(v => ['critical', 'serious'].includes(v.impact))).toHaveLength(0);
```

### Q5: Backend test fidelity -- behavior vs code paths

**Assessment: Mixed.** The tests are well-structured and test meaningful behavior:
- `test_resilience.py` -- tests partial failures, full outages, rate limiting scenarios with mock PNCP errors
- `test_filter.py` -- 63 tests covering keyword matching, normalization, exclusions
- `test_load.py` -- tests 1/5/27 UF searches and progress phase transitions
- `test_concurrency.py` -- tests 429 responses when job slots are full

However:
- No integration test exercises the full POST -> poll -> result pipeline with real (or semi-real) components
- The `test_pncp_integration.py` tests are permanently skipped
- All external calls (PNCP API, OpenAI) are mocked
- The `run_sync` fixture in `test_resilience.py` patches `run_in_executor` to avoid deadlocks -- this is necessary but means the async execution model is not truly tested

**Recommendation:** Add at least one integration test that runs the full pipeline with a mock HTTP server (using `pytest-httpx` or `respx`) returning canned PNCP responses. This would validate the entire chain without real API calls.

### Q6: TD-037 (Date range max removed) -- resource consumption testing

**Finding:** No specific test exists for large date range resource consumption. The `BuscaRequest` schema in `schemas.py` no longer enforces a max-days limit. A user could query 365 days across 27 UFs, which would create 27 x 7 (or 27 x 3 with modalidade reduction) = 81-189 PNCP API task combinations, each potentially fetching up to 10 pages.

**Risk:** This could result in:
- 810-1,890 HTTP requests to PNCP per single search
- Extended job duration (potentially 10+ minutes)
- Memory pressure from accumulating results
- Rate limiting from PNCP

**Mitigation already in place:** Dynamic pagination cap (`min(max_pages, max(2, 600/num_tasks))`) and modalidade reduction for >10 UFs. These limit the blast radius but do not prevent very long-running jobs.

**Recommendation:** Re-introduce a configurable max date range (e.g., 90 days) or add a warning/confirmation step for ranges >30 days. Add a test that verifies resource bounds for extreme queries.

### Q7: Circuit breaker / rate limiter testing

**Finding:** `test_resilience.py` has 9 test functions covering error scenarios, and `test_pncp_client.py` has 41 tests including retry, rate limiting, and circuit breaker logic. These are unit-tested with mocks simulating timeouts and 429 responses.

**Not tested under realistic load:** No test simulates concurrent requests hitting the circuit breaker under genuine latency conditions. The tests use synchronous mocks with `run_sync` fixture, which bypasses the actual threading model.

**Recommendation:** The unit tests are adequate for verifying logic correctness. True load testing should be done as a separate performance test suite (outside CI), not as part of the debt assessment.

---

## 6. Test Requirements

### For Critical/High Debts

| Debt ID | Required Tests | Type | Est. Hours |
|---------|---------------|------|------------|
| TD-001 | Verify CORS rejects requests from non-whitelisted origins; verify whitelisted origins work | Unit (backend) | 1 |
| TD-002 | Verify Dockerfile USER directive is non-root; container smoke test runs as appuser | Integration (Docker) | 0.5 |
| TD-003 | Auth middleware tests: reject without key, accept with valid key, reject expired token (Phase 2) | Unit (backend) | 4 |
| TD-004 | Unit tests for each extracted component; existing page.test.tsx must still pass; E2E full regression | Unit + E2E (frontend) | 8 |
| TD-005 | Job lifecycle tests against Redis (create, poll, complete, expire, TTL cleanup); horizontal scaling test with 2 instances | Integration (backend) | 4 |
| TD-006 | Rate limit enforcement: verify 429 after N requests from same IP; verify different IPs are independent | Unit (backend) | 2 |
| TD-007 | Download via signed URL works; base64 path removed; large file download completes | Integration (full stack) | 3 |
| TD-008 | Focus trap inside modal; Escape closes modal; focus returns to trigger; aria-modal present | Unit (frontend) + E2E | 2 |
| TD-009 | Escape key closes ThemeToggle and SavedSearchesDropdown | Unit (frontend) | 1 |
| TD-010 | Automated contrast ratio check via axe-core for all text elements in all 5 themes | E2E (frontend) | 2 |
| TD-011 | Response count parity test: same query returns same count with httpx as with requests | Integration (backend) | 2 |
| TD-012 | Verify production Docker image does not contain pytest/ruff/mypy binaries | Integration (Docker) | 0.5 |
| TD-013 | All existing tests pass with DI-based initialization; startup behavior unchanged | Unit (backend) | 2 |
| TD-014 | Lifespan events fire correctly; cleanup task runs on shutdown | Unit (backend) | 1 |

**Total estimated test hours for Critical/High debts: ~33 hours**

---

## 7. Effort Estimate Validation

| Area | DRAFT Estimate (Low-High) | QA Assessment | Adjustment Reason |
|------|---------------------------|---------------|-------------------|
| Security (6 items) | 24-54h | 28-58h (+4) | TD-003 Phase 1 (API key) should be scoped at minimum. Underestimate if JWT added. |
| Accessibility (8 items) | 15-28h | 15-28h | Reasonable |
| Code Quality (12 items) | 36-68h | 40-76h (+4-8) | TD-004 testing effort underestimated; add 4-8h for comprehensive test migration |
| Performance (6 items) | 33-62h | 33-62h | Reasonable |
| Scalability (3 items) | 25-42h | 25-42h | Reasonable |
| Maintainability (8 items) | 26-50h | 26-50h | Reasonable |
| Design/UX (3 items) | 5-10h | 5-10h | Reasonable |
| **Sprint 0 (new)** | N/A | **2-4h** | Fix broken tests (G-01), E2E assertions (TD-041) |
| **TOTAL** | **164-314h** | **174-330h** | +10-16h for Sprint 0 and test migration |

The estimates are generally reasonable. The wide ranges on TD-003 (16-40h) and TD-004 (24-40h) appropriately reflect scope uncertainty.

---

## 8. Additional Findings

### 8.1 Backend Branding Inconsistency in Tests (NEW -- not in DRAFT)

The following backend test files still reference "BidIQ":
- `tests/conftest.py:1` -- docstring
- `tests/mock_helpers.py:1` -- docstring
- `tests/__init__.py:1` -- comment
- `tests/test_main.py:24` -- **functional assertion** `app.title == "BidIQ Uniformes API"`
- `tests/test_main.py:238` -- **functional assertion** `info["title"] == "BidIQ Uniformes API"`
- `tests/test_pncp_client.py:75` -- asserts User-Agent header contains "BidIQ"

The first two `test_main.py` assertions are **broken** since `main.py:59` now sets `title="Descomplicita API"`. These are functional test failures, not just cosmetic branding issues.

### 8.2 `pyproject.toml` Still Uses Old Name

`pyproject.toml:6` states `name = "bidiq-uniformes-backend"`. This should be updated to `descomplicita-backend` as part of TD-016.

### 8.3 `DeprecationWarning` Filter in pytest Config

`pyproject.toml:43` has `"ignore::DeprecationWarning"`. This means deprecated API usage (TD-015, TD-024) does **not** surface as test warnings. When those debts are fixed, consider removing this filter to catch future deprecations.

---

## 9. Final Verdict

### Gate Decision: APPROVED WITH CONDITIONS

### Conditions (must be addressed before final consolidation):

1. **BLOCKING:** Add Sprint 0 / immediate fix for broken backend tests (`test_main.py` title assertions) and E2E test class name assertions (TD-041). These are not future debt -- they are currently broken tests that may be masking CI failures.

2. **REQUIRED:** Correct the 91.5% frontend coverage claim in the final document. State the actual figure (~49.45% statements) and the realistic target (60%).

3. **REQUIRED:** Elevate TD-003 Phase 1 (API key auth) from Backlog to Sprint 1 or Sprint 2. An unauthenticated public API with only IP-based rate limiting is insufficient for a production deployment.

4. **RECOMMENDED:** Add the gaps identified in this review (G-01 through G-10) to the debt inventory or acknowledge them in the final document.

5. **RECOMMENDED:** Note that backend test files must also be updated when fixing TD-015 (datetime.utcnow) and TD-024 (get_event_loop), as tests use the same deprecated patterns.

### Overall Assessment:

The Technical Debt Assessment DRAFT is a high-quality document. The 46 debts are well-categorized, correctly prioritized by severity, and the dependency map is accurate. The effort estimates are realistic with appropriate uncertainty ranges. The cross-cutting concern analysis in Section 6 demonstrates genuine architectural understanding.

The primary weaknesses are:
- An inaccurate frontend coverage claim inherited from the architecture document
- Authentication being deprioritized to the Backlog despite being Critical severity
- Missing detection of currently-broken tests (which should be Sprint 0 fixes, not debt items)

With the conditions above addressed, this assessment is ready for final consolidation and sprint planning.

---

*Review completed: 2026-03-07*
*Reviewed by: @qa (Shield)*
*Against codebase commit: 9fbd54d0 (main branch)*
