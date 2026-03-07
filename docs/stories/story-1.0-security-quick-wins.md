# Story 1.0: Security Hardening + Accessibility Quick Wins

**Sprint:** 1
**Epic:** Resolucao de Debitos Tecnicos
**Priority:** Critical
**Estimated Points:** 13
**Estimated Hours:** 22-41

## Objetivo

Close all critical and high-priority security vulnerabilities before any public launch. The backend currently has no authentication, accepts requests from any origin (wildcard CORS), runs containers as root, and exposes debug endpoints. An unauthenticated attacker from any origin can exhaust all 10 job slots, trigger unlimited PNCP API calls, and clear the cache. This sprint also harvests accessibility quick wins (contrast, keyboard, skip-link) that require minimal effort.

## Debts Addressed

| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-001 | CORS allows all origins (`backend/main.py:76`) | 1-2 | Backend |
| TD-002 | Backend Dockerfile runs as root (`backend/Dockerfile`) | 1-2 | Backend |
| TD-003 | No authentication -- Phase 1: API key auth (`backend/main.py`, all endpoints) | 4-8 | Backend |
| TD-006 | No per-IP/user rate limiting | 4-8 | Backend |
| TD-012 | Dev dependencies in production image (`backend/Dockerfile`) | 2-4 | Backend |
| TD-055 | Debug endpoints exposed in production (`/cache/stats`, `/cache/clear`, `/debug/pncp-test`) | 2-4 | Backend |
| TD-056 | Unbounded `termos_busca` input length (`backend/schemas.py`) | 1-2 | Backend |
| TD-009 | Missing Escape key handling on dropdowns | 2-3 | Frontend |
| TD-010 | Insufficient color contrast (`--ink-muted`, `--ink-faint`) | 4-6 | Frontend |
| TD-027 | No skip-to-content link | 1-2 | Frontend |

## Tasks

### Security (Backend)

- [ ] Task 1: TD-001 -- Replace `allow_origins=["*"]` in `backend/main.py:76` with `["https://descomplicita.vercel.app", "http://localhost:3000"]`. Add `CORS_ORIGINS` environment variable parsed from comma-separated string.
- [ ] Task 2: TD-002 -- Add non-root user to `backend/Dockerfile`: `RUN adduser --disabled-password --no-create-home appuser` and `USER appuser` directive before CMD.
- [ ] Task 3: TD-003 -- Implement API key authentication middleware. Create `backend/middleware/auth.py` with header-based API key validation (`X-API-Key` header). Add `API_KEY` environment variable. Exempt health check endpoint.
- [ ] Task 4: TD-003 -- Update frontend to send API key header with all backend requests. Store API key in environment variable `NEXT_PUBLIC_API_KEY`.
- [ ] Task 5: TD-006 -- Install `slowapi` and configure per-IP rate limiting on search and download endpoints. Set limits: 10 searches/minute, 30 result polls/minute, 5 downloads/minute per IP.
- [ ] Task 6: TD-012 -- Split `backend/Dockerfile` into multi-stage build. Use `requirements.txt` (production only) in final stage. Move dev dependencies to `requirements-dev.txt`.
- [ ] Task 7: TD-055 -- Gate `/cache/stats`, `/cache/clear`, and `/debug/pncp-test` behind environment-based feature flag (`ENABLE_DEBUG_ENDPOINTS=false` by default). Return 404 when disabled.
- [ ] Task 8: TD-056 -- Add `max_length=500` to `termos_busca` field in `backend/schemas.py` Pydantic model.

### Accessibility (Frontend)

- [ ] Task 9: TD-009 -- Add `onKeyDown` handler to all dropdown components: close on Escape key press, return focus to trigger element.
- [ ] Task 10: TD-010 -- Update CSS custom property `--ink-muted` to `#5a6a7a` (light themes, 4.86:1 ratio) and `#8a99a9` (dark themes, 5.2:1 ratio). Restrict `--ink-faint` to decorative elements only.
- [ ] Task 11: TD-027 -- Add skip-to-content link as first focusable element in `frontend/app/layout.tsx`. Link target: `#main-content`. Style: visible only on focus.

## Criterios de Aceite

- [ ] CORS rejects requests from origins not in the whitelist (verified with curl from arbitrary Origin header)
- [ ] Container process runs as non-root user (verified with `docker exec <container> whoami`)
- [ ] All API endpoints (except `/health`) return 401 without valid API key header
- [ ] Rate limiter returns 429 when limits are exceeded (verified with rapid curl requests)
- [ ] Production Docker image does not contain pytest, mypy, or other dev dependencies
- [ ] `/cache/clear` and `/debug/pncp-test` return 404 when `ENABLE_DEBUG_ENDPOINTS` is not set
- [ ] `termos_busca` rejects input longer than 500 characters with a 422 validation error
- [ ] Escape key closes all dropdown menus and returns focus to trigger
- [ ] All text using `--ink-muted` passes WCAG AA contrast ratio (>= 4.5:1) in all 5 themes
- [ ] Skip-to-content link is visible on keyboard focus and navigates to main content area
- [ ] Frontend successfully communicates with backend using API key header

## Testes Requeridos

- [ ] Unit test: CORS middleware rejects disallowed origins
- [ ] Unit test: CORS middleware allows whitelisted origins
- [ ] Unit test: API key middleware returns 401 for missing/invalid key
- [ ] Unit test: API key middleware passes valid key
- [ ] Unit test: Rate limiter returns 429 after threshold
- [ ] Unit test: `termos_busca` with 501+ characters returns 422
- [ ] Unit test: Debug endpoints return 404 when feature flag is off
- [ ] E2E test: Dropdown closes on Escape key
- [ ] E2E test: Skip-to-content link navigates to main content
- [ ] Manual/axe-core: Contrast check on `--ink-muted` across all 5 themes

## Dependencias

- Blocked by: Story 0.0 (CI must be green first)
- Blocks: None directly, but TD-003 (API key auth) is consumed by all subsequent backend work. TD-001 (CORS) should be deployed before TD-003 to avoid locking out the frontend during transition.

## Definition of Done

- [ ] Code reviewed
- [ ] All new and existing tests passing
- [ ] Coverage thresholds met (no regression)
- [ ] No regressions in existing functionality
- [ ] Documentation updated (README for API key setup, CORS configuration)
- [ ] Environment variables documented in `.env.example`
