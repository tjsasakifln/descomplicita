# Database Audit Report

> **Generated:** 2026-03-09 | **Agent:** @data-engineer (Delphi)
> **Scope:** SQLite database (`backend/database.py`), Redis data stores, all backend data access patterns
> **Severity Scale:** Critical > High > Medium > Low

---

## 1. Security Audit

### 1.1 RLS Coverage

| Table | RLS Enabled | Policies | Risk |
|-------|-------------|----------|------|
| `search_history` | N/A (SQLite) | None | Medium -- no per-user isolation |
| `user_preferences` | N/A (SQLite) | None | Medium -- global namespace, no user scoping |

**Finding:** SQLite does not support Row Level Security. All data is globally accessible to any authenticated API client. The `/search-history` endpoint returns all searches from all users without any user-scoping filter. When multiple tenants or users are introduced, this becomes a data exposure risk.

### 1.2 SQL Injection Analysis

| Location | Pattern | Risk Level |
|----------|---------|------------|
| `database.py` line 98-111 | Parameterized queries (`?` placeholders) | **Safe** |
| `database.py` line 124-137 | Parameterized queries | **Safe** |
| `database.py` line 143-147 | Parameterized queries | **Safe** |
| `database.py` line 153-158 | Parameterized queries for LIMIT | **Safe** |
| `database.py` line 184-195 | Parameterized queries for upsert | **Safe** |
| `database.py` line 202-203 | Parameterized queries | **Safe** |

**Verdict:** All SQL queries use parameterized placeholders (`?`). No string interpolation or f-string SQL construction was found. **SQL injection risk is effectively zero.**

### 1.3 Auth Token Handling

| Mechanism | Implementation | Assessment |
|-----------|---------------|------------|
| API Key | Compared via `==` in middleware | **Weak** -- vulnerable to timing attacks (should use `hmac.compare_digest`) |
| JWT | Custom HMAC-SHA256 implementation | **Adequate** -- uses `hmac.compare_digest` for signature validation |
| JWT Secret | From `JWT_SECRET` env var | **Good** -- not hardcoded |
| API Key Secret | From `API_KEY` env var | **Good** -- not hardcoded |
| Token Expiration | Configurable (default 24h) | **Adequate** for POC |
| Token Revocation | Not supported (stateless JWT) | **Acceptable** for POC, needs addressing for production |

**Note:** The API key comparison in `middleware/auth.py` line 71 uses `==` (Python string comparison), which is susceptible to timing side-channel attacks. The JWT signature comparison correctly uses `hmac.compare_digest`.

### 1.4 Data Exposure Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Global search history | Medium | `/search-history` returns all searches without user filtering |
| No encryption at rest | Low | SQLite file on disk is unencrypted (acceptable for POC) |
| Redis data unencrypted | Low | Redis keys store plaintext JSON (standard for Redis) |
| Debug endpoints | Low | Gated by `ENABLE_DEBUG_ENDPOINTS` flag, but expose cache internals |
| Error messages | Low | Job failure messages include internal error details in some paths |

---

## 2. Performance Audit

### 2.1 Missing Indexes

| Table | Column(s) | Current Index | Recommendation |
|-------|-----------|--------------|----------------|
| `search_history` | `job_id` | UNIQUE constraint (implicit index) | **Adequate** |
| `search_history` | `created_at DESC` | `idx_search_history_created` | **Adequate** |
| `search_history` | `setor_id` | `idx_search_history_setor` | **Adequate** |
| `search_history` | `status` | **None** | Consider adding if querying by status |
| `user_preferences` | `key` | UNIQUE constraint (implicit index) | **Adequate** |

**Verdict:** Indexes are sufficient for current query patterns. The only SELECT on `search_history` orders by `created_at DESC` which is covered. No queries filter by `status` currently, so the missing index is not impactful.

### 2.2 N+1 Query Patterns

**None detected.** The database access patterns are simple:
- Single INSERT per search job creation
- Single UPDATE per search completion/failure
- Single SELECT for recent history (bounded by LIMIT)

There are no join queries, no nested loops with queries, and no ORM lazy-loading patterns.

