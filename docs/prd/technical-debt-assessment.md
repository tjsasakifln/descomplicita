# Technical Debt Assessment -- FINAL

**Project:** Descomplicita (formerly Descomplicita)
**Date:** 2026-03-07
**Version:** 1.0 (Validated)
**Reviewed by:** @architect (Atlas), @ux-design-expert (Pixel), @qa (Shield)
**Codebase Commit:** 9fbd54d0 (main branch)

---

## Executive Summary

**Total debts identified:** 57 (46 original + 7 UX-discovered + 4 QA-discovered, after de-duplication)

**Breakdown by severity:**

| Severity | Count | % |
|----------|-------|---|
| Critical | 5 | 9% |
| High | 13 | 23% |
| Medium | 22 | 39% |
| Low | 17 | 30% |
| **Total** | **57** | 100% |

**Estimated total effort range:** 206--388 hours

**Key findings:**

1. **Security is the most urgent concern.** Wildcard CORS (TD-001), no authentication (TD-003), root container execution (TD-002), exposed debug endpoints (TD-055), and no rate limiting (TD-006) combine to create an exploitable attack surface. An unauthenticated attacker from any origin can exhaust all 10 job slots and abuse government API access.

2. **Tests are currently broken.** Backend tests assert the old app title ("Descomplicita API") while the codebase now says "Descomplicita API". E2E tests reference `bg-green-600` but the UI uses `bg-brand-navy`. These must be fixed before any other work (Sprint 0).

3. **Frontend test coverage is ~49%, not 91.5%.** The 91.5% figure in the architecture document is factually incorrect. The canonical measurement from `jest.config.js` shows 49.45% statements and 39.56% branches.

4. **The frontend monolith** (`page.tsx` at 1,071 lines, 23 useState calls) is the single largest maintainability risk, blocking all future feature work and making testing impractical.

5. **Accessibility gaps are systemic.** 13 debts across keyboard navigation, contrast, ARIA semantics, focus management, and heading structure indicate WCAG 2.1 AA compliance was not a design requirement. Brazilian accessibility law (LBI -- Law 13.146/2015) applies to government-facing tools.

**Recommendation:** Proceed with Sprint 0 immediately (fix broken tests), then execute the 6-sprint plan over 10 weeks. Total investment: 206--388 hours. Security hardening and authentication must precede any public marketing.

---

## Methodology

| Phase | Activity | Owner |
|-------|----------|-------|
| Phase 1 | System architecture analysis (31 debts from backend) | @architect |
| Phase 3 | Frontend/UX audit (20 debts from frontend spec) | @ux-design-expert |
| Phase 4 | Consolidation and de-duplication (51 raw to 46 unique) | @architect |
| Phase 6 | UX validation (2 severity adjustments, 7 new debts, effort estimates) | @ux-design-expert |
| Phase 7 | QA review (broken tests found, coverage debunked, 10 gaps identified) | @qa |
| Phase 8 | Final consolidation (this document) | @architect |

**Note:** Database review phases were skipped -- this project has no database. The system uses in-memory job storage and ephemeral cache.

---

## Complete Debt Inventory

### Critical (Immediate Action Required)

| ID | Debt | Area | Hours | Sprint | Owner |
|----|------|------|-------|--------|-------|
| TD-001 | CORS allows all origins | Security | 1-2 | Sprint 1 | Backend |
| TD-002 | Backend Dockerfile runs as root | Security | 1-2 | Sprint 1 | Backend |
| TD-003 | No authentication or authorization | Security | 4-8 (Phase 1) | Sprint 1 | Backend |
| TD-004 | God component (page.tsx, 1,071 lines) | Code Quality | 28-40 | Sprint 2 | Frontend |
| TD-054 | Broken backend test assertions (Descomplicita title) | Code Quality | 1-2 | Sprint 0 | Backend |

**TD-001: CORS Allows All Origins**
- Location: `backend/main.py:76`
- `allow_origins=["*"]` permits any website to make requests. Combined with TD-003 (no auth), any third party can consume backend resources.
- Remediation: Restrict to `["https://descomplicita.vercel.app", "http://localhost:3000"]`. Add `CORS_ORIGINS` environment variable.
- Effort: 1-2 hours

**TD-002: Backend Dockerfile Runs as Root**
- Location: `backend/Dockerfile`
- No `USER` directive. All container processes run as root.
- Remediation: Add non-root user (`appuser`) and `USER appuser` directive.
- Effort: 1-2 hours

**TD-003: No Authentication or Authorization** (Elevated per QA review)
- Location: `backend/main.py` (all endpoints)
- All API endpoints are publicly accessible. Any client can submit searches, poll results, and exhaust the 10-job concurrency limit.
- Remediation: Phase 1 (Sprint 1): API key authentication (header-based, 4-8 hours). Phase 2 (backlog): JWT user accounts. Phase 3 (backlog): RBAC.
- Note: QA review correctly identified that placing full auth in the Backlog while deploying rate limiting (TD-006) is insufficient -- IP-based rate limiting is trivially bypassed via IP rotation. Phase 1 API key auth is now Sprint 1.
- Effort: 4-8 hours (Phase 1 only)

