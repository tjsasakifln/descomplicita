# System Architecture -- Descomplicita

**Project:** Descomplicita (formerly Descomplicita)
**Date:** March 2026
**Version:** 2.0
**Author:** @architect (Atlas)
**Status:** POC Complete, Multi-Sector Expansion Underway

---

## 1. Executive Summary

Descomplicita is a Brazilian government procurement search and analysis platform. It ingests bid data from multiple official sources (primarily PNCP -- Portal Nacional de Contratacoes Publicas), applies sector-specific keyword filtering, generates AI-powered executive summaries via GPT-4.1-nano, and produces formatted Excel reports for download.

The system operates as a stateless, async-job-based web application with a Next.js 16 frontend proxying requests to a FastAPI backend. It has no persistent database -- all job state is held in-memory with TTL-based expiration. The platform currently supports 6 procurement sectors (vestuario, alimentos, informatica, medicamentos, engenharia, limpeza) with a tier-based keyword scoring system.

**Current state:** POC complete (34/34 issues), deployed to Railway (backend) and Vercel (frontend). 99.2% backend test coverage, 91.5% frontend test coverage. Two data sources actively enabled (PNCP, Transparencia), three disabled due to upstream API deprecation.

---

## 2. System Overview

### 2.1 Purpose and Business Context

Brazilian public procurement is governed by the PNCP portal, which publishes all government bids. Companies supplying uniforms, food, IT equipment, medicines, and other goods need to monitor thousands of bids across 27 states daily. Descomplicita automates this discovery process by:

1. Fetching raw procurement data from multiple government APIs
2. Filtering results using sector-specific keyword matching with exclusion rules
3. Generating an AI executive summary highlighting key opportunities
4. Producing a professionally formatted Excel report for download

### 2.2 Key Features

- **Multi-state search** across all 27 Brazilian UFs (states)
- **Multi-source data orchestration** with parallel fetch, deduplication, and graceful degradation
- **6 procurement sectors** with tiered keyword scoring (A/B/C tiers with weighted confidence)
- **Custom search terms** that override sector keywords
- **Async job pipeline** with real-time phase-based progress polling
- **AI executive summary** via GPT-4.1-nano with deterministic fallback
- **Excel report generation** with hyperlinks, currency formatting, and metadata
- **Circuit breaker and adaptive rate limiting** for PNCP API resilience
- **In-memory LRU cache** (4h TTL, 500 entries) for PNCP responses
- **Dark mode and theme support** (5 themes: light, paperwhite, sepia, dim, dark)
- **Saved searches** with localStorage persistence
- **Mixpanel analytics** for search and loading behavior tracking

### 2.3 Current Maturity Level

**POC (Proof of Concept)** -- feature-complete and deployed, but lacking:
- Persistent database (no user accounts, no search history beyond browser localStorage)
- Authentication/authorization
- Horizontal scaling (single-process, in-memory job store)
- Production-grade CORS (currently `allow_origins=["*"]`)

---

## 3. Architecture Diagram

```
                        +---------------------------+
                        |       User Browser        |
                        +---------------------------+
                                    |
                                    | HTTPS
                                    v
                    +-------------------------------+
                    |   Vercel (CDN + Edge)          |
                    |   Next.js 16 Frontend          |
                    |   +-------------------------+ |
                    |   | App Router (app/)        | |
                    |   |  page.tsx (SPA)          | |
                    |   |  components/             | |
                    |   |  api/ (Route Handlers)   | |
                    |   +-------------------------+ |
                    +-------------------------------+
                                    |
                        API Routes proxy to backend
                        POST /api/buscar -> POST /buscar
                        GET /api/buscar/status -> GET /buscar/{id}/status
                        GET /api/buscar/result -> GET /buscar/{id}/result
                        GET /api/download -> filesystem read
                        GET /api/setores -> GET /setores
                                    |
                                    v
                    +-------------------------------+
                    |   Railway (Container)          |
                    |   FastAPI Backend              |
                    |   +-------------------------+ |
                    |   | main.py                  | |
                    |   |   /buscar (POST)         | |
                    |   |   /buscar/{id}/status    | |
                    |   |   /buscar/{id}/result    | |
                    |   |   /setores (GET)         | |
                    |   |   /health (GET)          | |
                    |   +-------------------------+ |
                    |   | JobStore (in-memory)     | |
                    |   | MultiSourceOrchestrator  | |
                    |   +-------------------------+ |
                    +-------------------------------+
                          |         |         |
               +----------+---------+---------+----------+
               |                    |                     |
               v                    v                     v
    +------------------+  +------------------+  +------------------+
    | PNCP API         |  | Transparencia    |  | OpenAI API       |
    | (Gov Procurement)|  | (CGU/Federal)    |  | (GPT-4.1-nano)   |
    | pncp.gov.br      |  | portaldatrans..  |  | Structured Output|
    +------------------+  +------------------+  +------------------+

    +------------------+  +------------------+  +------------------+
    | ComprasGov       |  | Querido Diario   |  | TCE-RJ           |
    | (DISABLED)       |  | (DISABLED)       |  | (DISABLED)       |
    | API deprecated   |  | Returns HTML     |  | API 404          |
    +------------------+  +------------------+  +------------------+
```

