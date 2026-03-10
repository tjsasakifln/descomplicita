# QA Review - Technical Debt Assessment

**Reviewer:** @qa (Quartz)
**Date:** 2026-03-09
**Source Documents:**

1. `docs/prd/technical-debt-DRAFT.md` (Phase 4 -- consolidated, 51 items)
2. `docs/reviews/db-specialist-review.md` (Phase 5 -- 3 new items DB-014/015/016)
3. `docs/reviews/ux-specialist-review.md` (Phase 6 -- 5 new items FE-015/016/017/018/019)

**Source Commit:** 5e56b38d
**Emphasis Areas:** UX quality, acentuacao, false positives/negatives, large volume searches

---

## Gate Status: APPROVED WITH CONDITIONS

The assessment is thorough, well-researched, and covers the critical areas needed for planning. The three review phases (architect consolidation, data-engineer validation, UX specialist review) provide excellent multi-perspective coverage. The emphasis areas (accents, FP/FN, large volumes) are addressed with unusual depth, including concrete code references, edge case analysis, and actionable recommendations.

**Conditions for proceeding to planning:**

1. **Consolidate item count to 59** -- the DRAFT executive summary still says 51; must be updated to reflect the 8 items added by specialist reviews.
2. **Resolve UX NEEDS REVISION status** -- the 5 new FE items (FE-015 through FE-019) and severity adjustments (FE-005 elevated to Critical, FE-007 elevated to High) must be incorporated into the prioritization matrix. This is a documentation task, not a blocker for story writing.
3. **Add FE-020 for multi-word term input** -- the UX review flags that UXD-001 (multi-word terms impossible via spacebar delimiter) was never migrated to the FE-* scheme. This is a real, known UX gap that should be tracked.

**These conditions are NOT blocking.** They can be addressed during the consolidation step before story creation. The assessment is complete enough for sprint planning to begin.

---

## Assessment Completeness

### Item Count Reconciliation

| Source | Items | IDs |
|--------|-------|-----|
| DRAFT (architect) | 51 | SYS-001..024 (24), DB-001..013 (13), FE-001..014 (14) |
| DB specialist review | 3 new | DB-014, DB-015, DB-016 |
| UX specialist review | 5 new | FE-015, FE-016, FE-017, FE-018, FE-019 |
| **Total unique items** | **59** | |
| Proposed addition | +1 | FE-020 (multi-word term input, from UXD-001) |
| **Adjusted total** | **60** | |

### Severity Distribution (post-specialist adjustments)

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | **4** | SYS-001, SYS-002, SYS-003, **FE-005** (elevated by UX review) |
| High | **12** | SYS-004, SYS-005, SYS-006, SYS-007, DB-001, DB-002, DB-003, FE-001, **DB-009** (elevated), **FE-007** (elevated), **FE-015** (new), **FE-016** (new) |
| Medium | **24** | SYS-008..015, SYS-017, DB-004..007, DB-014, DB-015, FE-004, FE-006, FE-008, FE-011, FE-017 (new), FE-019 (new) |
| Low | **20** | SYS-016, SYS-018..024, DB-008 (downgraded), DB-010..013, DB-016, FE-002, FE-003, FE-009, FE-010, FE-012..014, FE-018 (new) |

Note: DB-008 was downgraded from Medium to Low by the data-engineer review (storage is ephemeral, so retention is moot until Supabase migration).

### Estimated Hours (post-adjustments)

| Category | DRAFT Estimate | Adjusted | Delta | Notes |
|----------|---------------|----------|-------|-------|
| SYS items | ~113h | ~113h | 0 | No changes |
| DB items (original 13) | ~44.5h | ~42.5h | -2h | DB-003: 8->6h, DB-010: 4->2h |
| DB items (new 3) | -- | +4h | +4h | DB-014: 0.5h, DB-015: 3h, DB-016: 0.5h |
| FE items (original 14) | ~21.5h | ~21.5h | 0 | No changes |
| FE items (new 5) | -- | +11.25h | +11.25h | FE-015: 4h, FE-016: 3h, FE-017: 2h, FE-018: 0.25h, FE-019: 2h |
| Search quality recs | ~22h | ~25h | +3h | Stemming 8->10h, exclusions 2->3h, keyword cleanup 4->2h |
| **Grand total** | **~240h** | **~255h** | **+15h** | |
| **Critical + High** | **~85h** | **~100h** | **+15h** | FE-005 elevated, DB-009 elevated, new High items |

