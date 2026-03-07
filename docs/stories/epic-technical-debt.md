# Epic: Resolucao de Debitos Tecnicos -- Descomplicita

## Objetivo

Systematically resolve all 57 identified technical debts across security, accessibility, architecture, code quality, and infrastructure to bring the Descomplicita platform to production-grade standards. The platform currently has critical security vulnerabilities (unauthenticated endpoints, wildcard CORS, root containers), broken tests, a monolithic frontend component blocking all feature work, and systemic WCAG accessibility gaps that violate Brazilian accessibility law (LBI -- Law 13.146/2015).

## Escopo

- Total de debitos: 57 (5 Critical, 13 High, 22 Medium, 17 Low)
- Sprints planejados: 6 (Sprint 0 through Sprint 5) + Backlog
- Timeline: ~10 semanas
- Esforco estimado: 173-287 horas (scheduled) / 206-388 horas (including backlog)
- Codebase baseline: commit 9fbd54d0 (main branch)

## Criterios de Sucesso

- [ ] All 5 critical debts resolved (TD-001, TD-002, TD-003 Phase 1, TD-004, TD-054)
- [ ] Frontend test coverage >= 65% statements after Sprint 2, >= 80% long-term
- [ ] Backend test coverage maintained >= 70% (CI enforcement without `continue-on-error`)
- [ ] Zero WCAG AA critical/serious violations (axe-core gated in E2E)
- [ ] CORS restricted to whitelisted origins
- [ ] API key authentication on all endpoints
- [ ] No containers running as root
- [ ] Debug endpoints disabled in production
- [ ] All test assertions reference "Descomplicita" (not "Descomplicita")
- [ ] E2E happy-path test passes on current codebase
- [ ] Sentry capturing production errors (backend + frontend)
- [ ] Job state survives container restart (Redis-backed)

## Stories

| Story | Sprint | Points | Priority |
|-------|--------|--------|----------|
| Story 0.0: Emergency Fixes -- Unblock CI | Sprint 0 | 3 | Critical |
| Story 1.0: Security Hardening + Quick Wins | Sprint 1 | 13 | Critical |
| Story 2.0: Frontend Architecture -- God Component Decomposition | Sprint 2 | 13 | Critical |
| Story 3.0: Frontend Quality + Accessibility Compliance | Sprint 3 | 13 | High |
| Story 4.0: Backend Architecture -- Persistent Storage + Async | Sprint 4 | 21 | High |
| Story 5.0: Polish + Infrastructure + Observability | Sprint 5 | 13 | Medium |

**Total Story Points: 76**

## Sprint-by-Sprint Debt Allocation

### Sprint 0: Emergency Fixes (Week 1, Days 1-2) -- 3-5 hours
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-054 | Broken backend test assertions (Descomplicita title) | 1-2 | Backend |
| TD-041 | E2E tests reference outdated class names | 2-3 | Frontend |

### Sprint 1: Security Hardening + Quick Wins (Weeks 1-2) -- 22-41 hours
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-001 | CORS allows all origins | 1-2 | Backend |
| TD-002 | Backend Dockerfile runs as root | 1-2 | Backend |
| TD-003 | No authentication (Phase 1: API key) | 4-8 | Backend |
| TD-006 | No per-IP/user rate limiting | 4-8 | Backend |
| TD-012 | Dev dependencies in production image | 2-4 | Backend |
| TD-055 | Debug endpoints exposed in production | 2-4 | Backend |
| TD-056 | Unbounded termos_busca input length | 1-2 | Backend |
| TD-009 | Missing Escape key on dropdowns | 2-3 | Frontend |
| TD-010 | Insufficient color contrast (ink-muted) | 4-6 | Frontend |
| TD-027 | No skip-to-content link | 1-2 | Frontend |

### Sprint 2: Frontend Architecture (Weeks 3-4) -- 31-45 hours
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-004 | God component (page.tsx, 1071 lines) | 28-40 | Frontend |
| TD-021 | Duplicate UFS constant definition | 1-2 | Frontend |
| TD-028 | External logo dependency (Wix CDN) | 2-3 | Frontend |
| TD-045 | Unused public asset (resolved by TD-028) | 0 | Frontend |

### Sprint 3: Frontend Quality + Accessibility (Weeks 5-6) -- 29-47 hours
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-008 | Modal missing focus trap and dialog role | 4-6 | Frontend |
| TD-031 | Missing focus management after search | 3-5 | Frontend |
| TD-029 | Outdated favicon (Descomplicita "B") | 1-2 | Frontend |
| TD-030 | Error boundary uses hardcoded colors | 2-4 | Frontend |
| TD-042 | No code splitting for components | 4-6 | Frontend |
| TD-043 | No nav semantic element | 1 | Frontend |
| TD-044 | SourceBadges/carouselData hardcoded colors | 3-5 | Frontend |
| TD-046 | Missing aria-describedby for terms input | 1 | Frontend |
| TD-047 | Dropdown menus lack ARIA menu pattern | 2-3 | Frontend |
| TD-048 | window.confirm() for destructive action | 2-3 | Frontend |
| TD-049 | EmptyState lacks ARIA live region | 1 | Frontend |
| TD-050 | SourceBadges lacks aria-expanded | 1-2 | Frontend |
| TD-051 | UF grid buttons lack group label | 1-2 | Frontend |
| TD-052 | No heading hierarchy in main sections | 1-2 | Frontend |
| TD-053 | Hardcoded borderColor in ThemeToggle | 0.5 | Frontend |

