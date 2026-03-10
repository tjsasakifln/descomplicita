# Descomplicita - System Architecture Document

**Version:** 4.0.0
**Date:** 2026-03-09
**Author:** @architect (Atlas)
**Status:** Comprehensive Brownfield Analysis
**Based on:** Codebase analysis at commit 5e56b38d (HEAD of main branch)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Patterns](#3-architecture-patterns)
4. [Component Architecture (Frontend)](#4-component-architecture-frontend)
5. [Backend Architecture](#5-backend-architecture)
6. [Database Architecture](#6-database-architecture)
7. [Infrastructure](#7-infrastructure)
8. [Security Architecture](#8-security-architecture)
9. [Testing Architecture](#9-testing-architecture)
10. [Technical Debt Inventory](#10-technical-debt-inventory)
11. [Integration Points](#11-integration-points)
12. [Scalability Assessment](#12-scalability-assessment)

---

## 1. System Overview

### 1.1 Purpose

Descomplicita (branded "DescompLicita" in the UI) is a web application for searching and analyzing public procurement bids ("licitacoes") from Brazil's government portals. The system aggregates data from multiple open-government data sources, applies sector-specific tiered keyword filtering, generates AI-powered executive summaries via OpenAI GPT-4.1-nano, and produces downloadable Excel reports.

### 1.2 Key Capabilities

- **Multi-source procurement search** across Brazilian government data portals (PNCP, Portal da Transparencia)
- **Sector-specific filtering** with tiered keyword scoring (6 configurable sectors)
- **AI-generated executive summaries** using GPT-4.1-nano with deterministic Python fallback
- **Excel report generation** with professional formatting, hyperlinks, and metadata
- **Async job processing** with real-time progress polling (phase-level granularity)
- **5-theme system** (light, paperwhite, sepia, dim, dark) with flash-free initialization
- **Accessibility-first design** with ARIA landmarks, skip links, screen reader announcements, and axe-core auditing

### 1.3 High-Level Architecture Diagram

```
                        +---------------------+
                        |      End User       |
                        |    (Web Browser)     |
                        +----------+----------+
                                   |
                                   | HTTPS
                                   v
                        +---------------------+
                        |   Vercel (CDN/SSR)   |
                        |   Next.js 16 App     |
                        |  +-----------------+ |
                        |  | App Router Pages | |
                        |  | API Routes (BFF) | |  <-- Server-side proxy, hides API keys
                        |  | /api/buscar      | |
                        |  | /api/download    | |
                        |  | /api/setores     | |
                        |  +-----------------+ |
                        +----------+----------+
                                   |
                        BACKEND_URL + JWT Bearer / X-API-Key
                                   |
                                   v
                        +---------------------+
                        |   Railway (Backend)  |
                        |   FastAPI 0.4.0      |
                        |  +-----------------+ |
                        |  | Middleware Stack | |  <-- CorrelationID -> Auth(JWT/APIKey) -> CORS
                        |  | Rate Limiter    | |  <-- slowapi (10/min search, 30/min poll)
                        |  | DurableTaskRun  | |  <-- Redis-backed task management
                        |  | Multi-Source     | |
                        |  | Orchestrator    | |  <-- Parallel fetch + dedup
                        |  | Filter Engine   | |  <-- Tiered keyword scoring (A/B/C tiers)
                        |  | LLM Summarizer  | |  <-- AsyncOpenAI GPT-4.1-nano
                        |  | Excel Generator | |  <-- openpyxl, streaming download
                        |  +-----------------+ |
                        +----+-----+-----+----+
                             |     |     |
                    +--------+     |     +--------+
                    v              v              v
             +------------+  +----------+  +----------+
             |   Redis    |  | SQLite   |  | External |
             |  (Railway) |  | (local)  |  | APIs     |
             +------------+  +----------+  +----------+
              - Job state    - Search      - PNCP (active)
              - PNCP cache     history    - Transparencia (active)
              - Excel bytes  - User       - OpenAI GPT-4.1-nano
              - Task params    prefs
              - TTL: 4h/24h
```

### 1.4 Current Metrics

| Metric | Value |
|--------|-------|
| Backend test files | 32 |
| Frontend test files (unit) | 37 |
| Frontend E2E specs | 5 |
| Data sources (active / total) | 2 / 2 (3 deprecated sources removed) |
| Procurement sectors | 6 |
| API version | 0.4.0 (versioned at /api/v1/) |
| Frontend coverage threshold | 65% statements, 50% branches |
| Backend coverage threshold | 70% |

---

## 2. Tech Stack

### 2.1 Frontend

| Technology | Version | Rationale |
|-----------|---------|-----------|
| **Next.js** | 16.1.4 | App Router for file-based routing, server components, API routes as BFF proxy |
| **React** | 18.3.1 | Component model, hooks ecosystem, concurrent features readiness |
| **TypeScript** | 5.9.3 | Type safety across the frontend codebase, strict mode enabled |
| **Tailwind CSS** | 3.4.19 | Utility-first styling with design token integration via CSS custom properties |
| **Mixpanel** | 2.74.0 | Product analytics (dynamically imported to avoid bundle bloat) |
| **Sentry** | 10.42.0 | Error monitoring with source map upload |
| **uuid** | 13.0.0 | Client-side unique ID generation |

### 2.2 Backend

| Technology | Version | Rationale |
|-----------|---------|-----------|
| **Python** | 3.11+ | Async ecosystem, type hints, performance (CI matrix tests 3.11 and 3.12) |
| **FastAPI** | 0.135.1 | Async-native, Pydantic validation, OpenAPI docs auto-generation |
| **Pydantic** | 2.12.5 | Request/response schema validation and LLM structured output |
| **httpx** | 0.28.1 | Async HTTP client for PNCP API calls with connection pooling |
| **Redis (async)** | 5.3.1 | Job state, response caching, Excel byte storage, task parameters |
| **OpenAI SDK** | 1.109.1 | AsyncOpenAI client for GPT-4.1-nano structured summaries |
| **openpyxl** | 3.1.5 | Excel report generation with formatting and hyperlinks |
| **slowapi** | 0.1.9 | IP-based rate limiting on API endpoints |
| **aiosqlite** | 0.20.0 | Async SQLite for search history and user preferences persistence |
| **Sentry** | 2.22.0 | Error tracking with FastAPI/Starlette integrations |
| **Uvicorn** | 0.41.0 | ASGI server with hot-reload for development |

### 2.3 Infrastructure

| Technology | Purpose |
|-----------|---------|
| **Railway** | Backend hosting (FastAPI + Redis), Dockerfile-based deployment |
| **Vercel** | Frontend hosting (Next.js standalone output), edge CDN |
| **Docker Compose** | Local development orchestration (backend + frontend + Redis) |
| **GitHub Actions** | CI/CD: tests, security audits, deployments, smoke tests |

### 2.4 Testing Tools

| Tool | Purpose |
|------|---------|
| **Jest** (29.7) | Frontend unit testing with jsdom environment |
| **Testing Library** (React 14, user-event 14) | Component testing with user-centric queries |
| **Playwright** (1.58) | E2E browser testing (Chromium) |
| **axe-core** (4.11) | Automated accessibility auditing in E2E tests |
| **MSW** (2.12) | API mocking for frontend tests |
| **pytest** + pytest-asyncio | Backend unit and integration testing |
| **SWC** (0.2.29) | Fast TypeScript/JSX transformation for Jest |

---

## 3. Architecture Patterns

### 3.1 Backend-for-Frontend (BFF) Pattern

All backend API calls are proxied through Next.js server-side API Route Handlers. The browser never communicates directly with the FastAPI backend.

```
Browser  -->  /api/buscar (Next.js Route Handler)  -->  POST /buscar (FastAPI)
Browser  -->  /api/buscar/status?jobId=X            -->  GET /buscar/X/status
Browser  -->  /api/buscar/result?jobId=X            -->  GET /buscar/X/result
Browser  -->  /api/buscar/items?jobId=X&page=1      -->  GET /buscar/X/items?page=1
Browser  -->  /api/download?jobId=X                 -->  GET /buscar/X/download
Browser  -->  /api/setores                          -->  GET /setores
```

**Benefits:** API keys (BACKEND_API_KEY, JWT_SECRET) remain server-side. JWT token acquisition and caching is handled transparently by `lib/backendAuth.ts`.

### 3.2 Async Job Pattern

Long-running procurement searches use a job-based async pattern:

1. **POST /buscar** -- Creates a job (UUID), enqueues via DurableTaskRunner, returns `{ job_id, status: "queued" }`
2. **GET /buscar/{id}/status** -- Client polls every 2s; returns phase, progress counts, elapsed time
3. **GET /buscar/{id}/result** -- Returns executive summary and metadata (no Excel bytes)
4. **GET /buscar/{id}/items** -- Paginated filtered items (page_size up to 100)
5. **GET /buscar/{id}/download** -- Streams Excel file in 64KB chunks

Job phases: `queued -> fetching -> filtering -> summarizing -> generating_excel -> completed/failed`

### 3.3 Multi-Source Adapter Pattern

```
DataSourceClient (ABC)                MultiSourceOrchestrator
  +-- PNCPSource                        - Parallel asyncio.gather with per-source timeout
  +-- TransparenciaSource               - Graceful degradation (failed sources skipped)
                                        - Composite-key deduplication (CNPJ+numero+ano)
                                        - Partial result recovery on timeout
                                        - Source priority for dedup conflict resolution
```

Each adapter implements: `fetch_records(query) -> List[NormalizedRecord]`, `normalize(raw) -> NormalizedRecord`, `is_healthy() -> bool`.

The `NormalizedRecord` dataclass provides a unified schema with `to_legacy_dict()` for backward compatibility with the filter/excel/LLM pipeline.

### 3.4 Dependency Injection

Centralized `AppState` class in `dependencies.py` encapsulates all mutable application state:

```python
class AppState:
    redis, job_store, pncp_client, pncp_source,
    orchestrator, redis_cache, task_runner, database
```

FastAPI's `Depends()` system injects components into route handlers. `get_app_state()` is overridable via `dependency_overrides` for test isolation. All initialization/shutdown logic runs in the lifespan context manager.

### 3.5 State Management (Frontend)

The frontend uses **no external state management library**. State is composed through custom hooks:

| Hook | Scope | Responsibilities |
|------|-------|-----------------|
| `useSearchForm` | App-level | UF selection, dates, sector, search terms, validation |
| `useSearchJob` | App-level | Job submission, polling, progress, results, download |
| `useSaveDialog` | App-level | Save search dialog state and persistence |
| `useSavedSearches` | Shared | localStorage-based saved searches (CRUD, max capacity) |
| `useAnalytics` | Shared | Mixpanel event tracking (dynamically imported) |

Data flows unidirectionally: `SearchForm -> useSearchJob.buscar() -> polling -> result -> SearchSummary/ItemsList`.

### 3.6 Authentication Flow

```
1. Next.js API Route calls getBackendHeaders() from lib/backendAuth.ts
2. getBackendHeaders() attempts JWT token:
   a. If cached token is valid (with 5min buffer): use it
   b. If not: POST /auth/token with X-API-Key header
   c. Cache received JWT token (expires_in from response)
3. If JWT unavailable: fall back to X-API-Key header
4. Backend APIKeyMiddleware validates (in order):
   a. Authorization: Bearer <JWT> -- HMAC-SHA256 validation
   b. X-API-Key header -- constant-time comparison
   c. If neither configured: skip auth (dev mode)
5. Public paths bypass auth: /, /health, /docs, /redoc, /openapi.json, /auth/token
```

### 3.7 API Versioning

Routes are mounted at both root level (backward compatibility) and under `/api/v1/` prefix:

```python
v1_router = APIRouter(prefix="/api/v1")
v1_router.add_api_route("/buscar", buscar_licitacoes, ...)
# Both /buscar and /api/v1/buscar resolve to the same handler
app.include_router(v1_router)
```

---

## 4. Component Architecture (Frontend)

### 4.1 Component Tree

```
RootLayout (layout.tsx)
  |-- ThemeProvider (data-theme attr + .dark class on <html>)
  |-- AnalyticsProvider (Mixpanel dynamic import)
  |-- NetworkIndicator (online/offline banner)
  |-- Skip Link ("Pular para o conteudo principal")
  |
  +-- HomePage (page.tsx) -- "use client"
      |-- SearchHeader
      |   +-- ThemeToggle (5-theme cycle)
      |   +-- SavedSearchesDropdown
      |
      |-- SearchForm (sector/terms mode toggle)
      |-- UfSelector (27 UFs, region grouping, select all/none)
      |-- DateRangeSelector (start/end date pickers with validation)
      |-- [Search Button]
      |
      |-- LoadingProgress (dynamic import)
      |   +-- loading-progress/ProgressBar
      |   +-- loading-progress/StageList
      |   +-- loading-progress/UfGrid
      |   +-- loading-progress/CuriosityCarousel
      |   +-- loading-progress/SkeletonCards
      |
      |-- EmptyState (dynamic import, shows filter stats)
      |-- SearchSummary (executive summary + stats)
      |-- ItemsList (paginated bid cards)
      |   +-- Pagination
      |   +-- SourceBadges
      |
      |-- SearchActions (download Excel, save search)
      |-- SaveSearchDialog (native <dialog> with showModal())
```

### 4.2 Key Component Details

| Component | Pattern | Notes |
|-----------|---------|-------|
| `ThemeProvider` | CSS cascade via `data-theme` attribute | Sets `data-theme` attr + `.dark` class; no imperative `style.setProperty` calls |
| `LoadingProgress` | Decomposed into 5 sub-components | Dynamically imported; shows phase-specific progress with curiosity carousel |
| `SaveSearchDialog` | Native `<dialog>` element | Uses `showModal()`; requires jsdom polyfill in tests |
| `AnalyticsProvider` | Dynamic import | `import('mixpanel-browser')` to avoid SSR issues |
| `carouselData` | CSS custom properties | Category colors use `--cat-{category}-bg/icon-bg/text` tokens |

### 4.3 Theming System

Five themes implemented via CSS custom properties in `globals.css`:

```css
:root { /* light -- default */ }
[data-theme="paperwhite"] { /* warm white */ }
[data-theme="sepia"] { /* warm yellowed */ }
[data-theme="dim"] { /* reduced contrast dark */ }
.dark, [data-theme="dark"] { /* full dark mode */ }
```

Theme initialization script (`/theme-init.js`) runs via `<Script strategy="beforeInteractive">` to prevent flash of unstyled content.

### 4.4 Design Tokens

The design system uses semantic CSS custom properties:

- **Canvas/Ink:** `--canvas`, `--ink`, `--ink-secondary`, `--ink-muted`, `--ink-faint`
- **Brand:** `--brand-navy`, `--brand-blue`, `--brand-blue-hover`, `--brand-blue-subtle`
- **Surfaces:** `--surface-0`, `--surface-1`, `--surface-2`, `--surface-elevated`
- **Semantic:** `--success`, `--error`, `--warning` (with `-subtle` variants)
- **Status:** `--status-{success|warning|error}-{bg|text|border|dot}`

### 4.5 Typography

Three font families loaded via `next/font/google`:

| Font | Variable | Usage |
|------|----------|-------|
| DM Sans | `--font-body` | Body text, UI elements |
| Fahkwang | `--font-display` | Headings, display text |
| DM Mono | `--font-data` | Numeric data, version badges |

---

## 5. Backend Architecture

### 5.1 API Endpoints

| Method | Path | Rate Limit | Auth | Description |
|--------|------|-----------|------|-------------|
| GET | `/` | None | No | Service info and endpoint listing |
| GET | `/health` | None | No | Health check with Redis status |
| GET | `/setores` | None | No | Available procurement sectors |
| POST | `/auth/token` | None | API Key | Exchange API key for JWT token |
| POST | `/buscar` | 10/min | Yes | Start async search job |
| GET | `/buscar/{id}/status` | 30/min | Yes | Poll job progress |
| GET | `/buscar/{id}/result` | 5/min | Yes | Get completed job results |
| GET | `/buscar/{id}/items` | 30/min | Yes | Paginated filtered items |
| GET | `/buscar/{id}/download` | 10/min | Yes | Stream Excel file (64KB chunks) |
| GET | `/search-history` | None | Yes | Recent search history from SQLite |
| GET | `/cache/stats` | None | Debug | PNCP cache statistics |
| POST | `/cache/clear` | None | Debug | Clear PNCP cache |
| GET | `/debug/pncp-test` | None | Debug | PNCP API connectivity test |

All authenticated routes are also available under `/api/v1/` prefix.

### 5.2 Search Pipeline

```
POST /buscar
  |
  v
DurableTaskRunner.enqueue() -- stores params in Redis, creates asyncio task
  |
  v
run_search_job()
  |
  +-- 1. Validate sector (get_sector)
  +-- 2. Parse search terms (parse_multi_word_terms -- CSV-style, quoted phrases)
  +-- 3. FETCH: orchestrator.search_all() -- parallel fetch from enabled sources
  |       +-- PNCPSource: paginated fetch across UFs x modalidades
  |       +-- TransparenciaSource: contracts API
  |       +-- Deduplication: composite key (CNPJ + numero + ano)
  |       +-- Partial result recovery on source timeout
  +-- 4. FILTER: filter_batch() -- runs in dedicated ThreadPoolExecutor(4 workers)
  |       +-- UF filter
  |       +-- Value range filter (sector-specific min/max)
  |       +-- Tiered keyword scoring (A=1.0, B=0.7, C=0.3; threshold=0.6)
  |       +-- Exclusion keyword filter
  |       +-- Deadline filter
  |       +-- Store items for paginated retrieval
  +-- 5. SUMMARIZE: gerar_resumo() -- async OpenAI call
  |       +-- Fallback: gerar_resumo_fallback() -- deterministic Python summary
  |       +-- Override LLM counts with actual computed values
  +-- 6. EXCEL: create_excel() -- runs in ThreadPoolExecutor
  |       +-- Store Excel bytes in Redis (separate key, 2h TTL)
  +-- 7. Complete: job_store.complete(job_id, result)
  +-- 8. Record in SQLite: database.complete_search()
```

### 5.3 Middleware Stack

Middleware executes in reverse registration order (Starlette convention):

```
Request -> CorrelationIdMiddleware (generates/propagates X-Request-ID)
        -> APIKeyMiddleware (JWT Bearer or X-API-Key validation)
        -> CORSMiddleware (origin whitelist)
        -> Rate Limiter (slowapi, per-endpoint limits)
        -> Route Handler
```

### 5.4 Error Handling

Structured error codes via `ErrorCode` enum in `error_codes.py`:

```python
ErrorCode.PNCP_RATE_LIMITED.to_dict(details={"retry_after": 60})
# -> {"error": {"code": "PNCP_RATE_LIMITED", "message": "...", "details": {...}}}
```

Error categories: Search (4), PNCP (4), Job (4), Validation (3), Download (2), Auth (5), Rate Limiting (1), Server (2).

All error messages are in Portuguese for the end-user audience.

### 5.5 Caching Strategy

| Cache Layer | Storage | TTL | Key Pattern | Content |
|------------|---------|-----|-------------|---------|
| PNCP responses | Redis | 4h | `pncp:cache:{hash}` | Raw API response JSON |
| Job metadata | Redis | 24h | `job:{uuid}` | Job status, progress, results |
| Excel bytes | Redis | 2h | `excel:{uuid}` | Raw bytes (not base64) |
| Task parameters | Redis | 24h | `job_params:{uuid}` | Search parameters for restart recovery |
| In-memory | Process | Session | Dict keys | Read-through cache for current process |

Fallback: When Redis is unavailable, the system uses in-memory `JobStore` with no cross-process sharing.

### 5.6 Sector Configuration

```python
@dataclass(frozen=True)
class SectorConfig:
    id, name, description
    keywords: Set[str]           # All matching keywords
    exclusions: Set[str]         # Terms that disqualify a match
    keywords_a: Set[str]         # Tier A -- unambiguous (weight 1.0)
    keywords_b: Set[str]         # Tier B -- strong (weight 0.7)
    keywords_c: Set[str]         # Tier C -- ambiguous (weight 0.3)
    threshold: float = 0.6      # Minimum score to approve
    search_keywords: List[str]  # High-precision terms for server-side filtering
    valor_min: float = 10_000   # Sector-specific value range
    valor_max: float = 10_000_000
```

Six sectors are configured: vestuario (clothing/uniforms), alimentos, informatica, construcao, saude, servicos.

---

## 6. Database Architecture

### 6.1 SQLite (Current -- POC)

The system uses SQLite via aiosqlite for lightweight persistence. This is explicitly a POC decision with a planned migration path to Supabase PostgreSQL.

**Schema:**

```sql
CREATE TABLE search_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT NOT NULL UNIQUE,
    ufs             TEXT NOT NULL,          -- JSON array of state codes
    data_inicial    TEXT NOT NULL,          -- YYYY-MM-DD
    data_final      TEXT NOT NULL,
    setor_id        TEXT NOT NULL,
    termos_busca    TEXT,                   -- Custom search terms (nullable)
    total_raw       INTEGER DEFAULT 0,
    total_filtrado  INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'queued',  -- queued/completed/failed
    created_at      TEXT NOT NULL,          -- ISO 8601 UTC
    completed_at    TEXT,
    elapsed_seconds REAL
);

CREATE TABLE user_preferences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    key        TEXT NOT NULL UNIQUE,
    value      TEXT NOT NULL,              -- JSON-encoded value
    updated_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX idx_search_history_created ON search_history(created_at DESC);
CREATE INDEX idx_search_history_setor ON search_history(setor_id);
```

### 6.2 Redis (Ephemeral State)

Redis serves as the primary store for job lifecycle state. It is not a persistent database; all keys have TTLs.

| Key Pattern | Type | TTL | Purpose |
|------------|------|-----|---------|
| `job:{uuid}` | String (JSON) | 24h | Full job state (status, progress, results minus Excel) |
| `excel:{uuid}` | String (bytes) | 2h | Raw Excel file bytes |
| `job_params:{uuid}` | String (JSON) | 24h | Search parameters for restart recovery |
| `pncp:cache:*` | String (JSON) | 4h | Cached PNCP API responses |

### 6.3 Client-Side Storage

| Storage | Key | Content |
|---------|-----|---------|
| localStorage | `descomplicita-saved-searches` | JSON array of saved search configurations |
| localStorage | `descomplicita-theme` | Current theme identifier |

### 6.4 Migration Path

The codebase comments indicate a planned migration to Supabase PostgreSQL for production. The current SQLite storage is ephemeral on Railway (filesystem is not persistent across deploys), making the database effectively a session-level cache rather than durable storage.

---

## 7. Infrastructure

### 7.1 Production Deployment

```
GitHub (main branch)
  |
  +-- Push triggers deploy.yml
      |
      +-- detect-changes (path-based: backend/** or frontend/**)
      |
      +-- deploy-backend (Railway CLI: `railway up --service backend --detach`)
      |     +-- Dockerfile build (Python 3.11, multi-stage)
      |     +-- Health check: GET /health (120s timeout, 3 retries)
      |
      +-- deploy-frontend (Railway CLI: `railway up --service frontend --detach`)
      |     +-- Dockerfile build (Next.js standalone output)
      |     +-- Health check: GET / (5 attempts, 15s intervals)
      |
      +-- smoke-tests
            +-- Backend: /health, /, /docs, /setores
            +-- Frontend: page loads, contains "Descomplicita"
            +-- Integration: POST /buscar returns non-5xx
            +-- On failure: auto-creates GitHub issue
```

### 7.2 CI/CD Pipeline

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `tests.yml` | PR + push to main | Backend tests (Python 3.11/3.12), frontend tests, E2E tests |
| `deploy.yml` | Push to main | Production deployment with smoke tests |
| `backend-ci.yml` | PR | Backend-specific CI checks |
| `pr-validation.yml` | PR | PR validation rules |
| `codeql.yml` | Schedule/PR | GitHub CodeQL security analysis |
| `bundle-size.yml` | PR | Frontend bundle size monitoring |
| `filter-quality-audit.yml` | Manual | Filter precision/recall analysis |
| `dependabot-auto-merge.yml` | Dependabot PR | Auto-merge minor/patch updates |
| `cleanup.yml` | Schedule | Repository maintenance |

### 7.3 Docker Compose (Local Development)

Three services orchestrated:

| Service | Image | Port | Dependencies |
|---------|-------|------|-------------|
| `redis` | redis:7-alpine | 6379 | None |
| `backend` | Custom (Python 3.11) | 8000 | Redis (healthy) |
| `frontend` | Custom (Next.js) | 3000 | Backend (healthy) |

Hot-reload enabled via volume mounts. Network: `descomplicita-network` (bridge).

### 7.4 Environment Variables

| Variable | Service | Required | Default | Purpose |
|----------|---------|----------|---------|---------|
| `OPENAI_API_KEY` | Backend | Yes | -- | OpenAI API authentication |
| `REDIS_URL` | Backend | No | `redis://localhost:6379/0` | Redis connection string |
| `API_KEY` | Backend | No | -- | API key for client authentication |
| `JWT_SECRET` | Backend | No | -- | JWT signing secret (HMAC-SHA256) |
| `JWT_EXPIRATION_HOURS` | Backend | No | 24 | JWT token validity period |
| `CORS_ORIGINS` | Backend | No | `https://descomplicita.vercel.app,http://localhost:3000` | Allowed CORS origins |
| `LOG_LEVEL` | Backend | No | INFO | Logging level |
| `LLM_MODEL` | Backend | No | gpt-4.1-nano | OpenAI model name |
| `LLM_TEMPERATURE` | Backend | No | 0.3 | LLM sampling temperature |
| `LLM_MAX_TOKENS` | Backend | No | 500 | LLM max response tokens |
| `ENABLE_STREAMING_DOWNLOAD` | Backend | No | true | Feature flag for chunked Excel streaming |
| `ENABLE_DEBUG_ENDPOINTS` | Backend | No | false | Enable /cache/stats, /debug/* |
| `MAX_DATE_RANGE_DAYS` | Backend | No | 90 | Maximum search date range |
| `MAX_DOWNLOAD_SIZE` | Backend | No | 50MB | Maximum Excel download size |
| `ENABLED_SOURCES` | Backend | No | (from config) | Comma-separated source names override |
| `SENTRY_DSN` | Both | No | -- | Sentry error tracking DSN |
| `BACKEND_URL` | Frontend | No | `http://localhost:8000` | FastAPI backend URL |
| `BACKEND_API_KEY` | Frontend | No | -- | API key for backend auth |
| `NEXT_PUBLIC_MIXPANEL_TOKEN` | Frontend | No | -- | Mixpanel analytics token |

---

## 8. Security Architecture

### 8.1 Authentication

**Dual-method authentication** with JWT as primary and API key as legacy fallback:

1. **JWT Bearer Token (HMAC-SHA256):** Custom implementation in `auth/jwt.py` using Python stdlib (`hmac`, `hashlib`, `json`, `base64`). No dependency on PyJWT. Tokens contain `sub`, `iat`, `exp` claims. Constant-time signature comparison via `hmac.compare_digest()`.

2. **API Key (X-API-Key header):** Simple shared secret comparison. Used for initial JWT token acquisition at `/auth/token`.

3. **Development mode:** If neither `API_KEY` nor `JWT_SECRET` is configured, authentication is completely bypassed. This is intentional for local development but must be documented.

**Frontend auth:** `lib/backendAuth.ts` manages JWT token lifecycle with automatic caching and 5-minute refresh buffer.

### 8.2 Authorization

Currently flat -- all authenticated clients have identical access. No role-based access control (RBAC), no user identity beyond `api_client` subject in JWT.

### 8.3 CORS

```python
CORSMiddleware(
    allow_origins=["https://descomplicita.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],  # <-- overly permissive
)
```

### 8.4 Rate Limiting

IP-based rate limiting via slowapi:

| Endpoint | Limit |
|----------|-------|
| POST /buscar | 10/minute |
| GET /buscar/{id}/status | 30/minute |
| GET /buscar/{id}/result | 5/minute |
| GET /buscar/{id}/items | 30/minute |
| GET /buscar/{id}/download | 10/minute |

### 8.5 Input Validation

- **Pydantic models** validate all request bodies (BuscaRequest: UFs, date format, date range, search terms length)
- **Date range cap:** Maximum 90 days (configurable via MAX_DATE_RANGE_DAYS)
- **Search terms:** Max 500 characters
- **Pagination:** page_size capped at 100
- **Download size:** Max 50MB (configurable via MAX_DOWNLOAD_SIZE)

### 8.6 Request Tracing

Every request receives a correlation ID (UUID) via `CorrelationIdMiddleware`. The ID is:
- Generated server-side or propagated from `X-Request-ID` header
- Injected into all log records via `CorrelationIdFilter`
- Returned in response header `X-Request-ID`

### 8.7 Error Monitoring

- **Backend:** Sentry SDK with FastAPI + Starlette integrations. Configurable traces_sample_rate (default 0.1). Flush on shutdown.
- **Frontend:** Sentry Next.js SDK wrapping `next.config.js`. Source maps hidden in production.

---

## 9. Testing Architecture

### 9.1 Frontend Unit Tests

- **Framework:** Jest 29 + Testing Library React + SWC transformer
- **Environment:** jsdom with polyfills for `HTMLDialogElement.prototype.showModal` and `Element.prototype.scrollIntoView`
- **Mocking:** MSW 2.x for API mocking, manual mocks for `@sentry/nextjs` and `mixpanel-browser`
- **Module resolution:** Path aliases (`@/*` -> `app/*`, `@/lib/*` -> `lib/*`)
- **ESM handling:** Custom `transformIgnorePatterns` patch for uuid, msw, and related ESM packages
- **Test count:** 37 test files, 404+ individual tests
- **Coverage thresholds:** Statements 65%, Lines 65%, Functions 57%, Branches 50%

### 9.2 Frontend E2E Tests

- **Framework:** Playwright 1.58 (Chromium)
- **Specs:** 5 E2E test files:
  1. `01-happy-path.spec.ts` -- Full search flow
  2. `02-llm-fallback.spec.ts` -- LLM failure with fallback summary
  3. `03-validation-errors.spec.ts` -- Form validation
  4. `04-error-handling.spec.ts` -- Backend error scenarios
  5. `05-accessibility.spec.ts` -- axe-core automated accessibility audits

### 9.3 Backend Tests

- **Framework:** pytest + pytest-asyncio + httpx (TestClient)
- **Test count:** 32 test files
- **Coverage threshold:** 70% (enforced in CI)
- **CI matrix:** Python 3.11 and 3.12
- **Security audit:** pip-audit --strict runs on every PR

### 9.4 CI Test Pipeline

```
PR opened/push to main
  |
  +-- backend-tests (parallel: Python 3.11, 3.12)
  |     +-- pip-audit security audit
  |     +-- pytest with coverage
  |     +-- Coverage threshold check (70%)
  |
  +-- frontend-tests
  |     +-- npm audit --audit-level=high
  |     +-- jest --coverage
  |     +-- Coverage upload to Codecov
  |
  +-- e2e-tests (depends on: backend-tests + frontend-tests)
        +-- Start backend (uvicorn)
        +-- Build + start frontend
        +-- Playwright (Chromium)
        +-- Upload artifacts (reports, logs)
```

---

## 10. Technical Debt Inventory

### Critical Severity

| ID | Description | Impact Area | Estimated Effort | Priority |
|----|------------|-------------|-----------------|----------|
| SYS-001 | **SQLite on Railway ephemeral filesystem.** The SQLite database (`descomplicita.db`) is stored on Railway's ephemeral filesystem. Every deploy wipes the database, making search history and user preferences effectively session-scoped. The system is designed for this (comments mention planned Supabase migration), but it negates the value of the persistence layer. | Data persistence | 16h | P1 -- Migrate to Supabase PostgreSQL |
| SYS-002 | **No user identity model.** Authentication validates a single shared API key or JWT with subject "api_client". There is no concept of individual users, roles, or permissions. All clients share the same access level. Search history is not user-scoped. | Security, Product | 24h | P1 -- Required before multi-tenant use |
| SYS-003 | **Custom JWT implementation without standard library.** `auth/jwt.py` implements JWT from scratch using stdlib hmac/hashlib instead of a battle-tested library like PyJWT or python-jose. While functional and using HMAC-SHA256 with constant-time comparison, custom cryptographic code carries higher risk of subtle vulnerabilities (e.g., no key rotation, no audience/issuer validation, no JWK support). | Security | 4h | P1 -- Replace with PyJWT |

### High Severity

| ID | Description | Impact Area | Estimated Effort | Priority |
|----|------------|-------------|-----------------|----------|
| SYS-004 | **CORS allow_headers=["*"] is overly permissive.** Accepts any request header. Should be restricted to `Content-Type`, `Authorization`, `X-API-Key`, `X-Request-ID`. | Security | 1h | P2 |
| SYS-005 | **No Content-Security-Policy or HSTS headers.** The frontend lacks CSP and Strict-Transport-Security response headers in production. CSP is referenced in project memory as completed in Story 2.0, but no evidence of it in `next.config.js` or Vercel configuration files. | Security | 4h | P2 |
| SYS-006 | **Saved searches in localStorage only.** No server-side persistence for saved searches. Data is lost on browser clear, no cross-device sync. With the SQLite `user_preferences` table available, server-side sync is architecturally possible but not implemented. | Product, UX | 8h | P2 |
| SYS-007 | **Dev-mode auth bypass with no safeguard.** When both `API_KEY` and `JWT_SECRET` are unset, all authentication is silently bypassed. There is no warning log, no environment check (e.g., NODE_ENV=production), and no guard preventing this in production. A misconfigured deploy exposes all endpoints. | Security | 2h | P2 |
| SYS-008 | **Version string hardcoded in multiple places.** API version "0.4.0" appears in `main.py` (app definition and root endpoint). No single source of truth (e.g., `__version__` module or pyproject.toml version). | Code quality | 2h | P3 |
| SYS-009 | **MD5 used for dedup keys.** `orchestrator.py` uses MD5 for composite key hashing. While collision risk is negligible for this domain, MD5 is deprecated for security-sensitive use and may trigger security audit findings. | Code quality | 1h | P3 |
| SYS-010 | **No request timeout on OpenAI API calls.** The AsyncOpenAI client uses default timeouts. A slow or hung LLM response can block the summarization phase indefinitely. The fallback mechanism catches exceptions but not indefinite hangs. | Performance, Reliability | 2h | P2 |

### Medium Severity

| ID | Description | Impact Area | Estimated Effort | Priority |
|----|------------|-------------|-----------------|----------|
| SYS-011 | **Vercel serverless function limits for download proxy.** The Next.js API route for downloads buffers the entire Excel file (`response.arrayBuffer()`) before returning to the client. Large files may exceed Vercel's 10s (free) or 60s (Pro) timeout, or the 1024MB memory limit. The backend uses streaming, but the BFF proxy negates it. | Performance | 4h | P3 |
| SYS-012 | **3 deprecated data sources referenced in config.** `config.py` SOURCES_CONFIG still contains entries for ComprasGov, Querido Diario, and TCE-RJ (commented out), along with comments explaining their removal. Source adapter files may still exist. | Code quality | 2h | P3 |
| SYS-013 | **In-memory JobStore as base class for RedisJobStore.** `RedisJobStore` extends `JobStore` (in-memory), creating a dual-write pattern. On process restart, in-memory state is lost but Redis state persists. The inheritance hierarchy creates conceptual coupling between ephemeral and persistent storage strategies. | Architecture | 8h | P3 |
| SYS-014 | **Filter engine uses regex for keyword matching.** The filter pipeline compiles regex patterns for ~130 inclusion keywords and ~100 exclusion keywords. While mitigated by fail-fast ordering (UF and value filters run first), this is CPU-intensive for large result sets. The dedicated ThreadPoolExecutor (4 workers) prevents event loop blocking. | Performance | 8h | P4 |
| SYS-015 | **No retry logic on Next.js BFF proxy calls.** The frontend API routes make single-attempt fetch calls to the backend. Network blips between Vercel and Railway cause immediate failures surfaced to the user. | Reliability | 4h | P3 |
| SYS-016 | **React 18 with Next.js 16.** Next.js 16 has React 19 support, but the project pins React 18.3.1. This prevents using React 19 features (use, Actions, optimistic updates) and will eventually diverge from Next.js defaults. | Dependencies | 8h | P4 |
| SYS-017 | **Frontend module alias mismatch.** `jest.config.js` maps `@/*` to `<rootDir>/app/$1`, but `tsconfig.json` maps `@/*` to `./*`. The Jest config is more restrictive. Additionally, `@/lib/*` has a separate explicit mapping. | Code quality | 2h | P3 |
| SYS-018 | **Transparencia source health check is synchronous.** `TransparenciaSource.is_healthy()` uses synchronous HTTP calls, which would block the event loop if invoked from async context. Currently only used in tests. | Code quality | 2h | P4 |

### Low Severity

| ID | Description | Impact Area | Estimated Effort | Priority |
|----|------------|-------------|-----------------|----------|
| SYS-019 | **Deadline filter partially disabled.** The `dataAberturaProposta` field interpretation in the filter engine has known limitations. Past dates are now excluded from urgency alerts (per latest commit), but the deadline filter logic may still need refinement. | Feature completeness | 4h | P4 |
| SYS-020 | **No OpenAPI schema for paginated items response.** The `/buscar/{id}/items` endpoint returns a JSON dict without a Pydantic response model, unlike other endpoints. | API documentation | 1h | P4 |
| SYS-021 | **Integration tests are placeholder.** The `integration-tests` job in `tests.yml` has a placeholder step that echoes "will be implemented in issue #27". The PostgreSQL service starts but is unused. | Test coverage | 16h | P4 |
| SYS-022 | **No Docker Compose profile for frontend dev mode.** The Docker Compose frontend service builds a production image. No profile or override for Next.js dev mode with hot-reload. | Developer experience | 2h | P5 |
| SYS-023 | **Mixpanel loaded on all pages.** The `AnalyticsProvider` wraps the entire app. While it uses dynamic import, Mixpanel initializes even for pages where analytics are unnecessary. | Performance | 2h | P5 |
| SYS-024 | **No structured logging on frontend.** Console.warn/error used for logging in `backendAuth.ts` and API routes. No structured logging library or log aggregation. | Observability | 4h | P5 |

---

## 11. Integration Points

### 11.1 External APIs

| Service | Type | Authentication | Rate Limits | Error Handling |
|---------|------|---------------|-------------|---------------|
| **PNCP** (pncp.gov.br) | REST API | None (public) | 10 RPS (self-imposed), server-enforced limits | Exponential backoff, circuit breaker, partial result recovery on timeout |
| **Portal da Transparencia** | REST API | API key (header `chave-api-dados`) | 3 RPS (self-imposed) | Timeout with graceful degradation, source disabled if API key missing |
| **OpenAI** | REST API | Bearer token (OPENAI_API_KEY) | Account-level | Fallback to deterministic Python summary on any failure |

### 11.2 Third-Party Services

| Service | Purpose | Integration Point |
|---------|---------|------------------|
| **Redis** (Railway) | Job state, caching, Excel storage | `redis.asyncio.from_url()`, graceful fallback to in-memory |
| **Sentry** | Error monitoring | SDK auto-instrumentation (FastAPI + Next.js) |
| **Mixpanel** | Product analytics | Browser-side dynamic import, event tracking |
| **Codecov** | Coverage reporting | CI upload of coverage artifacts |
| **Railway CLI** | Deployment | `railway up --service X --detach` in GitHub Actions |

### 11.3 Internal Integration (Frontend <-> Backend)

The Next.js frontend communicates exclusively through its own API Route Handlers (BFF pattern). These handlers:

1. Validate client input (basic checks)
2. Obtain authentication headers (JWT with caching, API key fallback)
3. Proxy the request to the FastAPI backend
4. Transform/filter the response for the client

No WebSocket or SSE connections exist. The client polls for job progress via HTTP.

---

## 12. Scalability Assessment

### 12.1 Current Bottlenecks

| Bottleneck | Severity | Description |
|-----------|----------|-------------|
| **Single-process backend** | High | FastAPI runs as a single uvicorn process. All async tasks, job management, and filtering run in one process. No horizontal scaling. |
| **PNCP API throughput** | High | The dominant bottleneck. PNCP responses take 30-300s depending on UF count and date range. Self-imposed 10 RPS limit. Max 10 pages per UF x modalidade combination (500 items each). |
| **In-process job execution** | Medium | Jobs run as asyncio tasks within the API server process. No external task queue (Celery/RQ). Concurrent searches compete for event loop time. |
| **Redis memory for Excel** | Medium | Excel files stored in Redis (2h TTL). Under concurrent load, many jobs with large Excel files can exhaust Redis memory. |
| **ThreadPoolExecutor(4)** | Low | CPU-bound filtering and Excel generation share a 4-worker thread pool. Under heavy concurrent load, this becomes a serialization point. |

### 12.2 Scaling Limits

| Dimension | Current Limit | Constraint |
|-----------|--------------|------------|
| Concurrent searches | ~10 (max_jobs in JobStore) | Single-process asyncio, thread pool size |
| Result set size | ~10,500 raw items per search | MAX_PAGES_PER_COMBO=10, 50 items/page, 21 combos (3 UFs x 7 modalidades) |
| Excel file size | 50MB | MAX_DOWNLOAD_SIZE env var |
| Date range | 90 days | MAX_DATE_RANGE_DAYS env var |
| UF count scaling | Timeout at 15+ UFs | PNCP timeout scaled: base 300s + 15s per UF beyond 5 |
| Rate limiting | 10 searches/minute per IP | slowapi, not shared across processes |

### 12.3 Scaling Recommendations

1. **Short-term (POC graduation):**
   - Migrate SQLite to Supabase PostgreSQL for durable persistence
   - Add Gunicorn with multiple uvicorn workers for horizontal process scaling
   - Implement proper user authentication with Supabase Auth

2. **Medium-term (production readiness):**
   - Extract job execution to a Celery/RQ worker for decoupled processing
   - Implement Redis Cluster or managed Redis with persistence for job durability
   - Add CDN caching for static assets and API responses where applicable
   - Implement WebSocket or SSE for real-time progress (replace polling)

3. **Long-term (scale):**
   - Kubernetes-based deployment for auto-scaling workers
   - Pre-computed procurement data pipeline (scheduled batch ingestion from PNCP)
   - Full-text search index (Elasticsearch/Typesense) for faster filtering
   - Event-driven architecture for multi-tenant search workloads

---

## Appendix A: File Map

```
descomplicita/
+-- backend/
|   +-- main.py                    # FastAPI app, routes, lifespan, job pipeline
|   +-- config.py                  # PNCP config, modalities, retry config, sources
|   +-- schemas.py                 # Pydantic request/response models
|   +-- schemas_contract.py        # Contract-specific schemas
|   +-- dependencies.py            # AppState DI container, init/shutdown
|   +-- database.py                # SQLite async database (search history, prefs)
|   +-- error_codes.py             # Structured ErrorCode enum with PT-BR messages
|   +-- exceptions.py              # Custom exception classes
|   +-- filter.py                  # Tiered keyword matching engine
|   +-- sectors.py                 # SectorConfig definitions (6 sectors)
|   +-- llm.py                     # AsyncOpenAI summarization + fallback
|   +-- excel.py                   # openpyxl Excel report generation
|   +-- job_store.py               # In-memory JobStore (base class)
|   +-- task_queue.py              # DurableTaskRunner (Redis-backed task management)
|   +-- pncp_client.py             # Legacy PNCP client
|   +-- auth/
|   |   +-- jwt.py                 # Custom HMAC-SHA256 JWT implementation
|   +-- clients/
|   |   +-- async_pncp_client.py   # Async PNCP HTTP client (httpx)
|   +-- middleware/
|   |   +-- auth.py                # APIKeyMiddleware (JWT + API key)
|   |   +-- correlation_id.py      # CorrelationIdMiddleware + log filter
|   +-- sources/
|   |   +-- base.py                # DataSourceClient ABC, NormalizedRecord, SearchQuery
|   |   +-- orchestrator.py        # MultiSourceOrchestrator (parallel + dedup)
|   |   +-- pncp_source.py         # PNCP adapter
|   |   +-- transparencia_source.py # Portal da Transparencia adapter
|   +-- stores/
|   |   +-- redis_job_store.py     # RedisJobStore (Redis-backed, Excel separation)
|   +-- app_cache/
|   |   +-- redis_cache.py         # RedisCache for PNCP response caching
|   +-- tests/                     # 32 test files (pytest)
|   +-- Dockerfile                 # Multi-stage Python 3.11 build
|   +-- railway.toml               # Railway deployment config
|   +-- requirements.txt           # Pinned Python dependencies
|   +-- start.py                   # Uvicorn startup script
|
+-- frontend/
|   +-- app/
|   |   +-- layout.tsx             # Root layout (fonts, providers, skip link)
|   |   +-- page.tsx               # Home page (search UI, client component)
|   |   +-- globals.css            # Design tokens, theme definitions
|   |   +-- types.ts               # TypeScript type definitions
|   |   +-- error.tsx              # Error boundary
|   |   +-- not-found.tsx          # 404 page
|   |   +-- components/            # 20 UI components
|   |   +-- hooks/                 # 3 app-scoped hooks (useSearchForm, useSearchJob, useSaveDialog)
|   |   +-- constants/             # UF data, static config
|   |   +-- api/                   # Next.js Route Handlers (BFF proxy)
|   |       +-- buscar/route.ts    # POST: create search job
|   |       +-- buscar/status/     # GET: poll job status
|   |       +-- buscar/result/     # GET: fetch job results
|   |       +-- buscar/items/      # GET: paginated items
|   |       +-- download/route.ts  # GET: download Excel
|   |       +-- setores/route.ts   # GET: list sectors
|   +-- hooks/                     # 2 shared hooks (useAnalytics, useSavedSearches)
|   +-- lib/
|   |   +-- backendAuth.ts         # JWT token management for BFF
|   |   +-- savedSearches.ts       # localStorage saved search CRUD
|   +-- __tests__/                 # 37 test files (Jest)
|   |   +-- e2e/                   # 5 Playwright E2E specs
|   +-- __mocks__/                 # Manual mocks (@sentry/nextjs)
|   +-- package.json               # Node.js dependencies
|   +-- jest.config.js             # Jest configuration with ESM patches
|   +-- jest.setup.js              # jsdom polyfills
|   +-- next.config.js             # Next.js + Sentry configuration
|   +-- tsconfig.json              # TypeScript strict mode
|   +-- Dockerfile                 # Next.js standalone build
|
+-- .github/workflows/            # 9 CI/CD workflow files
+-- docker-compose.yml            # Local dev orchestration (Redis + Backend + Frontend)
+-- docs/                         # Architecture, stories, PRDs, reports
```

---

## Appendix B: Architectural Decisions Record (ADR)

### ADR-001: Stateless API with Redis for Ephemeral State

**Context:** POC needed quick deployment without database setup.
**Decision:** Redis used for job state (24h TTL) and PNCP cache (4h TTL). SQLite added later for search history persistence. In-memory fallback when Redis unavailable.
**Consequences:** Jobs survive restarts via Redis. SQLite data does not survive Railway deploys. Simplifies deployment but limits durable persistence.

### ADR-002: Async Job Pattern over Synchronous Responses

**Context:** PNCP API can take 30-300 seconds across UFs and modalities.
**Decision:** POST /buscar returns immediately with job_id. Client polls every 2s. Job runs via DurableTaskRunner with Redis-backed parameter storage.
**Consequences:** Better UX with real-time progress. More complex implementation. Jobs are durable across process restarts (parameters stored in Redis for re-enqueue). DurableTaskRunner registers running tasks for SIGTERM graceful shutdown.

### ADR-003: BFF Pattern via Next.js API Routes

**Context:** Backend API key and JWT secret must not be exposed to the browser.
**Decision:** All backend calls proxied through server-side Route Handlers with JWT token caching.
**Consequences:** Secrets stay server-side. Adds latency (extra network hop). Vercel serverless limits apply. Download proxy buffers entire file (negates backend streaming).

### ADR-004: Multi-Source Adapter Architecture

**Context:** Brazil has multiple open government data portals with different APIs.
**Decision:** Abstract `DataSourceClient` interface. `MultiSourceOrchestrator` runs sources in parallel with independent timeouts, graceful degradation, and composite-key deduplication. Source priority determines conflict resolution (PNCP is canonical).
**Consequences:** Easy to add new sources. Complex dedup logic. 3 former sources removed (ComprasGov, Querido Diario, TCE-RJ) due to API deprecation.

### ADR-005: OpenAI GPT-4.1-nano with Deterministic Fallback

**Context:** Executive summaries add value but LLM APIs can fail.
**Decision:** Primary: AsyncOpenAI with structured output (Pydantic schema). Fallback: Python statistical summary. LLM counts are always overridden by actual computed values for accuracy.
**Consequences:** Graceful degradation. Low cost (~$0.001/search). Fallback is less informative but always available. Model configurable via LLM_MODEL env var.

### ADR-006: Tiered Keyword Scoring

**Context:** Binary keyword matching produced false positives (ambiguous terms) and false negatives.
**Decision:** Three keyword tiers (A=1.0, B=0.7, C=0.3) with configurable threshold (default 0.6). Extensive exclusion keyword sets prevent false positives.
**Consequences:** Better precision/recall. More complex sector configuration. Requires ongoing tuning per sector.

### ADR-007: Dedicated ThreadPoolExecutor for CPU-Bound Work

**Context:** filter_batch and Excel generation are CPU-bound, blocking the event loop.
**Decision:** Dedicated `ThreadPoolExecutor(max_workers=4, thread_name_prefix="filter")` for CPU work, separate from the default asyncio executor.
**Consequences:** Prevents thread pool starvation. LLM calls (now async) no longer compete for executor threads. Fixed pool size limits concurrency.

### ADR-008: Custom JWT over PyJWT

**Context:** Needed stateless authentication without adding dependencies.
**Decision:** Hand-rolled HMAC-SHA256 JWT in `auth/jwt.py` using stdlib only.
**Consequences:** Zero additional dependencies. Constant-time comparison. However: no key rotation, no audience/issuer claims, no JWK support, higher risk of subtle bugs vs. battle-tested library. Flagged as tech debt SYS-003.

---

*Document generated by @architect (Atlas) based on comprehensive codebase analysis. All file paths, version numbers, and architectural details verified against source code at the referenced commit.*