### Coverage Map

| Area | Covered By | Depth | Gaps |
|------|-----------|-------|------|
| Backend architecture | SYS-001..024 | Thorough | None significant |
| Database/Redis | DB-001..016 | Thorough after specialist review | None |
| Frontend/UX | FE-001..019 | Thorough after specialist review | FE-020 (multi-word input) missing |
| Accent handling | DRAFT deep dive + DB review | Excellent | None |
| False positives/negatives | DRAFT deep dive + DB review | Excellent | See emphasis area below |
| Large volume scenarios | DRAFT deep dive + DB review + UX review | Excellent | None |
| Security | SYS-002..007, DB-005, DB-014 | Adequate for POC | Production hardening needs story |
| Observability | SYS-024, DB-007, DB-011 | Adequate | No APM/tracing strategy |
| Test coverage | SYS-021, FE-010, FE-011 | Adequate | No mutation testing / coverage targets |

---

## Emphasis Area Validation

### 1. Acentuacao (Accent Handling)

**Coverage adequate: YES**

The assessment provides the most thorough accent analysis I have seen for a Portuguese-language search system. Specific strengths:

- **Code-level verification** of `normalize_text()` (filter.py lines 291-334) with NFD decomposition analysis
- **Edge case matrix** covering cedilha, til, agudo, circunflexo, trema, and hyphens
- **End-to-end trace** from user input (SearchForm.tsx `.toLowerCase()` preserves accents) through backend normalization (both sides normalized in `match_keywords()`) to display (PNCP text preserved)
- **Keyword redundancy quantification**: ~115 duplicate accent variants identified across all sectors
- **Confirmed by data-engineer**: no edge cases that fail NFD decomposition for Portuguese

**One minor gap found:** The assessment does not discuss Unicode NFC vs NFD handling for PNCP API responses. If the PNCP API returns NFC-normalized text (which is the standard for web APIs), and the user's input arrives as NFD (which can happen with some macOS keyboard input methods), the `normalize_text()` function handles this correctly because it explicitly performs NFD decomposition. However, this assumption is not tested. See test recommendation below.

**Verdict:** The accent handling is functionally correct. The ~115 redundant keyword variants are a maintenance burden but do not cause bugs. The FE-018 heading ("Licitacoes" without accents) is the only actual accent bug found.

#### Tests Needed

| # | Test Scenario | Type | Priority |
|---|--------------|------|----------|
| A1 | `normalize_text()` with all Portuguese diacritics (cedilha, til, agudo, circunflexo, grave, trema) | Unit | P2 |
| A2 | `normalize_text()` with NFC vs NFD input (both should produce identical output) | Unit | P2 |
| A3 | `match_keywords()` with accented keyword vs unaccented objeto, and vice versa | Unit | P2 |
| A4 | `match_keywords()` with hyphenated terms ("guarda-po" vs "guarda po") | Unit | P2 |
| A5 | End-to-end: user searches "licitacao" (no accents), results containing "licitacao" (with accents) are returned | Integration | P3 |
| A6 | End-to-end: user searches "licitacao" (with accents), same results returned as A5 | Integration | P3 |
| A7 | Validate no keyword pair in sectors.py has different `normalize_text()` outputs (redundancy detection script) | Script | P3 |
| A8 | Frontend: chips display accented text correctly after `.toLowerCase()` | Component | P4 |

---

### 2. Falsos Positivos / Falsos Negativos (False Positives / Negatives)

**Coverage adequate: YES, with one qualification**

The assessment identifies the two most critical FP/FN issues:

