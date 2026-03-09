# Adding New Data Sources

## Active Sources (v2-story-1.0)

| Source | File | Status |
|--------|------|--------|
| PNCP | `pncp_source.py` | Active (primary) |
| Portal da Transparencia | `transparencia_source.py` | Active |

## How to Add a New Source

1. **Create the adapter** in `sources/<name>_source.py`:
   - Extend `DataSourceClient` from `sources/base.py`
   - Implement `source_name`, `fetch_records()`, `normalize()`, `is_healthy()`

2. **Add config** in `config.py` → `SOURCES_CONFIG`:
   ```python
   "new_source": {
       "enabled": True,
       "base_url": "https://api.example.com",
       "auth": None,
       "rate_limit_rps": 5,
       "timeout": 60,
       "priority": 3,
   }
   ```

3. **Register** in `dependencies.py` → `init_dependencies()`:
   ```python
   from sources.new_source import NewSource
   sources = [_pncp_source, TransparenciaSource(), NewSource()]
   ```

4. **Write tests** in `tests/test_new_source.py`

5. **Test orchestrator integration**: Ensure the new source works with
   deduplication and graceful degradation via existing orchestrator tests.

## Removed Sources (TD-C03, March 2026)

| Source | Reason | Removal Date |
|--------|--------|-------------|
| ComprasGov | API deprecated, returns 404 | 2026-03-09 |
| Querido Diario | API returns HTML instead of JSON | 2026-03-09 |
| TCE-RJ | API endpoint returns 404 | 2026-03-09 |
