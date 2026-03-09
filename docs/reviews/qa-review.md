# QA Review - Technical Debt Assessment

## Reviewer: @qa (Quinn)
## Data: 2026-03-09

## Gate Status: APPROVED WITH CONDITIONS

## Assessment Completeness Score: 8/10

## Executive Summary

The technical debt DRAFT is a well-structured, thorough consolidation of the Brownfield Discovery Phases 1 and 3. It covers 52 debts across system, frontend/UX, and cross-cutting categories with a clear prioritization matrix and dependency analysis. The assessment demonstrates strong technical rigor and the severity ratings are largely accurate.

However, there are notable gaps: (1) the assessment does not address operational/infrastructure debts beyond the Vercel timeout issue, (2) secret management and environment variable handling are underexamined, (3) the dependency chain analysis is incomplete with some missing edges, and (4) the backend test coverage is not quantified while the frontend coverage is well-documented. The assessment is fit for planning with the conditions outlined below.

---

## Gaps Identificados

| # | Gap | Area | Impacto | Recomendacao |
|---|-----|------|---------|--------------|
| G-01 | **Backend test coverage not quantified.** The DRAFT quotes 33 backend test files but never states a coverage percentage. `pyproject.toml` sets `fail_under = 70.0` but actual measured coverage is not reported. | Backend / Testing | Cannot validate if backend coverage target is met; planning assumptions may be wrong | Run `pytest --cov` and document actual coverage in the assessment |
| G-02 | **No assessment of secret/credential management.** `OPENAI_API_KEY`, `API_KEY`, `BACKEND_API_KEY`, Redis URL, Sentry DSN -- all managed via environment variables with no rotation policy, no vault, no encryption at rest. | Security / Infra | Credential leak risk; no audit trail for secret access | Add a debt item for secrets management (at least Medium severity) |
| G-03 | **No assessment of logging/PII exposure.** Structured logging with correlation IDs is mentioned as a strength, but no analysis of whether user search terms, IP addresses, or other PII are logged. | Security / Compliance | LGPD compliance risk (Brazilian data protection law) | Audit log output for PII leakage; add debt if found |
| G-04 | **No assessment of dependency vulnerabilities.** No mention of `pip audit`, `npm audit`, Dependabot, or Snyk. Third-party supply chain risk unaddressed. | Security | Known CVEs in dependencies could be exploitable | Add debt item for dependency scanning in CI |
| G-05 | **No assessment of error information leakage.** Backend error responses may expose stack traces, internal paths, or dependency versions in production. | Security | Information disclosure to attackers | Audit error responses in production mode |
| G-06 | **Infrastructure debt not covered.** Railway and Vercel configuration drift, lack of IaC (Infrastructure as Code), no staging environment mentioned, no blue-green or canary deployment strategy. | Infra / DevOps | Deployment risk, no rollback strategy documented | Add infra debt section or explicitly scope it out |
| G-07 | **No assessment of data validation depth.** Input validation exists (termos_busca max length) but no analysis of injection risks in UF codes, date ranges, or sector IDs passed to external APIs. | Security | Potential SSRF or injection via crafted parameters forwarded to PNCP/Transparencia | Audit input validation for all API parameters |
| G-08 | **Backup/recovery not addressed.** Redis is ephemeral by design, but there is no mention of what happens when Redis is completely unavailable (not just slow). | Resilience | Complete service failure if Redis goes down without graceful degradation | Assess Redis failure modes |
| G-09 | **OpenAI API cost control not assessed.** No mention of token usage limits, cost caps, or monitoring for the LLM calls. A runaway loop could generate significant costs. | Operational | Unexpected cloud costs | Add operational debt item |
| G-10 | **Frontend bundle size not baselined.** No Lighthouse CI, no bundle analysis (webpack-bundle-analyzer), no performance budget. | Performance | Regressions undetectable without baseline | Establish bundle size budget |

---

## Riscos Cruzados