### Internal Backend Module Graph

```
main.py
  |-- schemas.py          (Pydantic request/response models)
  |-- job_store.py        (In-memory async job store)
  |-- config.py           (Retry config, modalities, source config)
  |-- exceptions.py       (Custom exception hierarchy)
  |-- sectors.py          (6 sector definitions with tiered keywords)
  |-- sources/
  |     |-- base.py            (ABC: DataSourceClient, NormalizedRecord)
  |     |-- orchestrator.py    (Parallel fetch, dedup, graceful degradation)
  |     |-- pncp_source.py     (Wraps PNCPClient in DataSourceClient)
  |     |-- comprasgov_source.py    (DISABLED)
  |     |-- transparencia_source.py (Portal da Transparencia)
  |     |-- querido_diario_source.py (DISABLED)
  |     |-- tce_rj_source.py        (DISABLED)
  |-- pncp_client.py     (Resilient HTTP client with retry, cache, circuit breaker)
  |-- filter.py           (Keyword matching engine with exclusions)
  |-- llm.py              (GPT-4.1-nano integration + fallback)
  |-- excel.py            (openpyxl report generator)
```

---

## 4. Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115.9 |
| Runtime | Python | 3.11+ |
| ASGI Server | Uvicorn | 0.34.3 |
| Validation | Pydantic | 2.11.7 |
| HTTP Client (PNCP) | requests + urllib3 | 2.32.3 / 2.3.0 |
| HTTP Client (async) | httpx | 0.28.1 |
| Excel Generation | openpyxl | 3.1.5 |
| LLM | OpenAI (GPT-4.1-nano) | 1.91.0 |
| Testing | pytest + pytest-asyncio | 8.3.5 / 0.25.0 |
| Linting | ruff | 0.9.6 |
| Type Checking | mypy | 1.15.0 |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js (App Router) | 16.1.4 |
| UI Library | React | 18.3.1 |
| Language | TypeScript | 5.9.3 |
| Styling | Tailwind CSS | 3.4.19 |
| Analytics | Mixpanel | 2.74.0 |
| Testing (Unit) | Jest + Testing Library | 29.7.0 |
| Testing (E2E) | Playwright | 1.58.0 |
| Accessibility | axe-core/playwright | 4.11.0 |

### Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Backend Hosting | Railway | Containerized, auto-deploy from main |
| Frontend Hosting | Vercel | Edge CDN, Next.js optimized |
| Local Dev | Docker Compose | backend + frontend containers |
| CI/CD | GitHub Actions | 8 workflows (tests, deploy, CodeQL, etc.) |
| Container Base (BE) | python:3.11-slim | Single-stage |
| Container Base (FE) | node:20-alpine | 3-stage build (deps, build, runner) |

---

## 5. Frontend Architecture

### 5.1 App Router Structure

```
frontend/app/
  page.tsx              -- Main SPA (search form + results display)
  layout.tsx            -- Root layout (fonts, theme, analytics providers)
  globals.css           -- Global CSS with Tailwind
  types.ts              -- TypeScript interfaces (BuscaResult, SearchPhase, etc.)
  error.tsx             -- Error boundary with fallback UI
  api/
    buscar/
      route.ts          -- POST: proxy search request to backend /buscar
      status/route.ts   -- GET: proxy job status polling
      result/route.ts   -- GET: fetch result, save Excel to tmpdir, return download_id
    download/route.ts   -- GET: serve Excel file from tmpdir by download_id
    setores/route.ts    -- GET: proxy sector list from backend
  components/
    LoadingProgress.tsx -- 5-stage progress bar with ETA, UF grid, curiosity carousel
    EmptyState.tsx      -- Illustrated empty state
    ThemeToggle.tsx     -- 5-theme switcher (light/paperwhite/sepia/dim/dark)
    ThemeProvider.tsx   -- Context provider for theme state
    RegionSelector.tsx  -- Geographic region-based UF multi-select
    SavedSearchesDropdown.tsx -- localStorage-persisted saved searches
    SourceBadges.tsx    -- Data source status badges with expandable stats
    AnalyticsProvider.tsx -- Mixpanel initialization wrapper
```

### 5.2 Component Hierarchy

```
RootLayout (layout.tsx)
  AnalyticsProvider
    ThemeProvider
      HomePage (page.tsx)
        ThemeToggle
        RegionSelector
        SavedSearchesDropdown
        LoadingProgress (shown during search)
        SourceBadges (shown with results)
        EmptyState (shown when no results)
        Results display (inline in page.tsx)
```

### 5.3 State Management

The frontend uses React `useState` hooks exclusively -- no external state library. Key state:

- `selectedUfs: string[]` -- selected Brazilian states
- `dataInicial / dataFinal: string` -- date range
- `setorId: string` -- selected sector
- `termosBusca: string` -- custom search terms
- `loading: boolean` -- search in progress
- `phase: SearchPhase` -- current pipeline stage (from backend polling)
- `result: BuscaResult | null` -- search results
- `validationErrors: ValidationErrors` -- form validation state

Saved searches are persisted to `localStorage` via the `useSavedSearches` custom hook.

### 5.4 API Communication Pattern (Async Job Polling)

```
1. User submits search
2. Frontend POST /api/buscar -> Backend POST /buscar
   Returns: { job_id: "uuid" }
3. Frontend polls GET /api/buscar/status?job_id=... every 2 seconds
   Returns: { status, progress: { phase, ufs_completed, items_fetched, ... } }
4. When status === "completed":
   Frontend GET /api/buscar/result?job_id=...
   Backend returns full result with excel_base64
   Next.js API route saves Excel to tmpdir, returns download_id
5. User clicks "Download Excel"
   Frontend GET /api/download?id=download_id
   Next.js serves file from tmpdir
```

### 5.5 Error Handling

- **Error boundary** (`error.tsx`) catches render-time errors with reset button
- **API route error handling** returns appropriate HTTP status codes (400, 404, 500, 503)
- **Backend unavailability** detected and reported as 503 with user-friendly Portuguese message
- **Form validation** prevents invalid submissions (no UFs, invalid dates, future dates)

---

## 6. Backend Architecture

### 6.1 FastAPI Application Structure

The application is a single-file FastAPI app (`main.py`) with modular imports. Key design decisions:

- **Single-process deployment** -- no Celery, no Redis, no external queue
- **asyncio.create_task** for background job execution
- **ThreadPoolExecutor** for CPU-bound work (filtering, Excel generation) and blocking I/O (PNCP HTTP calls via `requests`)
- **Global singletons** for PNCPSource, MultiSourceOrchestrator, and JobStore

### 6.2 Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `main.py` | FastAPI app, endpoints, background task orchestration |
| `config.py` | RetryConfig, PNCP modality codes, SOURCES_CONFIG, logging setup |
| `schemas.py` | Pydantic models: BuscaRequest, BuscaResponse, ResumoLicitacoes, Job* schemas |
| `exceptions.py` | PNCPAPIError hierarchy (base, RateLimit, Timeout, ServerError) |
| `sectors.py` | SectorConfig dataclass, 6 sector definitions with tiered keywords |
| `pncp_client.py` | Resilient HTTP client: retry, rate limiting, circuit breaker, caching, pagination |
| `sources/base.py` | ABC DataSourceClient, NormalizedRecord, SearchQuery |
| `sources/orchestrator.py` | Parallel multi-source search, composite-key dedup, graceful degradation |
| `sources/pncp_source.py` | PNCP adapter wrapping PNCPClient |
| `sources/transparencia_source.py` | Portal da Transparencia adapter (httpx async) |
| `filter.py` | Keyword matching with normalize, match_keywords, filter_batch |
| `llm.py` | GPT-4.1-nano structured output + deterministic fallback |
| `excel.py` | openpyxl report: 10 columns, currency format, hyperlinks, metadata tab |
| `job_store.py` | In-memory async job store with TTL cleanup |

### 6.3 Multi-Source Data Orchestration

The `MultiSourceOrchestrator` manages parallel data fetching:

1. **Source registry** -- 5 sources registered, 2 currently enabled (PNCP, Transparencia)
2. **Feature flags** -- `SOURCES_CONFIG[name]["enabled"]` or `ENABLED_SOURCES` env override
3. **Parallel execution** -- `asyncio.gather` with per-source timeouts
4. **Graceful degradation** -- failed/timed-out sources do not block others
5. **Partial result recovery** -- PNCPSource exposes `get_partial_results()` for timeout recovery
6. **Composite-key deduplication** -- primary key: `hash(cnpj + numero + ano)`, fallback: `hash(objeto[:100] + uf + data)`
7. **Source priority** -- PNCP is canonical (priority 1); on collision, PNCP record is preferred
8. **Field merging** -- missing fields in the winner are filled from the duplicate

### 6.4 Job Queue / Async Processing

The `JobStore` is an in-memory async store with `asyncio.Lock`:

- **Lifecycle:** `queued` -> `running` -> `completed` | `failed`
- **Max concurrent jobs:** 10 (returns HTTP 429 when full)
- **TTL:** 1800s (30 minutes) for completed/failed jobs
- **Periodic cleanup:** runs every 60 seconds via startup event
- **Progress phases:** `queued` -> `fetching` -> `filtering` -> `summarizing` -> `generating_excel` -> `done`

### 6.5 Resilience Patterns

#### Circuit Breaker (PNCPClient)
- Tracks consecutive timeout count across threads
- After 3 consecutive timeouts: pauses 15s (scales up to 60s max)
- Resets on first successful response