### 2.3 Slow Query Candidates

| Query | Risk | Mitigation |
|-------|------|------------|
| `get_recent_searches(limit=100)` | Low | Bounded by caller (`min(limit, 100)` in endpoint) |
| `executescript(_SCHEMA_SQL)` on startup | Low | `IF NOT EXISTS` makes it idempotent and fast |

**Verdict:** No slow query risks at current scale. SQLite handles the volume (hundreds to low thousands of rows) without issues.

### 2.4 Connection Pooling

| Component | Pooling | Assessment |
|-----------|---------|------------|
| SQLite | Single connection (`aiosqlite.connect`) | **Adequate** -- SQLite is single-writer by design; pooling adds complexity without benefit |
| Redis | Single connection via `redis.asyncio.from_url` | **Adequate** for POC -- `redis.asyncio` handles connection reuse internally |
| Redis timeouts | `socket_connect_timeout=5, socket_timeout=5` | **Good** -- prevents hanging connections |

### 2.5 Redis Performance Considerations

| Pattern | Risk | Assessment |
|---------|------|------------|
| Full JSON serialization of items list | Medium | Large result sets (500+ items) serialized to JSON and stored in a single Redis key. Could cause latency spikes for large payloads. |
| `scan_iter` for cache clear/count | Low | O(N) scan but only used for debug endpoints |
| Progress updates write full job JSON to Redis | Medium | Every progress update serializes and writes the entire job state. High-frequency updates during fetching phase could create write amplification. |

---

## 3. Schema Quality

### 3.1 Normalization Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| `ufs` stored as JSON string | Low | Array stored as `TEXT` (JSON-encoded). Prevents efficient querying by individual UF. Acceptable for audit log. |
| `termos_busca` stored as raw text | Low | Not normalized or parsed before storage. Acceptable for audit. |
| `value` in `user_preferences` as JSON string | Low | Generic key-value pattern. No schema validation at DB level. |

**Verdict:** Normalization level is appropriate for the use case (audit logging and simple key-value storage). The JSON-in-TEXT pattern is a pragmatic choice for SQLite.

### 3.2 Missing Constraints

| Table | Missing Constraint | Severity | Recommendation |
|-------|-------------------|----------|----------------|
| `search_history` | No CHECK on `status` values | Low | Add `CHECK(status IN ('queued','completed','failed'))` |
| `search_history` | No CHECK on date formats | Low | Application validates via Pydantic, so risk is low |
| `search_history` | No NOT NULL on `total_raw` | Low | Has DEFAULT 0, but explicit NOT NULL would be cleaner |
| `user_preferences` | No length limits on `key` or `value` | Low | Application should enforce max sizes |

### 3.3 Data Type Choices

| Column | Current Type | Assessment |
|--------|-------------|------------|
| `created_at`, `completed_at` | TEXT (ISO 8601) | **Acceptable** for SQLite (no native DATETIME). Consider INTEGER (Unix timestamp) for easier comparison. |
| `elapsed_seconds` | REAL | **Good** -- appropriate for fractional seconds |
| `ufs` | TEXT (JSON) | **Acceptable** -- array of strings in SQLite |
| `total_raw`, `total_filtrado` | INTEGER | **Good** |

### 3.4 Naming Conventions

| Convention | Assessment |
|------------|------------|
| Table names | snake_case -- **consistent** |
| Column names | snake_case -- **consistent** |
| Index names | `idx_{table}_{column}` -- **consistent** |
| Mixed Portuguese/English | `data_inicial`, `setor_id` (PT) vs `status`, `created_at` (EN) -- **inconsistent but acceptable** given the domain |
| Redis key patterns | `{entity}:{id}` -- **consistent** |

---

## 4. Technical Debt Items

### DB-001: No Multi-User / Multi-Tenant Data Isolation

- **Severity:** High
- **Description:** The `search_history` and `user_preferences` tables have no `user_id` column. All data is globally shared. The `/search-history` endpoint returns all searches from all users.
- **Impact:** When multiple users or tenants are introduced, search history from one user is visible to all. Privacy violation risk.
- **Estimated Effort:** 4 hours
- **Recommendation:** Add `user_id TEXT NOT NULL` column to both tables. Filter queries by authenticated user. When migrating to Supabase, implement RLS policies.