### Sprint 4: Backend Architecture (Weeks 7-8) -- 58-96 hours
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-005 | In-memory job store not scalable | 16-24 | Backend |
| TD-013 | Global mutable singletons | 8-12 | Backend |
| TD-014 | Deprecated startup event pattern | 2-4 | Backend |
| TD-026 | Cache not shared across restarts | 8-16 | Backend |
| TD-007 | Excel base64 in JSON response | 8-16 | Backend |
| TD-023 | Excel download uses filesystem tmpdir | 0 | Backend |
| TD-011 | PNCP client uses blocking requests lib | 16-24 | Backend |

### Sprint 5: Polish + Infrastructure (Weeks 9-10) -- 30-53 hours
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-015 | datetime.utcnow() deprecated | 1-2 | Backend |
| TD-016 | Branding inconsistency (Descomplicita remnants) | 4-8 | Both |
| TD-017 | No request/correlation ID logging | 4-8 | Backend |
| TD-018 | Hardcoded PNCP base URL | 1-2 | Backend |
| TD-020 | Filter diagnostic code in production | 1-2 | Backend |
| TD-022 | No OpenAPI schema for result endpoint | 2-4 | Backend |
| TD-024 | asyncio.get_event_loop() deprecated | 1-2 | Backend |
| TD-025 | No graceful shutdown | 4-8 | Backend |
| TD-033 | f-string in logger calls | 2-4 | Backend |
| TD-035 | Frontend emoji in source code | 1 | Frontend |
| TD-036 | No content-length validation for downloads | 1-2 | Backend |
| TD-037 | Date range max removed | 1-2 | Backend |
| TD-038 | Module-level singleton in job_store.py | 1 | Backend |
| TD-039 | Deprecated performance API in AnalyticsProvider | 1 | Frontend |
| TD-057 | No Sentry/APM integration | 4-8 | Both |

### Backlog (Unscheduled)
| ID | Debt | Hours | Owner |
|----|------|-------|-------|
| TD-003 Ph2 | JWT user accounts | 12-32 | Backend |
| TD-019 | API versioning | 4-8 | Backend |
| TD-032 | No structured error codes | 4-8 | Backend |
| TD-034 | No pagination for sectors endpoint | 1-2 | Backend |
| TD-040 | No loading state for sector list | 1-2 | Frontend |

## Riscos

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CORS exploitation before Sprint 1 | High | High | Prioritize TD-001 as first fix in Sprint 1 |
| Resource exhaustion (no auth) | High | High | API key auth in Sprint 1 |
| Root container escape | Low | Critical | Sprint 1 Dockerfile fix |
| Debug endpoint abuse (cache clear) | Medium | Medium | Feature flag or auth gate in Sprint 1 |
| TD-004 decomposition regression | High | High | Sprint 0 E2E baseline; incremental extraction |
| Redis migration data loss | Medium | Medium | Dual-write (in-memory + Redis) during transition |
| httpx migration response parity | Medium | Medium | Compare result counts old vs new on same query |
| Coverage drop during decomposition | High | Low | Enforce per-component coverage, not global threshold |
| Unbounded date range query abuse | Low | Medium | Re-introduce configurable max (90 days) |
| Production errors go unnoticed | High | Medium | Sentry integration in Sprint 5 |

## Dependencias

```
Sprint 0 is a PREREQUISITE for ALL subsequent sprints.

Sprint 1 has no dependencies beyond Sprint 0.

Sprint 2 depends on Sprint 0 (E2E baseline required).
  TD-004 decomposition UNBLOCKS Sprint 3 items: TD-008, TD-031, TD-042.

Sprint 3 depends on Sprint 2 (TD-004 extraction must be complete).
  TD-008 (modal a11y) requires SaveSearchDialog extracted in TD-004.
  TD-031 (focus management) is easier after TD-004 extraction.
  TD-042 (code splitting) requires separate components from TD-004.

Sprint 4 has no hard dependency on Sprints 2-3 (backend-only).
  TD-005 and TD-026 share Redis infrastructure (do together).
  TD-007 and TD-023 are paired (Excel delivery refactor).
  TD-013 and TD-014 are tightly coupled (DI + lifespan).

Sprint 5 has no hard dependency on Sprint 4.
  TD-015 and TD-024 must include test file updates.
  TD-016 branding cleanup includes TD-029 favicon if not done in Sprint 3.

Sprints 2-3 (Frontend) and Sprints 4-5 (Backend) can be parallelized
with separate developers.
```

## Notas

- Hours assume a single developer per task
- Backend and frontend sprints can be parallelized with separate developers
- Sprint 4 is the largest block (58-96 hours) and benefits most from parallel execution of Redis and httpx workstreams
- Story points use a rough 1 point = 4 hours mapping at the midpoint of each sprint's estimate range
- The 91.5% frontend coverage claim in the architecture document is incorrect; actual coverage is ~49.45% statements
- Brazilian accessibility law (LBI -- Law 13.146/2015) applies to this government-facing tool

---

*Created: 2026-03-07*
*Source: docs/prd/technical-debt-assessment.md (v1.0 Validated)*
*Codebase at commit: 9fbd54d0 (main branch)*