#### Adaptive Rate Limiting (PNCPClient)
- Base interval: 300ms between requests
- Doubles interval (max 2s) when response time > 5s or timeout occurs
- Decays 20% toward baseline when response time < 2s
- Thread-safe via `threading.Lock`

#### Retry with Exponential Backoff
- Max 2 retries per request (configurable)
- Exponential delay with +/-50% jitter to prevent thundering herd
- Honors `Retry-After` header on 429 responses
- Retryable codes: 408, 429, 500, 502, 503, 504

#### Dynamic Pagination Cap
- Base: 10 pages per UF x modalidade combo (500 items)
- Dynamic reduction: `min(max_pages, max(2, 600 / num_tasks))`
- Prevents cascading timeouts when many UFs selected (27 UFs x 7 mod = 189 combos)

#### Modalidade Reduction
- When >10 UFs selected, reduces from 7 modalities to 3 priority modalities
- Pregao Eletronico alone covers ~80% of procurement volume

### 6.6 LLM Integration

- **Model:** GPT-4.1-nano (structured output via `beta.chat.completions.parse`)
- **Temperature:** 0.3 (low creativity, high factual accuracy)
- **Max tokens:** 500
- **Input cap:** First 50 bids, descriptions truncated to 200 chars
- **Output schema:** `ResumoLicitacoes` Pydantic model (enforced by OpenAI)
- **Post-processing:** LLM-generated counts are overridden with actual computed values
- **Fallback:** `gerar_resumo_fallback()` -- pure Python statistical summary (top 3 by value, UF distribution, urgency detection)
- **Failure handling:** Any OpenAI exception triggers fallback (search never fails due to LLM)

---

## 7. API Contracts

### 7.1 Backend API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | Root -- API info and navigation links | None |
| GET | `/health` | Health check (status, timestamp, version) | None |
| GET | `/setores` | List available procurement sectors | None |
| POST | `/buscar` | Start async search job | None |
| GET | `/buscar/{job_id}/status` | Poll job status and progress | None |
| GET | `/buscar/{job_id}/result` | Get completed job result (202 if running) | None |
| GET | `/cache/stats` | PNCP cache statistics | None |
| POST | `/cache/clear` | Clear PNCP cache | None |
| GET | `/debug/pncp-test` | Diagnostic: test PNCP API reachability | None |

#### POST /buscar -- Request

```json
{
  "ufs": ["SP", "RJ", "MG"],
  "data_inicial": "2026-03-01",
  "data_final": "2026-03-07",
  "setor_id": "vestuario",
  "termos_busca": "jaleco avental"
}
```

**Validation rules:**
- `ufs`: min 1 item, Brazilian state codes
- `data_inicial`, `data_final`: YYYY-MM-DD format, inicial <= final
- `setor_id`: defaults to "vestuario"
- `termos_busca`: optional, space-separated custom terms (replace sector keywords)

#### POST /buscar -- Response (201)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

#### GET /buscar/{job_id}/status -- Response

```json
{
  "job_id": "...",
  "status": "running",
  "progress": {
    "phase": "fetching",
    "ufs_completed": 2,
    "ufs_total": 3,
    "items_fetched": 1523,
    "items_filtered": 0,
    "sources_completed": 1,
    "sources_total": 2
  },
  "created_at": "2026-03-07T10:00:00+00:00",
  "elapsed_seconds": 45.2
}
```

#### GET /buscar/{job_id}/result -- Response (completed)

```json
{
  "job_id": "...",
  "status": "completed",
  "resumo": {
    "resumo_executivo": "Encontradas 42 licitacoes...",
    "total_oportunidades": 42,
    "valor_total": 3500000.00,
    "destaques": ["..."],
    "alerta_urgencia": null
  },
  "excel_base64": "UEsDBBQ...",
  "total_raw": 2500,
  "total_filtrado": 42,
  "total_atas": 5,
  "total_licitacoes": 37,
  "filter_stats": {
    "rejeitadas_uf": 0,
    "rejeitadas_valor": 150,
    "rejeitadas_keyword": 2308,
    "rejeitadas_prazo": 0,
    "rejeitadas_outros": 0
  },
  "sources_used": ["PNCP", "transparencia"],
  "source_stats": { "...": "..." },
  "dedup_removed": 12,
  "truncated_combos": 3
}
```

### 7.2 Frontend API Routes (Next.js)

| Method | Path | Proxies To |
|--------|------|------------|
| POST | `/api/buscar` | Backend `POST /buscar` |
| GET | `/api/buscar/status?job_id=X` | Backend `GET /buscar/{X}/status` |
| GET | `/api/buscar/result?job_id=X` | Backend `GET /buscar/{X}/result` (saves Excel to tmpdir) |
| GET | `/api/download?id=X` | Reads Excel from tmpdir, serves as attachment |
| GET | `/api/setores` | Backend `GET /setores` |

The result route performs an additional step: it decodes the base64 Excel from the backend response, writes it to `os.tmpdir()` as `descomplicita_{timestamp}_{uuid}.xlsx`, and returns a `download_id` to the frontend. A cleanup routine deletes expired files (default TTL: 1 hour).