| Risco | Areas Afetadas | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------------|---------|-----------|
| Resolving TD-C02 (auth) without TD-H04 (database) creates a half-solution -- auth tokens need persistence | Backend + Infra | Alta | Alto | Plan these together; consider JWT stateless auth as interim or add database first |
| Resolving TD-C01 (Excel streaming) may break existing BFF download route (TD-H06) simultaneously | Backend + Frontend | Media | Alto | Implement with feature flag; test download flow end-to-end before cutover |
| Removing dead code from 3 disabled sources (TD-C03) risks accidentally breaking the orchestrator's source registry pattern | Backend | Media | Medio | Write orchestrator integration tests before removal; verify source discovery mechanism |
| Fixing UXD-001 (multi-word terms) changes the search API contract -- frontend tokenization change may require backend `termos_busca` parsing adjustment | Frontend + Backend | Media | Medio | Verify backend handles quoted terms or comma-separated terms correctly |
| Adding security headers (CSP) may break inline theme script (TD-M10/XD-SEC-03) | Frontend | Alta | Medio | Must add `nonce` or `sha256` hash to CSP for inline script; resolve TD-M10 first or simultaneously |
| Rate limiting (already implemented via slowapi) is per-IP, but behind Railway proxy all requests may share the same IP | Backend + Infra | Media | Alto | Verify `X-Forwarded-For` handling in slowapi configuration |
| Switching from synchronous to async OpenAI client (TD-H03) changes error handling patterns | Backend | Baixa | Medio | Comprehensive LLM test coverage already exists; verify fallback path still works |

---

## Validacao de Severidades

Items where QA disagrees with the DRAFT severity ratings:

| ID | Severidade DRAFT | Severidade QA | Justificativa |
|----|-----------------|---------------|---------------|
| TD-H05 | Alta (listed in 1.2) but P4 in matrix | **Deveria ser Media** | The DRAFT correctly identifies `allow_headers=["*"]` but inconsistently rates it -- Alta in the table (Section 1.2) but "Baixo impacto" in the description and P4 in the priority matrix. The actual codebase confirms `allow_origins` is properly whitelisted (not `*`), so only `allow_headers` is permissive. This is genuinely low-risk. Severity should be consistently Media with P3-P4 priority. |
| TD-M04 | Media | **Alta** | No timeout on OpenAI API calls is more dangerous than rated. A single hanging LLM call blocks a thread pool thread indefinitely, and since `filter_batch` shares the same default executor (TD-L06), this creates a cascading failure path. Under concurrent load, all threads could be blocked by slow LLM responses, causing the entire application to hang. Should be P2, not P4. |
| TD-M09 | Media | **Baixa** | MD5 for dedup keys is used on non-security-critical data (bid deduplication). The DRAFT itself acknowledges "risco teorico de colisao" is negligible. This is a code hygiene issue, not a Medium severity debt. |
| XD-PERF-03 | Baixa | **Media** | Fixed 2s polling for searches that can run 2-10 minutes generates 60-300 unnecessary requests per search. With concurrent users, this creates meaningful backend load. Exponential backoff is a simple fix with significant operational benefit. Should be P3, not P4. |
| TD-C03 | Critica | **Alta** | Three disabled data sources represent dead code and reduced coverage, but since the system is functional with 2 sources and this is a POC, "Critical" overstates the urgency. The dead code is inert (disabled, not actively breaking). Downgrade to Alta, keep at P1 for cleanup. |

---

## Dependencias Validadas

### Chain Analysis

The DRAFT's dependency graph (Section 8) is largely correct. QA validation and additions:

**Chain 1: Authentication -> Persistence (CONFIRMED)**
```
TD-C02 (auth) --> TD-H04 (database)
```
- Confirmed: Proper user auth requires persistent user store.
- **HOWEVER:** Stateless JWT auth could unblock TD-C02 without TD-H04. The dependency is conditional, not absolute. The DRAFT should note this alternative.

**Chain 2: Memory/Streaming (CONFIRMED with addition)**
```
TD-C01 (Excel in memory) --> TD-M02 (no pagination) --> TD-H06 (Vercel timeout)
```
- Confirmed: These three are tightly coupled. Streaming + pagination resolves all three.
- **ADDITION:** This chain should also include XD-PERF-01 (3-copy buffered download), which is the cross-cutting manifestation of the same problem.

**Chain 3: Security Headers (CONFIRMED with BLOCKER)**
```
XD-SEC-01 --> TD-M07 (CSP) + TD-M08 (HSTS)
```
- Confirmed.
- **BLOCKER IDENTIFIED:** TD-M10 (dangerouslySetInnerHTML for theme) MUST be resolved before or simultaneously with TD-M07 (CSP). Adding CSP with `script-src` restrictions will break the inline theme script. This is not captured in the DRAFT's dependency graph.

**Chain 4: Job Durability (CONFIRMED)**
```
TD-H02 (asyncio tasks) --> TD-H01 (in-memory store)
```
- Confirmed: Moving to a proper task queue (Celery/RQ) would eliminate the need for the dual-write in-memory + Redis store.

