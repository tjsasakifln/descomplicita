# Descomplicita - System Architecture Document

**Version:** 3.0.0
**Date:** 2026-03-09
**Author:** @architect (Atlas)
**Status:** Phase 1 - Brownfield Discovery (Complete Rewrite)
**Based on:** Codebase analysis at HEAD of main branch

---

## 1. Executive Summary

Descomplicita (branded "DescompLicita" in the UI) is a proof-of-concept web application for searching and analyzing public procurement bids ("licitacoes") from Brazil's government portals. The system aggregates data from multiple open-government data sources -- primarily PNCP (Portal Nacional de Contratacoes Publicas) -- applies sector-specific keyword filtering, generates AI-powered executive summaries via OpenAI GPT-4.1-nano, and produces downloadable Excel reports.

**Current State:** Functional POC deployed to Railway (backend) and Vercel (frontend). The application is stateless with Redis used for ephemeral job state and API response caching. Of the 5 configured data sources, only 2 are currently active (PNCP and Transparencia); the remaining 3 have been disabled due to API deprecation or endpoint changes. The system supports 6 procurement sectors with tiered keyword scoring.

**Technology Stack:**
- **Backend:** Python 3.11, FastAPI 0.3.0, httpx (async HTTP), Redis (async), openpyxl, OpenAI SDK
- **Frontend:** Next.js 16, React 18, TypeScript 5.9, Tailwind CSS 3.4
- **Infrastructure:** Railway (backend + Redis), Vercel (frontend), Docker Compose (local dev)
- **Observability:** Sentry (error tracking), Mixpanel (product analytics), structured logging with correlation IDs

**Key Metrics:**
- Backend test files: 33
- Frontend test files: 22 (unit) + 4 (E2E Playwright)
- Data sources: 2 active / 5 total
- Procurement sectors: 6
- API version: 0.3.0 (unversioned URLs)

---

## 2. System Overview

### 2.1 High-Level Architecture Diagram

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
                        |  | API Routes       | |  <-- BFF pattern (server-side proxy)
                        |  | (Route Handlers) | |
                        |  +-----------------+ |
                        +----------+----------+
                                   |
                        BACKEND_URL + X-API-Key
                                   |
                                   v
                        +---------------------+
                        |   Railway (Backend)  |
                        |   FastAPI + Uvicorn  |
                        |  +-----------------+ |
                        |  | Middleware Stack | |  <-- CorrelationID -> APIKey -> CORS
                        |  | Rate Limiter    | |  <-- slowapi (10/min search, 30/min poll)
                        |  | Job Manager     | |  <-- asyncio tasks, polling API
                        |  | Multi-Source     | |
                        |  | Orchestrator    | |
                        |  | Filter Engine   | |  <-- Tiered keyword scoring
                        |  | LLM Summarizer  | |  <-- GPT-4.1-nano
                        |  | Excel Generator | |  <-- openpyxl
                        |  +-----------------+ |
                        +----+----------+------+
                             |          |
                    +--------+          +--------+
                    v                            v
             +------------+              +-------------+
             |   Redis    |              | External    |
             |  (Railway) |              | Data APIs   |
             +------------+              +-------------+
              - Job State                 - PNCP (active)
              - PNCP Cache               - Transparencia (active)
              - TTL: 4h cache            - ComprasGov (disabled)
              - TTL: 24h jobs            - Querido Diario (disabled)
                                         - TCE-RJ (disabled)
                                               |
                                               v
                                         +----------+
                                         | OpenAI   |
                                         | GPT-4.1  |
                                         | nano     |
                                         +----------+
```

### 2.2 Key Architectural Patterns

| Pattern | Implementation |
|---------|---------------|
| **BFF (Backend-for-Frontend)** | Next.js API Routes proxy all backend calls, hiding API keys from the browser |
| **Async Job Pattern** | POST /buscar creates a job, client polls /buscar/{id}/status every 2s |
| **Multi-Source Adapter** | Abstract `DataSourceClient` interface with per-source implementations |
| **Graceful Degradation** | Failed sources do not block others; partial results recovered on timeout |
| **Circuit Breaker** | AsyncPNCPClient pauses after 3 consecutive timeouts |
| **Adaptive Rate Limiting** | PNCP client adjusts request interval based on server response times |
| **Tiered Keyword Scoring** | Keywords categorized as A (1.0), B (0.7), C (0.3) with configurable threshold |
| **Composite-Key Dedup** | Cross-source deduplication using CNPJ+numero+ano hash with fallback keys |
| **Dual-Write Job Store** | Jobs written to both in-memory dict and Redis for persistence |

---

## 3. Backend Architecture

### 3.1 API Endpoints and Routes

| Method | Path | Rate Limit | Auth | Purpose |
|--------|------|-----------|------|---------|
| GET | `/` | None | No | Root info (name, version, endpoints) |
| GET | `/health` | None | No | Health check with Redis status |
| GET | `/docs` | None | No | Swagger UI |
| GET | `/redoc` | None | No | ReDoc |
| GET | `/openapi.json` | None | No | OpenAPI spec |
| GET | `/setores` | None | Yes | List available procurement sectors |
| POST | `/buscar` | 10/min | Yes | Create async search job |
| GET | `/buscar/{job_id}/status` | 30/min | Yes | Poll job status and progress |
| GET | `/buscar/{job_id}/result` | 5/min | Yes | Get completed job result (no Excel) |
| GET | `/buscar/{job_id}/download` | 10/min | Yes | Download Excel file (streaming) |
| GET | `/cache/stats` | None | Yes | Cache statistics (debug only) |
| POST | `/cache/clear` | None | Yes | Clear cache (debug only) |
| GET | `/debug/pncp-test` | None | Yes | PNCP connectivity test (debug only) |

Debug endpoints are gated behind `ENABLE_DEBUG_ENDPOINTS=true` environment variable.

### 3.2 Multi-Source Data Pipeline

The system uses an adapter pattern to normalize data from multiple Brazilian government APIs:

```
SearchQuery (dates, UFs, modalidades)
       |
       v