---

## 8. Data Flow

### 8.1 Search Request Lifecycle (End-to-End)

```
User submits form
    |
    v
[Frontend] POST /api/buscar (validates UFs, dates)
    |
    v
[Next.js API Route] Forwards to Backend POST /buscar
    |
    v
[Backend main.py] Creates job, launches asyncio.create_task(run_search_job)
    |
    v
[run_search_job] Phase: FETCHING
    |-- Resolves sector config (keywords, exclusions, value range)
    |-- Gets MultiSourceOrchestrator
    |-- Calls orchestrator.search_all(query)
    |     |-- For each enabled source (PNCP, Transparencia):
    |     |     |-- asyncio.create_task with per-source timeout
    |     |     |-- PNCP: run_in_executor -> PNCPClient.fetch_all()
    |     |     |     |-- Builds UF x modalidade task matrix
    |     |     |     |-- ThreadPoolExecutor(max_workers=3)
    |     |     |     |-- For each combo: paginate, rate-limit, retry, cache
    |     |     |     |-- Yields normalized items, deduped by numeroControlePNCP
    |     |     |-- Transparencia: httpx async with retry
    |     |-- Deduplicates across sources (composite key)
    |     |-- Returns OrchestratorResult
    |
    v
[run_search_job] Phase: FILTERING
    |-- Converts NormalizedRecords to legacy dicts
    |-- filter_batch(licitacoes, ufs, valor_min/max, keywords, exclusions)
    |     |-- For each bid: UF check -> value range -> keyword regex -> status
    |     |-- Tier scoring: A=1.0, B=0.7, C=0.3, threshold=0.6
    |-- Returns approved list + rejection stats
    |
    v
[run_search_job] Phase: SUMMARIZING + GENERATING_EXCEL (parallel)
    |-- gerar_resumo() -> GPT-4.1-nano structured output
    |     |-- On failure: gerar_resumo_fallback() (pure Python)
    |-- create_excel() -> openpyxl BytesIO -> base64
    |-- Override LLM counts with actual values
    |
    v
[run_search_job] Phase: DONE
    |-- job_store.complete(job_id, result)
    |
    v
[Frontend] Polling detects status=completed
    |-- GET /api/buscar/result -> saves Excel to tmpdir -> returns BuscaResult
    |-- Renders: summary, stats, source badges, download button
    |
    v
[User] Clicks "Download Excel"
    |-- GET /api/download?id=... -> serves .xlsx file
```

---

## 9. External Integrations

### 9.1 PNCP Portal (Primary Source -- ENABLED)

- **API:** `https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao`
- **Auth:** None (public API)
- **Rate limit:** Undocumented; server returns 429 with Retry-After header
- **Page size:** 50 items (API max, despite docs claiming 500)
- **Key parameters:** `dataInicial`, `dataFinal`, `codigoModalidadeContratacao`, `uf`, `pagina`
- **Note:** `palavraChave` parameter is silently ignored by the API (verified 2026-03-07)
- **Modalities queried:** 7 default (Concorrencia, Pregao, Dispensa, etc.), 3 priority when >10 UFs

### 9.2 Portal da Transparencia (Secondary Source -- ENABLED)

- **API:** `https://api.portaldatransparencia.gov.br/api-de-dados/licitacoes`
- **Auth:** API key via `chave-api-dados` header (free registration)
- **Rate limit:** 3 req/s (enforced client-side)
- **Page size:** 15 items per page
- **Also provides:** Sanctions checks (CEIS/CNEP) via `check_sanctions(cnpj)`

### 9.3 ComprasGov (DISABLED)

- **Reason:** `licitacoes/v1` endpoint returns 404 since ~2026-03
- **Status:** API migrated to `compras.dados.gov.br`; licitacoes consolidated into PNCP

### 9.4 Querido Diario (DISABLED)

- **Reason:** API returns HTML instead of JSON since ~2026-03; endpoint deprecated

### 9.5 TCE-RJ (DISABLED)

- **Reason:** `/api/v1/compras-diretas` returns 404 since ~2026-03

### 9.6 OpenAI API

- **Model:** GPT-4.1-nano
- **Usage:** Structured output via `beta.chat.completions.parse`
- **Schema:** `ResumoLicitacoes` (Pydantic model)
- **Fallback:** Pure Python statistical summary when API unavailable
- **Cost driver:** ~50 bids per call, 200 chars per description, 500 max output tokens

---

## 10. Deployment Architecture

### 10.1 Docker Compose (Local Development)

```yaml
services:
  backend:   python:3.11-slim, port 8000, hot-reload via volume mount
  frontend:  Next.js, port 3000, depends_on backend (service_healthy)
networks:
  bidiq-network: bridge
```

Both services have health checks (30s interval, 3 retries).

### 10.2 Railway Configuration (Backend Production)

