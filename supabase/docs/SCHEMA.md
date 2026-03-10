# Database Schema Documentation

> **Generated:** 2026-03-09 | **Agent:** @data-engineer (Delphi)
> **Database Engine:** SQLite 3 (via aiosqlite 0.20.0)
> **ORM/Driver:** Raw SQL with aiosqlite (no ORM)
> **File Location:** `backend/descomplicita.db` (or `$DATA_DIR/descomplicita.db`)

---

## 1. Schema Overview

The Descomplicita backend uses a **minimal SQLite persistence layer** designed for POC-level storage. There is no Supabase or PostgreSQL in use despite environment placeholders existing in `.env.example`. The database serves two purposes:

1. **Search History** -- records every search job (parameters, results, timing)
2. **User Preferences** -- key-value store for user settings

Additionally, **Redis** (not SQLite) serves as the primary data store for:
- Job state and progress (`job:{id}` keys)
- Excel file bytes (`excel:{id}` keys)
- Filtered items for pagination (`job:{id}:items` keys)
- PNCP API response cache (`pncp_cache:*` keys)
- Durable task parameters (`job_params:{id}` keys)

### Storage Architecture Summary

| Store | Engine | Purpose | Persistence |
|-------|--------|---------|-------------|
| `search_history` | SQLite | Search audit trail | Durable (file-based) |
| `user_preferences` | SQLite | User settings (key-value) | Durable (file-based) |
| Job state | Redis (or in-memory fallback) | Active job tracking | TTL-based (24h) |
| Excel bytes | Redis (or in-memory fallback) | Download files | TTL-based (2h) |
| PNCP cache | Redis (or in-memory fallback) | API response caching | TTL-based (4h) |

---

## 2. Table Definitions

### 2.1 `search_history`

Records every search job submitted through the `/buscar` endpoint.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-incrementing row ID |
| `job_id` | TEXT | NOT NULL, UNIQUE | UUID v4 job identifier |
| `ufs` | TEXT | NOT NULL | JSON array of Brazilian state codes (e.g., `["SP","RJ"]`) |
| `data_inicial` | TEXT | NOT NULL | Search start date (YYYY-MM-DD) |
| `data_final` | TEXT | NOT NULL | Search end date (YYYY-MM-DD) |
| `setor_id` | TEXT | NOT NULL | Sector identifier (e.g., `vestuario`, `alimentos`) |
| `termos_busca` | TEXT | (nullable) | Custom search terms provided by user |
| `total_raw` | INTEGER | DEFAULT 0 | Total records fetched before filtering |
| `total_filtrado` | INTEGER | DEFAULT 0 | Total records after filtering |
| `status` | TEXT | DEFAULT 'queued' | Job status: `queued`, `completed`, `failed` |
| `created_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp of job creation |
| `completed_at` | TEXT | (nullable) | ISO 8601 UTC timestamp of job completion |
| `elapsed_seconds` | REAL | (nullable) | Total job execution time in seconds |

**Indexes:**

| Index Name | Column(s) | Purpose |
|------------|-----------|---------|
| `idx_search_history_created` | `created_at DESC` | Fast retrieval of recent searches |
| `idx_search_history_setor` | `setor_id` | Filter searches by sector |

### 2.2 `user_preferences`

Generic key-value store for user preferences.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-incrementing row ID |
| `key` | TEXT | NOT NULL, UNIQUE | Preference identifier |
| `value` | TEXT | NOT NULL | JSON-serialized value |
| `updated_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp of last update |

**Indexes:**

| Index Name | Column(s) | Purpose |
|------------|-----------|---------|
| (implicit UNIQUE) | `key` | Enforced by UNIQUE constraint |

---

## 3. Relationships

There are **no foreign key relationships** between tables. The schema is flat:

- `search_history` is a standalone audit log
- `user_preferences` is a standalone key-value store
- `job_id` in `search_history` corresponds to Redis job keys (`job:{id}`) but this relationship is **not enforced** at the database level -- it is maintained by application logic in `main.py`

---

## 4. Row Level Security (RLS)

**Not applicable.** SQLite does not support RLS. There is no Supabase/PostgreSQL in use.

