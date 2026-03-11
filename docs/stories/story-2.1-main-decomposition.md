# Story 2.1 -- Fundacao: Decomposicao do main.py e Qualidade de Codigo

## Contexto

O arquivo `main.py` do backend concentra ~1.230 linhas com toda a logica de endpoints, pipeline de busca, parsing de termos e execucao de tarefas. Este monolito dificulta onboarding de novos desenvolvedores, revisao de codigo, testes isolados e manutencao. Antes de refatorar, e necessario configurar um linter Python (ruff) e pre-commit hooks para garantir que a decomposicao nao introduza regressoes.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Sprint 2: Fundacao" e grafo de dependencias (TD-SYS-003 -> TD-SYS-008 -> TD-SYS-002)

## Objetivo

Configurar ferramentas de qualidade de codigo (linter + pre-commit hooks) e decompor `main.py` em modulos tematicos, reduzindo o arquivo principal para <300 linhas (apenas setup FastAPI, middleware e imports de routers).

## Tasks

- [x] **Task 1** (TD-SYS-003) -- Configurar ruff como linter e formatador Python: criar `ruff.toml` com regras adequadas, integrar no CI (GitHub Action), resolver erros iniciais de linting no codebase existente -- 4h
- [x] **Task 2** (TD-SYS-008) -- Configurar pre-commit hooks: ruff linter + formatter para backend via pre-commit framework, plus general file hygiene hooks. Hooks rodam em <10s -- 2h
- [x] **Task 3** (TD-SYS-002) -- Decompor main.py em modulos tematicos:
  - `routers/search.py` -- endpoints de busca (`/buscar`, `/buscar/{job_id}`, etc.) + search history
  - `routers/auth.py` -- endpoints de autenticacao (`/auth/*`)
  - `routers/health.py` -- endpoints de health check, root, setores, debug/cache
  - `services/search_pipeline.py` -- logica de pipeline de busca (execute_search_pipeline)
  - `services/term_parser.py` -- parsing e validacao de termos (parse_multi_word_terms)
  - `rate_limit.py` -- instancia compartilhada do limiter (evita imports circulares)
  - `main.py` -- 270 linhas: setup FastAPI, middleware, CORS, lifespan, include_router(), re-exports para backward compat com testes -- 8h

## Criterios de Aceite

- [x] `ruff check .` roda sem erros no CI
- [x] `ruff format --check .` roda sem diferencas no CI
- [x] Pre-commit hooks impedem commit de codigo com erros de linting
- [x] `main.py` reduzido para <300 linhas (270 linhas)
- [x] Cada modulo extraido tem responsabilidade unica e clara
- [x] Todos os endpoints mantidos com mesmos paths, metodos e comportamento
- [x] Nenhuma regressao nos 1.349+ testes backend (1378 passando + 19 novos = 1397 total)
- [x] Imports circulares ausentes (verificado com testes e ruff)

## Testes Requeridos

- [x] Todos os 1.349+ testes backend continuam passando sem modificacao (1378 passed, 24 skipped)
- [x] `ruff check .` passa no CI sem erros (CI)
- [x] Novos testes de importacao: cada router importavel isoladamente sem side effects (19 testes em test_module_imports.py)
- [x] Testes de endpoint: mesmos paths retornam mesmos status codes e payloads (verificado via testes existentes)
- [x] Pre-commit hooks executam e bloqueiam codigo com erros (verificado manualmente)

## Estimativa

- **Horas:** 14h
- **Complexidade:** Complexo (decomposicao de modulo monolitico requer manter compatibilidade total; linter pode revelar centenas de warnings iniciais)

## Dependencias

- **Depende de:** Story 1.2 (infraestrutura estavel, path alias corrigido)
- **Bloqueia:** Story 3.1 (testes de integracao CI, coverage, e demais melhorias estruturais)
- **Dependencia interna:** Task 2 depende de Task 1 (hooks precisam do linter); Task 3 depende de Tasks 1+2 (refatorar com linter ativo)

## Definition of Done

- [x] Codigo implementado e revisado
- [x] Todos os testes passando (existentes, sem modificacao)
- [x] `ruff check .` e `ruff format --check .` passam no CI
- [x] Pre-commit hooks configurados e funcionais
- [x] main.py <300 linhas (270 linhas)
- [ ] Review aprovado
- [x] Sem regressoes em nenhum endpoint

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-SYS-003 (Critico), TD-SYS-008 (Alto), TD-SYS-002 (Critico)*
*Implementada em 2026-03-11 por @squad-creator (full squad)*