**Chain 5: Theme Refactoring (CONFIRMED)**
```
UXD-010 (ThemeProvider imperative) --> UXD-011 (FOUC script duplication)
```
- Confirmed.

**MISSING Dependency: LLM + Thread Pool**
```
TD-M04 (no LLM timeout) --> TD-L06 (shared ThreadPoolExecutor) --> TD-H03 (sync OpenAI client)
```
- These three are interconnected: the lack of timeout on a synchronous OpenAI call running in a shared thread pool creates a cascading failure risk. Resolving TD-H03 (async client) resolves all three.

**MISSING Dependency: Contract Testing**
```
XD-API-02 (no contract tests) --> TD-L02/XD-API-03 (unstructured errors)
```
- Contract tests cannot be properly written until error codes are structured. Otherwise the contract would codify free-text error parsing.

### Is the proposed resolution order correct?

**Largely yes**, with these adjustments:
1. TD-M04 (LLM timeout) should move from P4 to P2 -- it is a production reliability risk.
2. TD-M10 must be resolved before or with TD-M07 (CSP header) -- blocking dependency.
3. XD-PERF-03 (polling backoff) should move from P4 to P3 -- easy win, reduces backend load.
4. TD-C02 (auth) does not necessarily require TD-H04 (database) if JWT is used.

### Circular Dependencies

No circular dependencies detected. The graph is a DAG.

---

## Testes Requeridos

### Per-Debt Test Requirements

| Debt ID | Testes Necessarios | Tipo | Prioridade |
|---------|--------------------|------|------------|
| TD-C02 | Auth middleware unit tests (valid/invalid/missing key, exempt routes), integration test for full auth flow, test API_KEY unset behavior | Unit + Integration | P0 |
| TD-C01 | Memory usage test under concurrent jobs (measure RSS), streaming download test, test with large result sets (500+ bids) | Performance + Integration | P1 |
| TD-H02 | Test job survival across SIGTERM, test job recovery after process restart, test concurrent job limits | Integration + Resilience | P1 |
| TD-H01 | Test Redis-only mode (no in-memory), test Redis unavailable fallback, test data consistency after restart | Integration | P1 |
| TD-C03 | Orchestrator test with reduced source list, verify no import errors after dead code removal, source registry integrity test | Unit + Integration | P1 |
| UXD-001 | E2E test for multi-word search term submission, test quote/delimiter parsing, test edge cases (empty quotes, nested quotes) | E2E + Unit | P1 |
| TD-H03 | Async OpenAI client test, test timeout behavior, test fallback path with async client, load test with concurrent LLM calls | Unit + Performance | P2 |
| TD-H06 | Test download with file sizes >5MB, test streaming response through BFF, test timeout boundary (9s, 10s, 11s) | Integration + E2E | P2 |
| TD-M02 | Pagination API contract test, test page boundaries, test with 0 results / 1 page / many pages | Unit + Contract | P2 |
| XD-SEC-01 | Security header presence tests (CSP, HSTS, Referrer-Policy), test CSP does not break inline scripts, Lighthouse security audit | Integration + E2E | P2 |
| XD-API-02 | Pydantic schema export, TypeScript type generation, schema diff in CI | Contract | P2 |
| TD-M04 | Test LLM call with artificial 30s delay, verify timeout triggers fallback, verify thread pool not exhausted | Unit + Resilience | P2 |

### General Test Improvements

1. **Backend coverage baseline needed.** Run `pytest --cov` and record the actual percentage. The `pyproject.toml` threshold of 70% must be validated.

2. **Frontend E2E mock server.** The 4 E2E tests in `frontend/__tests__/e2e/` require a live backend, making them unusable in CI. Implement MSW (Mock Service Worker) or a lightweight Express mock server for CI-friendly E2E runs. This is the single most impactful testing improvement.

3. **Contract tests between frontend TypeScript types and backend Pydantic schemas.** Generate a shared JSON Schema from Pydantic models and validate TypeScript interfaces against it in CI.

4. **Missing frontend unit tests for:**
   - ThemeProvider (theme switching, localStorage persistence, CSS property application)
   - RegionSelector (region toggle logic, partial selection state)
   - AnalyticsProvider (Mixpanel initialization, conditional loading)
   - API route for `setores` (not found in test files -- `buscar-result.test.ts` exists but no `setores.test.ts`)

5. **Backend smoke test suite.** Create a minimal post-deploy verification: `GET /health`, `GET /setores`, `POST /buscar` with a small valid request. Automate as a Railway post-deploy hook or GitHub Actions workflow.

