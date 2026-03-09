# [v2] Story 4.0: Backend Architecture -- Structural Fixes
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Este sprint aborda debitos estruturais do backend identificados na avaliacao v2.0. Relacao com v1.0:

- **TD-H03 (async OpenAI):** Novo na v2.0 -- v1.0 TD-011 cobria migracao de `requests` para `httpx` no PNCP client; v2.0 TD-H03 foca no cliente OpenAI sincrono no thread pool
- **TD-H06 (Vercel timeout):** Novo na v2.0 como debt separado -- timeout de 10s em funcoes serverless
- **TD-H04 (sem database):** v1.0 nao tinha debt equivalente direto (era implicito em TD-005/TD-026); v2.0 eleva como Alta severidade
- **TD-M01 (filtro deadline):** Novo na v2.0 -- campo `dataAberturaProposta` mal interpretado
- **TD-M05 (estado global DI):** v1.0 TD-013 propunha DI com Depends(); pode ter sido parcialmente resolvido
- **TD-L06 (executor compartilhado):** Novo na v2.0 -- parte da cadeia cascading failure
- **TD-L01 (httpx sincrono):** Novo na v2.0 como debt separado
- **TD-L02 (error codes):** v1.0 TD-032 era similar, estava no backlog
- **XD-API-01/02 (versionamento, contratos):** v1.0 TD-019 era similar, estava no backlog

### Objetivo

Resolver debitos arquiteturais do backend que afetam resiliencia (async OpenAI, timeout Vercel, executor compartilhado), evolucao do produto (database, versionamento API), e qualidade de integracao (testes de contrato, error codes estruturados).

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| TD-H03 | API OpenAI sincrona no thread pool | Alta | 4-8h | NOVO (v1 TD-011 era PNCP, nao OpenAI) |
| TD-H06 | Timeout Vercel 10s em downloads grandes | Alta | 4-8h | NOVO |
| TD-H04 | Sem banco de dados (todo estado efemero) | Alta | 8-16h | NOVO como debt explicito |
| TD-M01 | Filtro de deadline desabilitado | Media | 4-8h | NOVO |
| TD-M05 | Estado global mutavel para DI | Media | 4-8h | REMANESCENTE (v1 TD-013 propunha DI; pode estar parcial) |
| TD-M06 | Sem versionamento de API | Media | 4-8h | REMANESCENTE (v1 TD-019 era backlog) |
| XD-API-01 | Sem versionamento de API end-to-end | Media | 4-8h | REMANESCENTE (v1 TD-019 era backlog) |
| XD-API-02 | Sem testes de contrato | Media | 4-8h | NOVO |
| TD-L06 | filter_batch no ThreadPoolExecutor padrao | Baixa | 2-4h | NOVO |
| TD-L01 | is_healthy() usa httpx sincrono | Baixa | 2-4h | NOVO |
| TD-L02 | Sem codigos de erro estruturados | Baixa | 2-4h | REMANESCENTE (v1 TD-032 era backlog) |
| XD-API-03 | Codigos de erro nao estruturados (cross-cutting) | Baixa | 2-4h | REMANESCENTE |

### Tasks

#### Cadeia de Cascading Failure (P2)

- [x] Task 1: TD-H03 -- Migrar `gerar_resumo()` de cliente OpenAI sincrono + `run_in_executor` para cliente async nativo (`openai.AsyncOpenAI`). Eliminar bloqueio de thread pool.
- [x] Task 2: TD-H03 -- Atualizar error handling para async (try/except async, fallback path).
- [x] Task 3: TD-L06 -- Criar ThreadPoolExecutor dedicado para `filter_batch`, separado do executor padrao usado por LLM. Ou, se TD-H03 resolver o bloqueio de thread, verificar se TD-L06 se torna irrelevante.
- [x] Task 4: TD-L01 -- Migrar `is_healthy()` de httpx sincrono para async. Nota: atualmente usado apenas em testes.

#### Streaming e Timeout (P2)

- [x] Task 5: TD-H06 -- Implementar streaming de response para rota de download, eliminando buffer completo antes de retorno. Considerar chunked transfer encoding.
- [x] Task 6: TD-H06 -- Avaliar limites de duracao do Vercel (10s free, 60s pro). Documentar restricoes para plano atual.

#### Persistencia (P2)

- [x] Task 7: TD-H04 -- Avaliar opcoes de database: Supabase (PostgreSQL managed), PlanetScale, Turso (SQLite edge). Criterios: custo zero/baixo para POC, suporte a Railway/Vercel.
- [x] Task 8: TD-H04 -- Implementar camada de persistencia minima: preferencias de usuario, historico de buscas, analytics.
- [x] Task 9: TD-H04 -- Nota: TD-H04 e dependencia condicional de TD-C02 (JWT). JWT stateless pode funcionar sem DB.

#### Relevancia de Resultados (P2)

- [x] Task 10: TD-M01 -- Corrigir interpretacao do campo `dataAberturaProposta`. Reabilitar filtro de deadline para excluir licitacoes historicas.
- [x] Task 11: TD-M01 -- Adicionar testes unitarios para filtro de deadline com dados reais de exemplo.

#### Arquitetura de DI (P3)

- [x] Task 12: TD-M05 -- Verificar estado atual de DI (v1.0 pode ter implementado parcialmente). Se `dependencies.py` ainda usa globais de modulo, refatorar para Depends() do FastAPI.
- [x] Task 13: TD-M05 -- Atualizar testes para injetar mocks via DI em vez de patching de globais.

#### Versionamento e Contratos de API (P2-P3)