- **Container:** python:3.11-slim, single-stage Dockerfile
- **Entry:** `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
- **Health check:** `/health` endpoint
- **Auto-deploy:** On push to main (backend/ path changes)
- **Environment variables:** Injected via Railway dashboard

### 10.3 Vercel Configuration (Frontend Production)

- **Container:** node:20-alpine, 3-stage Dockerfile (deps -> build -> runner)
- **Output:** Next.js standalone mode
- **Non-root user:** `nextjs` (UID 1001)
- **Auto-deploy:** On push to main (frontend/ path changes)
- **Environment variables:** `BACKEND_URL` pointing to Railway backend

### 10.4 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (for LLM) | -- | OpenAI API key |
| `BACKEND_URL` | No | `http://localhost:8000` | Backend URL for frontend proxy |
| `TRANSPARENCIA_API_KEY` | No | -- | Portal da Transparencia API key |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `NEXT_PUBLIC_MIXPANEL_TOKEN` | No | -- | Mixpanel analytics token |
| `ENABLED_SOURCES` | No | Config-based | Comma-separated source names override |
| `DOWNLOAD_TTL_MS` | No | `3600000` | Excel download file TTL in ms |
| `PORT` | No | `8000` | Server port (Railway injects this) |

---

## 11. Security Considerations

### 11.1 CORS Configuration

**CURRENT:** `allow_origins=["*"]` -- allows all origins. This is explicitly marked as a POC setting with a TODO comment in `main.py:76`.

**RISK:** High. Any website can make authenticated requests to the API.

**RECOMMENDATION:** Restrict to specific domains (`https://descomplicita.vercel.app`, `http://localhost:3000`).

### 11.2 Rate Limiting

- **Backend -> PNCP:** Adaptive rate limiting (300ms-2s), circuit breaker, max 3 concurrent workers
- **Client -> Backend:** Only concurrency limit (10 max active jobs). No per-IP rate limiting.
- **RISK:** No protection against client-side abuse (DDoS, resource exhaustion)

### 11.3 Input Validation

- Pydantic model validation on `/buscar` (UFs list, date format, date range)
- Date range no longer has a max-days limit (was 30 days, removed)
- No sanitization of `termos_busca` beyond whitespace splitting
- Sector ID validated against `SECTORS` dict (raises KeyError -> job failure)

### 11.4 API Key Management

- `OPENAI_API_KEY` stored as environment variable, not in code
- `TRANSPARENCIA_API_KEY` stored as environment variable
- `.env` file excluded from git via `.gitignore`
- `.env.example` provided with empty values

### 11.5 Container Security

- Frontend Dockerfile uses non-root user (`nextjs`, UID 1001)
- Backend Dockerfile runs as root (no `USER` directive)

---

## 12. Performance and Resilience

### 12.1 Circuit Breaker Pattern

Located in `pncp_client.py`:
- **Threshold:** 3 consecutive timeouts
- **Pause formula:** `15 * (consecutive_timeouts / threshold)`, capped at 60s
- **Reset:** On first successful response
- **Scope:** Shared across all threads via `threading.Lock`

### 12.2 Adaptive Rate Limiting

Located in `pncp_client.py`:
- **Base interval:** 300ms
- **Increase condition:** Response time > 5s or timeout -> interval doubles (max 2s)
- **Decrease condition:** Response time < 2s -> interval decays by 20%
- **Thread-safe:** Uses `threading.Lock`

### 12.3 Caching Strategy

Located in `pncp_client.py`:
- **Cache key:** `{uf}:{modalidade}:{data_inicial}:{data_final}`
- **TTL:** 4 hours
- **Max entries:** 500
- **Eviction:** LRU (least recently accessed)
- **Scope:** Per-PNCPClient instance (shared across requests via global singleton)
- **Thread-safe:** Uses `threading.Lock`

### 12.4 Timeout Handling

| Layer | Timeout | Configurable |
|-------|---------|-------------|
| PNCP HTTP request | 40s | `RetryConfig.timeout` |
| PNCP orchestrator | 300s base + 15s per UF beyond 5 | `SOURCES_CONFIG["pncp"]["timeout"]` |
| Transparencia HTTP | 90s | `SOURCES_CONFIG["transparencia"]["timeout"]` |
| Transparencia orchestrator | 90s | Same |
| Frontend polling | Indefinite (user can cancel) | -- |

### 12.5 Parallelism

- **PNCP fetch:** ThreadPoolExecutor with max 3 workers (shared process)
- **Source orchestration:** asyncio.gather across enabled sources
- **LLM + Excel:** Parallel via asyncio.gather(run_in_executor)
- **No true async for PNCP:** Uses `requests` (blocking) wrapped in `run_in_executor`

---

## 13. Testing Strategy

### 13.1 Backend Tests