6. **Security regression tests.** The existing `test_security.py` covers CORS, auth, rate limiting, debug endpoints, and input validation -- this is good. Add tests for: response body does not contain stack traces in production mode, security headers are present.

---

## Metricas de Qualidade Propostas

| Metrica | Valor Atual | Meta | Prazo |
|---------|------------|------|-------|
| Frontend statement coverage | ~68% | 75% | Next sprint |
| Frontend branch coverage | ~53% | 60% | Next sprint |
| Backend statement coverage | Unknown (threshold: 70%) | 75% | Measure immediately, improve next sprint |
| E2E test scenarios | 4 (require live backend) | 8 (with mock server in CI) | Next milestone |
| Security headers present | 3/6 (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection) | 6/6 (add CSP, HSTS, Referrer-Policy) | Next sprint |
| Lighthouse Performance score | Not baselined | Baseline + no regression | Next milestone |
| Bundle size (frontend) | Not baselined | Baseline + budget | Next milestone |
| Mean time to detect deployment failure | No smoke tests | < 2 minutes via automated smoke test | Next sprint |
| Dependency vulnerability count | Not scanned | 0 critical, 0 high | Ongoing |
| OpenAI API error rate | Not monitored | < 5% with fallback activation | Next milestone |

---

## Riscos de Regressao

What could break during debt resolution, ordered by risk:

1. **Resolving TD-C01 (Excel streaming):** The entire download pipeline (backend generation -> BFF proxy -> browser download) is tightly coupled. Switching to streaming changes the response contract. Both `backend/main.py` and `frontend/app/api/download/route.ts` must change simultaneously. **Risk: broken downloads in production if only one side is updated.**

2. **Resolving TD-C02 (authentication):** Adding per-user auth will break every frontend API route that currently injects a single shared `BACKEND_API_KEY`. The BFF layer needs to forward user tokens instead. **Risk: complete service outage if auth middleware is deployed without frontend update.**

3. **Resolving TD-C03 (removing dead sources):** The orchestrator uses a source registry pattern. Removing source classes could affect the registry, import chain, or configuration. **Risk: import errors on startup if a removed source is still referenced in config.**

4. **Adding CSP header (TD-M07/XD-SEC-01):** The inline `<script>` for theme FOUC prevention in `layout.tsx` will be blocked by a restrictive CSP. **Risk: flash of unstyled content (broken theme) on every page load.**

5. **Resolving TD-H02 (task queue):** Moving from `asyncio.create_task` to Celery/RQ introduces a new infrastructure dependency (message broker). **Risk: new failure mode if broker goes down; increased deployment complexity.**

6. **Resolving TD-M02 (pagination):** Frontend currently renders all results. Adding pagination changes the data contract and requires frontend UI changes (page controls, state management). **Risk: partial results displayed without clear pagination UX.**

7. **Resolving UXD-001 (multi-word terms):** Changing tokenization behavior may affect existing users who have adapted to the current behavior (separate tokens). Saved searches in localStorage may become invalid. **Risk: breaking existing saved searches.**

---

## Parecer Final

### Strengths of the Assessment

1. **Comprehensive coverage.** 52 debts across 3 categories (system, frontend/UX, cross-cutting) with consistent ID naming scheme.
2. **Well-structured cross-cutting analysis.** Section 4 correctly identifies debts that span backend and frontend, avoiding siloed thinking.
3. **Honest severity ratings.** The assessment does not inflate or deflate -- most ratings are accurate and well-justified.
4. **Actionable dependency graph.** Section 8 captures the most important dependency chains, enabling informed sprint planning.
5. **Quick wins section.** Section 9 identifies 13 items (~25% of debts) requiring only ~12-14 hours -- excellent for building momentum.
6. **Expert questions.** Section 7 demonstrates self-awareness of blind spots and invites specialist validation.
7. **Accurate source material.** Claims about the codebase (CORS config, SIGTERM handler, MD5 usage, sync OpenAI client, `create_task` for jobs) were all verified against the actual source code.

### Weaknesses