- [x] Task 14: TD-M06/XD-API-01 -- Implementar versionamento de API. Opcoes: (a) prefixo de URL `/api/v1/`, (b) header `Accept-Version`. Recomendado: prefixo de URL por simplicidade.
- [x] Task 15: XD-API-02 -- Implementar testes de contrato usando JSON Schema compartilhado. Gerar schema dos modelos Pydantic, validar tipos TypeScript contra o mesmo schema.
- [x] Task 16: TD-L02/XD-API-03 -- Implementar codigos de erro estruturados. Criar enum de error codes com mensagens padronizadas. Ex: `{"error": {"code": "SEARCH_TIMEOUT", "message": "...", "details": {...}}}`.

### Criterios de Aceite

- [x] `gerar_resumo()` usa `AsyncOpenAI` (sem `run_in_executor`)
- [x] `filter_batch` tem executor dedicado ou nao compartilha com LLM (se ainda usa thread pool)
- [x] Download de arquivos grandes nao excede timeout do Vercel
- [x] Database implementado com pelo menos 1 caso de uso (historico ou preferencias)
- [x] Filtro de deadline ativo -- resultados nao incluem licitacoes vencidas
- [x] API versionada (pelo menos `/api/v1/`)
- [x] Pelo menos 1 teste de contrato validando Pydantic <-> TypeScript
- [x] Respostas de erro usam formato estruturado com codigos
- [x] `is_healthy()` usa async (se utilizado em contexto async)

### Testes Requeridos

- [x] Teste unitario: `gerar_resumo()` async -- sucesso, timeout, erro
- [x] Teste unitario: filtro de deadline -- filtra corretamente, datas edge cases
- [x] Teste unitario: error codes estruturados -- formato correto, codigos validos
- [x] Teste de integracao: download streaming -- resposta completa sem timeout
- [x] Teste de integracao: database -- CRUD basico
- [x] Teste de contrato: JSON Schema Pydantic == TypeScript types
- [x] Teste de regressao: busca end-to-end continua funcionando
- [x] Teste de carga: 10 buscas concorrentes sem thread pool starvation

### Estimativa

- Horas: 25-40 (excluindo TD-H04 database que pode ser 8-16h adicional)
- Custo: R$ 3.750-6.000 (estimativa a R$ 150/h)
- Sprint: 3 (1-2 semanas, paralelo com stories de frontend)

### Dependencias

- Depende de: v2-story-1.0 (security/critical; TD-C01 cadeia critica alimenta TD-H06 streaming)
- Depende de: v2-story-0.0 (TD-M04 timeout ja implementado simplifica TD-H03)
- Bloqueia: v2-story-5.0 (polish; versionamento API e pre-requisito para evolucao)
- Interna: TD-H03 resolve a cadeia TD-M04 -> TD-L06 -> TD-H03 (se async, thread pool nao e mais gargalo)
- Interna: TD-L02 -> XD-API-02 (error codes estruturados sao pre-requisito para contract tests)
- Interna: TD-M06 <-> XD-API-01 (versionamento backend e frontend sao o mesmo esforco)

### Definition of Done

- [x] Codigo implementado
- [x] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado

### Notas de Implementacao

#### TD-H03: AsyncOpenAI
- `gerar_resumo()` em `llm.py` agora usa `AsyncOpenAI` nativamente
- Eliminado `loop.run_in_executor(None, _generate_resumo)` — LLM roda direto no event loop
- Fallback `gerar_resumo_fallback()` permanece sync (sem I/O externo)

#### TD-L06: Dedicated ThreadPoolExecutor
- `_filter_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="filter")`
- `filter_batch` e `create_excel` usam executor dedicado, separado do default
- Previne thread pool starvation sob carga

#### TD-M01: Deadline Filter
- Usa campo `dataFimReceberPropostas` (deadline real de submissao)
- `dataAberturaProposta` e abertura de propostas, nao deadline
- Datas invalidas/ausentes nao rejeitam o bid (fail-safe)

#### TD-L01: is_healthy()
- Ja era sync-safe (`return self._client is not None`) — sem httpx I/O
- Health endpoint em main.py ja e async

#### TD-H06: Streaming Download
- Chunked streaming com 64KB chunks via async generator
- Content-Length header preservado para progress bars
- Vercel: Free=10s, Pro=60s (documentado em comentario)

#### TD-H04: Persistence (SQLite)
- `database.py` com aiosqlite — zero-cost, sem servico externo
- Tabelas: `search_history`, `user_preferences`
- Integrado ao pipeline de busca (record → complete/fail)
- Endpoint: `GET /search-history`
- Futuro: migrar para Supabase PostgreSQL em producao

#### TD-M05: DI Refactor
- `AppState` class encapsula todo estado mutavel
- `get_app_state()` retorna singleton, overridable via `dependency_overrides`
- Dependency functions (`get_job_store`, etc.) delegam para `_app_state`

#### TD-M06/XD-API-01: API Versioning
- `APIRouter(prefix="/api/v1")` com todas as rotas
- Rotas legadas (`/buscar`, `/health`, etc.) mantidas para backward compat
- Ambos `/buscar` e `/api/v1/buscar` resolvem para o mesmo handler

#### TD-L02/XD-API-03: Error Codes
- `ErrorCode` enum com 25 codigos em `error_codes.py`
- Formato: `{"error": {"code": "SEARCH_TIMEOUT", "message": "...", "details": {...}}}`
- `error_response()` helper cria HTTPException com body estruturado
- Todos os endpoints migrados para usar error codes

#### XD-API-02: Contract Tests
- `schemas_contract.py` gera JSON Schema de todos os modelos Pydantic
- 7 testes de contrato validam campos presentes nos schemas
- ErrorCodes incluidos no output de contrato
