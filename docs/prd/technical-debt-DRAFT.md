# Technical Debt Assessment -- DRAFT

**Project:** Descomplicita (formerly BidIQ Uniformes)
**Date:** 2026-03-07
**Status:** DRAFT -- Pending specialist validation
**Consolidated by:** @architect (Atlas)
**Sources:**
- `docs/architecture/system-architecture.md` -- Section 14 (31 debts)
- `docs/frontend/frontend-spec.md` -- Section 12 (20 debts)

---

## 1. Executive Summary

**Total unique debts identified:** 46 (after de-duplication of 5 overlapping items from 51 raw entries)

**Breakdown by severity:**

| Severity | Count | % |
|----------|-------|---|
| Critical | 4 | 9% |
| High | 10 | 22% |
| Medium | 17 | 37% |
| Low | 15 | 33% |
| **Total** | **46** | 100% |

**Breakdown by area:**

| Area | Count |
|------|-------|
| Security | 6 |
| Accessibility | 8 |
| Code Quality | 12 |
| Performance | 6 |
| Scalability | 3 |
| Maintainability | 8 |
| Design/UX | 3 |

**Estimated total effort range:** 164 -- 314 hours

**Key findings:**
- **Security is the most urgent concern**: wildcard CORS, no authentication, no rate limiting, and root container execution create a vulnerable attack surface in production.
- **Accessibility gaps are systemic**: 8 debts across keyboard navigation, contrast, ARIA semantics, and focus management indicate accessibility was not systematically validated against WCAG 2.1 AA.
- **The frontend monolith** (`page.tsx` at 1,071 lines) is the single largest maintainability risk, blocking all future feature work.
- **In-memory architecture** (job store, cache) prevents horizontal scaling and loses state on every deploy.

---

## 2. Critical Debts (Immediate Action Required)

| ID | Debt | Area | Severity | Est. Hours | Risk |
|----|------|------|----------|------------|------|
| TD-001 | CORS allows all origins | Security | Critical | 1-2 | Exploitation |
| TD-002 | Backend Dockerfile runs as root | Security | Critical | 1-2 | Container escape |
| TD-003 | No authentication or authorization | Security | Critical | 16-40 | Resource abuse |
| TD-004 | God component (page.tsx, 1,071 lines) | Code Quality | Critical | 24-40 | Dev velocity |

### TD-001: CORS Allows All Origins

- **Source ID:** System TD-01
- **Location:** `backend/main.py:76`
- **Description:** `allow_origins=["*"]` permits any website to make requests to the API. Combined with TD-003 (no auth), any third party can consume backend resources.
- **Impact:** Any malicious site can trigger searches, exhaust job slots, and exfiltrate procurement data.
- **Remediation:** Restrict to `["https://descomplicita.vercel.app", "http://localhost:3000"]`. Add `CORS_ORIGINS` environment variable for configurability.
- **Effort:** 1-2 hours

### TD-002: Backend Dockerfile Runs as Root

- **Source ID:** System TD-02
- **Location:** `backend/Dockerfile`
- **Description:** No `USER` directive in the Dockerfile. All container processes run as root, which violates container security best practices.
- **Impact:** If an attacker gains code execution in the container, they have root privileges. Risk of container escape on unpatched kernels.
- **Remediation:** Add `RUN adduser --disabled-password --gecos '' appuser` and `USER appuser` to Dockerfile. Ensure file permissions are correct for the app directory.
- **Effort:** 1-2 hours

### TD-003: No Authentication or Authorization

- **Source ID:** System TD-03
- **Location:** `backend/main.py` (all endpoints)
- **Description:** All API endpoints are publicly accessible. Any client can submit searches, poll results, and exhaust the 10-job concurrency limit.
- **Impact:** Resource exhaustion, potential abuse for competitive intelligence scraping, no audit trail.
- **Remediation:** Phase 1: Add API key authentication (header-based). Phase 2: User accounts with JWT. Phase 3: Role-based access control.
- **Effort:** 16-40 hours (depending on phase)

### TD-004: God Component (page.tsx)

- **Source ID:** Frontend TD-FE-001
- **Location:** `frontend/app/page.tsx` (1,071 lines, 20+ state variables)
- **Description:** The entire application UI, business logic, form handling, polling, download, and save-search logic lives in a single component. This violates single responsibility and makes testing, maintenance, and onboarding extremely difficult.
- **Impact:** Any UI or logic change requires modifying a massive file. Individual features cannot be tested in isolation. New developers face a steep learning curve.
- **Remediation:** Extract into feature modules:
  - `SearchForm` component (mode toggle, sector select, terms input)
  - `UfSelector` component (grid, region selector)
  - `DateRangeSelector` component
  - `SearchResults` component (summary, highlights, download)
  - `SaveSearchDialog` component
  - `useSearchJob` custom hook (polling logic)
  - Target: no component exceeds 200 lines