**TD-004: God Component (page.tsx)**
- Location: `frontend/app/page.tsx` (1,071 lines, 23 useState, 4 useRef)
- The entire application UI, business logic, form handling, polling, download, and save-search logic lives in a single component.
- Validated decomposition plan (per UX review):
  - `SearchHeader` (logo, dropdowns, theme toggle)
  - `SearchForm` (mode toggle, sector select, terms input)
  - `UfSelector` (includes RegionSelector as child)
  - `DateRangeSelector`
  - `SearchSummary` (executive summary, highlights)
  - `SearchActions` (download, save, stats)
  - `SaveSearchDialog` (with focus trap, resolving TD-008)
  - `useSearchJob` hook (polling, phase state, lifecycle)
  - `useSearchForm` hook (form state, validation, defaults)
  - Target: page.tsx < 150 lines, no component > 200 lines
- Effort: 28-40 hours (includes string extraction per UX recommendation)

**TD-054: Broken Backend Test Assertions** (NEW -- QA-discovered)
- Location: `tests/test_main.py:24,238`
- `test_main.py` asserts `app.title == "Descomplicita API"` but `main.py:59` now says `"Descomplicita API"`. At least 2 test functions are currently failing or masking CI failures.
- Also: `tests/test_pncp_client.py:75` asserts User-Agent contains "Descomplicita".
- Remediation: Update all test assertions to match current branding.
- Effort: 1-2 hours

---

### High Priority

| ID | Debt | Area | Hours | Sprint | Owner |
|----|------|------|-------|--------|-------|
| TD-005 | In-memory job store not scalable | Scalability | 16-24 | Sprint 4 | Backend |
| TD-006 | No per-IP/user rate limiting | Security | 4-8 | Sprint 1 | Backend |
| TD-007 | Excel base64 in JSON response | Performance | 8-16 | Sprint 4 | Backend |
| TD-008 | Modal missing focus trap and dialog role | Accessibility | 4-6 | Sprint 3 | Frontend |
| TD-009 | Missing Escape key on dropdowns | Accessibility | 2-3 | Sprint 1 | Frontend |
| TD-010 | Insufficient color contrast (ink-muted) | Accessibility | 4-6 | Sprint 1 | Frontend |
| TD-011 | PNCP client uses blocking requests lib | Performance | 16-24 | Sprint 4 | Backend |
| TD-012 | Dev dependencies in production image | Performance | 2-4 | Sprint 1 | Backend |
| TD-013 | Global mutable singletons | Maintainability | 8-12 | Sprint 4 | Backend |
| TD-014 | Deprecated startup event pattern | Maintainability | 2-4 | Sprint 4 | Backend |
| TD-031 | Missing focus management after search | Accessibility | 3-5 | Sprint 3 | Frontend |
| TD-041 | E2E tests reference outdated class names | Code Quality | 2-3 | Sprint 0 | Frontend |
| TD-055 | Debug/diagnostic endpoints exposed in production | Security | 2-4 | Sprint 1 | Backend |

**TD-031: Missing Focus Management After Search** (Upgraded: Medium to High per UX review)
- On mobile, the search form takes the full viewport, so results are entirely invisible until the user manually scrolls. Screen reader users receive zero announcement of completion. This directly impacts conversion -- users may abandon thinking the search failed.
- Remediation: After results load, scroll to and focus the results section. Add `aria-live` announcement.
- Effort: 3-5 hours

**TD-041: E2E Tests Reference Outdated Class Names** (Elevated to Sprint 0 per QA review)
- `01-happy-path.spec.ts:64` asserts `bg-green-600` but UI uses `bg-brand-navy`. E2E tests are currently failing or never executing.
- This must be fixed before TD-004 decomposition (Sprint 2) to establish a regression baseline.
- Effort: 2-3 hours

**TD-055: Debug/Diagnostic Endpoints Exposed in Production** (NEW -- QA-discovered)
- Location: `backend/main.py` -- `/cache/stats`, `/cache/clear`, `/debug/pncp-test`
- These endpoints are accessible without authentication and can disrupt service (cache clear) or leak internal state.
- Remediation: Gate behind environment-based feature flag or auth middleware. Disable in production.
- Effort: 2-4 hours

---

### Medium Priority