1. **Exclusions disabled for custom terms** (main.py line 543): confirmed in code, risk rated HIGH, with concrete examples and a hybrid mitigation plan (3h). This is the single biggest search quality issue.

2. **Tier scoring uses max() not sum()**: confirmed in code (filter.py lines 378-398). Items with multiple Tier C matches (e.g., "bota + meia + avental" = 0.3 + 0.3 + 0.3) never exceed 0.3, so they are systematically rejected despite being likely relevant. The data-engineer recommends additive scoring with cap (2h).

**Qualification:** The assessment does not provide a quantitative measurement framework for FP/FN rates. The data-engineer cites "20-40% FP rate for ambiguous terms without exclusions" but this is an estimate, not a measurement. Before and after any search quality change (stemming, exclusion policy, scoring), there should be a measurement test suite that runs a fixed set of query/expected-result pairs against real PNCP data snapshots.

**Additional FP/FN sources not fully explored:**

| Source | Type | Severity | Detail |
|--------|------|----------|--------|
| `MAX_PAGES_PER_COMBO = 10` truncation | FN | High | Acknowledged in DRAFT but no mitigation beyond "pre-computed pipeline" (40h). For SP + Pregao Eletronico with 228 pages, 95.6% of results are lost. This is the single largest source of false negatives. |
| No dedup across date chunks | Potential FP | Low | If PNCP returns the same item across adjacent date ranges (e.g., published on boundary date), it could appear twice. MD5 dedup should catch this, but the dedup key construction should be verified. |
| `palavraChave` not sent to PNCP | Indirect FN | High | The data-engineer correctly notes this parameter is simply never sent (not "silently ignored"). If it works, it could reduce volume 10-20x and indirectly reduce truncation-based FN. Testing this is potentially the highest-ROI action in the entire assessment. |

#### Tests Needed

| # | Test Scenario | Type | Priority |
|---|--------------|------|----------|
| FP1 | With custom terms and exclusions disabled: measure FP rate for "confeccao", "camisa", "bota", "colete" against 1000+ real PNCP items | Benchmark | P1 |
| FP2 | With exclusions re-enabled for custom terms: measure FP rate reduction for same terms | Benchmark | P1 |
| FP3 | Tier C scoring: verify "bota + meia + avental" (3 Tier C terms) is rejected with current max() scoring | Unit | P2 |
| FP4 | Tier C scoring: verify same item is accepted with additive scoring (0.3+0.3+0.3 = 0.9 >= 0.6) | Unit | P2 |
| FP5 | EPI_ONLY_KEYWORDS: verify item with only "epi" is rejected, but "epi + jaleco" is accepted | Unit | P2 |
| FP6 | Exclusion keyword with accent variant: verify "confeccao de placa" (without cedilha) still excludes "confeccao de placa" (with cedilha) | Unit | P2 |
| FP7 | MAX_PAGES_PER_COMBO truncation: measure how many results are lost for SP + Pregao Eletronico over 30 days | Measurement | P2 |
| FP8 | PNCP `palavraChave` parameter: manual API test to determine if it filters results | Manual | **P1** |
| FP9 | Dedup correctness: verify same item fetched from overlapping date chunks is deduped | Unit | P3 |
| FP10 | Golden test suite: 50 known-relevant and 50 known-irrelevant items, validate precision/recall after any search quality change | Regression | P2 |

---

### 3. Buscas de Grande Volume (Large Volume Searches)

**Coverage adequate: YES**

This is the most thoroughly analyzed emphasis area. Three independent analyses (DRAFT, data-engineer, UX specialist) converge on the same conclusions:

**Confirmed critical finding -- timeout race condition:**
- Frontend: 600,000ms (10 min) fixed
- Backend for 27 UFs: 300 + (27-5)*15 = 630s (10.5 min)
- 30-second window where backend may succeed but frontend has already shown error
- Verified in code: `useSearchJob.ts` line 154 (`POLL_TIMEOUT = 10 * 60 * 1000`) and `orchestrator.py` line 220