1. **Backend test coverage is a blind spot.** The assessment quotes file counts but not actual coverage percentages. The `pyproject.toml` sets a 70% threshold, but whether this is being met is unknown.
2. **Security analysis is surface-level.** CORS, auth, and headers are covered, but secret management, PII in logs, dependency vulnerabilities, error information leakage, and input validation depth are not assessed.
3. **Infrastructure/operational debts are absent.** No mention of IaC, staging environments, deployment strategy, monitoring/alerting gaps, or cost controls.
4. **Inconsistent severity for TD-H05.** Listed as Alta in the severity table but treated as Baixo in the priority matrix. This undermines trust in the ratings.
5. **Missing dependency edge.** TD-M10 (inline script) blocks TD-M07 (CSP) -- this is a critical planning dependency that is absent from the graph.
6. **TD-M04 underrated.** No LLM timeout combined with shared thread pool (TD-L06) and sync client (TD-H03) creates a cascading failure path that deserves Alta, not Media.
7. **No mention of LGPD compliance.** For a Brazilian government procurement tool, data protection law applicability should at least be acknowledged.

### Recommendations Before Proceeding to Planning

1. **REQUIRED:** Measure and document actual backend test coverage percentage. Run `pytest --cov` and add the result to the assessment.
2. **REQUIRED:** Fix TD-H05 severity inconsistency (choose one rating and apply consistently).
3. **REQUIRED:** Add the TD-M10 -> TD-M07 dependency to the graph (CSP requires inline script resolution).
4. **RECOMMENDED:** Upgrade TD-M04 from P4 to P2 and from Media to Alta (thread pool exhaustion risk).
5. **RECOMMENDED:** Add a "Security Gaps" subsection covering secret management, PII logging, dependency scanning, and error information leakage.
6. **RECOMMENDED:** Add infrastructure/operational debt items or explicitly declare them out of scope with justification.
7. **OPTIONAL:** Add XD-PERF-03 (polling backoff) to the Quick Wins section -- it is a low-effort, high-impact operational improvement.

### Verdict: APPROVED WITH CONDITIONS

The assessment is comprehensive enough to proceed to sprint planning, provided the three REQUIRED items are addressed:

1. Backend test coverage must be measured and documented.
2. TD-H05 severity inconsistency must be resolved.
3. TD-M10 -> TD-M07 dependency must be added to the graph.

The RECOMMENDED items should be addressed during sprint planning but do not block proceeding from the assessment phase.

---

### QA Answers to Questions Raised in Section 7

Responding to the questions directed at @qa in the DRAFT:

**1. Coverage target (75% statements):** Yes, 75% is a reasonable next-milestone target for the frontend. For the backend, first establish the baseline -- the 70% `fail_under` in `pyproject.toml` is the immediate gate. Focus coverage efforts on hooks (`useSearchJob`, `useSearchForm`) and API routes for maximum risk reduction per test written.

**2. Contract testing approach:** For a POC at this scale, **shared JSON Schema validation** is the pragmatic choice over Pact. Export Pydantic models as JSON Schema, generate or validate TypeScript interfaces against them in CI. Pact is overkill until there are multiple consumers or teams.

**3. E2E without live backend:** **MSW (Mock Service Worker)** is the recommended approach. It runs in the same process as the tests, requires no additional infrastructure, and supports request interception at the network level. Docker Compose adds complexity that is not justified for 4-8 E2E scenarios.

**4. Visual regression testing:** **Not yet.** For a POC with 5 themes, the cost of maintaining visual snapshots outweighs the benefit. Instead, run a one-time manual contrast audit (UXD-015) and add a Lighthouse CI check for accessibility scores. Revisit visual regression after the design system is extracted.

**5. Smoke tests scope:** Minimum viable: `GET /health` (backend alive), `GET /setores` (data layer working), `POST /buscar` with 1 UF + short date range (full pipeline). Skip download in smoke tests -- it is slow and tested by E2E. Implement as a 30-second GitHub Actions workflow triggered on deploy.

**6. Quality gates beyond coverage:** Enforce in CI: (a) `npm audit --audit-level=high` and `pip audit`, (b) TypeScript strict mode (already enabled), (c) ESLint with no warnings, (d) bundle size budget (set after baselining), (e) Lighthouse accessibility score >= 90.

**7. Untested component priority:** ThemeProvider > RegionSelector > AnalyticsProvider > carouselData. ThemeProvider is the highest risk -- it touches every visual element and has 5 code paths (themes). RegionSelector has user-facing logic (partial selection). AnalyticsProvider and carouselData are lower risk.

---

*Review generated: 2026-03-09*
*Reviewer: @qa (Quinn)*
*Source documents: technical-debt-DRAFT.md, system-architecture.md v3.0, frontend-spec.md v3.0*
*Codebase validation: backend/tests/ (31 test files), frontend/__tests__/ (22 unit + 4 E2E), backend/main.py, backend/llm.py, backend/sources/orchestrator.py, vercel.json*
