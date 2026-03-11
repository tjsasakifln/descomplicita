# Story 2.1 -- Fundacao: Decomposicao do main.py e Qualidade de Codigo

## Contexto

O arquivo `main.py` do backend concentra ~1.230 linhas com toda a logica de endpoints, pipeline de busca, parsing de termos e execucao de tarefas. Este monolito dificulta onboarding de novos desenvolvedores, revisao de codigo, testes isolados e manutencao. Antes de refatorar, e necessario configurar um linter Python (ruff) e pre-commit hooks para garantir que a decomposicao nao introduza regressoes.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Sprint 2: Fundacao" e grafo de dependencias (TD-SYS-003 -> TD-SYS-008 -> TD-SYS-002)

## Objetivo

Configurar ferramentas de qualidade de codigo (linter + pre-commit hooks) e decompor `main.py` em modulos tematicos, reduzindo o arquivo principal para <300 linhas (apenas setup FastAPI, middleware e imports de routers).

## Tasks

- [ ] **Task 1** (TD-SYS-003) -- Configurar ruff como linter e formatador Python: criar `pyproject.toml` ou `ruff.toml` com regras adequadas, integrar no CI (GitHub Action), resolver erros iniciais de linting no codebase existente -- 4h
- [ ] **Task 2** (TD-SYS-008) -- Configurar pre-commit hooks: instalar husky + lint-staged para frontend (ESLint, Prettier), integrar ruff para backend via pre-commit framework. Garantir que hooks rodam em <10s -- 2h
- [ ] **Task 3** (TD-SYS-002) -- Decompor main.py em modulos tematicos. Sugestao de estrutura:
  - `routers/search.py` -- endpoints de busca (`/buscar`, `/buscar/{job_id}`, etc.)
  - `routers/auth.py` -- endpoints de autenticacao (`/auth/*`)
  - `routers/saved_searches.py` -- endpoints de buscas salvas
  - `routers/health.py` -- endpoints de health check e status
  - `services/search_pipeline.py` -- logica de pipeline de busca
  - `services/term_parser.py` -- parsing e validacao de termos
  - `main.py` -- apenas setup FastAPI, middleware, CORS, e `include_router()` -- 8h

## Criterios de Aceite

- [ ] `ruff check .` roda sem erros no CI
- [ ] `ruff format --check .` roda sem diferencas no CI
- [ ] Pre-commit hooks impedem commit de codigo com erros de linting
- [ ] `main.py` reduzido para <300 linhas
- [ ] Cada modulo extraido tem responsabilidade unica e clara
- [ ] Todos os endpoints mantidos com mesmos paths, metodos e comportamento
- [ ] Nenhuma regressao nos 1.349+ testes backend
- [ ] Imports circulares ausentes (verificar com ruff ou pyright)

## Testes Requeridos

- [ ] Todos os 1.349+ testes backend continuam passando sem modificacao (unit + integration)
- [ ] `ruff check .` passa no CI sem erros (CI)
- [ ] Novos testes de importacao: cada router importavel isoladamente sem side effects (unit)
- [ ] Testes de endpoint: mesmos paths retornam mesmos status codes e payloads (integration)
- [ ] Pre-commit hooks executam e bloqueiam codigo com erros (manual verification)

## Estimativa

- **Horas:** 14h
- **Complexidade:** Complexo (decomposicao de modulo monolitico requer manter compatibilidade total; linter pode revelar centenas de warnings iniciais)

## Dependencias

- **Depende de:** Story 1.2 (infraestrutura estavel, path alias corrigido)
- **Bloqueia:** Story 3.1 (testes de integracao CI, coverage, e demais melhorias estruturais)
- **Dependencia interna:** Task 2 depende de Task 1 (hooks precisam do linter); Task 3 depende de Tasks 1+2 (refatorar com linter ativo)

## Definition of Done

- [ ] Codigo implementado e revisado
- [ ] Todos os testes passando (existentes, sem modificacao)
- [ ] `ruff check .` e `ruff format --check .` passam no CI
- [ ] Pre-commit hooks configurados e funcionais
- [ ] main.py <300 linhas
- [ ] Review aprovado
- [ ] Sem regressoes em nenhum endpoint

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-SYS-003 (Critico), TD-SYS-008 (Alto), TD-SYS-002 (Critico)*