| ID | Debt | Area | Hours | Sprint | Owner |
|----|------|------|-------|--------|-------|
| TD-015 | `datetime.utcnow()` deprecated | Code Quality | 1-2 | Sprint 5 | Backend |
| TD-016 | Branding inconsistency (Descomplicita remnants) | Maintainability | 4-8 | Sprint 5 | Both |
| TD-017 | No request/correlation ID logging | Maintainability | 4-8 | Sprint 5 | Backend |
| TD-018 | Hardcoded PNCP base URL | Maintainability | 1-2 | Sprint 5 | Backend |
| TD-019 | No API versioning | Maintainability | 4-8 | Backlog | Backend |
| TD-020 | Filter diagnostic code in production | Code Quality | 1-2 | Sprint 5 | Backend |
| TD-021 | Duplicate UFS constant definition | Code Quality | 1-2 | Sprint 2 | Frontend |
| TD-022 | No OpenAPI schema for result endpoint | Maintainability | 2-4 | Sprint 5 | Backend |
| TD-023 | Excel download uses filesystem tmpdir | Scalability | 8-16 | Sprint 4 | Backend |
| TD-024 | `asyncio.get_event_loop()` deprecated | Code Quality | 1-2 | Sprint 5 | Backend |
| TD-025 | No graceful shutdown | Maintainability | 4-8 | Sprint 5 | Backend |
| TD-026 | Cache not shared across restarts | Performance | 8-16 | Sprint 4 | Backend |
| TD-027 | No skip-to-content link | Accessibility | 1-2 | Sprint 1 | Frontend |
| TD-028 | External logo dependency (Wix CDN) | Performance | 2-3 | Sprint 2 | Frontend |
| TD-029 | Outdated favicon (Descomplicita "B") | Design | 1-2 | Sprint 3 | Frontend |
| TD-030 | Error boundary uses hardcoded colors | Design | 2-4 | Sprint 3 | Frontend |
| TD-044 | SourceBadges/carouselData hardcoded colors | Design | 3-5 | Sprint 3 | Frontend |
| TD-047 | Dropdown menus lack ARIA menu pattern | Accessibility | 2-3 | Sprint 3 | Frontend |
| TD-048 | `window.confirm()` for destructive action | UX | 2-3 | Sprint 3 | Frontend |
| TD-051 | UF grid buttons lack group label | Accessibility | 1-2 | Sprint 3 | Frontend |
| TD-056 | Unbounded `termos_busca` input length | Security | 1-2 | Sprint 1 | Backend |
| TD-057 | No Sentry/APM integration | Observability | 4-8 | Sprint 5 | Backend |

**TD-044: SourceBadges/carouselData Hardcoded Colors** (Upgraded: Low to Medium per UX review)
- `SourceBadges.tsx` uses `bg-green-100`, `bg-yellow-100`, `bg-red-100` with explicit `dark:` variants that do not account for the 5-theme system. Paperwhite and Sepia themes (light themes with different canvas colors) display visual inconsistencies.
- Remediation: Create semantic status tokens (`--status-success`, `--status-warning`, `--status-error`) that work across all 5 themes.
- Effort: 3-5 hours

**TD-056: Unbounded `termos_busca` Input Length** (NEW -- QA-discovered)
- Location: `backend/schemas.py` -- `BuscaRequest.termos_busca`
- While `re.escape()` mitigates regex injection, there is no `max_length` validation. A user could submit a megabyte-long string causing memory pressure.
- Remediation: Add `max_length=500` to the Pydantic field.
- Effort: 1-2 hours

**TD-057: No Sentry/APM Integration** (NEW -- QA-discovered)
- `.env.example` has a `SENTRY_DSN` placeholder but no Sentry SDK is installed in `requirements.txt` or `package.json`. Production errors go unobserved.
- Remediation: Install `sentry-sdk[fastapi]`, configure with DSN, add to frontend via `@sentry/nextjs`.
- Effort: 4-8 hours

---

### Low Priority

| ID | Debt | Area | Hours | Sprint | Owner |
|----|------|------|-------|--------|-------|
| TD-032 | No structured error codes | Maintainability | 4-8 | Backlog | Backend |
| TD-033 | f-string in logger calls | Code Quality | 2-4 | Sprint 5 | Backend |
| TD-034 | No pagination for sectors endpoint | Scalability | 1-2 | Backlog | Backend |
| TD-035 | Frontend emoji in source code | Code Quality | 1 | Sprint 5 | Frontend |
| TD-036 | No content-length validation for downloads | Security | 1-2 | Sprint 5 | Backend |
| TD-037 | Date range max removed | Performance | 1-2 | Sprint 5 | Backend |
| TD-038 | Module-level singleton in job_store.py | Code Quality | 1 | Sprint 5 | Backend |
| TD-039 | Deprecated performance API in AnalyticsProvider | Code Quality | 1 | Sprint 5 | Frontend |
| TD-040 | No loading state for sector list | UX | 1-2 | Backlog | Frontend |
| TD-042 | No code splitting for components | Performance | 4-6 | Sprint 3 | Frontend |
| TD-043 | No `<nav>` semantic element | Accessibility | 1 | Sprint 3 | Frontend |
| TD-045 | Unused public asset (logo-descomplicita.png) | Code Quality | 0.5 | Sprint 2 | Frontend |
| TD-046 | Missing aria-describedby for terms input | Accessibility | 1 | Sprint 3 | Frontend |
| TD-049 | EmptyState lacks ARIA live region | Accessibility | 1 | Sprint 3 | Frontend |
| TD-050 | SourceBadges lacks aria-expanded | Accessibility | 1-2 | Sprint 3 | Frontend |
| TD-052 | No heading hierarchy in main sections | Accessibility | 1-2 | Sprint 3 | Frontend |
| TD-053 | Hardcoded borderColor in ThemeToggle | Design | 0.5 | Sprint 3 | Frontend |