MultiSourceOrchestrator.search_all()
       |
       +---> PNCPSource.fetch_records()          [ACTIVE, priority 1]
       |         |
       |         +---> AsyncPNCPClient.fetch_all()
       |                   |
       |                   +---> fetch_page() x N  (semaphore=3 concurrent)
       |                   +---> _normalize_item()  (flatten nested JSON)
       |                   +---> dedup by numeroControlePNCP
       |
       +---> TransparenciaSource.fetch_records()  [ACTIVE, priority 3]
       |         |
       |         +---> API key auth (chave-api-dados header)
       |         +---> UF-to-IBGE code mapping
       |         +---> Paginated fetch (15 per page)
       |
       +---> ComprasGovSource.fetch_records()     [DISABLED - API deprecated]
       +---> QueridoDiarioSource.fetch_records()  [DISABLED - returns HTML]
       +---> TCERJSource.fetch_records()          [DISABLED - 404 endpoint]
       |
       v
Cross-Source Deduplication
       |
       +---> Primary key: MD5(cnpj + numero + ano)
       +---> Fallback key: MD5(objeto[:100] + uf + data_publicacao)
       +---> Source aggregation (merged sources list)
       +---> Field merging (fill gaps from lower-priority sources)
       |
       v
OrchestratorResult (records, stats, dedup_removed)
```

**Source Configuration** (from `config.py`):

| Source | Status | Base URL | Rate Limit | Timeout | Priority |
|--------|--------|----------|-----------|---------|----------|
| PNCP | Enabled | pncp.gov.br/api/consulta/v1 | 10 rps | 300s | 1 |
| ComprasGov | Disabled | dadosabertos.compras.gov.br | 5 rps | 60s | 2 |
| Transparencia | Enabled | api.portaldatransparencia.gov.br | 3 rps | 90s | 3 |
| Querido Diario | Disabled | queridodiario.ok.org.br/api | 5 rps | 60s | 4 |
| TCE-RJ | Disabled | dados.tcerj.tc.br | 3 rps | 90s | 5 |

### 3.3 PNCP Client Details (AsyncPNCPClient)

The `AsyncPNCPClient` (`clients/async_pncp_client.py`) is the most complex component, using fully async httpx:

- **HTTP client:** httpx.AsyncClient with connection pooling (max 10 connections, 5 keepalive)
- **Concurrency:** asyncio.Semaphore(3) limits parallel HTTP requests
- **Date chunking:** Splits ranges >30 days into 30-day chunks
- **Modalidade reduction:** When >10 UFs selected, reduces from 7 to 3 modalities (Pregao Eletronico covers ~80%)
- **Max pages cap:** 10 pages per UF x modalidade combo (500 items max per combo)
- **Dynamic page cap:** Further reduced when task count is high: `min(max_pages, max(2, 600 // len(tasks)))`
- **Circuit breaker:** Pauses 15-60s after 3+ consecutive timeouts
- **Adaptive rate limiting:** Base interval 0.3s, doubles on timeout/slow response, decays 20% on fast response; uses asyncio.Lock
- **429 handling:** Honors Retry-After header, logs high 429 ratio warnings (>20%)
- **User-Agent:** `Descomplicita/1.0`
- **Retry:** 2 retries with exponential backoff and jitter

### 3.4 Job Management (Async Processing)

Jobs flow through these states:

```
queued -> running -> completed
                  -> failed
```

Progress phases reported during execution:

```
queued -> fetching -> filtering -> summarizing -> generating_excel -> done
```

**In-Memory JobStore** (`job_store.py`):
- asyncio.Lock for concurrent access safety
- Max 10 concurrent active jobs
- TTL: 30 minutes for completed/failed jobs
- Periodic cleanup every 60 seconds via background asyncio task (launched in lifespan)

**RedisJobStore** (`stores/redis_job_store.py`):
- Extends in-memory JobStore (dual-write pattern)
- Redis TTL: 24 hours
- Fallback: reads from Redis if not in memory (survives restarts)
- Graceful degradation: logs warning on Redis failure, continues with in-memory

**Critical concern:** Excel bytes are stored in the job result dict, persisted both in Python memory and serialized to Redis. Large result sets can cause significant memory pressure.

### 3.5 Caching Strategy

**RedisCache** (`app_cache/redis_cache.py`):
- Cache key: `pncp_cache:{uf}:{modalidade}:{data_inicial}:{data_final}`
- TTL: 4 hours (DEFAULT_CACHE_TTL = 14400s)
- Graceful degradation: returns None on Redis failure
- Tracks hits/misses/ratio for observability
- Clear operation uses SCAN to find matching keys

### 3.6 Middleware Stack

Middleware is applied in reverse order of `app.add_middleware()` calls (last added = first executed):

1. **CorrelationIdMiddleware** (first to execute) -- Generates UUID per request via `ContextVar`, sets `X-Request-ID` response header, injects correlation_id into all log records via `CorrelationIdFilter`
2. **APIKeyMiddleware** -- Validates `X-API-Key` header against `API_KEY` env var; bypasses auth for public paths (`/health`, `/docs`, `/redoc`, `/openapi.json`) and OPTIONS preflight; **skips auth entirely if API_KEY env var is not set** (development mode)
3. **CORSMiddleware** -- Origins from `CORS_ORIGINS` env var (default: `https://descomplicita.vercel.app,http://localhost:3000`); allows GET and POST only; credentials enabled; allows all headers

### 3.7 Error Handling Patterns

- **Custom exception hierarchy:** `PNCPAPIError` -> `PNCPRateLimitError`, `PNCPTimeoutError`, `PNCPServerError`
- **Rate limit handler:** Returns 429 JSON response via slowapi `RateLimitExceeded` handler
- **Job-level error handling:** All exceptions caught in `run_search_job()`, stored as user-friendly Portuguese error message
- **LLM fallback:** If OpenAI API fails, `gerar_resumo_fallback()` generates statistical summary without AI
- **Partial result recovery:** On PNCP timeout, orchestrator recovers whatever was collected before the timeout via `get_partial_results()`
- **Sentry integration:** Optional, initialized from `SENTRY_DSN` env var with FastAPI and Starlette integrations; flushed on shutdown
- **SIGTERM handling:** Graceful shutdown handler registered via `loop.add_signal_handler` (not supported on Windows)

### 3.8 Sector Configuration

Six procurement sectors defined in `sectors.py`, each as a `SectorConfig` dataclass:

| Sector ID | Name | Value Range | Threshold |
|-----------|------|-------------|-----------|
| vestuario | Vestuario e Uniformes | R$10k - R$10M | 0.6 |
| alimentos | Alimentos e Nutricao | R$10k - R$10M | 0.6 |
| informatica | Informatica e Tecnologia | R$10k - R$10M | 0.6 |
| medicamentos | Medicamentos e Saude | R$10k - R$10M | 0.6 |
| mobiliario | Mobiliario e Equipamentos | R$10k - R$10M | 0.6 |
| material_escritorio | Material de Escritorio | R$10k - R$10M | 0.6 |

Each sector includes:
- `keywords`: Flat set of all keywords (backward compat)
- `keywords_a`: Tier A -- unambiguous terms (weight 1.0)
- `keywords_b`: Tier B -- strong terms (weight 0.7)
- `keywords_c`: Tier C -- ambiguous terms (weight 0.3)
- `exclusions`: Set of exclusion keywords checked first (fail-fast)
- `search_keywords`: High-precision terms for PNCP server-side filtering
- `threshold`: Minimum score to approve (default 0.6)

### 3.9 Dependency Injection

The application uses module-level global singletons in `dependencies.py`:

```python
_redis = None
_job_store = None
_pncp_client = None
_pncp_source = None
_orchestrator = None
_redis_cache = None
```

Initialized in `init_dependencies()` (called from lifespan startup), cleaned up in `shutdown_dependencies()`. FastAPI `Depends()` functions expose each:

- `get_job_store()` -> JobStore or RedisJobStore
- `get_orchestrator()` -> MultiSourceOrchestrator
- `get_pncp_source()` -> PNCPSource
- `get_redis()` -> Redis client or None
- `get_redis_cache()` -> RedisCache or None

---

## 4. Frontend Architecture

### 4.1 Page Structure and Routing

The frontend is a single-page application using Next.js 16 App Router:

```
frontend/
  app/
    layout.tsx           -- Root layout (fonts, theme, analytics providers)
    page.tsx             -- Main search page (SPA, "use client")
    error.tsx            -- Error boundary
    globals.css          -- Tailwind CSS + custom design tokens
    icon.svg             -- Favicon
    api/
      buscar/
        route.ts         -- POST proxy to backend /buscar
        status/
          route.ts       -- GET proxy to backend /buscar/{id}/status
        result/
          route.ts       -- GET proxy to backend /buscar/{id}/result
      setores/
        route.ts         -- GET proxy to backend /setores
      download/
        route.ts         -- GET proxy to backend /buscar/{id}/download
    components/          -- 15 UI components
    hooks/               -- 3 page-level hooks
    constants/
      ufs.ts             -- Brazilian state definitions
    types.ts             -- TypeScript type definitions
  hooks/
    useAnalytics.ts      -- Mixpanel event tracking
    useSavedSearches.ts  -- LocalStorage saved searches
  lib/
    savedSearches.ts     -- Saved search persistence
```

### 4.2 Component Hierarchy

```
RootLayout (server component)
  +-- AnalyticsProvider (Mixpanel)
  +-- ThemeProvider
        +-- HomePage (client component, "use client")
              +-- SearchHeader
              |     +-- SavedSearchesDropdown
              +-- SearchForm (sector/terms toggle)
              +-- UfSelector (27 states + region groups)
              +-- DateRangeSelector
              +-- [Button: Buscar]
              +-- LoadingProgress* (dynamic import, shown during search)
              +-- EmptyState* (dynamic import, shown when 0 results)
              +-- SearchSummary (AI summary display)
              +-- SearchActions (download Excel, save search)
              +-- SaveSearchDialog* (dynamic import, modal)
              +-- SourceBadges (multi-source status)

* = dynamically imported for code splitting
```

### 4.3 State Management

No external state management library. State is managed through custom React hooks:

1. **`useSearchForm`** -- Form state: selected UFs, dates, sector, search mode (setor/termos), terms, validation
2. **`useSearchJob`** -- Job lifecycle: loading, polling, result, download, progress phases, cancellation, browser notifications
3. **`useSaveDialog`** -- Save search dialog state (name, errors)
4. **`useSavedSearches`** -- Saved searches in localStorage (max capacity enforced)
5. **`useAnalytics`** -- Mixpanel event tracking wrapper

### 4.4 API Integration Patterns

The frontend uses a **Backend-for-Frontend (BFF)** pattern:

1. Browser calls Next.js API Routes (e.g., `POST /api/buscar`)
2. API Route adds `X-API-Key` header from server env `BACKEND_API_KEY`
3. API Route proxies request to FastAPI backend at `BACKEND_URL`
4. Response is forwarded back to browser

This pattern keeps the API key server-side only. All 5 API routes follow this pattern.

**Polling mechanism** (`useSearchJob.ts`):
- Interval: 2 seconds (`POLL_INTERVAL = 2000`)
- Timeout: 10 minutes (`POLL_TIMEOUT = 10 * 60 * 1000`)
- Updates: phase, progress counters, elapsed time
- Cancellation: user can abort via cancel button (stops polling, fires analytics event)
- Completion notification: Browser Notification API + document title change when tab is backgrounded

**Download flow:**
- Frontend calls `GET /api/download?id={job_id}`
- API route proxies to `GET /buscar/{job_id}/download` on backend
- Backend streams Excel bytes
- API route buffers into `ArrayBuffer` and returns as attachment
- Client creates Blob URL and triggers download with descriptive filename

### 4.5 Theming and Accessibility

- **5 themes:** light, paperwhite, sepia, dim, dark
- **Theme persistence:** localStorage (`descomplicita-theme`)
- **Flash prevention:** Inline `<script>` in layout applies theme before React hydration
- **Skip-to-content link:** "Pular para o conteudo principal" for keyboard navigation
- **ARIA live regions:** Search result announcements for screen readers
- **Focus management:** Results heading receives focus after search completes
- **Language:** `lang="pt-BR"` on html element

---

## 5. Data Flow

### 5.1 End-to-End Search Request Flow

```
1. User selects UFs, dates, sector -> clicks "Buscar"

2. Browser: POST /api/buscar { ufs, data_inicial, data_final, setor_id }

3. Next.js API Route: validates, adds X-API-Key, proxies to backend

4. FastAPI POST /buscar:
   - Validates BuscaRequest (Pydantic schema)
   - Checks job store capacity (max 10 active jobs -> 429 if full)
   - Creates job (UUID), returns { job_id, status: "queued" }
   - Launches asyncio.create_task(run_search_job())

5. Background task pipeline (run_search_job):

   a. VALIDATE SECTOR
      - get_sector(setor_id) -> SectorConfig
      - Resolve active keywords (custom terms override sector keywords)

   b. PHASE "fetching"
      - orchestrator.search_all(query, on_progress)
      - Parallel fetch from enabled sources (PNCP + Transparencia)
      - Each source has independent timeout and rate limiting
      - PNCP: semaphore(3), date chunking, modalidade x UF matrix
      - On timeout: recover partial results via get_partial_results()
      - Cross-source deduplication (composite key hash)

   c. PHASE "filtering"
      - filter_batch() run in ThreadPoolExecutor
      - Pipeline: UF check -> Value range -> Keyword scoring -> (Deadline disabled)
      - Tiered scoring: A=1.0, B=0.7, C=0.3, threshold=0.6
      - Exclusion keywords checked first (fail-fast)
      - Returns approved list + rejection stats by category

   d. PHASE "summarizing" + "generating_excel" (parallel)
      - gerar_resumo() via run_in_executor -> GPT-4.1-nano structured output
        (On failure: gerar_resumo_fallback() -> pure Python statistical summary)
      - create_excel() via run_in_executor -> openpyxl BytesIO
      - LLM-generated counts overridden with actual computed values
      - Both run via asyncio.gather for parallelism

   e. PHASE "done"
      - job_store.complete(job_id, result) -- stores in memory + Redis

6. Browser polls GET /api/buscar/status every 2s
   - Gets phase, progress counters, elapsed time
   - On "completed": fetches GET /api/buscar/result
   - Renders summary, stats, source badges, download button

7. User clicks "Download Excel"
   - GET /api/download?id={job_id} -> proxied to backend
   - Backend streams Excel bytes as attachment
```

---

## 6. Infrastructure and Deployment

### 6.1 Railway (Backend)

- **Service:** FastAPI Python application in Docker container
- **Startup:** `python start.py` -> uvicorn on `0.0.0.0:$PORT`
- **Start script:** `start.py` includes crash diagnostics (prints Python version, PORT, CWD before importing app)
- **Redis:** Railway-managed Redis instance, connected via `REDIS_URL`
- **Config:** `railway.toml` describes monorepo setup with instructions for creating 2 services
- **Key environment variables:** OPENAI_API_KEY, REDIS_URL, API_KEY, CORS_ORIGINS, LOG_LEVEL, SENTRY_DSN, TRANSPARENCIA_API_KEY, ENABLED_SOURCES

### 6.2 Vercel (Frontend)

- **Framework:** Next.js 16
- **Build command:** `cd frontend && npm run build`
- **Output directory:** `frontend/.next`
- **Region:** iad1 (US East)
- **Config file:** `vercel.json`
- **Security headers:** X-Content-Type-Options: nosniff, X-Frame-Options: DENY, X-XSS-Protection: 1; mode=block
- **Serverless functions:** API routes with 1024MB memory, 10s max duration
- **Environment:** NEXT_PUBLIC_BACKEND_URL (via Vercel secret @backend-url), BACKEND_API_KEY, NEXT_PUBLIC_MIXPANEL_TOKEN, NEXT_PUBLIC_SENTRY_DSN

### 6.3 Docker Compose (Local Development)

Three services:

1. **redis** -- Redis 7 Alpine, healthcheck (ping every 10s), persistent volume (`redis_data`)
2. **backend** -- FastAPI with volume mount for hot-reload, depends on Redis (service_healthy), env vars for PNCP/LLM config
3. **frontend** -- Next.js (Dockerfile reference, port 3000), depends on backend (service_healthy)

Network: `descomplicita-network` (bridge driver)

### 6.4 Environment Variables Summary

| Variable | Required | Default | Service | Purpose |
|----------|---------|---------|---------|---------|
| OPENAI_API_KEY | Yes | -- | Backend | LLM summary generation |
| REDIS_URL | No | redis://localhost:6379/0 | Backend | Redis connection (fallback to in-memory) |
| API_KEY | No | (none) | Backend | API key auth (skipped if unset) |
| CORS_ORIGINS | No | Vercel + localhost | Backend | Allowed CORS origins |
| LOG_LEVEL | No | INFO | Backend | Logging level |
| SENTRY_DSN | No | -- | Backend | Sentry error tracking |
| SENTRY_TRACES_SAMPLE_RATE | No | 0.1 | Backend | Sentry trace sampling |
| TRANSPARENCIA_API_KEY | No | -- | Backend | Portal da Transparencia auth |
| ENABLED_SOURCES | No | config-based | Backend | Override enabled sources |
| ENABLE_DEBUG_ENDPOINTS | No | false | Backend | Enable /cache/* and /debug/* |
| MAX_DATE_RANGE_DAYS | No | 90 | Backend | Max search date range |
| MAX_DOWNLOAD_SIZE | No | 50MB | Backend | Max Excel download size |
| PNCP_BASE_URL | No | pncp.gov.br/... | Backend | PNCP API base URL |
| BACKEND_URL | Yes | http://localhost:8000 | Frontend | Backend API URL |
| BACKEND_API_KEY | Yes | -- | Frontend | API key for backend auth |
| NEXT_PUBLIC_MIXPANEL_TOKEN | No | -- | Frontend | Mixpanel analytics |
| NEXT_PUBLIC_SENTRY_DSN | No | -- | Frontend | Sentry error tracking |
| DOWNLOAD_TTL_MS | No | 3600000 | Frontend | Download file TTL |

---

## 7. Security Analysis

### 7.1 Authentication / Authorization

- **API Key Auth:** Single shared API key via `X-API-Key` header, validated by `APIKeyMiddleware`. No per-user auth, no JWT, no session management, no RBAC.
- **Development bypass:** If `API_KEY` env var is unset, **all requests are unauthenticated**. This is a deliberate dev-mode feature but a significant risk if deployed without the key configured.
- **Public paths:** `/health`, `/docs`, `/redoc`, `/openapi.json` bypass auth entirely. The root `/` endpoint also bypasses (not listed in PUBLIC_PATHS but included in general auth skip logic).
- **BFF proxy:** Frontend API routes inject the API key server-side via `BACKEND_API_KEY`, keeping it out of browser code.

### 7.2 API Key Management

- Backend API key: Railway env vars (single key for all clients)
- Frontend API key: Vercel env vars (`BACKEND_API_KEY`, server-side only, not prefixed with `NEXT_PUBLIC_`)
- OpenAI API key: Railway env vars
- Transparencia API key: Railway env vars
- No key rotation mechanism
- No per-user or per-client key differentiation
- `.env.example` files provided with empty values for all keys

### 7.3 Rate Limiting

- **slowapi** rate limiter on key endpoints (based on remote IP via `get_remote_address`)
- POST `/buscar`: 10 requests/minute
- GET `/buscar/{id}/status`: 30 requests/minute
- GET `/buscar/{id}/result`: 5 requests/minute
- GET `/buscar/{id}/download`: 10 requests/minute
- **Job capacity limit:** Max 10 concurrent active jobs (returns 429 with Portuguese message)
- **PNCP adaptive rate limiting:** Client-side throttle based on response times (0.3s to 2s)

### 7.4 CORS Configuration

- Configurable via `CORS_ORIGINS` env var (comma-separated)
- Default origins: `https://descomplicita.vercel.app,http://localhost:3000`
- Allowed methods: GET, POST only
- Allow credentials: true
- Allow headers: `*` (**overly permissive** -- should whitelist specific headers)

### 7.5 Security Headers (Frontend)

Via `vercel.json`:
- `X-Content-Type-Options: nosniff` -- prevents MIME sniffing
- `X-Frame-Options: DENY` -- prevents clickjacking
- `X-XSS-Protection: 1; mode=block` -- legacy XSS protection

**Missing headers:**
- `Content-Security-Policy` -- no CSP configured
- `Strict-Transport-Security` -- no HSTS header
- `Referrer-Policy` -- not set
- `Permissions-Policy` -- not set

### 7.6 Input Validation

- Pydantic model validation on all POST request bodies
- Date format regex validation (`^\d{4}-\d{2}-\d{2}$`)
- Date range cap: MAX_DATE_RANGE_DAYS = 90 days
- `data_inicial` must be <= `data_final`
- UF list must have at least 1 entry (`min_length=1`)
- Custom search terms: `max_length=500`
- Download size cap: MAX_DOWNLOAD_SIZE = 50MB

---

## 8. Test Coverage Analysis

### 8.1 Backend Test Coverage

**33 test files** in `backend/tests/`:

| Category | Files | Coverage |
|----------|-------|----------|
| Core modules | test_main.py, test_schemas.py, test_config.py | API endpoints, schemas, config |
| Filter engine | test_filter.py, test_filter_normalized.py | Keyword matching, tiered scoring |
| Data sources | test_pncp_source.py, test_pncp_client.py, test_comprasgov_source.py, test_transparencia_source.py, test_querido_diario_source.py, test_tce_rj_source.py, test_sources_base.py, test_sources_config.py | All 5 source adapters |
| Orchestrator | test_orchestrator.py | Multi-source search, dedup |
| Job management | test_job_store.py, test_redis_job_store.py | In-memory and Redis stores |
| LLM | test_llm.py, test_llm_fallback.py | GPT integration + fallback |
| Excel | test_excel.py | Excel generation |
| Sectors | test_sectors.py | Sector configuration |
| Infrastructure | test_dependencies.py, test_cache.py, test_cache_integration.py | DI, caching |
| Non-functional | test_security.py, test_concurrency.py, test_resilience.py, test_load.py | Security, concurrency, resilience, load |
| Integration | test_pncp_integration.py | PNCP API integration |
| Observability | test_story5_observability.py | Logging, correlation IDs |
| Helpers | mock_helpers.py, conftest.py, test_placeholder.py | Test infrastructure |

**Assessment:** Backend test coverage is comprehensive. Every major module has corresponding tests. Notable presence of non-functional tests (security, concurrency, resilience, load). The `conftest.py` file provides shared fixtures.

### 8.2 Frontend Test Coverage

**22 test files** in `frontend/__tests__/` (excluding node_modules):

| Category | Files | Coverage |
|----------|-------|----------|
| Page tests | page.test.tsx, error.test.tsx | Main page, error boundary |
| Component tests | EmptyState, LoadingProgress, DateRangeSelector, SaveSearchDialog, SearchActions, SearchForm, SearchHeader, SearchSummary, UfSelector, ThemeToggle, SavedSearchesDropdown | 11 component tests |
| Accessibility | accessibility.test.tsx | Accessibility audit |
| API Route tests | buscar.test.ts, buscar-status.test.ts, buscar-result.test.ts, download.test.ts | All 4 API routes |
| Hook tests | useSearchForm.test.ts, useSearchJob.test.ts | 2 core hooks |
| Utility tests | analytics.test.ts, savedSearches.test.ts, setup.test.ts | Analytics, storage, setup |
| E2E tests | 01-happy-path.spec.ts, 02-llm-fallback.spec.ts, 03-validation-errors.spec.ts, 04-error-handling.spec.ts | 4 Playwright specs |

**Assessment:** Frontend test coverage is strong. All components, hooks, and API routes have unit tests. E2E tests cover happy path, fallback, validation, and error handling. Accessibility tests are present. Testing Library + Jest for unit tests; Playwright for E2E.

### 8.3 Test Coverage Gaps

1. **No integration tests between frontend and backend** -- E2E tests likely mock the backend API
2. **No load/stress tests for the frontend** -- Only backend has load tests
3. **No contract tests** -- No schema validation between frontend TypeScript types and backend Pydantic schemas
4. **No dedicated middleware tests** -- Auth and correlation ID middleware tested indirectly via `test_main.py`
5. **No smoke test for production** -- No post-deploy verification suite
6. **No visual regression tests** -- No screenshot comparison for UI components
7. **Missing tests for some components** -- RegionSelector, SourceBadges, AnalyticsProvider, carouselData have no dedicated tests

---

## 9. Technical Debt Inventory

### Critical Severity

| ID | Description | Impact | Effort |
|----|------------|--------|--------|
| TD-C01 | **Excel bytes stored in job result (memory + Redis)** -- Completed jobs store raw Excel bytes in both Python dict and serialized to Redis as JSON. A job with 500 bids can produce multi-MB data duplicated across two stores. No streaming or temporary file storage. | Memory exhaustion under concurrent load, Redis memory pressure | Medium |
| TD-C02 | **No user authentication** -- Single shared API key for all clients. No user identity, no authorization model, no audit trail. If API_KEY is unset, all endpoints are fully open. | Security exposure, no accountability | High |
| TD-C03 | **3 of 5 data sources disabled** -- ComprasGov (API deprecated), Querido Diario (returns HTML), TCE-RJ (404). The multi-source architecture is underutilized; effectively a dual-source system. Dead code remains in codebase. | Reduced data coverage, maintenance burden for dead code | High |

### High Severity

| ID | Description | Impact | Effort |
|----|------------|--------|--------|
| TD-H01 | **In-memory job store as primary** -- RedisJobStore extends in-memory JobStore in a dual-write pattern. On process restart, in-memory state is lost. Redis serves as fallback for reads but the dual-write adds complexity and potential inconsistency. | Job data loss on restart during active searches | Medium |
| TD-H02 | **asyncio.create_task for background jobs** -- Jobs run as untracked asyncio tasks in the same process. No task queue (Celery, RQ). On server shutdown or deploy, running jobs are silently lost. SIGTERM handler exists but only sets an event that nothing awaits. | Job loss on deploy/restart | High |
| TD-H03 | **OpenAI API called synchronously in thread pool** -- `gerar_resumo()` uses synchronous OpenAI client wrapped in `loop.run_in_executor(None, ...)`, blocking a default thread pool thread. Should use async OpenAI client. | Thread pool exhaustion under concurrent searches | Medium |
| TD-H04 | **No database** -- All state is ephemeral. No historical search data, no analytics persistence, no user preferences server-side. Limits product evolution. | Cannot build features requiring persistence | High |
| TD-H05 | **CORS allow_headers=* is overly permissive** -- Accepts any header. Should whitelist Content-Type, X-API-Key, X-Request-ID. | Minor security risk, non-standard practice | Low |
| TD-H06 | **Vercel serverless functions have 10s max duration** -- The download API route buffers the entire Excel file (`response.arrayBuffer()`) before returning. Large files may exceed the 10s limit or 1024MB memory limit. | Download failures for large files | Medium |

### Medium Severity

| ID | Description | Impact | Effort |
|----|------------|--------|--------|
| TD-M01 | **Deadline filter disabled** -- The `dataAberturaProposta` field was misinterpreted as submission deadline. Filter is commented out with TODO. No alternative deadline check exists. | Users see irrelevant historical bids | Medium |
| TD-M02 | **No pagination on results** -- All filtered results returned in a single response. Large result sets affect response time and memory. | Performance degradation with many results | Medium |
| TD-M03 | **Hardcoded LLM model** -- `gpt-4.1-nano` hardcoded in `llm.py` line 131. Docker-compose exposes `LLM_MODEL` env var but the code ignores it. | Cannot switch models without code change | Low |
| TD-M04 | **No request timeout for LLM calls** -- OpenAI client uses default timeout. Long LLM responses can block the thread pool worker indefinitely. | Thread starvation | Low |
| TD-M05 | **Global mutable state for DI** -- `dependencies.py` uses module-level globals with no DI framework. Testing requires careful patching. | Testing complexity, hidden coupling | Medium |
| TD-M06 | **No API versioning** -- Endpoints are unversioned (`/buscar` not `/v1/buscar`). Breaking changes affect all clients simultaneously. | Difficult API evolution | Medium |
| TD-M07 | **No Content-Security-Policy header** -- Missing CSP in Vercel config. | XSS mitigation gap | Low |
| TD-M08 | **No Strict-Transport-Security header** -- Missing HSTS in Vercel config. | Protocol downgrade risk | Low |
| TD-M09 | **MD5 used for dedup keys** -- `orchestrator.py` uses MD5 for composite key hashing. While collision risk is negligible for this use case, it is a weak hash by modern standards. | Theoretical collision risk | Low |
| TD-M10 | **Frontend dangerouslySetInnerHTML for theme** -- Inline script in `layout.tsx` to prevent theme flash. While currently safe (no user input), it bypasses React's XSS protection. | Potential XSS vector if modified | Low |
| TD-M11 | **Version hardcoded in multiple places** -- "0.3.0" appears in `main.py` app definition and root endpoint response. No single source of truth. | Version drift risk | Low |

### Low Severity

| ID | Description | Impact | Effort |
|----|------------|--------|--------|
| TD-L01 | **is_healthy() uses synchronous httpx** -- `ComprasGovSource.is_healthy()` and `TransparenciaSource.is_healthy()` make synchronous HTTP calls, which would block the event loop if called from async context. Currently only used in tests. | Blocking call in async context if used | Low |
| TD-L02 | **No structured error codes** -- Error responses use free-text Portuguese messages. No machine-readable error codes for client-side handling. | Client error handling is fragile | Low |
| TD-L03 | **Saved searches in localStorage only** -- No server-side persistence. Lost on browser clear. No cross-device sync. | Data loss, no cross-device | Low |
| TD-L04 | **test_placeholder.py exists** -- Empty test file committed as scaffolding. | Minor code hygiene | Low |
| TD-L05 | **Large keyword/exclusion sets** -- Vestuario sector has ~130 inclusion and ~100 exclusion keywords matched via regex. CPU cost mitigated by fail-fast filter ordering. | Performance concern at scale | Low |
| TD-L06 | **filter_batch runs in default ThreadPoolExecutor** -- Uses `loop.run_in_executor(None, ...)` which shares the default executor with LLM calls. Contention possible. | Resource contention under load | Low |

---

## 10. Architectural Decisions Record (ADR)

### ADR-001: Stateless API with Redis for Ephemeral State

**Context:** POC needed quick deployment without database setup.
**Decision:** No persistent database. Redis used only for job state (24h TTL) and PNCP response cache (4h TTL). In-memory fallback when Redis is unavailable.
**Consequences:** Cannot persist search history, user preferences, or analytics. Simplifies deployment. Limits features requiring historical data.

### ADR-002: Async Job Pattern over Synchronous Responses

**Context:** PNCP API can take 30-300 seconds to return results across multiple UFs and modalities.
**Decision:** POST /buscar returns immediately with a job_id. Client polls status every 2 seconds. Job runs as asyncio background task.
**Consequences:** Better UX (real-time progress). More complex implementation. Requires job state management. Jobs are not durable.

### ADR-003: BFF Pattern via Next.js API Routes

**Context:** Backend API key must not be exposed to the browser.
**Decision:** All backend calls proxied through Next.js server-side API Routes that inject the API key.
**Consequences:** API key stays server-side. Adds latency (extra network hop). Vercel serverless function limits apply (10s timeout, 1024MB memory).

### ADR-004: Multi-Source Adapter Architecture

**Context:** Brazil has multiple open government data portals with different APIs.
**Decision:** Abstract `DataSourceClient` interface with source-specific adapters. `MultiSourceOrchestrator` runs them in parallel with independent timeouts and graceful degradation.
**Consequences:** Easy to add new sources. Complex deduplication logic. Currently 3/5 sources are disabled, adding dead code burden.

### ADR-005: OpenAI GPT-4.1-nano for Summaries with Python Fallback

**Context:** Executive summaries add user value but LLM APIs can fail.
**Decision:** Primary: OpenAI GPT-4.1-nano with structured output (Pydantic schema enforcement). Fallback: Python statistical summary (top bids by value, UF distribution, urgency detection).
**Consequences:** Graceful degradation. OpenAI cost per search (~$0.001). Fallback summaries are less informative but always available. LLM counts are overridden by actual computed values for accuracy.

### ADR-006: Tiered Keyword Scoring over Binary Matching

**Context:** Single-keyword matching produced too many false positives (ambiguous terms like "camisa", "bota", "meia") and false negatives (missing partial matches).
**Decision:** Keywords categorized into three tiers with weighted scoring. Score = max(weight of matched tiers). Approval requires score >= threshold (0.6).
**Consequences:** Better precision. More complex configuration per sector. Requires ongoing tuning. Exclusion lists prevent false positives from ambiguous terms.

### ADR-007: Excel as Primary Export Format

**Context:** Target users (procurement teams) prefer spreadsheets for analysis and distribution.
**Decision:** Generate Excel files server-side using openpyxl with professional formatting (headers, currency, hyperlinks, totals, metadata tab).
**Consequences:** Natural fit for the audience. Files stored in memory/Redis. No web-based results table for quick scanning.

### ADR-008: Dual-Write Job Store (In-Memory + Redis)

**Context:** Need job persistence across restarts without abandoning simple in-memory store.
**Decision:** `RedisJobStore` extends `JobStore`, writing to both in-memory dict and Redis. Reads check in-memory first, fall back to Redis.
**Consequences:** Jobs survive restarts via Redis. Adds dual-write complexity. Potential inconsistency if Redis write fails silently (logged as warning).

### ADR-009: PNCP Client Migration from requests to httpx

**Context:** Original PNCP client used synchronous `requests` library wrapped in `run_in_executor`, tying up thread pool threads.
**Decision:** Migrated to `AsyncPNCPClient` using `httpx.AsyncClient` with native asyncio support, connection pooling, and semaphore-based concurrency control.
**Consequences:** Better resource utilization. No thread pool threads consumed by HTTP I/O. Circuit breaker and adaptive rate limiting use `asyncio.Lock` instead of `threading.Lock`.

---

## 11. Risk Assessment

### 11.1 Technical Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| PNCP API changes or goes down | Medium | Critical | Circuit breaker, timeout handling, partial result recovery, Transparencia as secondary source |
| Redis unavailable | Low | Medium | In-memory fallback for both job store and cache; application continues functioning |
| OpenAI API failure | Medium | Low | Deterministic fallback summary generator |
| Memory exhaustion from large Excel files | Medium | High | MAX_DOWNLOAD_SIZE cap (50MB), max 10 concurrent jobs; but no per-job memory limit |
| Job loss on deploy/restart | High | Medium | Redis recovery for completed jobs; no mitigation for in-progress jobs |
| Thread pool exhaustion from concurrent LLM calls | Low | Medium | Max 10 concurrent jobs limits exposure; but default thread pool shared with filter_batch |
| Vercel function timeout on large downloads | Medium | Medium | No current mitigation; files buffered fully in memory |

### 11.2 Operational Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| No monitoring dashboards | High | Medium | Sentry for errors, Mixpanel for product analytics; no infrastructure metrics |
| No automated deployment verification | High | Low | Health endpoint exists; no smoke test suite |
| No backup/disaster recovery | High | Low | Stateless architecture reduces DR need; Redis data is ephemeral |
| Cost overrun from OpenAI API | Low | Low | GPT-4.1-nano is cheap; 50 bids max, 500 max_tokens per call |
| Railway/Vercel platform outage | Low | High | No multi-region or failover strategy; single point of failure |
| Disabled data sources permanently broken | Medium | Medium | Dead code remains; 3/5 sources deprecated upstream; architecture supports it but reality has diverged |

### 11.3 Security Risks

| Risk | Likelihood | Impact | Current Mitigation |
|------|-----------|--------|-------------------|
| API key leakage | Low | High | BFF pattern keeps key server-side; no key rotation mechanism |
| Unauthorized access if API_KEY unset | Medium | Medium | Dev-mode bypass is deliberate; risk if misconfigured in production |
| DDoS via job exhaustion | Medium | Medium | Rate limiting (10/min), job capacity limit (10); but same IP can create all 10 |
| Missing CSP header enables XSS | Low | Medium | No user-generated content currently displayed as HTML |
| CORS allow_headers=* | Low | Low | Limited to GET/POST methods; credentials enabled |
| Sentry DSN in client bundle | Low | Low | Only if NEXT_PUBLIC_SENTRY_DSN is set; Sentry DSNs are semi-public by design |
| No HSTS enforcement | Low | Low | Vercel/Railway provide HTTPS; but no explicit HSTS header |

---

## Appendix A: File Map

```
backend/
  main.py                          -- FastAPI app, routes, middleware, job runner (703 lines)
  config.py                        -- Configuration, modalities, source config, logging
  schemas.py                       -- Pydantic request/response models (253 lines)
  filter.py                        -- Keyword matching engine, batch filtering (606 lines)
  llm.py                           -- OpenAI GPT integration + fallback (327 lines)
  sectors.py                       -- Multi-sector keyword definitions (large, 6 sectors)
  dependencies.py                  -- Dependency injection (global state, 126 lines)
  exceptions.py                    -- Custom exception hierarchy (26 lines)
  excel.py                         -- Excel report generator (226 lines)
  job_store.py                     -- In-memory async job store (155 lines)
  start.py                         -- Railway startup with crash diagnostics (33 lines)
  clients/
    async_pncp_client.py           -- httpx async client for PNCP API (471 lines)
  sources/
    base.py                        -- Abstract DataSourceClient + NormalizedRecord (121 lines)
    pncp_source.py                 -- PNCP adapter (155 lines)
    comprasgov_source.py           -- ComprasGov adapter (disabled, 360 lines)
    transparencia_source.py        -- Transparencia adapter (379 lines)
    querido_diario_source.py       -- Querido Diario adapter (disabled)
    tce_rj_source.py               -- TCE-RJ adapter (disabled)
    orchestrator.py                -- Multi-source orchestrator + dedup (425 lines)
  stores/
    redis_job_store.py             -- Redis-backed job store (134 lines)
  app_cache/
    redis_cache.py                 -- Redis-backed PNCP response cache (100 lines)
  middleware/
    auth.py                        -- API key authentication (52 lines)
    correlation_id.py              -- Request tracing (31 lines)
  tests/                           -- 33 test files

frontend/
  app/
    page.tsx                       -- Main SPA page (185 lines)
    layout.tsx                     -- Root layout with theme/analytics (81 lines)
    error.tsx                      -- Error boundary
    types.ts                       -- TypeScript types (109 lines)
    globals.css                    -- Tailwind + design tokens
    api/                           -- 5 BFF proxy routes
      buscar/route.ts              -- POST /api/buscar (65 lines)
      buscar/status/route.ts       -- GET /api/buscar/status
      buscar/result/route.ts       -- GET /api/buscar/result
      download/route.ts            -- GET /api/download (62 lines)
      setores/route.ts             -- GET /api/setores
    components/                    -- 15 UI components
    hooks/                         -- 3 page-level hooks
      useSearchJob.ts              -- Job lifecycle (364 lines)
      useSearchForm.ts             -- Form state management
      useSaveDialog.ts             -- Save dialog state
    constants/
      ufs.ts                       -- Brazilian state definitions
  hooks/
    useAnalytics.ts                -- Mixpanel wrapper
    useSavedSearches.ts            -- localStorage persistence
  lib/
    savedSearches.ts               -- Saved search utilities
  __tests__/                       -- 22 test files + 4 E2E specs

Infrastructure:
  docker-compose.yml               -- Local dev (Redis + backend + frontend)
  railway.toml                     -- Railway monorepo config
  vercel.json                      -- Vercel deployment config
  .env.example                     -- Root env template
  backend/.env.example             -- Backend env template
  frontend/.env.example            -- Frontend env template
```

---

*Document generated: 2026-03-09*
*Supersedes: system-architecture.md v2.0 (2026-03-07)*