- **Effort:** 24-40 hours

---

## 3. High Priority Debts

| ID | Debt | Area | Severity | Est. Hours | Risk |
|----|------|------|----------|------------|------|
| TD-005 | In-memory job store not scalable | Scalability | High | 16-24 | Data loss on restart |
| TD-006 | No per-IP/user rate limiting | Security | High | 4-8 | Resource exhaustion |
| TD-007 | Excel base64 in JSON response | Performance | High | 8-16 | Memory/bandwidth waste |
| TD-008 | Modal missing focus trap and dialog role | Accessibility | High | 4-6 | WCAG failure |
| TD-009 | Missing Escape key on dropdowns | Accessibility | High | 2-3 | WCAG failure |
| TD-010 | Insufficient color contrast (ink-muted) | Accessibility | High | 3-5 | WCAG AA failure |
| TD-011 | PNCP client uses blocking requests lib | Performance | High | 16-24 | Thread pool exhaustion |
| TD-012 | Dev dependencies in production image | Performance | High | 2-4 | Larger image, slower deploys |
| TD-013 | Global mutable singletons | Maintainability | High | 8-12 | Testing difficulty |
| TD-014 | Deprecated startup event pattern | Maintainability | High | 2-4 | Future breakage |

### TD-005: In-Memory Job Store Not Horizontally Scalable

- **Source ID:** System TD-04
- **Location:** `backend/job_store.py`
- **Description:** All job state is held in a Python dict with asyncio.Lock. State is lost on every container restart. Cannot run multiple backend instances behind a load balancer.
- **Impact:** Every deployment causes all active jobs to fail silently. Users get 404 on their job_id after a redeploy.
- **Remediation:** Replace with Redis-backed job store (preserves state across restarts, enables horizontal scaling).
- **Effort:** 16-24 hours

### TD-006: No Per-IP/User Rate Limiting

- **Source ID:** System TD-05
- **Location:** `backend/main.py:289-293`
- **Description:** Only a global concurrency limit of 10 active jobs exists. A single client can monopolize all job slots.
- **Impact:** Trivial denial-of-service: 10 concurrent POST /buscar requests fill the queue. All other users get HTTP 429.
- **Remediation:** Add SlowAPI middleware or similar per-IP rate limiting (e.g., 5 requests/minute per IP).
- **Effort:** 4-8 hours

### TD-007: Excel Base64 Transmitted in JSON Response

- **Source ID:** System TD-06
- **Location:** `backend/main.py:538-539`
- **Description:** The entire Excel file is base64-encoded and embedded in the JSON job result. For large reports (hundreds of bids), this bloats JSON payloads significantly (~1.37x the file size).
- **Impact:** Increased memory usage on both backend and frontend. Slower response times for large result sets.
- **Remediation:** Use pre-signed URLs (S3/R2) or direct streaming via a dedicated download endpoint.
- **Effort:** 8-16 hours

### TD-008: Modal Missing Focus Trap and Dialog Role

- **Source ID:** Frontend TD-FE-003
- **Location:** `frontend/app/page.tsx:1002-1061`
- **Description:** The save-search modal dialog lacks `role="dialog"`, `aria-modal="true"`, focus trapping, and focus restoration on close.
- **Impact:** Screen reader users may not know they are in a modal. Keyboard users can tab behind the modal overlay, interacting with obscured content.
- **Remediation:** Add proper ARIA attributes, implement focus trap (e.g., via `focus-trap-react`), restore focus to trigger button on close, close on Escape.
- **Effort:** 4-6 hours

### TD-009: Missing Escape Key Handling on Dropdowns

- **Source ID:** Frontend TD-FE-002
- **Location:** `frontend/app/components/ThemeToggle.tsx`, `frontend/app/components/SavedSearchesDropdown.tsx`
- **Description:** Both dropdowns close on outside click but do not respond to the Escape key. WCAG 2.1 SC 1.4.13 requires dismissible content to be closable via Escape.
- **Impact:** Keyboard-only users cannot dismiss dropdowns without clicking elsewhere, which is impossible without a pointing device.
- **Remediation:** Add `useEffect` with `keydown` listener for Escape key in both components.
- **Effort:** 2-3 hours

### TD-010: Insufficient Color Contrast for Muted Text