---

## Cross-Cutting Concerns

### Security Posture (TD-001 + TD-002 + TD-003 + TD-006 + TD-036 + TD-055 + TD-056)

The backend has **no authentication, no per-client rate limiting, accepts requests from any origin, and exposes debug endpoints**. The container runs as root. These debts compound: an unauthenticated attacker from any origin can exhaust all 10 job slots, trigger unlimited PNCP API calls (incurring rate-limit penalties with the government API), clear the cache via `/cache/clear`, and potentially exploit container-level vulnerabilities. These must be addressed as a group before any public launch.

### Broken Tests (TD-054 + TD-041)

At least 2 backend tests and 1 E2E test are currently failing due to the Descomplicita-to-Descomplicita rebrand. This may be masking CI failures and prevents establishing a regression baseline before the TD-004 decomposition. These are not future debt -- they are currently broken and must be Sprint 0.

### In-Memory Architecture Ceiling (TD-005 + TD-026 + TD-023)

The job store, PNCP cache, and Excel download files all rely on ephemeral storage. Data is lost on every deploy, horizontal scaling is impossible, and tmpdir-based downloads are incompatible with serverless. Redis (for jobs + cache) and object storage (for Excel files) resolve all three.

### Accessibility Compliance (13 items: TD-008, TD-009, TD-010, TD-027, TD-031, TD-043, TD-046, TD-047, TD-049, TD-050, TD-051, TD-052 + related a11y aspects of TD-004)

Thirteen accessibility debts indicate WCAG 2.1 AA compliance was not a design requirement. Issues range from structural (missing focus trap, no skip link, no heading hierarchy) to perceptual (contrast ratios) to semantic (missing ARIA roles and states). Brazilian accessibility law (LBI -- Law 13.146/2015) requires digital accessibility for government-facing tools.

### Frontend Test Coverage Reality

The 91.5% frontend coverage claim in the architecture document is **factually incorrect**. Actual coverage per `jest.config.js`: 49.45% statements, 39.56% branches. Components without any dedicated tests include RegionSelector, SavedSearchesDropdown, SourceBadges, AnalyticsProvider, ThemeProvider, and the `useSavedSearches` hook.

Realistic targets:
- After TD-004 decomposition: 65% statements, 50% branches
- After accessibility sprint: 70% statements, 55% branches
- Long-term: 80% statements, 65% branches

### Branding Migration Completeness (TD-016 + TD-029 + TD-028 + TD-045 + TD-054)

The Descomplicita-to-Descomplicita rebrand is incomplete across documentation, Docker configuration, favicon, logo hosting, `pyproject.toml`, and test assertions. Individually low-effort but collectively creates a fragmented identity and broken tests.

### Deprecated API Usage (TD-015 + TD-024 + TD-014 + TD-039)

Four items use deprecated Python/JS APIs. Note per QA review: backend test files also use these deprecated patterns and must be updated simultaneously. The `pyproject.toml` `DeprecationWarning` filter suppresses warnings, hiding these issues.

---

## Resolution Plan

### Sprint 0: Emergency Fixes (Week 1, Days 1-2)

**Objective:** Unblock CI, establish regression baseline.

| ID | Item | Hours | Owner |
|----|------|-------|-------|
| TD-054 | Fix broken backend test assertions (Descomplicita title, User-Agent) | 1-2 | Backend |
| TD-041 | Fix E2E test class name assertions (bg-green-600 to bg-brand-navy) | 2-3 | Frontend |

**Total: 3-5 hours**

Exit criteria: All backend unit tests pass. E2E happy-path test passes. CI is green.

---

### Sprint 1: Security Hardening + Quick Wins (Week 1-2)

**Objective:** Close the critical security gaps and harvest accessibility quick wins.

| ID | Item | Hours | Owner |
|----|------|-------|-------|
| TD-001 | CORS: restrict to whitelisted origins | 1-2 | Backend |
| TD-002 | Dockerfile: add non-root user | 1-2 | Backend |
| TD-003 | Auth Phase 1: API key authentication | 4-8 | Backend |
| TD-006 | Per-IP rate limiting (SlowAPI) | 4-8 | Backend |
| TD-012 | Split dev dependencies from production image | 2-4 | Backend |
| TD-055 | Gate debug endpoints behind auth/feature flag | 2-4 | Backend |
| TD-056 | Add max_length to termos_busca | 1-2 | Backend |
| TD-009 | Escape key handling on dropdowns | 2-3 | Frontend |
| TD-010 | Color contrast fix (ink-muted, ink-faint audit) | 4-6 | Frontend |
| TD-027 | Skip-to-content link | 1-2 | Frontend |

**Total: 22-41 hours**

Exit criteria: CORS restricted. API key required. Rate limiting active. Container non-root. Debug endpoints gated. Contrast passes WCAG AA. Keyboard users can dismiss dropdowns and skip navigation.

---

### Sprint 2: Frontend Architecture (Weeks 3-4)

**Objective:** Decompose the God component into maintainable modules.