- **Framework:** pytest + pytest-asyncio
- **Coverage:** 99.2% (threshold: 70%)
- **Test count:** 226+ tests
- **Key test files:**
  - `test_pncp_client.py` -- 32 tests (retry, rate limiting, pagination, circuit breaker)
  - `test_filter.py` -- 48 tests (keyword matching, normalization, exclusions)
  - `test_excel.py` -- 20 tests (formatting, data integrity, edge cases)
  - `test_llm.py` -- 15 tests (GPT integration, fallback, empty input)
  - `test_main.py` -- 14 tests (API endpoints, validation)
  - `test_schemas.py` -- 25 tests (Pydantic validation)
- **Mocking:** OpenAI API calls mocked; PNCP API calls mocked
- **CI matrix:** Python 3.11, 3.12

### 13.2 Frontend Tests

- **Framework:** Jest + Testing Library (unit), Playwright (E2E)
- **Coverage:** 91.5% (threshold: 60%)
- **Unit tests:** 94 tests across page, error boundary, API routes
- **E2E tests:** 25 Playwright tests
- **Accessibility:** axe-core integration in E2E tests

### 13.3 CI/CD Integration

8 GitHub Actions workflows:
- `tests.yml` -- Backend (Python 3.11/3.12) + Frontend + coverage upload
- `deploy.yml` -- Auto-deploy to Railway/Vercel on push to main
- `codeql.yml` -- Security scanning + secret detection
- `backend-ci.yml` -- Backend-specific CI
- `pr-validation.yml` -- PR checks
- `filter-quality-audit.yml` -- Filter false positive/negative auditing
- `dependabot-auto-merge.yml` -- Auto-merge minor dependency updates
- `cleanup.yml` -- Resource cleanup

---

## 14. Technical Debt Inventory (PRELIMINARY)

### CRITICAL

| # | Description | Location | Category |
|---|-------------|----------|----------|
| TD-01 | **CORS allows all origins** -- `allow_origins=["*"]` permits any website to call the API. Should be restricted to Vercel domain in production. | `backend/main.py:76` | Security |
| TD-02 | **Backend Dockerfile runs as root** -- no `USER` directive, container processes run as root user. | `backend/Dockerfile` | Security |
| TD-03 | **No authentication or authorization** -- all API endpoints are publicly accessible with no auth. Any user can exhaust job capacity. | `backend/main.py` (all endpoints) | Security |

### HIGH

| # | Description | Location | Category |
|---|-------------|----------|----------|
| TD-04 | **In-memory job store is not horizontally scalable** -- all state lost on restart. Cannot run multiple backend instances. Needs Redis/PostgreSQL. | `backend/job_store.py` | Scalability |
| TD-05 | **No per-IP/user rate limiting on API** -- only global concurrency limit (10 jobs). A single client can monopolize all slots. | `backend/main.py:289-293` | Security |
| TD-06 | **Excel base64 transmitted in job result** -- entire Excel file base64-encoded in JSON response. For large reports, this wastes bandwidth and memory. Should use streaming/file reference. | `backend/main.py:538-539` | Performance |
| TD-07 | **Global mutable singletons** -- `_pncp_source`, `_orchestrator`, `_job_store` are module-level globals. Makes testing harder and prevents proper DI. | `backend/main.py:151-188` | Maintainability |
| TD-08 | **Deprecated `@app.on_event("startup")`** -- FastAPI recommends lifespan context manager instead. | `backend/main.py:191` | Maintainability |
| TD-09 | **`datetime.utcnow()` is deprecated** -- should use `datetime.now(timezone.utc)`. | `backend/main.py:145` | Code Quality |
| TD-10 | **Dev dependencies in production requirements.txt** -- pytest, ruff, mypy, faker bundled in production image. Should be separated. | `backend/requirements.txt:23-31` | Performance |
| TD-11 | **PNCP client uses blocking `requests` library** -- wrapped in `run_in_executor` but ties up thread pool. Should migrate to `httpx` async like Transparencia source. | `backend/pncp_client.py` | Performance |

### MEDIUM

