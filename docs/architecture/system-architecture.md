# Arquitetura do Sistema -- Descomplicita

> **Versao:** 5.0.0
> **Data:** 2026-03-11
> **Autor:** @architect (Atlas)
> **Status:** Analise brownfield (POC)
> **Base:** Codebase no commit 2a76827b (HEAD de main)

---

## Indice

1. [Stack Tecnologico](#1-stack-tecnologico)
2. [Visao Geral da Arquitetura](#2-visao-geral-da-arquitetura)
3. [Backend (FastAPI)](#3-backend-fastapi)
4. [Frontend (Next.js App Router)](#4-frontend-nextjs-app-router)
5. [Banco de Dados (Supabase/PostgreSQL)](#5-banco-de-dados-supabasepostgresql)
6. [Integracoes Externas](#6-integracoes-externas)
7. [Infraestrutura](#7-infraestrutura)
8. [Qualidade de Codigo](#8-qualidade-de-codigo)
9. [Inventario de Debito Tecnico](#9-inventario-de-debito-tecnico)

---

## 1. Stack Tecnologico

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Frontend framework | Next.js (App Router) | 16.1.6 |
| Frontend linguagem | TypeScript (strict) | 5.9.3 |
| Frontend runtime | React | 18.3.1 |
| CSS | Tailwind CSS | 3.4.19 |
| Backend framework | FastAPI | 0.135.1 |
| Backend linguagem | Python | >= 3.11 |
| Banco de dados | Supabase (PostgreSQL) | supabase-py >= 2.13 |
| Cache / Job store | Redis 7 | redis-py 5.3.1 |
| LLM | OpenAI (gpt-4.1-nano) | openai 1.109.1 |
| NLP | NLTK (RSLPStemmer) | 3.9.1 |
| Autenticacao | Supabase Auth + PyJWT + python-jose | |
| Monitoramento erros | Sentry | nextjs 10.42, python 2.22 |
| Analytics | Mixpanel | 2.75.0 |
| Testes backend | pytest + pytest-cov + pytest-asyncio | |
| Testes frontend | Jest 29 + Testing Library + MSW 2 | |
| Testes E2E | Playwright | 1.58.2 |
| Acessibilidade E2E | axe-core/playwright | 4.11.1 |
| Bundler/transpiler | SWC (via @swc/jest) | |
| Deploy backend | Railway (Docker) | Python 3.11-slim |
| Deploy frontend | Vercel (standalone) | regiao iad1 |
| CI/CD | GitHub Actions | 9 workflows |

---

## 2. Visao Geral da Arquitetura

### 2.1 Diagrama de Componentes

```
                       +-------------+
                       |  Navegador  |
                       +------+------+
                              |
                  HTTPS (Vercel CDN)
                              |
                    +---------v---------+
                    |  Next.js 16       |
                    |  (App Router)     |
                    |  Vercel / iad1    |
                    +---+----+----+----+
                        |    |    |
           API Routes   |    |    |  Supabase Auth
           (proxy)      |    |    |  (cookie SSR)
                        v    |    v
                    +--------v--------+       +------------------+
                    |  FastAPI 0.4.0  |       |  Supabase        |
                    |  Railway        |       |  (PostgreSQL)    |
                    +--+---+---+--+--+       |  - users         |
                       |   |   |  |          |  - search_history|
                       |   |   |  +--------->|  - saved_searches|
                       |   |   |             |  - user_prefs    |
                       |   |   |             +------------------+
                       |   |   |
              +--------+   |   +--------+
              v            v            v
         +--------+  +---------+  +---------+
         | Redis  |  | PNCP    |  | OpenAI  |
         | 7      |  | API     |  | API     |
         +--------+  +---------+  +---------+
         - jobs                   gpt-4.1-nano
         - cache
         - excel bytes
         - items LIST
```

### 2.2 Fluxo de Dados Principal

1. Usuario preenche formulario (UFs, datas, setor, termos) no frontend
2. Next.js API Route (`/api/buscar`) valida e faz proxy para FastAPI
3. FastAPI cria job assincrono (`POST /buscar`) e retorna `job_id`
4. Frontend faz polling em `/api/buscar/status?job_id=...` (intervalo 2s)
5. Backend executa pipeline: fetch PNCP -> filtragem (keywords/stemming) -> resumo LLM + Excel
6. Itens filtrados armazenados como Redis LIST para paginacao
7. Frontend exibe resultados paginados, download Excel/CSV

### 2.3 Camadas

- **Apresentacao**: Next.js (React components, CSS tokens, temas)
- **BFF (Backend for Frontend)**: Next.js API Routes (proxy, auth header injection)
- **API**: FastAPI (endpoints, middleware, rate limiting)
- **Dominio**: filter.py, sectors.py, llm.py (logica de negocio)
- **Infraestrutura**: Redis (cache/state), Supabase (persistencia), PNCP (fonte de dados)

---

## 3. Backend (FastAPI)

### 3.1 Estrutura de Diretorios

```
backend/
  main.py              # App FastAPI, endpoints, pipeline de busca (~1230 linhas)
  config.py            # Configuracao PNCP, modalidades, retry
  database.py          # Persistencia Supabase (search history, prefs)
  dependencies.py      # DI centralizada (AppState singleton)
  filter.py            # Filtragem por keyword/valor/UF + stemming RSLP
  excel.py             # Geracao Excel (openpyxl) + CSV, limite 10K
  llm.py               # Integracao OpenAI (resumo executivo)
  schemas.py           # Modelos Pydantic (request/response)
  schemas_contract.py  # Contratos de API
  sectors.py           # Definicao de setores e keywords
  task_queue.py        # DurableTaskRunner (Redis-backed)
  job_store.py         # JobStore in-memory (fallback sem Redis)
  error_codes.py       # Enum de codigos de erro padronizados
  exceptions.py        # Excecoes customizadas (PNCPAPIError, PNCPRateLimitError)
  start.py             # Entrypoint do container (uvicorn wrapper)
  auth/
    jwt.py             # Geracao/validacao JWT customizado (PyJWT)
    supabase_auth.py   # Validacao Supabase JWT (python-jose)
  middleware/
    auth.py            # APIKeyMiddleware (3-tier auth)
    correlation_id.py  # CorrelationIdMiddleware (tracing)
    security_headers.py# CSP + HSTS
  sources/
    base.py            # Interface DataSourceClient + NormalizedRecord
    pncp_source.py     # Fonte PNCP
    transparencia_source.py # Fonte Portal Transparencia
    orchestrator.py    # MultiSourceOrchestrator (parallel + dedup)
  clients/
    async_pncp_client.py # Cliente HTTP async para PNCP API
  stores/
    redis_job_store.py # RedisJobStore (items como LIST, excel separado)
  app_cache/
    redis_cache.py     # Cache Redis para respostas PNCP
```

### 3.2 Endpoints da API

| Metodo | Rota | Descricao | Rate Limit |
|--------|------|-----------|------------|
| GET | `/` | Info da API | - |
| GET | `/health` | Health check + status Redis | - |
| GET | `/setores` | Lista setores disponiveis | - |
| POST | `/auth/token` | Troca API key por JWT | - |
| POST | `/auth/signup` | Registro via Supabase Auth | - |
| POST | `/auth/login` | Login via Supabase Auth | - |
| POST | `/auth/refresh` | Refresh token Supabase | - |
| POST | `/buscar` | Inicia job de busca assincrono | 10/min |
| GET | `/buscar/{job_id}/status` | Status e progresso do job | 30/min |
| GET | `/buscar/{job_id}/result` | Resultado do job completo | 5/min |
| GET | `/buscar/{job_id}/items` | Itens paginados (page, page_size) | 30/min |
| GET | `/buscar/{job_id}/download` | Download Excel ou CSV | 10/min |
| DELETE | `/buscar/{job_id}` | Cancela job em execucao | 10/min |
| GET | `/search-history` | Historico de buscas (per-user) | - |

Todos os endpoints tambem montados sob `/api/v1/` via APIRouter (versionamento).

### 3.3 Middleware Stack

Ordem de execucao (de fora para dentro):

1. **CorrelationIdMiddleware** -- gera/propaga `X-Correlation-Id` para tracing
2. **APIKeyMiddleware** -- autenticacao 3-tier (Supabase JWT > Custom JWT > API Key)
3. **SecurityHeadersMiddleware** -- CSP + HSTS em todas as respostas
4. **CORSMiddleware** -- origens explicitas (Vercel + localhost), metodos GET/POST, headers Content-Type/Authorization/X-API-Key

### 3.4 Fluxo de Autenticacao

```
Request -->  Bearer token presente?
              |
         Sim: 1) Tenta Supabase JWT (SUPABASE_JWT_SECRET)
              |     Sucesso: request.state.user_id = sub (UUID)
              |
              2) Tenta Custom JWT (JWT_SECRET, PyJWT)
              |     Sucesso: request.state.user_id = None
              |
         Nao: 3) Tenta X-API-Key header (hmac.compare_digest)
              |     Sucesso: request.state.user_id = None
              |
              4) Path em OPTIONAL_AUTH_PATHS?
                    Sim: acesso anonimo (user_id = None)
                    Nao: 401 Unauthorized
```

**Safeguard de producao**: se nenhum segredo configurado e `NODE_ENV=production`, retorna 503.

**Custom JWT**: inclui `iss=descomplicita-api`, `aud=descomplicita-client`. Suporta key rotation via `JWT_SECRET_PREVIOUS`.

### 3.5 Pipeline de Busca (run_search_job)

1. **Validacao**: setor (via `get_sector()`), datas, UFs
2. **Parse de termos**: `parse_multi_word_terms()` suporta aspas e virgulas (CSV-style parser)
3. **Fetch** (fase `fetching`):
   - `MultiSourceOrchestrator.search_all()` busca fontes em paralelo
   - PNCP: paginacao (max 10 paginas/combo UF x modalidade), retry com backoff exponencial
   - 7 modalidades default (reduz para 3 quando >10 UFs)
   - Deduplicacao por hash (orgao + objeto + data)
   - Transparencia: fonte secundaria com API key
4. **Filtragem** (fase `filtering`, CPU-bound em `ThreadPoolExecutor` dedicado de 4 workers):
   - UF, valor (min/max por setor), prazo
   - Keywords em 3 tiers (A/B/C) com pesos
   - Stemming RSLP para matching flexivel (portugues)
   - Exclusoes (exact match apenas, sem stemming)
   - Retorna `matched_keywords` e `relevance_score` por item
5. **Armazenamento**: itens filtrados salvos como Redis LIST (RPUSH/LRANGE)
6. **Resumo LLM** (fase `summarizing`):
   - `AsyncOpenAI` com `gpt-4.1-nano`, structured output via Pydantic
   - Fallback deterministico `gerar_resumo_fallback()` em caso de erro
   - Max 50 itens enviados ao LLM (otimizacao de tokens)
7. **Excel** (fase `generating_excel`):
   - `openpyxl` com formatacao profissional, hyperlinks, metadata
   - Limite de 10K itens; CSV disponivel para dataset completo (`?format=csv`)
   - LLM e Excel gerados em paralelo (`asyncio.gather`)
8. **Conclusao**: resultado salvo no Redis + historico no Supabase

### 3.6 Dependency Injection

`AppState` (singleton em `dependencies.py`) encapsula todo estado da aplicacao:
- Redis client, JobStore (Redis ou in-memory), RedisCache
- AsyncPNCPClient, PNCPSource, TransparenciaSource
- MultiSourceOrchestrator
- DurableTaskRunner
- Database (Supabase)

Inicializacao em `lifespan()`, cleanup no shutdown. Testes usam `dependency_overrides`.

---

## 4. Frontend (Next.js App Router)

### 4.1 Estrutura de Diretorios

```
frontend/
  app/
    layout.tsx          # RootLayout (AuthProvider > AnalyticsProvider > ThemeProvider)
    page.tsx            # HomePage (formulario + resultados) -- client component
    error.tsx           # Error boundary global Next.js
    not-found.tsx       # Pagina 404 customizada
    globals.css         # CSS com 5 temas via data-theme selectors
    types.ts            # Tipos compartilhados (LicitacaoItem, etc.)
    termos/
      page.tsx          # /termos (pagina de buscas salvas)
    api/
      buscar/route.ts          # Proxy POST /buscar
      buscar/status/route.ts   # Proxy GET /buscar/{id}/status
      buscar/result/route.ts   # Proxy GET /buscar/{id}/result
      buscar/items/route.ts    # Proxy GET /buscar/{id}/items
      buscar/cancel/route.ts   # Proxy DELETE /buscar/{id}
      download/route.ts        # Proxy GET /buscar/{id}/download
      setores/route.ts         # Proxy GET /setores
    components/ (27 componentes)
      SearchForm.tsx            # Formulario de busca principal
      SearchHeader.tsx          # Cabecalho com logo
      SearchSummary.tsx         # Resumo executivo (dados do LLM)
      SearchActions.tsx         # Botoes de acao (download, salvar)
      ItemsList.tsx             # Lista paginada de resultados
      SourceBadges.tsx          # Badges licitacao/ata com cores semanticas
      HighlightedText.tsx       # Highlight de keywords com <mark>
      Pagination.tsx            # Controles de paginacao
      UfSelector.tsx            # Seletor de estados (27 UFs)
      DateRangeSelector.tsx     # Seletor de periodo (data inicio/fim)
      RegionSelector.tsx        # Seletor por regiao (Norte, Sul, etc.)
      LoadingProgress.tsx       # Barra de progresso com fases
      LargeVolumeWarning.tsx    # Warning inline >10 UFs ou >30 dias
      EmptyState.tsx            # Estado vazio com carousel de categorias
      SaveSearchDialog.tsx      # Dialog nativo (<dialog>) para salvar busca
      SavedSearchesDropdown.tsx # Dropdown de buscas salvas com ARIA
      AuthModal.tsx             # Modal login/registro (<dialog>)
      ThemeProvider.tsx         # Provider 5 temas via data-theme attribute
      ThemeToggle.tsx           # Toggle de tema (5 opcoes)
      NetworkIndicator.tsx      # Indicador de status offline
      AnalyticsProvider.tsx     # Mixpanel (dynamic import)
      Spinner.tsx               # Spinner reutilizavel (sm/md/lg)
      Button.tsx                # Botao reutilizavel (primary/secondary/ghost/danger)
      ErrorBoundary.tsx         # Error boundary (class component, fallback customizavel)
      carouselData.ts           # Dados do carousel com cores CSS custom properties
    hooks/
      useSearchForm.ts     # Estado do formulario (UFs, datas, setor, termos)
      useSearchJob.ts      # Ciclo de vida do job (polling 2s, resultados, erros, cancelamento)
      useSaveDialog.ts     # Logica do dialog de salvar busca
    contexts/
      AuthContext.tsx      # Provider Supabase Auth (user, session, signUp, signIn, signOut)
  hooks/
    useAnalytics.ts        # Hook Mixpanel (trackEvent)
    useSavedSearches.ts    # CRUD buscas salvas (server quando auth, localStorage quando anonimo)
  lib/
    backendAuth.ts         # Headers auth para proxy server-side (Supabase > JWT > API key)
    savedSearches.ts       # Logica localStorage buscas salvas
    savedSearchesServer.ts # CRUD Supabase saved_searches
    supabase/
      client.ts            # createBrowserClient (client-side)
      server.ts            # createServerClient (server-side, cookies)
      middleware.ts         # updateSession (refresh token no middleware)
  middleware.ts            # Next.js middleware (session refresh em todas as rotas)
```

### 4.2 Gerenciamento de Estado

Sem biblioteca de estado global. Estado gerenciado via React hooks:

- **`useSearchForm`**: UFs selecionadas, datas, setor, termos de busca
- **`useSearchJob`**: job_id, status, progresso, resultado, erro, polling automatico
- **`useSaveDialog`**: controle do dialog de salvar busca
- **`useSavedSearches`**: CRUD dual (Supabase quando autenticado, localStorage quando anonimo; migracao automatica no primeiro login)
- **`AuthContext`**: user, session, loading, signUp, signIn, signOut (via Supabase)
- **`useAnalytics`**: trackEvent para Mixpanel

### 4.3 Sistema de Temas

5 temas implementados via atributo `data-theme` no `<html>`:

| Tema | Descricao |
|------|-----------|
| `light` | Padrao, fundo claro |
| `paperwhite` | Fundo off-white |
| `sepia` | Tom sepia, quente |
| `dim` | Escuro suave |
| `dark` | Escuro completo |

Tokens CSS semanticos em `globals.css`: `--ink-primary`, `--ink-muted`, `--surface-1`, `--surface-2`, `--badge-licitacao-*`, `--badge-ata-*`, `--status-warning-*`, etc.

Todos os valores de `--ink-muted` validados para WCAG AA (contraste >= 4.5:1).

### 4.4 Componentes Reutilizaveis

| Componente | Props | Uso |
|-----------|-------|-----|
| `<Spinner>` | `size: sm\|md\|lg` | Loading states |
| `<Button>` | `variant: primary\|secondary\|ghost\|danger` | Acoes padronizadas |
| `<ErrorBoundary>` | `fallback?: ReactNode` | Wraps secoes criticas |
| `<HighlightedText>` | `text, keywords` | Highlight com NFD accent stripping |

### 4.5 Estrategia de Carregamento

- **Dynamic imports** (`next/dynamic`, `ssr: false`): SaveSearchDialog, LoadingProgress, EmptyState, ItemsList
- **Analytics**: Mixpanel carregado via dynamic import
- **Fontes**: Google Fonts (DM Sans, Fahkwang, DM Mono) com `display: "swap"`
- **Skip link**: "Pular para o conteudo principal" para acessibilidade
- **Theme init**: script `beforeInteractive` para evitar flash

### 4.6 API Routes (BFF Pattern)

Todas as API routes do Next.js atuam como proxy para o backend FastAPI. O `backendAuth.ts` injeta headers de autenticacao automaticamente (prioridade: Supabase token > Custom JWT > API key).

---

## 5. Banco de Dados (Supabase/PostgreSQL)

### 5.1 Tabelas

| Tabela | Colunas Chave | RLS |
|--------|--------------|-----|
| `users` | id (UUID, FK auth.users), email, display_name, created_at | Sim |
| `search_history` | id (BIGSERIAL), user_id, job_id (UNIQUE), ufs[], data_inicial, data_final, setor_id, termos_busca, total_raw, total_filtrado, status, elapsed_seconds | Sim |
| `user_preferences` | id (BIGSERIAL), user_id, key, value (JSONB), UNIQUE(user_id, key) | Sim |
| `saved_searches` | id (UUID), user_id, name, search_params (JSONB), last_used_at | Sim |

### 5.2 Row Level Security

Todas as tabelas tem RLS habilitado. Politicas: `auth.uid() = user_id` (ou `id` para `users`).

Backend usa **service role key** (`SUPABASE_SERVICE_ROLE_KEY`) para operacoes administrativas, fazendo bypass de RLS.

### 5.3 Triggers e Funcoes

- **`handle_new_user()`**: `SECURITY DEFINER`. Trigger em `auth.users` AFTER INSERT. Cria perfil automaticamente em `public.users` com display_name extraido do metadata ou email.
- **`update_updated_at()`**: atualiza `updated_at` em UPDATE em `users` e `user_preferences`.

### 5.4 Indices

- `idx_search_history_user_created`: (user_id, created_at DESC)
- `idx_search_history_setor`: (setor_id)
- `idx_search_history_status`: (status)
- `idx_user_preferences_user`: (user_id)
- `idx_saved_searches_user`: (user_id, last_used_at DESC)

### 5.5 Migracoes

- `001_initial_schema.sql`: schema completo (tabelas, indices, RLS, triggers)
- `002_retention_policy.sql`: politica de retencao
- Localizacao: `backend/supabase/migrations/`
- Aplicacao: manual (sem runner automatizado)

### 5.6 Legado

Arquivo `descomplicita.db` (SQLite 32KB) e dependencia `aiosqlite` ainda presentes no projeto.

---

## 6. Integracoes Externas

### 6.1 PNCP (Portal Nacional de Contratacoes Publicas)

| Aspecto | Valor |
|---------|-------|
| URL base | `https://pncp.gov.br/api/consulta/v1` |
| Protocolo | REST (JSON) |
| Autenticacao | Nenhuma (API publica) |
| Rate limit | 10 rps (self-imposed) |
| Retry | 2 tentativas, backoff exponencial (base 1s, max 10s, jitter) |
| Timeout | 40s/request, 300s/source |
| Paginacao | 50 itens/pagina, max 10 paginas/combo |
| Modalidades | 7 default, reduz para 3 com >10 UFs |
| Cache | Redis com TTL |

### 6.2 Portal da Transparencia

| Aspecto | Valor |
|---------|-------|
| URL base | `https://api.portaldatransparencia.gov.br` |
| Autenticacao | API key (header `chave-api-dados`) |
| Rate limit | 3 rps |
| Timeout | 90s |
| Prioridade | 3 (fonte secundaria) |

### 6.3 OpenAI

| Aspecto | Valor |
|---------|-------|
| Modelo | `gpt-4.1-nano` (configuravel via `LLM_MODEL`) |
| Uso | Resumo executivo de licitacoes filtradas |
| Fallback | `gerar_resumo_fallback()` -- funcao deterministica |
| Limite | Max 50 itens enviados ao LLM |
| Client | `AsyncOpenAI` (nativo async) |
| Temperatura | 0.3 (configuravel) |

### 6.4 Redis

| Funcao | Implementacao |
|--------|--------------|
| Job state | RedisJobStore (status, progress, result) |
| PNCP cache | RedisCache (responses com TTL) |
| Excel bytes | Armazenado separado (nao base64 em JSON) |
| Items filtrados | Redis LIST (RPUSH/LRANGE) para paginacao |
| Job params | DurableTaskRunner (TTL 24h, recovery) |
| Fallback | In-memory JobStore quando Redis indisponivel |

### 6.5 Mixpanel

- Uso: analytics de produto no frontend
- Carregamento: dynamic import
- Token: `NEXT_PUBLIC_MIXPANEL_TOKEN`

### 6.6 Sentry

- Backend: `sentry-sdk[fastapi]` com FastAPI + Starlette integrations
- Frontend: `@sentry/nextjs` com source maps ocultos
- Sample rate: 10% traces (configuravel via `SENTRY_TRACES_SAMPLE_RATE`)

---

## 7. Infraestrutura

### 7.1 Deployment

| Servico | Plataforma | Build | Regiao |
|---------|-----------|-------|--------|
| Backend | Railway | Docker multi-stage (Python 3.11-slim) | - |
| Frontend | Vercel | Next.js standalone output | iad1 (US East) |
| Banco | Supabase | Managed PostgreSQL | - |
| Cache | Railway (Redis addon) | redis:7-alpine | - |

### 7.2 Docker

- **Dockerfile backend**: multi-stage (builder instala deps, production copia e limpa)
- **Producao**: usuario non-root (`appuser`), sem testes/examples
- **docker-compose.yml**: Redis + Backend + Frontend para dev local
- **Health checks**: configurados em todos os servicos do compose

### 7.3 CI/CD (GitHub Actions)

| Workflow | Trigger | Descricao |
|----------|---------|-----------|
| `tests.yml` | push/PR main | Backend (Python 3.11+3.12), Frontend Jest, E2E Playwright |
| `deploy.yml` | push main (backend/\|frontend/) | Deploy Railway + Vercel + smoke tests |
| `backend-ci.yml` | push/PR | CI especifico backend |
| `pr-validation.yml` | PR | Validacao de pull request |
| `codeql.yml` | scheduled | Analise de seguranca CodeQL |
| `bundle-size.yml` | PR | Monitoramento tamanho do bundle |
| `filter-quality-audit.yml` | - | Auditoria de qualidade do filtro |
| `dependabot-auto-merge.yml` | - | Auto-merge Dependabot |
| `cleanup.yml` | - | Limpeza de artefatos |

Deploy pipeline: detect-changes -> deploy-backend (Railway) -> deploy-frontend (Railway) -> smoke-tests (health + API + integracao). Cria issue automaticamente em falha de smoke test.

### 7.4 Headers de Seguranca (Vercel)

Configurados no `vercel.json` para todas as rotas:

- `Content-Security-Policy` (scripts, styles, fonts, connect restritos)
- `Strict-Transport-Security` (HSTS 1 ano, includeSubDomains)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (camera, mic, geolocation desabilitados)

Backend tambem adiciona CSP + HSTS via `SecurityHeadersMiddleware`.

### 7.5 Variaveis de Ambiente

| Variavel | Servico | Obrigatoria |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Backend | Sim |
| `REDIS_URL` | Backend | Nao (fallback in-memory) |
| `SUPABASE_URL` | Ambos | Sim (producao) |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Sim (producao) |
| `SUPABASE_KEY` | Backend auth | Sim (producao) |
| `SUPABASE_JWT_SECRET` | Backend | Sim (producao) |
| `JWT_SECRET` | Backend | Nao (legacy) |
| `API_KEY` | Backend | Nao (legacy) |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend | Sim (producao) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend | Sim (producao) |
| `BACKEND_URL` | Frontend server | Sim |
| `NEXT_PUBLIC_MIXPANEL_TOKEN` | Frontend | Nao |
| `SENTRY_DSN` | Backend | Nao |
| `NEXT_PUBLIC_SENTRY_DSN` | Frontend | Nao |
| `TRANSPARENCIA_API_KEY` | Backend | Nao |
| `CORS_ORIGINS` | Backend | Nao (default: Vercel + localhost) |
| `LLM_MODEL` | Backend | Nao (default: gpt-4.1-nano) |

---

## 8. Qualidade de Codigo

### 8.1 Testes Backend

- **Framework**: pytest com pytest-asyncio
- **Arquivos de teste**: ~40 em `backend/tests/`
- **Testes registrados**: 1349+ testes
- **Cobertura**: threshold 70% (branch coverage habilitado)
- **Markers**: `unit`, `integration`, `slow`
- **Mocks**: `mock_helpers.py` centralizado
- **Warnings**: tratados como erros (`filterwarnings = ["error"]`)
- **CI**: roda em Python 3.11 e 3.12

### 8.2 Testes Frontend

- **Framework**: Jest 29 + Testing Library + MSW 2
- **Testes registrados**: 576+
- **Cobertura thresholds**: branches 50%, functions 57%, lines 65%, statements 65%
- **Componentes testados**: 27 arquivos de teste
- **API routes testadas**: 4 arquivos (buscar, status, result, download)
- **Hooks testados**: 3 arquivos (useSearchForm, useSearchJob, polling)
- **Seguranca**: `security-headers.test.ts`
- **Integracao**: `search-flow.test.ts` com MSW handlers
- **Regra especial**: `noEmptyCatch.test.ts` -- catch blocks devem usar `catch (_e) { void _e }`

### 8.3 Testes E2E

- **Framework**: Playwright (Chromium)
- **5 specs**:
  - `01-happy-path.spec.ts`
  - `02-llm-fallback.spec.ts`
  - `03-validation-errors.spec.ts`
  - `04-error-handling.spec.ts`
  - `05-accessibility.spec.ts` (axe-core)
- **CI**: roda apos testes unitarios passarem

### 8.4 Linting e Tipagem

- **Frontend**: ESLint flat config (apenas regra `no-empty`), TypeScript strict mode
- **Backend**: sem linter configurado (nem ruff, flake8, mypy, ou black)
- **TSConfig**: `strict: true`, `isolatedModules: true`, `ES2020`

### 8.5 Padroes Arquiteturais

| Padrao | Implementacao |
|--------|--------------|
| Dependency Injection | `AppState` singleton + FastAPI `dependency_overrides` |
| Error Codes | Enum `ErrorCode` centralizado com `to_dict()` |
| Correlation ID | Middleware propaga `X-Correlation-Id` em logs |
| Feature Flags | Env vars booleanas (ex: `ENABLE_STREAMING_DOWNLOAD`) |
| Graceful Shutdown | SIGTERM handler + `DurableTaskRunner.shutdown()` |
| Rate Limiting | SlowAPI com limites por endpoint |
| API Versioning | Rotas duplicadas em `/` e `/api/v1/` |
| BFF Pattern | Next.js API Routes como proxy com auth injection |
| Multi-source | Orchestrator com parallel fetch + dedup |
| Tiered Keywords | 3 tiers (A/B/C) com pesos para relevancia |

---

## 9. Inventario de Debito Tecnico

### Critico

| ID | Descricao | Area de Impacto | Esforco (h) |
|----|-----------|-----------------|-------------|
| TD-SYS-001 | **SQLite legado nao removido.** Arquivo `descomplicita.db` (32KB) e dependencia `aiosqlite` permanecem no projeto apos migracao completa para Supabase. Risco de confusao sobre qual e a fonte de verdade e possivel vazamento de dados legados. | Manutencao, seguranca | 2 |
| TD-SYS-002 | **main.py monolitico com ~1230 linhas.** Toda logica de endpoints, pipeline de busca, helpers de parsing e job execution concentrada em um unico arquivo. Dificulta revisao de codigo, teste isolado e onboarding. | Manutencao | 8 |
| TD-SYS-003 | **Sem linter Python configurado.** Nenhum ruff, flake8, mypy ou black configurado para o backend. Inconsistencias de estilo e bugs de tipo nao detectados antes do commit. | Qualidade | 4 |

### Alto

| ID | Descricao | Area de Impacto | Esforco (h) |
|----|-----------|-----------------|-------------|
| TD-SYS-004 | **Testes de integracao CI nao implementados.** O job `integration-tests` no `tests.yml` esta com `echo "will be implemented"` e `continue-on-error: true`. Nenhum teste de integracao real roda no CI. | Qualidade, confiabilidade | 8 |
| TD-SYS-005 | **Supabase client criado a cada request de auth.** Nos endpoints `/auth/signup`, `/auth/login`, `/auth/refresh`, `create_client()` e chamado em cada request em vez de reutilizar o client do DI (`Database`). | Performance | 3 |
| TD-SYS-006 | **Sem validacao Pydantic nos endpoints de auth.** Os endpoints de autenticacao usam `request.json()` manual em vez de modelos Pydantic, perdendo validacao automatica, documentacao OpenAPI e type safety. | Seguranca, DX | 4 |
| TD-SYS-007 | **JWT token cached em variavel de modulo (backendAuth.ts).** `cachedToken` e singleton de modulo no server-side Next.js. Em Vercel (serverless), funcoes podem ser cold-started independentes, tornando o cache ineficaz ou inconsistente entre instancias. | Confiabilidade | 3 |
| TD-SYS-008 | **Ausencia de pre-commit hooks.** Nao ha husky, lint-staged ou pre-commit Python configurados. Codigo pode ser commitado sem passar por linting, formatacao ou testes. | Qualidade | 2 |
| TD-SYS-009 | **Coverage thresholds frontend baixos.** Branches 50%, lines 65%. Para um sistema em producao que manipula dados de licitacoes publicas, esses thresholds sao insuficientes para prevenir regressoes. | Qualidade | 16 |

### Medio

| ID | Descricao | Area de Impacto | Esforco (h) |
|----|-----------|-----------------|-------------|
| TD-SYS-010 | **docker-compose.yml desatualizado.** Secao frontend referencia "placeholder" e Dockerfile que pode estar desatualizado. Variaveis de ambiente do backend incompletas (faltam SUPABASE_*, JWT_SECRET, SENTRY_DSN). | DX | 2 |
| TD-SYS-011 | **Sem endpoint /health dedicado no frontend.** Deploy workflow faz smoke test via curl na raiz, mas nao ha health check especifico que verifique conectividade com backend. | Observabilidade | 2 |
| TD-SYS-012 | **API versioning sem estrategia de deprecacao.** Rotas existem em `/` e `/api/v1/` simultaneamente sem redirect, headers de deprecacao ou documentacao de lifecycle. | Manutencao | 4 |
| TD-SYS-013 | **Sem migration runner automatizado.** Migracoes SQL aplicadas manualmente. Nao ha Alembic, supabase CLI, ou script no CI para validar/aplicar migracoes. | Operacional | 6 |
| TD-SYS-014 | **ThreadPoolExecutor fixo sem monitoring.** `_filter_executor` com 4 workers usados para filtragem e Excel. Sem metricas de saturacao, fila ou latencia. | Performance | 3 |
| TD-SYS-015 | **Sem rate limiting na autenticacao.** Endpoints `/auth/login`, `/auth/signup` e `/auth/refresh` nao tem `@limiter.limit()`, permitindo ataques de brute force. | Seguranca | 2 |
| TD-SYS-016 | **Vercel functions com timeout de 10s.** `maxDuration: 10` no `vercel.json` para API routes. Downloads de Excel grandes ou buscas em muitas UFs podem exceder o timeout. | Confiabilidade | 2 |
| TD-SYS-017 | **Sem logging estruturado no frontend.** Apenas `console.error`/`console.warn` nos API routes Next.js. Sem correlacao com `X-Correlation-Id` do backend. | Observabilidade | 4 |

### Baixo

| ID | Descricao | Area de Impacto | Esforco (h) |
|----|-----------|-----------------|-------------|
| TD-SYS-018 | **Diretorio com nome invalido na raiz.** `D:descomplicitadocsreviews` -- diretorio com caminho sem separadores, provavelmente criado por erro de script. | Limpeza | 0.5 |
| TD-SYS-019 | **Arquivos markdown acumulados na raiz.** 10+ arquivos `.md` na raiz (ROADMAP.md, ISSUES-ROADMAP.md, FEATURE-1-COMPLETION-REPORT.md, etc.) que deveriam estar em `docs/` ou removidos. | Organizacao | 1 |
| TD-SYS-020 | **ESLint config minimal.** Apenas 1 regra (`no-empty`). Nao usa `@typescript-eslint/recommended`, `jsx-a11y`, nem regras de import order. | Qualidade | 3 |
| TD-SYS-021 | **Google Fonts sem fallback system font.** DM Sans, Fahkwang, DM Mono carregadas de CDN Google. CSS `display: swap` mitiga, mas layout pode ter FOUT significativo. | UX | 1 |
| TD-SYS-022 | **Inconsistencia de path alias entre build e teste.** `@/` mapeia para `./` no tsconfig mas `./app/` no Jest `moduleNameMapper`. Pode causar falsos positivos em testes. | DX | 1 |
| TD-SYS-023 | **Transparencia source habilitada sem garantia de API key.** `TRANSPARENCIA_API_KEY` nao e obrigatoria. Se ausente, requests podem falhar silenciosamente ou retornar 401 tratado como "sem dados". | Confiabilidade | 1 |
| TD-SYS-024 | **Sem CHANGELOG ou release notes.** Historico de mudancas depende exclusivamente de commits Git e documento PRD. Nao ha versionamento semantico formalizado. | Documentacao | 2 |

---

## Resumo Quantitativo

| Metrica | Valor |
|---------|-------|
| Debitos tecnicos identificados | 24 |
| Criticos | 3 |
| Altos | 6 |
| Medios | 8 |
| Baixos | 7 |
| Esforco total estimado | ~83 horas |
| Linhas de codigo backend (main.py) | ~1.230 |
| Endpoints API | 14 (+14 versionados) |
| Componentes React | 27 |
| Hooks customizados | 5 |
| Tabelas no banco | 4 |
| Workflows CI/CD | 9 |
| Testes backend | 1349+ |
| Testes frontend | 576+ |
| Testes E2E | 5 specs |