| ID | Item | Hours | Owner |
|----|------|-------|-------|
| TD-004 | God component decomposition (hooks, components, orchestrator) | 28-40 | Frontend |
| TD-021 | Centralize UFS constant (natural during extraction) | 1-2 | Frontend |
| TD-028 | Self-host logo via Next.js Image (natural during SearchHeader extraction) | 2-3 | Frontend |
| TD-045 | Resolve unused public asset (consumed by TD-028) | 0 | Frontend |

**Total: 31-45 hours**

Exit criteria: page.tsx < 150 lines. No component > 200 lines. All existing tests pass. E2E regression suite green. Each extracted component has co-located unit test.

**Decomposition phases (per UX-validated plan):**
1. Extract hooks: `useSearchJob`, `useSearchForm` (4-6 hours)
2. Extract leaf components: `SaveSearchDialog`, `UfSelector`, `SearchHeader`, `DateRangeSelector` (8-12 hours)
3. Extract result components: `SearchSummary`, `SearchActions` (6-10 hours)
4. Wire and test: thin orchestrator, unit tests, E2E verification (8-12 hours)

---

### Sprint 3: Frontend Quality + Accessibility (Weeks 5-6)

**Objective:** Complete accessibility remediation, design system alignment.

| ID | Item | Hours | Owner |
|----|------|-------|-------|
| TD-008 | Modal focus trap, dialog role, Escape close | 4-6 | Frontend |
| TD-031 | Focus management after search (scroll, focus, aria-live) | 3-5 | Frontend |
| TD-029 | Update favicon to Descomplicita brand | 1-2 | Frontend |
| TD-030 | Error boundary: use design tokens with CSS fallback | 2-4 | Frontend |
| TD-042 | Code splitting (dynamic imports for LoadingProgress, carouselData) | 4-6 | Frontend |
| TD-043 | Add nav semantic element to header | 1 | Frontend |
| TD-044 | Semantic status tokens for SourceBadges/carouselData | 3-5 | Frontend |
| TD-046 | aria-describedby for terms input | 1 | Frontend |
| TD-047 | ARIA menu pattern on dropdowns | 2-3 | Frontend |
| TD-048 | Replace window.confirm with custom modal | 2-3 | Frontend |
| TD-049 | EmptyState aria-live region | 1 | Frontend |
| TD-050 | SourceBadges aria-expanded | 1-2 | Frontend |
| TD-051 | UF grid group label | 1-2 | Frontend |
| TD-052 | Heading hierarchy (h2/h3 structure) | 1-2 | Frontend |
| TD-053 | ThemeToggle hardcoded borderColor | 0.5 | Frontend |

**Total: 29-47 hours**

Exit criteria: Zero WCAG AA critical/serious violations (verified via axe-core in E2E). All modals have focus trap. Focus managed after search completion. Design tokens used consistently across all 5 themes.

---

### Sprint 4: Backend Architecture (Weeks 7-8)

**Objective:** Replace in-memory architecture, modernize HTTP layer.

| ID | Item | Hours | Owner |
|----|------|-------|-------|
| TD-005 | Redis-backed job store | 16-24 | Backend |
| TD-013 | FastAPI dependency injection refactor | 8-12 | Backend |
| TD-014 | Lifespan context manager migration | 2-4 | Backend |
| TD-026 | Redis-backed cache (pairs with TD-005) | 8-16 | Backend |
| TD-007 | Excel delivery via signed URLs or streaming | 8-16 | Backend |
| TD-023 | Remove tmpdir dependency (pairs with TD-007) | 0 | Backend |
| TD-011 | PNCP client httpx migration | 16-24 | Backend |

**Total: 58-96 hours**

Note: TD-013 and TD-014 should be combined in the same PR (tightly coupled). TD-005 and TD-026 share Redis infrastructure. TD-007 and TD-023 are two sides of the same file delivery refactor.

Exit criteria: Job state survives container restart. Cache shared across instances. Excel files delivered via signed URL or streaming. PNCP client fully async. DI pattern established.

---

### Sprint 5: Polish + Infrastructure (Weeks 9-10)

**Objective:** Clean up deprecated APIs, improve observability, complete branding.

| ID | Item | Hours | Owner |
|----|------|-------|-------|
| TD-015 | datetime.utcnow() migration (include test files) | 1-2 | Backend |
| TD-016 | Branding cleanup (docker-compose, README, pyproject.toml, backend modules) | 4-8 | Both |
| TD-017 | Request/correlation ID logging | 4-8 | Backend |
| TD-018 | Configurable PNCP base URL | 1-2 | Backend |
| TD-020 | Remove filter diagnostic code | 1-2 | Backend |
| TD-022 | OpenAPI schema for result endpoint | 2-4 | Backend |
| TD-024 | get_event_loop() migration (include test files) | 1-2 | Backend |
| TD-025 | Graceful shutdown (SIGTERM handler) | 4-8 | Backend |
| TD-033 | Logger lazy formatting | 2-4 | Backend |
| TD-035 | Remove hardcoded emoji from source | 1 | Frontend |
| TD-036 | Content-length validation for downloads | 1-2 | Backend |
| TD-037 | Re-introduce configurable date range max | 1-2 | Backend |
| TD-038 | Remove unused job_store singleton | 1 | Backend |
| TD-039 | Deprecated performance.timing migration | 1 | Frontend |
| TD-057 | Sentry/APM integration | 4-8 | Both |