- **Source ID:** Frontend TD-FE-004
- **Location:** `frontend/app/globals.css` (token definitions), multiple components
- **Description:** `--ink-muted` (#808f9f) on white canvas achieves only 3.4:1 contrast ratio, failing WCAG AA for normal text (4.5:1 required). `--ink-faint` (#c0d2e5) at 1.7:1 is used for some text content. Dark mode `--ink-muted` (#6b7a8a) also fails at 3.8:1.
- **Impact:** Low-vision users cannot reliably read muted labels, timestamps, and helper text.
- **Remediation:** Darken `--ink-muted` to approximately #5a6a7a (meets 4.5:1). Audit all uses of `text-ink-faint` and restrict to truly decorative contexts.
- **Effort:** 3-5 hours

### TD-011: PNCP Client Uses Blocking `requests` Library

- **Source ID:** System TD-11
- **Location:** `backend/pncp_client.py`
- **Description:** The PNCP client uses the synchronous `requests` library wrapped in `run_in_executor`, consuming ThreadPoolExecutor threads. The Transparencia source already uses `httpx` async natively.
- **Impact:** Thread pool contention under load. Maximum 3 concurrent workers limits throughput.
- **Remediation:** Migrate PNCPClient to `httpx.AsyncClient` with `asyncio.Semaphore(3)` for concurrency control.
- **Effort:** 16-24 hours

### TD-012: Dev Dependencies in Production Image

- **Source ID:** System TD-10
- **Location:** `backend/requirements.txt:23-31`
- **Description:** pytest, ruff, mypy, faker, and other dev tools are installed in the production Docker image.
- **Impact:** Larger container image (~50-100MB extra), slower deployments, increased attack surface.
- **Remediation:** Split into `requirements.txt` (production) and `requirements-dev.txt` (development/CI).
- **Effort:** 2-4 hours

### TD-013: Global Mutable Singletons

- **Source ID:** System TD-07
- **Location:** `backend/main.py:151-188`
- **Description:** `_pncp_source`, `_orchestrator`, and `_job_store` are module-level globals with lazy initialization. This pattern prevents proper dependency injection and complicates testing.
- **Impact:** Tests must monkeypatch module-level globals. Cannot run tests in parallel safely.
- **Remediation:** Use FastAPI's dependency injection system (`Depends()`) with app state or a proper DI container.
- **Effort:** 8-12 hours

### TD-014: Deprecated `@app.on_event("startup")` Pattern

- **Source ID:** System TD-08
- **Location:** `backend/main.py:191`
- **Description:** Uses deprecated FastAPI startup event handler. FastAPI recommends the lifespan context manager pattern.
- **Impact:** Will emit deprecation warnings and eventually break in future FastAPI versions.
- **Remediation:** Migrate to `@asynccontextmanager async def lifespan(app)` pattern.
- **Effort:** 2-4 hours

---

## 4. Medium Priority Debts

| ID | Debt | Area | Severity | Est. Hours | Risk |
|----|------|------|----------|------------|------|
| TD-015 | `datetime.utcnow()` deprecated | Code Quality | Medium | 1-2 | Future breakage |
| TD-016 | Branding inconsistency (BidIQ remnants) | Maintainability | Medium | 4-8 | User confusion |
| TD-017 | No request/correlation ID logging | Maintainability | Medium | 4-8 | Debug difficulty |
| TD-018 | Hardcoded PNCP base URL | Maintainability | Medium | 1-2 | Env inflexibility |
| TD-019 | No API versioning | Maintainability | Medium | 4-8 | Breaking changes |
| TD-020 | Filter diagnostic code in production | Code Quality | Medium | 1-2 | Performance waste |
| TD-021 | Duplicate UFS constant definition | Code Quality | Medium | 1-2 | Divergence risk |
| TD-022 | No OpenAPI schema for result endpoint | Maintainability | Medium | 2-4 | Poor docs |
| TD-023 | Excel download uses filesystem tmpdir | Scalability | Medium | 8-16 | Serverless incompatible |
| TD-024 | `asyncio.get_event_loop()` deprecated | Code Quality | Medium | 1-2 | Future breakage |
| TD-025 | No graceful shutdown | Maintainability | Medium | 4-8 | Orphaned tasks |
| TD-026 | Cache not shared across restarts | Performance | Medium | 8-16 | Repeated fetches |
| TD-027 | No skip-to-content link | Accessibility | Medium | 1-2 | WCAG failure |
| TD-028 | External logo dependency (Wix CDN) | Performance | Medium | 2-4 | Reliability risk |
| TD-029 | Outdated favicon (BidIQ "B") | Design | Medium | 1-2 | Brand inconsistency |
| TD-030 | Error boundary uses hardcoded colors | Design | Medium | 2-4 | Theme breakage |
| TD-031 | Missing focus management after search | Accessibility | Medium | 2-4 | UX / a11y gap |

### TD-015: `datetime.utcnow()` Deprecated

- **Source ID:** System TD-09
- **Location:** `backend/main.py:145`
- **Description:** `datetime.utcnow()` is deprecated in Python 3.12+ in favor of `datetime.now(timezone.utc)`.
- **Effort:** 1-2 hours

### TD-016: Branding Inconsistency (BidIQ Remnants)

- **Source IDs:** System TD-12, TD-13, TD-14; Frontend TD-FE-007
- **Locations:**
  - `docker-compose.yml:30,74,94` -- container names `bidiq-backend`, `bidiq-frontend`, network `bidiq-network`
  - `README.md:1` -- title says "BidIQ Uniformes"
  - `backend/sectors.py:1` -- module docstring says "BidIQ"
  - `frontend/app/icon.svg` -- shows green "B" from BidIQ era
- **Description:** Multiple files retain BidIQ branding despite the rebrand to Descomplicita. This is a consolidated debt covering 4 original items.
- **Impact:** User-facing brand confusion (favicon), developer confusion (documentation/config).
- **Remediation:** Batch update all BidIQ references. Update favicon with Descomplicita brand mark.
- **Effort:** 4-8 hours

### TD-017: No Request/Correlation ID Logging

- **Source ID:** System TD-15
- **Location:** `backend/main.py` (throughout)
- **Description:** Log entries are correlated only by job_id in string interpolation, not structured logging fields. No correlation ID is generated per HTTP request.
- **Effort:** 4-8 hours

### TD-018: Hardcoded PNCP Base URL

- **Source ID:** System TD-16
- **Location:** `backend/pncp_client.py:81`
- **Description:** `PNCPClient.BASE_URL` is a class constant, not configurable via environment variable.
- **Effort:** 1-2 hours

### TD-019: No API Versioning

- **Source ID:** System TD-17
- **Location:** `backend/main.py`
- **Description:** Endpoints are unversioned (`/buscar` not `/v1/buscar`). Breaking changes affect all clients simultaneously.
- **Effort:** 4-8 hours

### TD-020: Filter Diagnostic Code in Production Path

- **Source ID:** System TD-18
- **Location:** `backend/main.py:441-455`
- **Description:** Debug logging imports `filter.py` internals and iterates raw data inside the request handler.
- **Effort:** 1-2 hours

### TD-021: Duplicate UFS Constant Definition

- **Source IDs:** System TD-19; Frontend TD-FE-009
- **Locations:** `frontend/app/page.tsx:18-21`, `frontend/app/types.ts:6-10`
- **Description:** The UFS array is defined in both files with slightly different forms (`as const` vs plain array). `UF_NAMES` mapping only exists in `page.tsx`.
- **Remediation:** Centralize in `frontend/lib/constants.ts`.
- **Effort:** 1-2 hours

### TD-022: No OpenAPI Schema for Job Result Endpoint

- **Source ID:** System TD-20
- **Location:** `backend/main.py:650`
- **Description:** `GET /buscar/{job_id}/result` returns raw `JSONResponse`, not a typed Pydantic model. Swagger docs are incomplete.
- **Effort:** 2-4 hours

### TD-023: Excel Download Uses Filesystem tmpdir

- **Source ID:** System TD-21
- **Location:** `frontend/app/api/buscar/result/route.ts:63-64`
- **Description:** Excel files are saved to `os.tmpdir()` on the Next.js server. Not suitable for serverless (Vercel edge) or multi-instance deployment.
- **Remediation:** Use signed URLs (S3/R2) or pass-through streaming. Ties closely to TD-007.
- **Effort:** 8-16 hours

### TD-024: `asyncio.get_event_loop()` Deprecated

- **Source ID:** System TD-22
- **Location:** `backend/main.py:320`, `backend/sources/pncp_source.py:104`
- **Description:** Should use `asyncio.get_running_loop()`.
- **Effort:** 1-2 hours

### TD-025: No Graceful Shutdown

- **Source ID:** System TD-23
- **Location:** `backend/main.py:191-198`
- **Description:** Background tasks (`run_search_job`, cleanup) are not cancelled on SIGTERM. Active searches may produce orphaned results.
- **Effort:** 4-8 hours

### TD-026: Cache Not Shared Across Restarts

- **Source ID:** System TD-24
- **Location:** `backend/pncp_client.py:108`
- **Description:** In-memory LRU cache is lost on container restart. After every deployment, all PNCP responses must be re-fetched.
- **Remediation:** Use Redis for shared cache (pairs with TD-005).
- **Effort:** 8-16 hours

### TD-027: No Skip-to-Content Link

- **Source ID:** Frontend TD-FE-005
- **Location:** `frontend/app/page.tsx`
- **Description:** No skip navigation link for keyboard users to bypass header elements.
- **Effort:** 1-2 hours

### TD-028: External Logo Dependency (Wix CDN)

- **Source ID:** Frontend TD-FE-006
- **Location:** `frontend/app/page.tsx` (LOGO_URL constant)
- **Description:** Logo loaded from `static.wixstatic.com` instead of self-hosted. Not using Next.js `<Image>` component.
- **Remediation:** Use existing `public/logo-descomplicita.png` via Next.js `<Image>`.
- **Effort:** 2-4 hours

### TD-029: Outdated Favicon (BidIQ "B")

- **Source ID:** Frontend TD-FE-007 (also covered in TD-016 branding consolidation)
- **Location:** `frontend/app/icon.svg`
- **Description:** Favicon displays a green "B" from the BidIQ era.
- **Note:** This is a sub-item of TD-016 but tracked separately for frontend team assignment.
- **Effort:** 1-2 hours

### TD-030: Error Boundary Uses Hardcoded Colors

- **Source ID:** Frontend TD-FE-008
- **Location:** `frontend/app/error.tsx`
- **Description:** Uses `bg-gray-50`, `bg-green-600`, `text-gray-900` instead of design system tokens. Error page does not respect themes.
- **Effort:** 2-4 hours

### TD-031: Missing Focus Management After Search

- **Source ID:** Frontend TD-FE-014
- **Location:** `frontend/app/page.tsx`
- **Description:** When search completes, focus remains on the search button. Results may be below viewport. Screen reader users are not informed.
- **Remediation:** After results load, scroll to and focus the results section via ref.
- **Effort:** 2-4 hours

---

## 5. Low Priority Debts

| ID | Debt | Area | Severity | Est. Hours | Risk |
|----|------|------|----------|------------|------|
| TD-032 | No structured error codes | Maintainability | Low | 4-8 | Client parsing |
| TD-033 | f-string in logger calls | Code Quality | Low | 2-4 | Minor perf |
| TD-034 | No pagination for sectors endpoint | Scalability | Low | 1-2 | Future concern |
| TD-035 | Frontend emoji in source code | Code Quality | Low | 1-2 | Style inconsistency |
| TD-036 | No content-length validation for downloads | Security | Low | 1-2 | Large file risk |
| TD-037 | Date range max removed | Performance | Low | 1-2 | PNCP overload |
| TD-038 | Module-level singleton in job_store.py | Code Quality | Low | 1 | Unused code |
| TD-039 | Deprecated performance API in AnalyticsProvider | Code Quality | Low | 1 | Future breakage |
| TD-040 | No loading state for sector list | UX | Low | 1-2 | Minor UX gap |
| TD-041 | E2E tests reference outdated class names | Code Quality | Low | 2-4 | Test failures |
| TD-042 | No code splitting for components | Performance | Low | 4-8 | Bundle size |
| TD-043 | No `<nav>` semantic element | Accessibility | Low | 1 | Screen reader |
| TD-044 | SourceBadges/carouselData hardcoded colors | Design | Low | 2-4 | Theme inconsistency |
| TD-045 | Unused public asset (logo-descomplicita.png) | Code Quality | Low | 0.5 | Repo bloat |
| TD-046 | Missing aria-describedby for terms input | Accessibility | Low | 1 | Screen reader gap |

### Brief Descriptions

- **TD-032** (System TD-26): Error responses use free-text Portuguese messages, not machine-parseable codes. `backend/main.py` throughout.
- **TD-033** (System TD-27): Uses `f"msg {val}"` in `logger.info()` instead of `"msg %s", val` for lazy formatting. `backend/main.py`.
- **TD-034** (System TD-28): `/setores` returns all sectors in one response. Not a problem at 6 sectors. `backend/main.py:201-204`.
- **TD-035** (System TD-29): LoadingProgress.tsx and other components embed emoji characters directly in JSX. `frontend/app/components/LoadingProgress.tsx`.
- **TD-036** (System TD-30): Frontend serves downloaded Excel files without size validation. `frontend/app/api/download/route.ts`.
- **TD-037** (System TD-31): `BuscaRequest` no longer enforces a max date range, allowing arbitrarily large queries. `backend/schemas.py:59-73`.
- **TD-038** (System TD-25): `job_store.py:158` creates a `job_store = JobStore()` singleton that is never used. `main.py` creates its own `_job_store`.
- **TD-039** (Frontend TD-FE-011): `performance.timing.navigationStart` is deprecated. `frontend/app/components/AnalyticsProvider.tsx:52`.
- **TD-040** (Frontend TD-FE-012): No loading indicator while fetching sector list from `/api/setores`. `frontend/app/page.tsx`.
- **TD-041** (Frontend TD-FE-013): E2E tests check for `bg-green-600` (old BidIQ) but UI uses `bg-brand-navy`. `frontend/__tests__/e2e/01-happy-path.spec.ts:64`.
- **TD-042** (Frontend TD-FE-015): All components statically imported. LoadingProgress (415 lines) and carouselData (368 lines) could use dynamic imports. `frontend/app/page.tsx`.
- **TD-043** (Frontend TD-FE-016): Header lacks `<nav>` element for navigation area. `frontend/app/page.tsx`.
- **TD-044** (Frontend TD-FE-017): SourceBadges and carouselData use raw Tailwind colors (`bg-green-100`, `bg-blue-50`) instead of design tokens. `frontend/app/components/SourceBadges.tsx`, `frontend/app/components/carouselData.ts`.
- **TD-045** (Frontend TD-FE-018): `public/logo-descomplicita.png` exists but is unused. Will be resolved if TD-028 is implemented (self-host logo).
- **TD-046** (Frontend TD-FE-019): Terms input helper text not linked via `aria-describedby`. `frontend/app/page.tsx`.

---

## 6. Cross-Cutting Concerns

### 6.1 Security Posture (TD-001 + TD-002 + TD-003 + TD-006 + TD-036)

The backend has **no authentication, no per-client rate limiting, and accepts requests from any origin**. The container runs as root. These debts compound: an unauthenticated attacker from any origin can exhaust all 10 job slots, trigger unlimited PNCP API calls (incurring rate-limit penalties with the government API), and potentially exploit container-level vulnerabilities. These must be addressed as a group before any public launch or marketing.

### 6.2 In-Memory Architecture Ceiling (TD-005 + TD-026 + TD-023)

The job store, PNCP cache, and Excel download files all rely on ephemeral storage (Python dicts and filesystem tmpdir). This creates three problems:
1. **Data loss on deploy** -- active jobs vanish, cache is cold
2. **No horizontal scaling** -- cannot run multiple backend instances
3. **Serverless incompatibility** -- tmpdir-based downloads fail on Vercel Edge

Introducing Redis (for jobs + cache) and object storage (for Excel files) would resolve all three simultaneously.

### 6.3 Accessibility Compliance (TD-008 + TD-009 + TD-010 + TD-027 + TD-031 + TD-043 + TD-046)

Seven accessibility debts indicate that WCAG 2.1 AA compliance was not a design requirement. The issues range from structural (missing focus trap, no skip link) to perceptual (contrast ratios). These affect keyboard-only users, screen reader users, and low-vision users. Brazilian accessibility law (LBI -- Lei Brasileira de Inclusao, Law 13.146/2015) requires digital accessibility for government-facing tools.

### 6.4 Branding Migration Completeness (TD-016 + TD-029 + TD-028 + TD-045)

The BidIQ-to-Descomplicita rebrand is incomplete across documentation, Docker configuration, favicon, and logo hosting. These are individually low-effort but collectively create a fragmented brand identity.

### 6.5 Deprecated API Usage (TD-015 + TD-024 + TD-014 + TD-039)

Four items use deprecated Python/JS APIs (`datetime.utcnow()`, `asyncio.get_event_loop()`, `@app.on_event`, `performance.timing`). While not immediately breaking, these will cause warnings and eventual failures as runtimes are upgraded.

---

## 7. Dependency Map

```
TD-004 (God Component)
  |
  +-- UNBLOCKS --> TD-031 (Focus management -- easier after extraction)
  +-- UNBLOCKS --> TD-008 (Modal a11y -- easier as separate component)
  +-- UNBLOCKS --> TD-021 (UFS dedup -- natural during extraction)
  +-- UNBLOCKS --> TD-042 (Code splitting -- requires separate components)

TD-005 (Redis Job Store)
  |
  +-- ENABLES --> TD-026 (Shared cache via Redis)
  +-- PAIRS WITH --> TD-023 (Excel storage -- both need external state)

TD-007 (Excel base64 removal)
  |
  +-- PAIRS WITH --> TD-023 (tmpdir Excel -- both about file delivery)
  +-- REQUIRES --> Object storage decision (S3/R2/Supabase)

TD-003 (Authentication)
  |
  +-- ENHANCES --> TD-006 (Per-user rate limiting with identity)
  +-- REQUIRES --> TD-001 (CORS must be restricted first)

TD-013 (DI refactor)
  |
  +-- ENHANCES --> TD-005 (Redis migration cleaner with DI)
  +-- ENHANCES --> TD-014 (Lifespan pattern aligns with DI)

TD-016 (Branding)
  |
  +-- INCLUDES --> TD-029 (Favicon)
  +-- RESOLVES --> TD-045 (Unused logo -- use it for TD-028)
  +-- PAIRS WITH --> TD-028 (Self-host logo)
```

---

## 8. Preliminary Priority Matrix

| Quadrant | IDs | Rationale |
|----------|-----|-----------|
| **High Impact + Low Effort (Quick Wins)** | TD-001, TD-002, TD-009, TD-012, TD-015, TD-020, TD-021, TD-024, TD-027 | 1-4 hours each, meaningful security/quality improvement |
| **High Impact + High Effort (Strategic)** | TD-003, TD-004, TD-005, TD-007, TD-011, TD-023, TD-026 | Core architecture improvements, 16-40 hours each |
| **Low Impact + Low Effort (Fill-ins)** | TD-016, TD-018, TD-029, TD-030, TD-033, TD-035, TD-038, TD-039, TD-040, TD-043, TD-045, TD-046 | Can be batched into a cleanup sprint, 1-4 hours each |
| **Low Impact + High Effort (Deprioritize)** | TD-010 (requires full contrast audit), TD-019, TD-032, TD-042 | Important but not urgent; schedule for later |

### Suggested Execution Order

**Sprint 1 -- Security Hardening (Quick Wins):**
TD-001, TD-002, TD-006, TD-012 (~10-16 hours)

**Sprint 2 -- Accessibility Critical Path:**
TD-008, TD-009, TD-010, TD-027, TD-031 (~12-20 hours)

**Sprint 3 -- Frontend Architecture:**
TD-004 (God component decomposition, ~24-40 hours)

**Sprint 4 -- Backend Architecture:**
TD-005, TD-026, TD-013, TD-014 (~34-56 hours)

**Sprint 5 -- File Delivery Pipeline:**
TD-007, TD-023 (~16-32 hours)

**Sprint 6 -- Cleanup Batch:**
TD-015, TD-016, TD-018, TD-020, TD-021, TD-024, TD-025, TD-028, TD-029, TD-030 (~20-40 hours)

**Backlog:**
TD-003 (auth), TD-011 (httpx migration), TD-019 (API versioning), remaining Low items

---

## 9. Questions for Specialist Validation

### For @ux-design-expert (Pixel):

1. **TD-004 (God Component):** The proposed decomposition splits into 5 components + 1 hook. Does the suggested component boundary (`SearchForm`, `UfSelector`, `DateRangeSelector`, `SearchResults`, `SaveSearchDialog`) align with how you envision the UX evolving? Are there alternative split points that would better support future features (e.g., comparison view, saved search management page)?

2. **TD-010 (Color Contrast):** The proposed fix darkens `--ink-muted` to ~#5a6a7a. Does this align with the visual design intent? Would adjusting the muted role's purpose (e.g., only for decorative text) be preferable to changing the color value?

3. **TD-FE-010 (i18n):** The frontend has no internationalization infrastructure. Given the target market is exclusively Brazilian, is i18n a realistic near-term need? Should we plan for it during the God Component decomposition (extracting string constants) or defer entirely?

4. **TD-030 (Error Boundary):** The error page uses hardcoded Tailwind colors. Should the error page intentionally use a simple, reliable color scheme (avoiding CSS custom property failures in error states), or should it fully participate in the theme system?

5. **TD-028 (Logo):** The local `logo-descomplicita.png` exists but is unused. Is this the current approved brand asset? Should we use it as-is or is there an updated version? What should the new favicon look like?

6. **Frontend test coverage** is reported at 91.5% in the architecture doc but actual Jest thresholds show ~49% statements and ~39% branches. Can you clarify which measurement is canonical? What is the realistic target for the next milestone?

7. **Large-screen optimization:** The current layout caps at 896px (`max-w-4xl`). Is there a design vision for wider displays, or is the narrow content column intentional?

### For @qa (Cypress):

1. **TD-041 (E2E Tests):** E2E tests reference `bg-green-600` but the UI uses `bg-brand-navy`. Are the E2E tests currently passing in CI? Are they being skipped? What is the actual state of the E2E test suite?

2. **TD-020 (Frontend Coverage):** The discrepancy between claimed 91.5% and actual ~49% statement coverage needs investigation. Are there additional test suites not captured in `jest.config.js` thresholds? Is coverage being measured differently in CI?

3. **Risk assessment for TD-004 (God Component decomposition):** What is the testing strategy for a major refactor of `page.tsx`? Should we establish a baseline E2E suite before the decomposition to catch regressions?

4. **Accessibility testing:** axe-core is installed as a dependency but does not appear to be actively used in E2E tests. Is there an accessibility testing strategy? Should we gate PRs on axe-core violations?

5. **Backend test fidelity:** The 99.2% backend coverage is impressive, but are the tests testing behavior or just code paths? Are there integration tests that exercise the full search pipeline (POST -> poll -> result)?

6. **TD-037 (Date range max removed):** The date range validation was relaxed (no max days limit). Was this tested for resource consumption? What happens when a user queries 365 days across 27 UFs?

7. **Circuit breaker / rate limiter testing:** Are the resilience patterns (in `pncp_client.py`) tested under realistic load conditions, or only unit-tested with mocks?

---

## 10. Preliminary Effort Summary

| Area | Items | Hours (Low) | Hours (High) |
|------|-------|-------------|--------------|
| Security | 6 | 24 | 54 |
| Accessibility | 8 | 15 | 28 |
| Code Quality | 12 | 36 | 68 |
| Performance | 6 | 33 | 62 |
| Scalability | 3 | 25 | 42 |
| Maintainability | 8 | 26 | 50 |
| Design/UX | 3 | 5 | 10 |
| **TOTAL** | **46** | **164** | **314** |

**Notes on estimation:**
- Hours assume a single developer per task
- TD-003 (authentication) has the widest range (16-40h) depending on scope (API key vs. full user system)
- TD-004 (God component) and TD-005 (Redis migration) are the largest individual items
- Many Low items can be batched into a single cleanup session (estimated total: 20-30h)
- The Security quick wins (TD-001, TD-002, TD-006, TD-012) total only ~8-16 hours and should be done immediately

---

## Appendix A: De-Duplication Log

| Merged Into | Original Items | Reason |
|-------------|---------------|--------|
| TD-016 | System TD-12, TD-13, TD-14; Frontend TD-FE-007 | All are BidIQ branding remnants; consolidated into one branding debt |
| TD-021 | System TD-19; Frontend TD-FE-009 | Identical issue: duplicate UFS array definition |
| TD-029 | Frontend TD-FE-007 (also in TD-016) | Tracked separately for frontend team but acknowledged as part of branding |
| TD-028 | Frontend TD-FE-006 + TD-FE-018 (related) | Logo hosting and unused local asset are two sides of the same fix |

**Raw counts:** 31 (system) + 20 (frontend) = 51 raw items -> 46 unique debts after merging

## Appendix B: ID Cross-Reference

| Unified ID | System ID | Frontend ID | Short Name |
|------------|-----------|-------------|------------|
| TD-001 | TD-01 | -- | CORS wildcard |
| TD-002 | TD-02 | -- | Root container |
| TD-003 | TD-03 | -- | No auth |
| TD-004 | -- | TD-FE-001 | God component |
| TD-005 | TD-04 | -- | In-memory job store |
| TD-006 | TD-05 | -- | No rate limiting |
| TD-007 | TD-06 | -- | Excel base64 |
| TD-008 | -- | TD-FE-003 | Modal a11y |
| TD-009 | -- | TD-FE-002 | Escape key dropdowns |
| TD-010 | -- | TD-FE-004 | Color contrast |
| TD-011 | TD-11 | -- | Blocking requests lib |
| TD-012 | TD-10 | -- | Dev deps in prod |
| TD-013 | TD-07 | -- | Global singletons |
| TD-014 | TD-08 | -- | Deprecated startup |
| TD-015 | TD-09 | -- | datetime.utcnow |
| TD-016 | TD-12+13+14 | TD-FE-007 | Branding remnants |
| TD-017 | TD-15 | -- | No correlation ID |
| TD-018 | TD-16 | -- | Hardcoded PNCP URL |
| TD-019 | TD-17 | -- | No API versioning |
| TD-020 | TD-18 | -- | Filter debug code |
| TD-021 | TD-19 | TD-FE-009 | Duplicate UFS |
| TD-022 | TD-20 | -- | No OpenAPI result |
| TD-023 | TD-21 | -- | tmpdir Excel |
| TD-024 | TD-22 | -- | get_event_loop |
| TD-025 | TD-23 | -- | No graceful shutdown |
| TD-026 | TD-24 | -- | Ephemeral cache |
| TD-027 | -- | TD-FE-005 | Skip-to-content |
| TD-028 | -- | TD-FE-006+018 | External logo |
| TD-029 | -- | TD-FE-007 | Outdated favicon |
| TD-030 | -- | TD-FE-008 | Error boundary colors |
| TD-031 | -- | TD-FE-014 | Focus after search |
| TD-032 | TD-26 | -- | No error codes |
| TD-033 | TD-27 | -- | f-string in logger |
| TD-034 | TD-28 | -- | Sectors pagination |
| TD-035 | TD-29 | -- | Emoji in source |
| TD-036 | TD-30 | -- | Download size limit |
| TD-037 | TD-31 | -- | No date range max |
| TD-038 | TD-25 | -- | Unused singleton |
| TD-039 | -- | TD-FE-011 | Deprecated perf API |
| TD-040 | -- | TD-FE-012 | Sector loading state |
| TD-041 | -- | TD-FE-013 | E2E outdated classes |
| TD-042 | -- | TD-FE-015 | No code splitting |
| TD-043 | -- | TD-FE-016 | No nav element |
| TD-044 | -- | TD-FE-017 | Hardcoded colors |
| TD-045 | -- | TD-FE-018 | Unused public asset |
| TD-046 | -- | TD-FE-019 | aria-describedby |

## Appendix C: Items Not Carried Forward (from Frontend TD-FE-010)

- **i18n infrastructure** (Frontend TD-FE-010): Noted as a potential future need but not classified as technical debt since the product targets a single-language market (Brazilian Portuguese). Listed as a question for @ux-design-expert validation in Section 9.
- **Frontend test coverage target** (Frontend TD-FE-020): Folded into Section 9 questions for @qa rather than listed as a standalone debt, since the discrepancy between reported (91.5%) and measured (49.45%) coverage needs clarification before actionable work can be scoped.

---

*Document generated: 2026-03-07*
*Consolidated from system architecture and frontend specification analyses*
*Based on codebase at commit `9fbd54d0` (main branch)*
*Pending review by: @ux-design-expert (Pixel), @qa (Cypress)*
