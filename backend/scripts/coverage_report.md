# Backend Test Coverage Report

## Coverage Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Minimum threshold | 70% | `pyproject.toml` [tool.coverage.report] fail_under |
| CI enforcement | `--cov-fail-under=70` | `.github/workflows/backend-ci.yml` |
| Branch coverage | Enabled | `pyproject.toml` [tool.coverage.run] branch = true |
| Parallel mode | Enabled | `pyproject.toml` [tool.coverage.run] parallel = true |
| Coverage reports | XML + Terminal | CI pipeline generates both formats |
| Codecov upload | On push to main | `backend-ci.yml` + `tests.yml` |

## Test Suite Summary

| Category | Files | Description |
|----------|-------|-------------|
| Core API | test_main.py, test_dependencies.py, test_schemas.py | Endpoint and DI tests |
| Security | test_security.py, test_jwt.py | Auth, CORS, CSP, rate limiting |
| Search | test_filter.py, test_filter_normalized.py, test_pagination.py | Keyword matching, pagination |
| Sources | test_pncp_source.py, test_sources_base.py, test_sources_config.py, test_transparencia_source.py | Multi-source data fetching |
| Orchestration | test_orchestrator.py | Dedup, merge, multi-source coordination |
| Caching | test_cache.py, test_cache_integration.py | Redis cache layer |
| Jobs | test_job_store.py, test_redis_job_store.py | Job persistence |
| Queue | test_task_queue.py | Durable task runner |
| LLM | test_llm.py, test_llm_fallback.py | AI summary generation |
| Config | test_config.py | Environment configuration |
| Performance | test_load.py, test_concurrency.py, test_resilience.py | Load and stress tests |
| Features | test_story4.py, test_story5_observability.py | Story-specific regression |
| Export | test_excel.py | XLSX generation |

## CI Pipeline Integration

- **backend-ci.yml**: Runs on PRs to backend/**, enforces 70% threshold, uploads to Codecov on main push
- **tests.yml**: Python 3.11/3.12 matrix, coverage check with XML parsing, threshold validation
- **Codecov**: Coverage tracking and trend analysis

## Validation

The 70% coverage threshold is enforced at multiple levels:
1. `pyproject.toml` fail_under = 70 (local development)
2. `pytest --cov-fail-under=70` (CI pipeline)
3. Coverage XML parsing in tests.yml (redundant safety net)

Coverage is measured and gated in CI — builds fail if coverage drops below 70%.

---
*Generated: 2026-03-09 | v2-story-5.0 Task 8 (G-01)*