**Total: 30-53 hours**

Exit criteria: Zero deprecated API warnings. Structured logging with correlation IDs. Sentry capturing production errors. All branding references updated.

---

### Backlog (Unscheduled)

| ID | Item | Hours | Notes |
|----|------|-------|-------|
| TD-003 Phase 2 | JWT user accounts | 12-32 | After Phase 1 API key is validated |
| TD-019 | API versioning | 4-8 | When breaking changes are planned |
| TD-032 | Structured error codes | 4-8 | When client ecosystem grows |
| TD-034 | Sectors endpoint pagination | 1-2 | Only 6 sectors currently |
| TD-040 | Sector list loading state | 1-2 | Falls back to hardcoded list |

---

## Dependency Map

```
SPRINT 0 (PREREQUISITE FOR ALL)
  TD-054 (Fix broken tests) ──> Unblocks CI
  TD-041 (Fix E2E assertions) ──> Unblocks regression baseline

SPRINT 1
  TD-001 (CORS) ──> Required before TD-003
  TD-003 Phase 1 (API key) ──> Enhances TD-006 (rate limiting with identity)
  TD-055 (debug endpoints) ──> Requires TD-003 or feature flag

SPRINT 2
  TD-004 (God Component)
    +-- UNBLOCKS --> TD-008 (Modal a11y -- extracted as SaveSearchDialog)
    +-- UNBLOCKS --> TD-031 (Focus management -- easier after extraction)
    +-- UNBLOCKS --> TD-042 (Code splitting -- requires separate components)
    +-- INCLUDES --> TD-021 (UFS dedup -- natural during extraction)
    +-- INCLUDES --> TD-028 (Logo self-host -- natural during SearchHeader)
    +-- RESOLVES --> TD-045 (Unused logo asset consumed by TD-028)

SPRINT 3
  TD-008 (Modal) ──> Requires TD-004 extraction
  TD-031 (Focus mgmt) ──> Requires TD-004 extraction

SPRINT 4
  TD-005 (Redis job store) ──> ENABLES TD-026 (shared cache via Redis)
  TD-005 + TD-026 ──> Require Redis in docker-compose + Railway
  TD-007 (Excel signed URLs) ──> PAIRS WITH TD-023 (tmpdir removal)
  TD-007 + TD-023 ──> Require object storage decision (S3/R2/Supabase)
  TD-013 (DI refactor) ──> ENHANCES TD-005 (cleaner with DI)
  TD-013 ──> PAIRS WITH TD-014 (lifespan aligns with DI)

SPRINT 5
  TD-015, TD-024 ──> Must include test file updates (per QA G-09)
  TD-016 (Branding) ──> INCLUDES TD-029 (favicon, if not done Sprint 3)
```

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Related Debts |
|------|-------------|--------|------------|---------------|
| CORS exploitation before Sprint 1 | High | High | Prioritize TD-001 as first fix | TD-001, TD-003 |
| Resource exhaustion (no auth) | High | High | API key auth in Sprint 1 | TD-003, TD-006 |
| Root container escape | Low | Critical | Sprint 1 Dockerfile fix | TD-002 |
| Debug endpoint abuse (cache clear) | Medium | Medium | Feature flag or auth gate | TD-055 |
| TD-004 decomposition regression | High | High | Sprint 0 E2E baseline; incremental extraction with test runs after each step | TD-004, TD-041 |
| Redis migration data loss | Medium | Medium | Dual-write (in-memory + Redis) during transition | TD-005, TD-026 |
| httpx migration response parity | Medium | Medium | Compare result counts old vs. new on same query | TD-011 |
| Coverage drop during decomposition | High | Low | Enforce per-component coverage, not global threshold | TD-004 |
| Unbounded date range query abuse | Low | Medium | Re-introduce configurable max (90 days) | TD-037 |
| Production errors go unnoticed | High | Medium | Sentry integration in Sprint 5 | TD-057 |

---

## Success Metrics

- [ ] All critical debts resolved (TD-001, TD-002, TD-003 Phase 1, TD-004, TD-054)
- [ ] Frontend test coverage >= 65% statements after Sprint 2, >= 80% long-term
- [ ] Backend test coverage maintained >= 70% (CI enforcement without `continue-on-error`)
- [ ] Zero WCAG AA critical/serious violations (axe-core gated in E2E)
- [ ] CORS restricted to whitelisted origins
- [ ] API key authentication on all endpoints
- [ ] No containers running as root
- [ ] Debug endpoints disabled in production
- [ ] All test assertions reference "Descomplicita" (not "Descomplicita")
- [ ] E2E happy-path test passes on current codebase
- [ ] Sentry capturing production errors (backend + frontend)
- [ ] Job state survives container restart (Redis-backed)

---

## Appendix A: Specialist Review Summary

