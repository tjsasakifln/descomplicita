# Story 4.0: Backend Architecture -- Persistent Storage + Async Migration

**Sprint:** 4
**Epic:** Resolucao de Debitos Tecnicos
**Priority:** High
**Estimated Points:** 21
**Estimated Hours:** 58-96

## Objetivo

Replace the in-memory architecture (job store, cache, file storage) with persistent Redis-backed storage and migrate the synchronous PNCP HTTP client to async. Currently, all job state, cached PNCP responses, and Excel files are lost on every container restart or deploy. Horizontal scaling is impossible because state is process-local. The blocking `requests` library in the PNCP client ties up async worker threads during HTTP calls.

## Debts Addressed

| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-005 | In-memory job store -- not scalable, state lost on restart | 16-24 | Backend |
| TD-026 | Cache not shared across restarts -- ephemeral in-memory cache | 8-16 | Backend |
| TD-013 | Global mutable singletons -- tight coupling prevents testing and DI | 8-12 | Backend |
| TD-014 | Deprecated startup event pattern -- `@app.on_event("startup")` | 2-4 | Backend |
| TD-007 | Excel base64 in JSON response -- memory-intensive, slow | 8-16 | Backend |
| TD-023 | Excel download uses filesystem tmpdir -- incompatible with serverless (resolved by TD-007) | 0 | Backend |
| TD-011 | PNCP client uses blocking `requests` library | 16-24 | Backend |

## Tasks

### Workstream A: Redis Infrastructure (TD-005 + TD-026) -- 24-40 hours

- [ ] Task 1: Add Redis to `docker-compose.yml` and document Railway/cloud Redis setup in README
- [ ] Task 2: TD-005 -- Create `backend/stores/redis_job_store.py` implementing the same interface as the current in-memory job store but backed by Redis. Use `redis.asyncio` client.
- [ ] Task 3: TD-005 -- Implement dual-write mode: write to both in-memory and Redis during transition period to validate data parity
- [ ] Task 4: TD-005 -- Add TTL-based job expiry in Redis (e.g., 24 hours) to prevent unbounded growth
- [ ] Task 5: TD-026 -- Create `backend/cache/redis_cache.py` implementing PNCP response cache in Redis. Set TTL matching current cache duration.
- [ ] Task 6: TD-026 -- Migrate cache reads/writes from in-memory dict to Redis, maintaining cache key format compatibility
- [ ] Task 7: Add Redis health check to `/health` endpoint (connection test)
- [ ] Task 8: Remove dual-write mode after validation, remove in-memory fallback

### Workstream B: Dependency Injection + Lifespan (TD-013 + TD-014) -- 10-16 hours

- [ ] Task 9: TD-013 -- Refactor global singletons (`job_store`, `pncp_cache`, `pncp_client`) to use FastAPI dependency injection via `Depends()`. Create provider functions in `backend/dependencies.py`.
- [ ] Task 10: TD-014 -- Migrate `@app.on_event("startup")` and `@app.on_event("shutdown")` to `lifespan` context manager pattern. Initialize Redis connections, PNCP client in lifespan startup; close in shutdown.
- [ ] Task 11: Update all endpoint functions to receive dependencies via `Depends()` instead of importing globals
- [ ] Task 12: Update all tests to inject mock dependencies instead of patching globals

### Workstream C: Excel Delivery (TD-007 + TD-023) -- 8-16 hours