### DB-002: Ephemeral Storage on Railway/Vercel

- **Severity:** High
- **Description:** SQLite stores data on the filesystem. Railway and Vercel use ephemeral containers -- the database file is lost on every deploy or container restart. The `database.py` header acknowledges this: "ephemeral storage is acceptable for POC."
- **Impact:** All search history is lost on deployments. No durable persistence of analytics data.
- **Estimated Effort:** 16 hours
- **Recommendation:** Migrate to Supabase PostgreSQL (env vars already defined). Use the Supabase Python client or SQLAlchemy with asyncpg. Implement proper migrations with Alembic or Supabase CLI.

### DB-003: No Migration System

- **Severity:** High
- **Description:** Schema is created via `CREATE TABLE IF NOT EXISTS` on startup. There is no migration tool (Alembic, Supabase CLI, or custom). Schema changes require manual ALTER TABLE or database recreation.
- **Impact:** Schema evolution is manual and error-prone. No rollback capability. Cannot track schema history.
- **Estimated Effort:** 8 hours
- **Recommendation:** Adopt Alembic for SQLAlchemy-based migrations, or Supabase CLI migrations if migrating to Supabase. Create initial migration from current schema.

### DB-004: User Preferences Table is Unused

- **Severity:** Medium
- **Description:** The `user_preferences` table and its three methods (`set_preference`, `get_preference`, `get_all_preferences`) are defined but never called from any endpoint or background process.
- **Impact:** Dead code increases maintenance burden and test surface. The table exists in production but serves no purpose.
- **Estimated Effort:** 1 hour
- **Recommendation:** Either wire up preferences to an API endpoint or remove the table and methods. If keeping, add a `GET/PUT /preferences` endpoint.

### DB-005: API Key Comparison Vulnerable to Timing Attack

- **Severity:** Medium
- **Description:** In `middleware/auth.py` line 71, API key validation uses Python `==` operator (`request_key == api_key`), which is not constant-time. The JWT signature comparison at `auth/jwt.py` line 124 correctly uses `hmac.compare_digest`.
- **Impact:** Theoretical timing side-channel attack could leak API key bytes. Low practical risk for a POC but violates security best practices.
- **Estimated Effort:** 0.5 hours
- **Recommendation:** Replace `request_key == api_key` with `hmac.compare_digest(request_key, api_key)` in `middleware/auth.py`.

### DB-006: Redis Write Amplification on Progress Updates

- **Severity:** Medium
- **Description:** `RedisJobStore.update_progress()` serializes and writes the entire job state JSON to Redis on every progress update. During the fetching phase, progress is updated for each source completion, and potentially for each UF.
- **Impact:** Unnecessary Redis writes. Each update writes the full job JSON (which may include the result dict after completion). Not a bottleneck at current scale but will degrade at higher concurrency.
- **Estimated Effort:** 4 hours
- **Recommendation:** Use Redis HSET to store job fields individually, or batch progress updates with a debounce interval (e.g., update Redis at most every 2 seconds).

### DB-007: No Database Connection Health Check

- **Severity:** Medium
- **Description:** The `/health` endpoint checks Redis connectivity but does not check SQLite database health. If the database file becomes corrupted or the connection drops, it would not be detected until a write fails.
- **Impact:** Silent database failures. Health checks report "healthy" even when persistence is broken.
- **Estimated Effort:** 1 hour
- **Recommendation:** Add SQLite connectivity check to `/health` endpoint (e.g., `SELECT 1`). Return database status alongside Redis status.

### DB-008: No Data Retention / Cleanup Policy for SQLite

- **Severity:** Medium
- **Description:** The `search_history` table grows unbounded. There is no cleanup mechanism for old records. Redis has TTL-based expiry, but SQLite rows persist indefinitely.
- **Impact:** On long-running instances (if not ephemeral), the SQLite file grows without bound. Performance degrades as the table grows (though slowly, given the simple queries).
- **Estimated Effort:** 2 hours
- **Recommendation:** Add a periodic cleanup task that deletes rows older than N days (e.g., 90 days). Run alongside the existing Redis cleanup in the lifespan periodic task.