**Confirmed critical finding -- memory pressure:**
- 85K items: ~120MB Python + ~51MB Redis + ~200MB Excel peak = ~460MB per job
- Railway free tier: 512MB -- a single large search can cause OOM
- DB-015 (dual-write) doubles the Python memory cost: items stored both in `self._items` and Redis

**Confirmed critical finding -- ETA inaccuracy:**
- Post-fetching ETAs are hardcoded ("~15s", "~10s", "~5s") regardless of item count
- For 85K items, filtering takes 30-60s, not 15s
- Progress bar stuck at 60% during filtering phase
- User perceives system as frozen

**Cross-validated scenario analysis:**

| Scenario | DRAFT | DB Review | UX Review | Consensus |
|----------|-------|-----------|-----------|-----------|
| 27 UFs x 30 days | 4-7 min | 240-440s | Confirmed | FUNCTIONAL but close to limits |
| 27 UFs x 90 days | Exceeds timeouts | 600-1200s | Confirmed | BREAKS -- exceeds all timeouts |
| Memory for 85K items | ~50-100MB Redis | ~460MB total peak | N/A | RISK of OOM on free tier |

#### Tests Needed

| # | Test Scenario | Type | Priority |
|---|--------------|------|----------|
| LV1 | Frontend timeout >= backend timeout for any valid UF/date combination | Property-based | P1 |
| LV2 | Simulated 27 UF search with mock PNCP: verify no timeout before backend completes | Integration | P1 |
| LV3 | Memory measurement: track peak RSS during 85K item processing (filter + store + Excel) | Performance | P2 |
| LV4 | Redis LIST pagination: verify LRANGE returns correct page for 85K items | Unit | P2 |
| LV5 | ETA accuracy: verify ETA is proportional to actual remaining time for 10K+ items | Component | P3 |
| LV6 | Progress bar interpolation: verify bar moves from 60-75% during filtering, not stuck | Component | P3 |
| LV7 | Cancel button: verify backend job is actually cancelled, not just frontend polling stopped | Integration | P3 |
| LV8 | Concurrent large searches: 2 simultaneous 27-UF searches, verify no OOM or resource starvation | Stress | P3 |
| LV9 | Circuit breaker activation: verify search degrades gracefully when PNCP rate-limits | Integration | P3 |

---

### 4. UX Quality

**Coverage adequate: YES, after UX specialist review**

The UX specialist review (Pixel) is exceptionally thorough and addresses every question posed by the architect. Key findings validated through code:

1. **FE-005 elevation to Critical**: Verified. `ItemsList.tsx` line 44 has `catch { // silently fail }`. No error state, no retry, no logging. User sees "Carregando..." forever or empty list. For a B2B procurement tool, this is unacceptable.

2. **FE-015 (no term highlight)**: Verified. `ItemsList.tsx` line 79 renders `item.objeto` as plain text with no `<mark>` or highlight. The `ProcurementItem` interface (line 6-15) does not include matched terms or score from backend. This means the frontend cannot highlight even if it wanted to -- the backend would need to pass matched terms.

3. **FE-016 (no large volume warning)**: Verified. `UfSelector.tsx` and `page.tsx` have no conditional warning for >10 UFs or >30 days.

4. **FE-019 (pagination race condition)**: Verified. `fetchPage` in `ItemsList.tsx` (lines 30-51) has no AbortController. Rapid page navigation can cause stale data display.

5. **tipo field not rendered**: Verified. `ProcurementItem` interface includes `tipo?: string` (line 13) but it is never used in the JSX.

**Additional UX gap identified by this QA review:**

- **No "resultados parciais" concept**: When `MAX_PAGES_PER_COMBO` truncation occurs, the `SourceBadges` component shows a warning, but this warning is hidden behind a collapsed toggle (`expanded` state defaults to `false`). Users may make business decisions based on incomplete data without realizing it. This risk is acknowledged in the UX review but not given an FE-* item ID. Recommend tracking as FE-021 or incorporating into the SourceBadges visibility story.

#### Tests Needed