| # | Description | Location | Category |
|---|-------------|----------|----------|
| TD-12 | **`docker-compose.yml` still references `bidiq-` names** -- container names and network are `bidiq-backend`, `bidiq-frontend`, `bidiq-network`. Should be rebranded to `descomplicita`. | `docker-compose.yml:30,74,94` | Maintainability |
| TD-13 | **`README.md` title still says "Descomplicita"** -- inconsistent branding across documentation. | `README.md:1` | Maintainability |
| TD-14 | **sectors.py module docstring says "Descomplicita"** -- needs brand update. | `backend/sectors.py:1` | Maintainability |
| TD-15 | **No request ID / correlation ID** -- log entries for a single search are correlated only by job_id in string interpolation, not structured logging fields. | `backend/main.py` (throughout) | Maintainability |
| TD-16 | **Hardcoded PNCP base URL** -- `PNCPClient.BASE_URL` is a class constant, not configurable via env. | `backend/pncp_client.py:81` | Maintainability |
| TD-17 | **No API versioning** -- endpoints are unversioned (`/buscar` not `/v1/buscar`). Breaking changes will affect all clients simultaneously. | `backend/main.py` | Maintainability |
| TD-18 | **Filter diagnostic code in production path** -- lines 441-455 in `main.py` import `filter.py` internals and iterate over raw data for debug logging inside the request handler. | `backend/main.py:441-455` | Code Quality |
| TD-19 | **UFS constant duplicated** -- defined in both `frontend/app/page.tsx:18-21` and `frontend/app/types.ts:6-10`. | `frontend/app/page.tsx:18`, `frontend/app/types.ts:6` | Code Quality |
| TD-20 | **No OpenAPI schema for job result endpoint** -- `GET /buscar/{job_id}/result` returns raw `JSONResponse`, not a typed Pydantic model. Swagger docs are incomplete. | `backend/main.py:650` | Maintainability |
| TD-21 | **Excel download uses filesystem tmpdir** -- not suitable for serverless (Vercel edge functions) or multi-instance deployment. Should use signed URLs or streaming. | `frontend/app/api/buscar/result/route.ts:63-64` | Scalability |
| TD-22 | **`asyncio.get_event_loop()` deprecated usage** -- should use `asyncio.get_running_loop()`. | `backend/main.py:320`, `backend/sources/pncp_source.py:104` | Code Quality |
| TD-23 | **No graceful shutdown** -- background tasks (`run_search_job`, cleanup) are not properly cancelled on SIGTERM. | `backend/main.py:191-198` | Maintainability |
| TD-24 | **Cache not shared across restarts** -- in-memory LRU cache in PNCPClient is lost on container restart. Repeated searches after deploy re-fetch everything. | `backend/pncp_client.py:108` | Performance |
| TD-25 | **Module-level singleton in job_store.py** -- `job_store = JobStore()` at line 158 creates a second instance that is never used (main.py creates its own `_job_store`). | `backend/job_store.py:158` | Code Quality |

### LOW

| # | Description | Location | Category |
|---|-------------|----------|----------|
| TD-26 | **No structured error codes** -- error responses use free-text Portuguese messages, not machine-parseable error codes. | Throughout backend | Maintainability |
| TD-27 | **`f-string` in logger calls** -- should use `logger.info("msg %s", val)` for lazy formatting. | `backend/main.py` (many lines) | Performance |
| TD-28 | **No pagination for sectors endpoint** -- returns all sectors in a single response. Not a problem now (6 sectors) but could be if expanded. | `backend/main.py:201-204` | Scalability |
| TD-29 | **Frontend emoji usage in source code** -- LoadingProgress.tsx and other components embed emoji characters directly in JSX. | `frontend/app/components/LoadingProgress.tsx` | Code Quality |
| TD-30 | **No content-length validation for Excel downloads** -- frontend serves whatever is on disk without size limits. | `frontend/app/api/download/route.ts` | Security |
| TD-31 | **Date range max removed** -- BuscaRequest no longer enforces a max date range. Users can query arbitrarily large ranges, potentially overloading PNCP. | `backend/schemas.py:59-73` | Performance |

---

## 15. Recommendations

### Priority 1 -- Security (Immediate)

1. **Restrict CORS origins** to production domains (TD-01)
2. **Run backend container as non-root user** (TD-02)
3. **Implement per-IP rate limiting** (e.g., SlowAPI middleware) (TD-05)
4. **Add API authentication** for production use (TD-03) -- even a simple API key would prevent abuse

### Priority 2 -- Scalability (Before Multi-Tenant)

5. **Replace in-memory job store with Redis** -- enables horizontal scaling, survives restarts (TD-04)
6. **Stream Excel files** instead of base64 in JSON -- use pre-signed URLs or direct streaming (TD-06)
7. **Migrate PNCP client to httpx async** -- eliminate thread pool bottleneck (TD-11)
8. **Share cache via Redis** -- enables cache persistence across restarts and instances (TD-24)

### Priority 3 -- Code Quality (Next Sprint)

9. **Separate dev/prod requirements** -- use `requirements-dev.txt` for test/lint tools (TD-10)
10. **Complete branding migration** -- update docker-compose, README, sectors.py to Descomplicita (TD-12, TD-13, TD-14)
11. **Adopt FastAPI lifespan** context manager to replace deprecated `on_event` (TD-08)
12. **Replace deprecated `datetime.utcnow()`** with `datetime.now(timezone.utc)` (TD-09)
13. **Add API versioning** prefix (`/v1/`) before any breaking changes (TD-17)
14. **Add structured logging** with correlation IDs per request (TD-15)
15. **Remove filter diagnostic code** from production path (TD-18)
16. **Type the job result endpoint** with a proper Pydantic response model (TD-20)

### Priority 4 -- Observability (Medium-Term)

17. **Add Sentry error tracking** (DSN already in `.env.example`)
18. **Add response time metrics** (Prometheus or DataDog)
19. **Add health check dependencies** (verify PNCP/OpenAI reachability in `/health`)
20. **Dashboard for job queue metrics** (active jobs, avg duration, failure rate)

---

*Document generated: 2026-03-07*
*Based on codebase analysis at commit `9fbd54d0` (main branch)*