### UX Specialist Review (@ux-design-expert)

**Status:** Complete (2026-03-07)

Key contributions:
1. **Severity adjustments:** TD-031 Medium to High (mobile conversion impact), TD-044 Low to Medium (visual breakage in 2 of 5 themes)
2. **Priority correction:** TD-010 moved from "Deprioritize" quadrant to Quick Wins (primary fix is a 2-line CSS change)
3. **7 new debts discovered:** TD-047 (ARIA menu roles), TD-048 (window.confirm), TD-049 (EmptyState aria-live), TD-050 (aria-expanded), TD-051 (UF grid group label), TD-052 (heading hierarchy), TD-053 (ThemeToggle hardcoded color)
4. **God component decomposition validated** with modifications: UfSelector includes RegionSelector, SearchResults split into SearchSummary + SearchActions, new SearchHeader component
5. **Color contrast fix validated:** `--ink-muted` to `#5a6a7a` (light, 4.86:1) and `#8a99a9` (dark, 5.2:1). `--ink-faint` restricted to decoration-only.
6. **i18n deferred** (single-language market), but string extraction recommended during decomposition
7. **Error boundary:** partial theme participation with CSS fallback recommended
8. **max-w-4xl confirmed intentional** for reading width and UF grid layout

### QA Review (@qa)

**Status:** Approved with Conditions (2026-03-07)

Key contributions:
1. **Coverage debunked:** 91.5% frontend claim is incorrect; actual is ~49.45% statements
2. **Broken tests discovered:** `test_main.py` title assertions fail against current codebase; E2E class name assertions outdated
3. **Sprint 0 requirement:** Fix broken tests before any other work
4. **TD-003 elevation:** API key auth must move from Backlog to Sprint 1
5. **10 gaps identified (G-01 through G-10):** broken tests, non-blocking CI coverage, missing Sentry, unbounded input, debug endpoints, unused axe-core, unused Postgres in CI, CORS comment branding, test deprecated APIs, health check validation
6. **Backend coverage qualified:** 99.2% plausible but quality is moderate (heavy mocking, no integration tests, `continue-on-error` in CI)
7. **Test requirements defined:** 33 hours of test work for Critical/High debt items
8. **Effort estimates validated:** +10-16 hours adjustment for Sprint 0 and test migration

QA Conditions addressed in this document:
- [x] Sprint 0 added for broken tests (Condition 1)
- [x] 91.5% coverage corrected to ~49% (Condition 2)
- [x] TD-003 Phase 1 elevated to Sprint 1 (Condition 3)
- [x] QA gaps incorporated as TD-054 through TD-057 + notes (Condition 4)
- [x] Test file updates noted as dependencies for TD-015 and TD-024 (Condition 5)

---

## Appendix B: Full Cross-Reference

### Original IDs to Final IDs