| # | Test Scenario | Type | Priority |
|---|--------------|------|----------|
| UX1 | FE-005: verify error state is displayed when fetch fails (after fix) | Component | P1 |
| UX2 | FE-005: verify retry button re-fetches the page | Component | P1 |
| UX3 | FE-015: verify search terms are highlighted in resultado objects (after fix) | Component | P2 |
| UX4 | FE-016: verify warning banner appears when >10 UFs selected | Component | P2 |
| UX5 | FE-016: verify warning banner appears when date range > 30 days | Component | P2 |
| UX6 | FE-019: verify AbortController cancels previous fetch on page change | Component | P3 |
| UX7 | FE-018: verify heading uses "Licitacoes" with proper accents | Component | P4 |
| UX8 | Theme coverage: verify badges in SearchSummary are legible in all 5 themes | Visual | P2 |
| UX9 | ink-muted contrast: verify WCAG AA (4.5:1) in light theme after fix | Accessibility | P2 |
| UX10 | EmptyState: verify text is not redundant for custom term searches | Component | P3 |

---

## Gaps Identificados

### Gap 1: No Observability/Monitoring Strategy

The assessment identifies individual observability items (SYS-024 logging, DB-007 health check, DB-011 silent degradation) but lacks a cohesive monitoring strategy. For a procurement tool where timeliness matters, there should be:

- Response time tracking per search (P50/P95/P99)
- PNCP API availability monitoring
- Rate limit / circuit breaker activation metrics
- Memory usage trends
- Error rate by endpoint

**Recommendation:** Add a cross-cutting "Observability Story" that bundles SYS-024 + DB-007 + DB-011 + memory metrics (data-engineer recommendation) + PNCP metrics. Estimate: 8-12h total.

### Gap 2: No Accessibility Regression Strategy

FE-007 (ink-muted contrast) is the only accessibility debt item, but the assessment does not mention ongoing accessibility compliance. The existing Playwright axe-core tests (`frontend/__tests__/e2e/`) provide a baseline, but there is no accessibility gate in CI/CD or contrast validation for new theme tokens.

**Recommendation:** Add a task to integrate axe-core checks into the CI pipeline and add contrast ratio validation for all `--ink-*` tokens across all 5 themes. Estimate: 4h.

### Gap 3: No Error Boundary Strategy

FE-005 (error swallowing) and FE-009 (no fallback for dynamic imports) are symptoms of a broader gap: no React Error Boundary strategy. If any component throws during render (not just fetch), the entire page crashes with no recovery. Next.js `error.tsx` exists but only catches page-level errors, not component-level.

**Recommendation:** Add a generic `ErrorBoundary` component that wraps critical sections (results, search form) with fallback UI. Estimate: 3h.

### Gap 4: No Data Freshness Indicator

The assessment does not address how users know if data is current. PNCP data has publication dates, but:
- There is no "data atualizada em" indicator showing when the last PNCP fetch occurred
- If PNCP is down or rate-limiting, partial results are returned without clear indication
- The circuit breaker silently degrades -- users may see fewer results without knowing why

**Recommendation:** Display "Dados consultados em {timestamp}" in the results header. Estimate: 1h.

### Gap 5: FE-020 -- Multi-Word Term Input (from UXD-001)

The UX review explicitly flags that UXD-001 (multi-word terms impossible via spacebar delimiter in SearchForm.tsx) was never migrated to the FE-* numbering scheme. The backend supports quoted multi-word terms (`parse_multi_word_terms` in main.py line 214), but the frontend SearchForm splits on space (line 126), making it impossible for users to enter "camisa polo" as a single search term without using quotes -- and there is no affordance indicating quotes are supported.

**Recommendation:** Track as FE-020. Severity: Medium. Effort: 3h (add comma delimiter support in frontend + hint text). Priority: P3.

---

## Riscos Cruzados