### DB-009: Redis Items Deserialization Loads Entire Dataset

- **Severity:** Medium
- **Description:** `RedisJobStore.get_items_page()` retrieves the entire items JSON from Redis and then slices in Python. For jobs with 500+ items, this deserializes the full array even for page 1 with 20 items.
- **Impact:** Memory waste and latency for large result sets. Each page request deserializes the full items list.
- **Estimated Effort:** 4 hours
- **Recommendation:** Store items as a Redis LIST (RPUSH individual items) and use LRANGE for pagination. Or use Redis Sorted Sets for ordered pagination.

### DB-010: No Backup Strategy

- **Severity:** Low
- **Description:** No backup mechanism exists for the SQLite database or Redis data. The SQLite file is a single point of failure.
- **Impact:** Data loss on disk failure (mitigated by ephemeral nature on Railway). Redis data is inherently volatile.
- **Estimated Effort:** 4 hours
- **Recommendation:** For production, migrate to Supabase (which handles backups). For POC, accept the risk. If staying with SQLite, add periodic WAL checkpoints and file-level backups.

### DB-011: Graceful Degradation Hides Failures Silently

- **Severity:** Low
- **Description:** Both `Database` methods and `RedisJobStore` methods silently return empty results or None when the connection is unavailable (e.g., `if not self._db: return []`). While this enables graceful degradation, it also means data persistence failures go unnoticed.
- **Impact:** Search history may silently not be recorded. Operators have no visibility into persistence failures unless they check logs.
- **Estimated Effort:** 2 hours
- **Recommendation:** Add structured metrics/counters for persistence failures. Emit warnings that are surfaced in health checks (e.g., `"database": "degraded"` in `/health` response).

### DB-012: Supabase Env Vars Defined but Unused

- **Severity:** Low
- **Description:** The root `.env.example` defines `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`, but no code references these variables. No Supabase client library is installed.
- **Impact:** Confusing for developers who assume Supabase is integrated. Placeholder variables without implementation.
- **Estimated Effort:** 0.5 hours
- **Recommendation:** Either remove the Supabase env vars from `.env.example` (add them back when Supabase is integrated), or add a comment marking them as "planned / not yet implemented."

### DB-013: No Transaction Boundaries for Multi-Step Operations

- **Severity:** Low
- **Description:** Each `Database` method commits immediately after its single SQL statement (`await self._db.commit()`). The `record_search` and `complete_search` calls in `run_search_job` are separated by the entire search pipeline execution.
- **Impact:** No atomicity risk currently (single-statement operations). However, if more complex multi-table operations are added, the lack of explicit transaction management could cause inconsistencies.
- **Estimated Effort:** 2 hours
- **Recommendation:** Acceptable for current single-statement operations. When adding multi-table operations, introduce explicit transaction context managers.

---

## 5. Priority Summary

| Priority | Items | Action |
|----------|-------|--------|
| **Critical** | None | -- |
| **High** | DB-001, DB-002, DB-003 | Address before production launch |
| **Medium** | DB-004, DB-005, DB-006, DB-007, DB-008, DB-009 | Address in next sprint |
| **Low** | DB-010, DB-011, DB-012, DB-013 | Address opportunistically |

### Recommended Migration Path

The highest-impact improvement is **DB-002 (Supabase migration)**, which would simultaneously resolve:
- DB-001 (multi-tenant isolation via RLS)
- DB-002 (durable storage)
- DB-003 (migration system via Supabase CLI)
- DB-008 (retention policies via PostgreSQL)
- DB-010 (managed backups)

**Estimated total effort for Supabase migration:** 24-32 hours, including:
- Schema design in PostgreSQL (4h)
- RLS policies (4h)
- Backend client migration from aiosqlite to supabase-py or asyncpg (8h)
- Migration system setup (4h)
- Testing and validation (4-8h)
- Frontend Supabase client setup for future auth/realtime features (4h)