| Final ID | System ID | Frontend ID | Short Name | Severity Change |
|----------|-----------|-------------|------------|-----------------|
| TD-001 | TD-01 | -- | CORS wildcard | -- |
| TD-002 | TD-02 | -- | Root container | -- |
| TD-003 | TD-03 | -- | No auth | Sprint elevated |
| TD-004 | -- | TD-FE-001 | God component | -- |
| TD-005 | TD-04 | -- | In-memory job store | -- |
| TD-006 | TD-05 | -- | No rate limiting | -- |
| TD-007 | TD-06 | -- | Excel base64 | -- |
| TD-008 | -- | TD-FE-003 | Modal a11y | -- |
| TD-009 | -- | TD-FE-002 | Escape key dropdowns | -- |
| TD-010 | -- | TD-FE-004 | Color contrast | Priority: Deprioritize to Quick Wins |
| TD-011 | TD-11 | -- | Blocking requests lib | -- |
| TD-012 | TD-10 | -- | Dev deps in prod | -- |
| TD-013 | TD-07 | -- | Global singletons | -- |
| TD-014 | TD-08 | -- | Deprecated startup | -- |
| TD-015 | TD-09 | -- | datetime.utcnow | -- |
| TD-016 | TD-12+13+14 | TD-FE-007 | Branding remnants | -- |
| TD-017 | TD-15 | -- | No correlation ID | -- |
| TD-018 | TD-16 | -- | Hardcoded PNCP URL | -- |
| TD-019 | TD-17 | -- | No API versioning | -- |
| TD-020 | TD-18 | -- | Filter debug code | -- |
| TD-021 | TD-19 | TD-FE-009 | Duplicate UFS | -- |
| TD-022 | TD-20 | -- | No OpenAPI result | -- |
| TD-023 | TD-21 | -- | tmpdir Excel | -- |
| TD-024 | TD-22 | -- | get_event_loop | -- |
| TD-025 | TD-23 | -- | No graceful shutdown | -- |
| TD-026 | TD-24 | -- | Ephemeral cache | -- |
| TD-027 | -- | TD-FE-005 | Skip-to-content | -- |
| TD-028 | -- | TD-FE-006+018 | External logo | -- |
| TD-029 | -- | TD-FE-007 | Outdated favicon | -- |
| TD-030 | -- | TD-FE-008 | Error boundary colors | -- |
| TD-031 | -- | TD-FE-014 | Focus after search | Medium to High |
| TD-032 | TD-26 | -- | No error codes | -- |
| TD-033 | TD-27 | -- | f-string in logger | -- |
| TD-034 | TD-28 | -- | Sectors pagination | -- |
| TD-035 | TD-29 | -- | Emoji in source | -- |
| TD-036 | TD-30 | -- | Download size limit | -- |
| TD-037 | TD-31 | -- | No date range max | -- |
| TD-038 | TD-25 | -- | Unused singleton | -- |
| TD-039 | -- | TD-FE-011 | Deprecated perf API | -- |
| TD-040 | -- | TD-FE-012 | Sector loading state | -- |
| TD-041 | -- | TD-FE-013 | E2E outdated classes | Low to High (Sprint 0) |
| TD-042 | -- | TD-FE-015 | No code splitting | -- |
| TD-043 | -- | TD-FE-016 | No nav element | -- |
| TD-044 | -- | TD-FE-017 | Hardcoded colors | Low to Medium |
| TD-045 | -- | TD-FE-018 | Unused public asset | -- |
| TD-046 | -- | TD-FE-019 | aria-describedby | -- |
| TD-047 | -- | UX-NEW-1 | ARIA menu pattern | NEW (Medium) |
| TD-048 | -- | UX-NEW-2 | window.confirm | NEW (Medium) |
| TD-049 | -- | UX-NEW-3 | EmptyState aria-live | NEW (Low) |
| TD-050 | -- | UX-NEW-4 | SourceBadges aria-expanded | NEW (Low) |
| TD-051 | -- | UX-NEW-5 | UF grid group label | NEW (Medium) |
| TD-052 | -- | UX-NEW-6 | Heading hierarchy | NEW (Low) |
| TD-053 | -- | UX-NEW-7 | ThemeToggle borderColor | NEW (Low) |
| TD-054 | -- | QA-G-01 | Broken test assertions | NEW (Critical) |
| TD-055 | -- | QA-G-05 | Debug endpoints exposed | NEW (High) |
| TD-056 | -- | QA-G-04 | Unbounded input length | NEW (Medium) |
| TD-057 | -- | QA-G-03 | No Sentry/APM | NEW (Medium) |

### QA Gaps Not Assigned Separate IDs (Incorporated as Notes)

| QA Gap | Disposition |
|--------|------------|
| G-02: CI coverage continue-on-error | Noted in Success Metrics (remove continue-on-error) |
| G-06: Unused axe-core in E2E | Noted in Sprint 3 exit criteria (axe-core E2E gating) |
| G-07: Unused Postgres service in CI | Noted; remove when integration tests are implemented or skipped |
| G-08: CORS comment references bidiq domain | Included in TD-016 branding cleanup scope |
| G-09: Test files use deprecated APIs | Noted as dependency in TD-015 and TD-024 |
| G-10: Health check lacks dependency validation | Noted; recommend adding to TD-057 Sentry/observability scope |

---

## Appendix C: Effort Summary by Sprint

| Sprint | Items | Hours (Low) | Hours (High) | Weeks |
|--------|-------|-------------|--------------|-------|
| Sprint 0: Emergency Fixes | 2 | 3 | 5 | 0.5 |
| Sprint 1: Security + Quick Wins | 10 | 22 | 41 | 1-2 |
| Sprint 2: Frontend Architecture | 4 | 31 | 45 | 2 |
| Sprint 3: Frontend Quality | 15 | 29 | 47 | 2 |
| Sprint 4: Backend Architecture | 7 | 58 | 96 | 2 |
| Sprint 5: Polish + Infrastructure | 15 | 30 | 53 | 1-2 |
| Backlog | 5 | 22 | 52 | -- |
| **Scheduled Total** | **53** | **173** | **287** | **~10** |
| **Including Backlog** | **57** (excl. TD-003 Ph2) | **206** | **388** | -- |

**Notes on estimation:**
- Hours assume a single developer per task
- Backend and frontend sprints can be parallelized with separate developers
- Sprint 4 is the largest block (58-96 hours) and benefits most from parallel execution of Redis and httpx workstreams
- TD-003 has the widest total range (4-8 hours Phase 1 + 12-32 hours Phase 2) depending on auth scope
- QA-estimated test hours (33 hours for Critical/High items) are included in the per-item estimates

---

## Appendix D: Items Not Carried Forward

- **i18n infrastructure** (Frontend TD-FE-010): Not classified as debt. Product exclusively targets Brazilian Portuguese market. String extraction recommended during TD-004 decomposition for maintainability, not i18n.
- **Large-screen optimization:** Confirmed by UX specialist as intentional design. The 896px (max-w-4xl) content column is optimal for reading width and UF grid layout.

---

*Document generated: 2026-03-07*
*Final consolidation from: technical-debt-DRAFT.md, ux-specialist-review.md, qa-review.md*
*Codebase at commit: 9fbd54d0 (main branch)*
*This is the authoritative document for all technical debt planning.*