| Risco | Areas Afetadas | Severidade | Mitigacao Proposta |
|-------|---------------|-----------|-------------------|
| **Timeout race condition** (frontend 10min vs backend 10.5min for 27 UFs) | Backend (orchestrator.py), Frontend (useSearchJob.ts), UX (user sees false error) | **Critica** | Dynamic frontend timeout based on UF count (3h). Backend sends `X-Expected-Duration` header. |
| **Memory pressure from large searches** (85K items = ~460MB) | Backend (filter.py, redis_job_store.py), Database (Redis), Infrastructure (Railway 512MB) | **Critica** | DB-009 (Redis LIST, 6h) + DB-015 (eliminate dual-write, 3h) + Excel limit (4h) |
| **Search quality degrades for custom terms** (exclusions disabled) | Backend (main.py line 543), Frontend (ItemsList shows irrelevant results), UX (user trust) | **Alta** | Hybrid exclusion approach (3h) + term highlighting FE-015 (4h) |
| **Truncation hides relevant results** (MAX_PAGES_PER_COMBO = 10) | Backend (PNCP client), Frontend (SourceBadges warning hidden), UX (incomplete data for decisions) | **Alta** | Test PNCP `palavraChave` param (4h) -- if it works, reduces volume 10-20x. Otherwise, surface truncation warning more prominently. |
| **FE-005 error swallowing cascades with DB-009** | Backend (pagination endpoint deserializes 85K items), Frontend (catch {} hides OOM/timeout errors) | **Alta** | Fix FE-005 first (2h), then DB-009 (6h). Order matters -- fixing FE-005 alone will make DB-009 failures visible to users. |
| **Supabase migration affects 7+ items** | Database (DB-001/002/003/008/010/012), Backend (SYS-001), Auth (SYS-002) | **Alta** | Single migration story resolving all 7 items (24-32h). Must be planned as atomic unit. |
| **ETA inaccuracy erodes user trust during long searches** | Frontend (LoadingProgress), UX (user perceives system frozen at 60%) | **Media** | Dynamic ETA based on item count (2h). Progress interpolation during filtering (2h). |

---

## Dependencias Validadas

### Resolution Order Analysis

The data-engineer's proposed sprint order is sound. Here is the validated dependency graph:

```
Sprint 1 (Critical -- before production):
  1. DB-002 + SYS-001 (Supabase migration)
     |- Blocks: DB-001 (user isolation needs user_id column)
     |- Blocks: DB-003 (migration system only useful with persistent DB)
     |- Resolves simultaneously: DB-008, DB-010, DB-012
     |- Requires: SYS-002 (user identity model) should be designed concurrently

  2. SYS-003 (PyJWT) + DB-005 + DB-014 (timing attack)
     |- Independent of Supabase migration
     |- Can run in parallel with item 1

  3. Frontend timeout alignment
     |- Independent, can run in parallel
     |- Should coordinate with FE-016 (large volume warning) for consistent UX
```

```
Sprint 2 (High impact):
  4. FE-005 (error swallowing) -- MUST come before DB-009
     |- Reason: fixing DB-009 changes pagination behavior; without proper error
        handling (FE-005), any regression in pagination would be silently swallowed

  5. DB-009 (Redis LIST for items)
     |- Depends on: FE-005 being fixed (error visibility)
     |- Should coordinate with: DB-015 (dual-write elimination)

  6. FE-015 (term highlight) + FE-016 (volume warning)
     |- FE-015 requires backend change: pass matched_keywords in items response
     |- FE-016 is frontend-only, can run independently

  7. Exclusions for custom terms (main.py line 543)
     |- Independent, but should be validated with FP benchmark tests (FP1/FP2)
```

```
Sprint 3 (Quality):
  8. Stemming RSLP (10h)
     |- Should be validated against golden test suite (FP10) before merge
     |- Risk: new false positives from over-stemming

  9. FE-001 (hardcoded badge colors) + FE-007 (ink-muted contrast)
     |- Independent, quick wins

  10. PNCP palavraChave test (4h)
     |- Should be done ASAP despite being in Sprint 3 -- highest potential ROI
     |- If successful, fundamentally changes the architecture (server-side filtering)
     |- Recommend moving to Sprint 1 or Sprint 2 as an investigation spike
```

### Hidden Blockers Identified