Access control is handled at the application layer:
- **API Key middleware** (`middleware/auth.py`) -- validates `X-API-Key` header
- **JWT authentication** (`auth/jwt.py`) -- HMAC-SHA256 signed tokens
- All database operations flow through the FastAPI dependency injection system
- The `/search-history` endpoint exposes data without user-scoping (see audit)

---

## 5. Functions / Triggers

**None.** The database uses no triggers, stored procedures, or views. All logic is in the Python application layer (`database.py`).

### Database Operations (Application Layer)

| Method | SQL Operation | Called From |
|--------|--------------|-------------|
| `Database.record_search()` | `INSERT OR IGNORE INTO search_history` | `POST /buscar` (job creation) |
| `Database.complete_search()` | `UPDATE search_history SET status='completed'` | `run_search_job()` (on success) |
| `Database.fail_search()` | `UPDATE search_history SET status='failed'` | `run_search_job()` (on error) |
| `Database.get_recent_searches()` | `SELECT ... FROM search_history ORDER BY created_at DESC LIMIT ?` | `GET /search-history` |
| `Database.set_preference()` | `INSERT ... ON CONFLICT(key) DO UPDATE` (upsert) | Not currently called by any endpoint |
| `Database.get_preference()` | `SELECT value FROM user_preferences WHERE key=?` | Not currently called by any endpoint |
| `Database.get_all_preferences()` | `SELECT key, value FROM user_preferences` | Not currently called by any endpoint |

---

## 6. Migrations

**There is no migration system.** Schema creation uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements executed on every application startup via `Database.connect()`.

The schema SQL is defined inline in `backend/database.py` as the `_SCHEMA_SQL` constant (lines 30-59).

### Migration History

| Version | Date | Description |
|---------|------|-------------|
| v1 (initial) | ~2026-02 | `search_history` + `user_preferences` tables created (TD-H04) |

There are no subsequent migrations. Schema changes would require manual `ALTER TABLE` or recreating the database.

---

## 7. Data Flow

### 7.1 Search Job Lifecycle

```
User POST /buscar
  |
  +--> [FastAPI] Create UUID job_id
  |
  +--> [SQLite] record_search(job_id, params)     -- Insert "queued" row
  |
  +--> [Redis]  job:{id} = {status: "queued"}      -- Create job state
  |
  +--> [TaskRunner] enqueue background coroutine
         |
         +--> [PNCP API] Fetch procurement records
         |
         +--> [Redis] Update job progress
         |
         +--> [Filter] Apply keyword/value/UF filters
         |
         +--> [Redis] Store filtered items (job:{id}:items)
         |
         +--> [LLM] Generate executive summary
         |
         +--> [Redis] Store Excel bytes (excel:{id})
         |
         +--> [Redis] Complete job (job:{id} = completed)
         |
         +--> [SQLite] complete_search(job_id, totals, elapsed)
```

### 7.2 Data Retrieval

```
GET /buscar/{id}/status  --> Redis (job state)
GET /buscar/{id}/result  --> Redis (job result JSON)
GET /buscar/{id}/items   --> Redis (paginated items, fallback from in-memory)
GET /buscar/{id}/download --> Redis (excel bytes)
GET /search-history      --> SQLite (recent search rows)
```

### 7.3 Redis Key Schema

| Key Pattern | Value Type | TTL | Purpose |
|-------------|-----------|-----|---------|
| `job:{uuid}` | JSON string | 24h | Job state, progress, result |
| `excel:{uuid}` | Raw bytes | 2h | Excel report file |
| `job:{uuid}:items` | JSON string (array) | 24h | Filtered items for pagination |
| `job_params:{uuid}` | JSON string | 24h | Durable task parameters (crash recovery) |
| `pncp_cache:{uf}:{modalidade}:{date}:{date}` | JSON string (array) | 4h | Cached PNCP API responses |

---

## 8. Supabase Status

The root `.env.example` contains `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` placeholders, but **Supabase is not integrated into the codebase**. No Supabase client library is installed, no frontend code references Supabase, and no migrations exist in the `supabase/` directory.

The `database.py` module header explicitly states:
> "Future migration path: Supabase PostgreSQL for production persistence"

The current database is SQLite, intended as a zero-cost POC solution with ephemeral-safe characteristics for Railway/Vercel deployments.