- [ ] Task 13: TD-007 -- Replace base64-in-JSON Excel delivery with streaming response (`StreamingResponse`) or signed URL pattern. Evaluate: (a) `StreamingResponse` with `content-type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, or (b) upload to object storage (S3/R2/Supabase Storage) and return signed URL.
- [ ] Task 14: TD-007 -- Update frontend download handler to work with new delivery mechanism (direct binary download or redirect to signed URL)
- [ ] Task 15: TD-023 -- Remove tmpdir-based file creation (naturally resolved by streaming or object storage approach)

### Workstream D: Async PNCP Client (TD-011) -- 16-24 hours

- [ ] Task 16: TD-011 -- Install `httpx` and create `backend/clients/async_pncp_client.py` using `httpx.AsyncClient` with connection pooling, timeouts, and retry logic
- [ ] Task 17: TD-011 -- Migrate all PNCP API calls from synchronous `requests.get()` to `await client.get()`
- [ ] Task 18: TD-011 -- Validate response parity: run identical queries through old (requests) and new (httpx) clients, compare result counts and content
- [ ] Task 19: TD-011 -- Remove `requests` from `requirements.txt` after full migration. Add `httpx` to requirements.
- [ ] Task 20: TD-011 -- Update User-Agent string in new client to "Descomplicita/1.0"

## Criterios de Aceite

- [ ] Job state survives container restart (create job, restart container, poll job -- state preserved)
- [ ] Cache is shared across multiple container instances (write in instance A, read in instance B)
- [ ] Redis connection failure does not crash the application (graceful degradation or clear error)
- [ ] Excel files are delivered without base64 encoding in JSON (either streaming binary or signed URL)
- [ ] Frontend download works correctly with new Excel delivery mechanism
- [ ] No tmpdir files are created during Excel generation
- [ ] All PNCP API calls use async httpx (no `requests` import remains in production code)
- [ ] Response parity validated: httpx client returns identical results to requests client for same queries
- [ ] No global mutable singletons remain -- all dependencies injected via FastAPI `Depends()`
- [ ] `@app.on_event` is no longer used -- lifespan context manager handles startup/shutdown
- [ ] All existing tests pass with dependency injection (mocks injected, not patched)

## Testes Requeridos

- [ ] Integration test: Redis job store -- create, read, update, delete, TTL expiry
- [ ] Integration test: Redis cache -- set, get, miss, TTL expiry
- [ ] Integration test: Redis connection failure -- graceful degradation
- [ ] Unit test: DI provider functions return correct instances
- [ ] Unit test: Lifespan context manager starts and stops cleanly
- [ ] Unit test: Excel streaming response returns valid .xlsx content
- [ ] Unit test: Async PNCP client -- successful request, timeout, retry, error handling
- [ ] Parity test: Same PNCP query returns identical results via requests vs httpx
- [ ] E2E test: Full search flow with Redis backend (submit, poll, results, download)
- [ ] Load test: 10 concurrent searches with Redis (verify no data corruption)

## Dependencias

- Blocked by: Story 0.0 (tests must be green). Story 1.0 (API key auth should be in place before architecture changes).
- Blocks: None directly. Can run in parallel with Sprints 2-3 (frontend work) if separate developers are available.
- Internal dependencies:
  - TD-013 (DI) and TD-014 (lifespan) are tightly coupled -- do in same PR
  - TD-005 (Redis job store) and TD-026 (Redis cache) share infrastructure -- deploy Redis first
  - TD-007 (Excel delivery) and TD-023 (tmpdir removal) are two sides of same refactor
  - TD-013 (DI) enhances TD-005 (cleaner with injection)

## Notes on Parallelization

This is the largest sprint (58-96 hours). Recommended parallel execution:
- **Developer A:** Workstream A (Redis) + Workstream B (DI/Lifespan) -- 34-56 hours
- **Developer B:** Workstream C (Excel) + Workstream D (httpx) -- 24-40 hours

Workstream B should start after Workstream A has Redis running, as DI refactor will inject Redis-backed stores.

## Definition of Done

- [ ] Code reviewed (recommend per-workstream PRs)
- [ ] All tests passing (unit + integration + E2E)
- [ ] Coverage maintained >= 70% backend
- [ ] No regressions in search functionality
- [ ] Redis documented in docker-compose.yml and deployment guide
- [ ] `requests` library removed from production requirements
- [ ] No global mutable singletons in production code
- [ ] Performance benchmarked: search latency not degraded by Redis or httpx migration