1. **FE-015 (term highlight) is blocked by a backend API change.** The current `/api/buscar/items` endpoint returns items without matched keywords or scores. To highlight terms in the frontend, either: (a) the backend must include `matched_keywords: string[]` in each item's response, or (b) the frontend must re-run normalization + regex matching client-side (wasteful and duplicative). Recommendation: backend change first (1h), then FE-015 (4h). Total: 5h, not 4h.

2. **Supabase migration (SYS-001 / DB-002) is blocked by design decisions.** The data-engineer recommends supabase-py for CRUD and Supabase CLI for migrations, but the architect's SYS-002 (user identity model) needs to be designed first to define the schema. These two items must be planned together as a design + implementation pair.

3. **PNCP `palavraChave` test should be prioritized.** Currently placed in Sprint 3 backlog, but if this parameter works, it would: (a) reduce volume 10-20x, (b) eliminate most truncation-based false negatives, (c) reduce memory pressure, (d) reduce search time, (e) make large volume scenarios viable. This single test could obsolete or significantly reduce the urgency of DB-009, DB-015, and the timeout alignment work. **Recommend elevating to a Sprint 1 investigation spike (2h).**

---

## Duplicatas Encontradas

| Items | Overlap | Resolution |
|-------|---------|-----------|
| **SYS-001** (SQLite ephemeral) and **DB-002** (storage ephemeral Railway/Vercel) | Describe the same root problem from different perspectives (system architecture vs database) | Resolve as single migration story. Count as 1 item for planning. Estimate: use DB-002's 16h (migration work), not SYS-001's 16h (same). |
| **DB-005** (timing attack middleware) and **DB-014** (timing attack /auth/token) | Same vulnerability in two code locations | Fix together in single PR. DB-014 adds 0.5h to DB-005's 0.5h = 1h total. Already recommended by data-engineer. |
| **SYS-013** (in-memory JobStore base class) and **DB-015** (dual-write without invalidation) | Related but distinct. SYS-013 is about architecture (inheritance pattern). DB-015 is about memory waste (items stored twice). | Can be resolved together (remove in-memory fallback when Redis available). Use DB-015's 3h estimate. SYS-013's broader refactoring (8h) is separate. |
| DRAFT "Recommendation 1 for large volume" (frontend timeout alignment, 4h) and **UX review item 3** (frontend timeout, 4h) and **DB review recommendation 1** (3h) | Same fix proposed independently by all three reviewers | Confirms importance. Use 3h estimate (data-engineer's, most specific implementation plan with `X-Expected-Duration` header). |
| DRAFT "Recommendation 2 for large volume" (proactive warning, 4h) and **FE-016** (3h) | Same concept: warn user about large volume searches | Use FE-016 (3h, more specific design: banner with tokens and threshold triggers). |

**Effective item count after dedup:** 60 unique items, but 3 pairs should be resolved together, reducing to ~57 planning units.

---

## Testes Requeridos Pos-Resolucao

### Critical Path Tests (must exist before production)

| ID | Test | Validates | Type | Effort |
|----|------|-----------|------|--------|
| CP1 | Frontend timeout >= backend timeout for all valid input combinations | Timeout race condition | Property-based / Unit | 2h |
| CP2 | Pagination error state renders retry button (FE-005 fix validation) | Error handling | Component | 1h |
| CP3 | Pagination fetch with AbortController cancels stale requests (FE-019) | Race condition | Component | 1h |
| CP4 | `hmac.compare_digest` used in both auth paths (DB-005 + DB-014) | Security | Unit | 0.5h |
| CP5 | Supabase connection and basic CRUD (post-migration) | Data persistence | Integration | 2h |
| CP6 | Search with custom terms: exclusions applied when sector selected | FP reduction | Integration | 1h |

### Emphasis Area Tests

| ID | Test | Validates | Type | Effort |
|----|------|-----------|------|--------|
| EA1 | `normalize_text()` with all Portuguese diacritics + NFC/NFD variants | Accents | Unit | 1h |
| EA2 | Golden test suite: 50 relevant + 50 irrelevant items, precision/recall measurement | FP/FN baseline | Benchmark | 4h |
| EA3 | PNCP `palavraChave` API test with real endpoint | Search volume reduction | Manual | 2h |
| EA4 | 27 UFs mock search: completes within frontend timeout | Large volume | Integration | 2h |
| EA5 | Memory tracking during 85K item processing | Large volume | Performance | 2h |
| EA6 | Term highlight renders correctly with accented terms | Accents + UX | Component | 1h |
| EA7 | Large volume warning banner triggers at >10 UFs and >30 days | Large volume UX | Component | 1h |

### Regression Tests

| ID | Test | Prevents | Type | Effort |
|----|------|----------|------|--------|
| RT1 | No keyword pair in sectors.py has different `normalize_text()` outputs | Accent variant re-introduction | CI Script | 1h |
| RT2 | axe-core accessibility check in CI (all themes) | WCAG regression | E2E | 2h |
| RT3 | Contrast ratio validation for `--ink-muted` across all themes | FE-007 regression | Unit | 1h |
| RT4 | SearchSummary badges use semantic tokens, not hardcoded colors | FE-001 regression | Component | 0.5h |
| RT5 | `catch {}` blocks in frontend have error handling (no empty catch) | FE-005 regression | Lint rule | 0.5h |

**Total test effort: ~25h**

---

## Parecer Final

### Strengths of the Assessment

1. **Exceptional depth on emphasis areas.** The accent handling analysis traces the full stack from input to display. The FP/FN analysis includes concrete examples with code references. The large volume analysis includes three independent scenario calculations that converge.

2. **Multi-perspective validation.** Having the architect, data-engineer, and UX specialist review the same codebase independently provides high confidence. All three reviewers reached consistent conclusions on the critical issues (timeout race condition, exclusion bypass, memory pressure).

3. **Actionable recommendations with estimates.** Each debt item has effort estimates, priority, and specific implementation guidance. The data-engineer's revised estimates (stemming 10h not 8h, DB-009 6h not 4h) reflect deeper understanding of implementation complexity.

4. **Honest about uncertainties.** The PNCP `palavraChave` parameter is flagged as needing manual verification rather than assumed. The data-engineer explicitly states "no production metrics available" for Redis memory rather than guessing.

### Weaknesses

1. **Item count inconsistency.** The executive summary still says 51 items, but the true count is 60 after specialist reviews. This must be corrected before the document is used for planning.

2. **Missing FE-020.** The UXD-001 multi-word term issue was explicitly flagged by the UX reviewer but not assigned an FE-* ID. This creates a tracking gap.

3. **PNCP `palavraChave` test buried in backlog.** This is potentially the single highest-ROI action (2h to test, could reduce volume 10-20x and obsolete several other items). It should be Sprint 1.

4. **No quantitative FP/FN baseline.** The assessment describes FP/FN sources qualitatively but does not establish a measurable baseline. Without before/after measurements, it will be impossible to validate that search quality changes (stemming, exclusions, scoring) actually improved results.

### Final Verdict

**APPROVED WITH CONDITIONS.** The assessment is comprehensive and ready for sprint planning. The three conditions listed at the top (consolidate count to 60, incorporate UX severity adjustments, add FE-020) are documentation tasks that can be done during the consolidation step. No additional investigation or analysis is needed before story creation can begin.

**Priority recommendation for story creation order:**

1. **Investigation spike:** PNCP `palavraChave` parameter test (2h) -- do this first, results may change priorities
2. **Story: Security & Persistence** (SYS-001/002/003, DB-001/002/003/005/014) -- foundation for everything else
3. **Story: Search Quality** (exclusion fix, FE-005, FE-015, FP/FN golden test suite)
4. **Story: Large Volume Resilience** (timeout alignment, FE-016/017, DB-009/015)
5. **Story: UX Polish** (FE-001/007/018, theme fixes, accessibility)

---

**Review Status: COMPLETE**
**Reviewer:** @qa (Quartz)
**Signed:** 2026-03-09
