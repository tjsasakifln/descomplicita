# [v2] Story 5.0: Polish & Infrastructure
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Sprint final de polish, testes cross-cutting, e resolucao de debitos de baixa prioridade. Relacao com v1.0:

- **TD-M03 (modelo LLM hardcoded):** Novo na v2.0 -- `gpt-4.1-nano` hardcoded ignorando env var
- **XD-TEST-01/02/03 (testes cross-cutting):** Novos na v2.0 -- integracao, smoke tests, regressao visual
- **TD-M09 (MD5):** Novo na v2.0 -- risco teorico rebaixado para P5
- **TD-L03 (localStorage):** Novo na v2.0 -- buscas salvas sem persistencia server-side
- **TD-L05 (keywords grandes):** Novo na v2.0 -- concern de performance em escala
- **XD-TEST-03 (regressao visual):** Novo na v2.0 -- considerado prematuro para POC por @qa

A v1.0 story 5.0 focava em deprecated APIs, branding, observability (Sentry), e graceful shutdown. Varios desses itens podem ja ter sido resolvidos.

### Objetivo

Fechar debitos de baixa prioridade restantes, implementar testes cross-cutting (integracao, smoke tests pos-deploy), configuracoes operacionais (modelo LLM, bundle baseline), e resolver gaps identificados pelo QA. Ao final deste sprint, todos os 55 debitos da v2.0 estarao enderecados.

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| TD-M03 | Modelo LLM hardcoded (gpt-4.1-nano) | Media | 2-4h | NOVO |
| XD-TEST-01 | Sem testes de integracao frontend-backend | Media | 4-8h | NOVO |
| XD-TEST-02 | Sem smoke tests pos-deploy | Media | 2-4h | NOVO |
| XD-TEST-03 | Sem testes de regressao visual | Baixa | 4-8h | NOVO (prematuro para POC per @qa) |
| TD-M09 | MD5 usado para chaves de dedup | Baixa | 2-4h | NOVO |
| TD-L03 | Buscas salvas apenas em localStorage | Baixa | 2-4h | NOVO |
| TD-L05 | Conjuntos grandes de keywords/exclusoes | Baixa | 2-4h | NOVO |

#### Gaps do QA (da secao "Gaps Reconhecidos" da avaliacao)

| Gap | Debito | Horas | Status |
|-----|--------|-------|--------|
| G-01 | Backend test coverage nao quantificada | 1-2h | ACAO IMEDIATA |
| G-04 | Sem scan de vulnerabilidades em dependencias | 2-4h | NOVO |
| G-10 | Bundle size nao baselinado | 2-4h | NOVO |

### Tasks

#### Configuracao Operacional

- [x] Task 1: TD-M03 -- Refatorado `llm.py` para ler `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` de env vars com fallback para defaults.
- [x] Task 2: TD-M03 -- Testes adicionados: `test_gerar_resumo_custom_model` e `test_gerar_resumo_custom_temperature_and_tokens` verificam troca via env var.

#### Testes Cross-Cutting

- [x] Task 3: XD-TEST-01 -- Implementado MSW (Mock Service Worker) com handlers para 6 endpoints. Arquivo: `__tests__/integration/mswHandlers.ts`.
- [x] Task 4: XD-TEST-01 -- 18 cenarios de integracao: busca sucesso (5), erro (4), polling timeout (3), download Excel (4), setores (2).
- [x] Task 5: XD-TEST-02 -- Smoke tests ja existiam em `deploy.yml`. Adicionado check de `/setores`. Cobertura: `/health`, `/`, `/docs`, `/setores`, `POST /buscar`.
- [x] Task 6: XD-TEST-02 -- Configurado alerta automatico via GitHub Issues com label `smoke-test-failure` em caso de falha.
- [x] Task 7: XD-TEST-03 -- AVALIADO: Prematuro para POC. Requer design system para viabilidade. Documentado para implementacao futura.

#### Gaps do QA

- [x] Task 8: G-01 -- Coverage documentada em `backend/scripts/coverage_report.md`. Threshold de 70% enforced em pyproject.toml + CI (backend-ci.yml + tests.yml).
- [x] Task 9: G-04 -- `pip audit --strict` adicionado a backend-ci.yml e tests.yml. `npm audit --audit-level=high` adicionado a tests.yml (frontend-tests job).
- [x] Task 10: G-10 -- Bundle size baseline via `.github/workflows/bundle-size.yml`. Budget: 500KB JS. Executa em PRs com changes em frontend/.

#### Debitos de Baixa Prioridade

- [x] Task 11: TD-M09 -- AVALIADO: MD5 aceitavel para chaves de dedup (nao-criptografico). Risco de colisao desprezivel para ~10k registros. Decisao documentada.
- [x] Task 12: TD-L03 -- AVALIADO: localStorage adequado para POC (max 10 buscas). Migracao server-side depende de autenticacao de usuario (nao implementada). Deferido para pos-POC.
- [x] Task 13: TD-L05 -- AVALIADO: Performance adequada para escala atual (~10k registros). Fail-fast exclusions + string matching eficiente. Trie/regex pre-compilado desnecessario.

### Criterios de Aceite

- [x] Modelo LLM configuravel via env var sem alterar codigo
- [x] Pelo menos 4 cenarios de integracao com MSW passando (18 cenarios implementados)
- [x] Smoke tests pos-deploy rodando automaticamente em GitHub Actions
- [x] Backend test coverage medido e documentado (>= 70%)
- [x] `pip audit` e `npm audit` no CI, falhando em vulnerabilidades criticas/altas
- [x] Bundle size baselinado e budget configurado (500KB)
- [x] Todos os 55 debitos da v2.0 enderecados (resolvidos ou documentados como decisoes conscientes)

### Testes Requeridos

- [x] Teste de integracao MSW: busca sucesso, erro, timeout, download
- [x] Smoke test: endpoints criticos respondem com status 200
- [x] Coverage: `pytest --cov` reporta >= 70%
- [x] Audit: `pip audit` sem vulnerabilidades criticas/altas
- [x] Audit: `npm audit --audit-level=high` sem vulnerabilidades criticas/altas
- [x] Teste unitario: LLM_MODEL env var e lido corretamente
- [x] Teste de regressao: todos os testes existentes continuam passando

### Estimativa

- Horas: 30-40
- Custo: R$ 4.500-6.000 (estimativa a R$ 150/h)
- Sprint: 4 (1-2 semanas, apos sprints 2-3)

### Dependencias

- Depende de: v2-story-1.0 (security), v2-story-2.0 (frontend arch), v2-story-4.0 (backend arch)
- Depende de: v2-story-4.0 TD-H04 (database) para TD-L03 (buscas salvas server-side)
- Bloqueia: Nenhuma (sprint final)
- Nota: XD-TEST-03 (regressao visual) pode ser adiado para apos design system per @qa

### Definition of Done

- [x] Codigo implementado
- [x] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado
- [x] Todos os 55 debitos documentados como resolvidos ou conscientemente adiados
- [x] Metricas de sucesso da avaliacao v2.0 atingidas (coverage, security headers, smoke tests)

---

### Decisoes Tecnicas Documentadas

#### TD-M09: MD5 para Chaves de Deduplicacao
- **Decisao**: Manter MD5
- **Justificativa**: Uso nao-criptografico (hash para dedup keys). Risco de colisao birthday-problem requer ~2^64 operacoes -- desprezivel para ~10k registros. SHA-256 adicionaria overhead sem beneficio pratico.
- **Arquivos**: `backend/sources/orchestrator.py`, `backend/sources/transparencia_source.py`

#### TD-L03: Buscas Salvas em localStorage
- **Decisao**: Manter localStorage, deferido para server-side
- **Justificativa**: POC sem autenticacao de usuario. Max 10 buscas em localStorage e adequado. Database (SQLite) existe via TD-H04 mas migracao requer auth layer.
- **Dependencia**: Implementacao de autenticacao de usuario
- **Arquivos**: `frontend/lib/savedSearches.ts`, `backend/database.py`

#### TD-L05: Performance de Keywords (~130 inclusao + ~100 exclusao)
- **Decisao**: Manter implementacao atual
- **Justificativa**: String matching com `in` operator e fail-fast exclusions adequados para ~10k registros por busca. Trie ou pre-compilacao de regex so justificavel em 100k+ registros (alem do limite PNCP).
- **Arquivos**: `backend/filter.py`, `backend/sectors.py`

#### XD-TEST-03: Testes de Regressao Visual
- **Decisao**: Deferido para pos-design system
- **Justificativa**: 5 temas x breakpoints responsivos = alto custo de manutencao de snapshots. Sem design system estavel, snapshots quebrariam frequentemente. Recomendado: implementar apos design system com Chromatic ou Percy.
- **Prerequisito**: Design system estabilizado
