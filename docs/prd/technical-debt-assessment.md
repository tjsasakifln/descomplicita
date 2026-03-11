# Technical Debt Assessment - FINAL

**Projeto:** Descomplicita (POC)
**Data:** 2026-03-11
**Versao:** 1.0
**Status:** Validado por @architect (Atlas), @data-engineer (Forge), @ux-design-expert (Pixel), @qa (Shield)
**Commit base:** 2a76827b (HEAD de main)

---

## Executive Summary

| Metrica | Valor |
|---------|-------|
| **Total de debitos identificados** | **63** (24 sistema + 16 database + 23 frontend/UX) |
| **Debitos unicos apos deduplicacao** | **56** (7 sobreposicoes identificadas) |
| **Distribuicao por severidade** | Criticos: 4 | Altos: 11 | Medios: 18 | Baixos: 23 |
| **Esforco total estimado** | **~152h** (~83h sistema + ~16h DB + ~48h UX, com ajustes) |
| **Esforco critico POC (pre-demo)** | **~12h** (5.5h visual + 6.5h seguranca) |
| **Areas mais criticas** | AuthModal (tokens CSS quebrados), Autenticacao (cross-cutting), SQLite legado |

### Contexto

O Descomplicita e uma plataforma de busca de licitacoes publicas brasileiras construida sobre Next.js 14+ (App Router) + FastAPI + Supabase + Redis. A plataforma esta em estagio POC com maturidade tecnica significativa (1349+ testes backend, 576+ testes frontend, 5 E2E specs com axe-core, CI/CD com 9 workflows, 5 temas visuais, WCAG AA validado). Os debitos identificados sao gerenciaveis e nenhum e bloqueante para um lancamento controlado (beta fechado), exceto os 12h de itens criticos.

### Distribuicao por Area

| Area | Criticos | Altos | Medios | Baixos | Total | Horas |
|------|----------|-------|--------|--------|-------|-------|
| Sistema (TD-SYS-*) | 3 | 6 | 8 | 7 | 24 | ~83h |
| Database (TD-DB-*) | 0 | 2 | 4 | 10 | 16 | ~16h |
| Frontend/UX (TD-UX-*) | 1 | 2 | 6 | 14 | 23 | ~48h |

### Mudancas do DRAFT para FINAL

| Acao | Detalhes |
|------|----------|
| Debitos removidos | TD-DB-004 (substituido por TD-DB-014 -- unificacao JWT incompleta, nao ausente) |
| Debitos adicionados por @data-engineer | TD-DB-014, TD-DB-015, TD-DB-016, TD-DB-017 (+3.5h) |
| Debitos adicionados por @ux-design-expert | TD-UX-021, TD-UX-022, TD-UX-023 (+2.5h) |
| Severidades ajustadas | TD-DB-001 Media->Alta, TD-DB-006 Media->Baixa, TD-UX-008 Baixo->Trivial, TD-UX-016 Medio->Baixo |
| Estimativas ajustadas | TD-DB-010 2h->1.5h, TD-UX-009 2h->1h, TD-UX-011+019 combinados 1.5h->1h |
| Dependencias atualizadas | TD-DB-015 movido para Nivel 0, TD-DB-014 como pre-requisito de TD-DB-005 |
| Itens pre-demo marcados | TD-UX-001, TD-UX-002, TD-UX-003, TD-SYS-001/TD-DB-016 como BLOQUEANTE |

---

## Inventario Completo de Debitos

### Sistema (validado por @architect)

| ID | Debito | Severidade | Horas | Prioridade | Quick Win | Notas |
|----|--------|------------|-------|------------|-----------|-------|
| TD-SYS-001 | SQLite legado nao removido (descomplicita.db + aiosqlite) | **Critico** | 2 | P0 | **Sim** | **BLOQUEANTE pre-demo.** Complementa TD-DB-016 (detalhes de implementacao). Arquivo pode conter dados de usuarios. |
| TD-SYS-002 | main.py monolitico (~1230 linhas) | Critico | 8 | P3 | -- | Depende de TD-SYS-003 (linter). Dificulta onboarding e manutencao. |
| TD-SYS-003 | Sem linter Python (ruff, flake8, mypy, black) | Critico | 4 | P2 | -- | Prerequisito para refatoracao segura de main.py. |
| TD-SYS-004 | Testes de integracao CI placeholder | Alto | 8 | P4 | -- | Workflows existem mas testes sao stub. |
| TD-SYS-005 | Supabase client criado a cada request de auth | Alto | 3 | P2 | -- | Performance. Cluster de auth. |
| TD-SYS-006 | Sem Pydantic nos endpoints de auth | Alto | 4 | P2 | -- | Seguranca e DX. Cluster de auth. |
| TD-SYS-007 | JWT token cached em variavel de modulo (serverless) | Alto | 3 | P2 | -- | Confiabilidade em ambiente Vercel. Cluster de auth. |
| TD-SYS-008 | Ausencia de pre-commit hooks | Alto | 2 | P2 | **Sim** | Depende de TD-SYS-003 (linter). |
| TD-SYS-009 | Coverage thresholds frontend baixos (branches 52.74%) | Alto | 16 | P4 | -- | Merge com TD-UX-014. Contabilizar 1x. |
| TD-SYS-010 | docker-compose.yml desatualizado | Medio | 2 | P3 | -- | DX para desenvolvimento local. |
| TD-SYS-011 | Sem /health no frontend | Medio | 2 | P4 | -- | Depende de politica de monitoramento. |
| TD-SYS-012 | API versioning sem deprecacao | Medio | 4 | P3 | -- | Governanca de API. |
| TD-SYS-013 | Sem migration runner automatizado | Medio | 6 | P2 | -- | Usar `supabase db push` (CLI oficial). Habilita todas as migracoes DB. |
| TD-SYS-014 | ThreadPoolExecutor sem monitoring | Medio | 3 | P4 | -- | So relevante com carga real. |
| TD-SYS-015 | Sem rate limiting na autenticacao | Medio | 2 | P2 | **Sim** | Brute force prevention. Cluster de auth. |
| TD-SYS-016 | Vercel functions timeout 10s | Medio | 2 | P3 | **Sim** | Evita timeout em buscas grandes. |
| TD-SYS-017 | Sem logging estruturado no frontend | Medio | 4 | P4 | -- | Observabilidade cross-stack. |
| TD-SYS-018 | Diretorio com nome invalido na raiz | Baixo | 0.5 | P5 | **Sim** | Limpeza trivial. Visivel ao inspecionar repo. |
| TD-SYS-019 | Markdown acumulados na raiz | Baixo | 1 | P5 | **Sim** | Higiene do repositorio. |
| TD-SYS-020 | ESLint config minimal | Baixo | 3 | P4 | -- | Qualidade incremental. |
| TD-SYS-021 | Google Fonts sem fallback system | Baixo | 1 | P5 | **Sim** | FOUT em conexoes lentas. |
| TD-SYS-022 | Path alias inconsistente build/test | Baixo | 1 | P5 | **Sim** | DX. |
| TD-SYS-023 | Transparencia source sem API key obrigatoria | Baixo | 1 | P5 | **Sim** | Confiabilidade. |
| TD-SYS-024 | Sem CHANGELOG ou release notes | Baixo | 2 | P5 | -- | Commits suficientes para equipe pequena. |

**Subtotal Sistema: ~83h** (24 itens)

---

### Database (validado por @data-engineer)

| ID | Debito | Severidade | Horas | Prioridade | Quick Win | Notas |
|----|--------|------------|-------|------------|-----------|-------|
| TD-DB-001 | CHECK constraint em `search_history.status` (incluir `cancelled`) | **Alta** | 0.5 | P1 | **Sim** | **Ajustado de Media para Alta** por @data-engineer. Status `cancelled` vs `failed` e bug real de integridade; afeta cleanup futuro. CHECK deve incluir `queued`, `completed`, `failed`, `cancelled`. |
| TD-DB-002 | RLS granular por operacao (WITH CHECK no INSERT) | Media | 2 | P2 | -- | PostgreSQL protege implicitamente via USING como WITH CHECK. Risco real baixo, mas policies explicitas por operacao documentam intencao e facilitam auditoria. Manter como Media por boas praticas. |
| TD-DB-003 | UNIQUE em `users.email` | Baixa | 0.5 | P8 | **Sim** | `auth.users` ja protege. Risco apenas teorico (insercao via service_role). |
| TD-DB-005 | Habilitar `verify_aud` no Supabase JWT | Media | 1 | P1 | **Sim** | `supabase_auth.py` linha 52: `verify_aud: False`. Audience padrao Supabase: `"authenticated"`. **Depende de TD-DB-014** (migrar para PyJWT primeiro). |
| TD-DB-006 | Cleanup em batches (evitar locks) | **Baixa** | 1 | P9 | -- | **Rebaixado de Media** por @data-engineer. Volume POC (<3000 rows em 90 dias) nao justifica. Lock <100ms. Reavaliar com >50K registros. |
| TD-DB-007 | Indice parcial para cleanup | Baixa | 0.5 | P10 | **Sim** | `idx_search_history_status` ja cobre filtro. Beneficio apenas com >50K rows. |
| TD-DB-008 | Limite em `saved_searches.name` (CHECK length) | Baixa | 0.5 | P7 | **Sim** | Nome de 10KB passaria. CHECK simples resolve. |
| TD-DB-009 | `updated_at` em `saved_searches` | Baixa | 0.5 | P8 | **Sim** | Consistencia com outras 3 tabelas. `last_used_at` serve como proxy. |
| TD-DB-010 | Ativar pg_cron ou cron externo para retention | Media | 1.5 | P5 | -- | **Ajustado de 2h para 1.5h.** Funcao existe mas nunca chamada. Para POC: GitHub Actions schedule semanal. `pg_cron` requer Supabase Pro. |
| TD-DB-011 | Indice em `users.email` | Baixa | 0.5 | P10 | **Sim** | Nenhuma query busca por `users.email`. Desnecessario para POC. |
| TD-DB-012 | Limite de saved_searches no DB (trigger/constraint) | Baixa | 1 | P7 | -- | Codigo ja enforca no frontend. Trigger seria defesa em profundidade. |
| TD-DB-013 | Metricas de falha de persistencia (Database silencioso) | Baixa | 1.5 | P6 | -- | Todos os metodos em `database.py` fazem `except: log + return None`. Para POC aceitavel; producao precisa contadores. |
| **TD-DB-014** | **Unificacao JWT incompleta: `supabase_auth.py` ainda usa python-jose** | **Media** | 1.5 | **P1** | -- | **NOVO.** Substitui TD-DB-004. `auth/jwt.py` usa PyJWT (v3-story-3.3), mas `auth/supabase_auth.py` linhas 46-54 ainda usa `from jose import jwt`. `requirements.txt` ainda lista `python-jose[cryptography]==3.3.0`. python-jose tem CVEs conhecidos. |
| **TD-DB-015** | **Schema drift: `DEFAULT auth.uid()` em `saved_searches.user_id` nao rastreado em migracoes** | **Alta** | 1 | **P1** | **Sim** | **NOVO.** INSERT em `savedSearchesServer.ts` nao envia `user_id`, mas coluna e NOT NULL sem DEFAULT na migracao `001_initial_schema.sql`. Funciona em producao = `DEFAULT auth.uid()` adicionado via dashboard Supabase. Criar migracao `003_add_default_auth_uid.sql`. |
| **TD-DB-016** | **SQLite legado: `descomplicita.db` (arquivo fisico) + `aiosqlite` no requirements.txt** | **Alta** | 0.5 | **P0** | **Sim** | **NOVO. BLOQUEANTE pre-demo.** Complementa TD-SYS-001. Arquivo fisico no repo pode conter historico de buscas com user_ids. Verificar conteudo antes de remover. Adicionar `.db` ao `.gitignore`. Remover `aiosqlite==0.20.0` do requirements.txt. |
| **TD-DB-017** | **Status `cancelled` nao propagado ao banco de dados** | **Baixa** | 0.5 | P6 | **Sim** | **NOVO.** `DELETE /buscar/{job_id}` retorna `{"status": "cancelled"}` mas DB grava `failed` via `job_store.fail()`. Semanticamente incorreto. Depende de TD-DB-001 (CHECK constraint). |

**Subtotal Database: ~16h** (16 itens)

**Nota:** Total base caiu de ~14.5h para ~12.5h com ajustes (remocao TD-DB-004, ajuste TD-DB-010). Novos debitos (TD-DB-014 a TD-DB-017) adicionam ~3.5h. Total efetivo: ~16h.

---

### Frontend/UX (validado por @ux-design-expert)

| ID | Debito | Severidade | Horas | Prioridade | Quick Win | Notas |
|----|--------|------------|-------|------------|-----------|-------|
| TD-UX-001 | AuthModal usa tokens CSS inexistentes (--card-bg, --text-primary, etc.) | **Critico** | 2 | **P0** | **Sim** | **BLOQUEANTE pre-demo.** 6 tokens inexistentes. Modal inutilizavel em temas escuros: texto preto sobre fundo escuro, inputs sem borda/focus, botao submit transparente. Afeta conversao de cadastro/login. Mapeamento: --card-bg->--surface-elevated, --text-primary->--ink, --text-secondary->--ink-secondary, --border-color->--border, --input-bg->--surface-1, --accent-color->--brand-blue. |
| TD-UX-002 | AuthModal usa classes Tailwind hardcoded (bg-red-100, bg-green-100) | **Alto** | 1 | **P0** | **Sim** | **BLOQUEANTE pre-demo.** Feedback erro/sucesso so funciona em light/dark. Paperwhite, sepia e dim ficam inconsistentes. Usar `bg-error-subtle`/`text-error` e `bg-success-subtle`/`text-success`. |
| TD-UX-003 | ItemsList usa cores Tailwind hardcoded para badges e texto de erro | **Alto** | 2 | **P0** | **Sim** | **BLOQUEANTE pre-demo.** Dois problemas: (1) erro `text-red-600` deveria usar `text-error`; (2) badges `bg-amber-100`/`bg-blue-100` hardcoded enquanto SearchSummary usa `--badge-licitacao-*`/`--badge-ata-*` via tokens. Inconsistencia visivel na mesma pagina. |
| TD-UX-004 | Button reutilizavel existe mas nao e usado em nenhum lugar | Medio | 3 | P2 | -- | Button.tsx bem implementado (variantes, tamanhos, loading state, min-height 44px). Zero usos na app. Pelo menos 4 botoes em page.tsx deveriam usa-lo. |
| TD-UX-005 | Pagina unica (SPA-like), sem rota de resultados | Medio | 8 | P3 | -- | Deep-linking de resultados tem valor medio para o publico-alvo. Resultados expiram no Redis. Postergar para pos-POC. |
| TD-UX-006 | Footer duplicado (page.tsx e termos/page.tsx) | Baixo | 1 | P3 | **Sim** | Extrair componente Footer reutilizavel. |
| TD-UX-007 | Versao hardcoded "v2.0" no footer | Baixo | 0.5 | P4 | **Sim** | Contradiz narrativa v3.x em demos. Fix trivial. |
| TD-UX-008 | rounded-modal definido mas nao usado | **Trivial** | 0.5 | P4 | **Sim** | **Rebaixado de Baixo para Trivial** por @ux-design-expert. Token orfao em Tailwind config. Ambos os modals usam `rounded-xl` (AuthModal) e `rounded-card` (SaveSearchDialog). Nenhum impacto visual. |
| TD-UX-009 | Sem loading state para pagina inicial | Baixo | **1** | P3 | -- | **Ajustado de 2h para 1h** por @ux-design-expert. Fetch de setores e rapido (<500ms). Select mostra "Carregando setores...". Skeleton simples no select seria suficiente. |
| TD-UX-010 | Paginacao sem acentos nos aria-labels | Baixo | 0.5 | P1 | **Sim** | Fix trivial de acessibilidade. "Navegacao de paginas", "Pagina anterior", "Proxima pagina". |
| TD-UX-011 | SearchSummary usa inline style={{}} para badge tokens | Baixo | **0.5** | P4 | **Sim** | **Combinado com TD-UX-019** (mesma raiz: tokens nao mapeados no Tailwind). Resolver via TD-UX-022. |
| TD-UX-012 | Sem i18n framework | Baixo | 16 | Fora POC | -- | App 100% brasileiro. Sem plano de internacionalizacao no roadmap. |
| TD-UX-013 | dateDiffInDays duplicada em dois arquivos | Baixo | 0.5 | P2 | **Sim** | Extrair para utils. Risco de divergencia. |
| TD-UX-014 | Coverage frontend abaixo do ideal (branches 52.74%) | Medio | 8 | P3 | -- | Merge com TD-SYS-009. Contabilizar 1x (16h no SYS-009). |
| TD-UX-015 | Sem indicacao visual de setores fallback | Baixo | 1 | P4 | -- | Transparencia para o usuario quando dados de setores estao em cache. |
| TD-UX-016 | SSE nao implementado (polling com backoff) | **Baixo** | 12 | Fora POC | -- | **Rebaixado de Medio para Baixo** por @ux-design-expert. Polling com backoff (1-15s) e adequado para buscas de 30s-5min. Ganho perceptivel proximo de zero. 12h de esforco para beneficio marginal. |
| TD-UX-017 | carouselData.ts nao auditado | Baixo | 2 | P4 | -- | Requer validacao com especialista juridico. |
| TD-UX-018 | Sem PWA / Service Worker | Baixo | 8 | Fora POC | -- | Licitacoes dependem 100% de APIs online. NetworkIndicator ja avisa quando offline. |
| TD-UX-019 | SourceBadges usa style={{}} para --ink-warning | Baixo | **0.5** | P4 | **Sim** | **Combinado com TD-UX-011** (mesma raiz). Resolver via TD-UX-022. |
| TD-UX-020 | Sem componente Input/Select reutilizavel | Medio | 4 | P2 | -- | ~10 inputs com classes duplicadas. Seguir padrao do Button. |
| **TD-UX-021** | **HighlightedText mark sem estilizacao tematica** | **Medio** | 1 | P2 | **Sim** | **NOVO.** Elemento `<mark>` usa estilo default do browser (fundo amarelo). Em temas escuros, contraste amarelo-sobre-escuro pode violar WCAG AA (1.4.3). Adicionar CSS para mark por tema usando `var(--brand-blue-subtle)`. |
| **TD-UX-022** | **Tokens CSS nao mapeados no Tailwind config** | **Baixo** | 1 | P2 | **Sim** | **NOVO.** `--ink-warning`, `--badge-licitacao-*`, `--badge-ata-*` existem em globals.css mas nao no Tailwind. Raiz unica de TD-UX-011 e TD-UX-019. Mapear no tailwind.config.ts elimina necessidade de style={{}}. |
| **TD-UX-023** | **Botao Buscar nao usa componente Button** | **Medio** | 0.5 | P1 | **Sim** | **NOVO.** Botao principal da app (page.tsx linhas 165-168) replica classes manualmente. Nao tem loading spinner integrado (mostra apenas texto "Buscando..."). Button component ja tem loading prop com Spinner. |

**Subtotal Frontend/UX: ~48h** (23 itens, ~36h priorizavel para POC excluindo i18n, PWA, SSE)

---

## Matriz de Priorizacao Final

Ordenado por severidade ajustada (incorporando revisoes de todos os especialistas), depois por esforco (menor primeiro dentro do mesmo nivel).

| Rank | ID | Debito | Severidade | Horas | Area | Quick Win | Pre-Demo |
|------|-----|--------|------------|-------|------|-----------|----------|
| 1 | TD-UX-001 | AuthModal: tokens CSS inexistentes | Critico | 2 | UX | **Sim** | **BLOQUEANTE** |
| 2 | TD-SYS-001 / TD-DB-016 | SQLite legado nao removido | Critico | 2 | SYS+DB | **Sim** | **BLOQUEANTE** |
| 3 | TD-UX-002 | AuthModal: classes Tailwind hardcoded | Alto | 1 | UX | **Sim** | **BLOQUEANTE** |
| 4 | TD-UX-003 | ItemsList: cores hardcoded | Alto | 2 | UX | **Sim** | **BLOQUEANTE** |
| 5 | TD-SYS-003 | Sem linter Python | Critico | 4 | SYS | -- | -- |
| 6 | TD-SYS-002 | main.py monolitico | Critico | 8 | SYS | -- | -- |
| 7 | TD-DB-001 | CHECK constraint em status (incluir cancelled) | Alta | 0.5 | DB | **Sim** | -- |
| 8 | TD-DB-016 | SQLite legado (detalhes: .db fisico + aiosqlite) | Alta | 0.5 | DB | **Sim** | **BLOQUEANTE** |
| 9 | TD-DB-015 | Schema drift: DEFAULT auth.uid() nao rastreado | Alta | 1 | DB | **Sim** | -- |
| 10 | TD-UX-023 | Botao Buscar nao usa Button component | Medio | 0.5 | UX | **Sim** | -- |
| 11 | TD-UX-010 | Paginacao sem acentos nos aria-labels | Baixo | 0.5 | UX | **Sim** | -- |
| 12 | TD-UX-013 | dateDiffInDays duplicada | Baixo | 0.5 | UX | **Sim** | -- |
| 13 | TD-DB-005 | Habilitar verify_aud no Supabase JWT | Media | 1 | DB | **Sim** | -- |
| 14 | TD-DB-014 | Unificacao JWT incompleta (python-jose) | Media | 1.5 | DB | -- | -- |
| 15 | TD-UX-021 | mark sem estilizacao tematica | Medio | 1 | UX | **Sim** | -- |
| 16 | TD-UX-022 | Tokens CSS nao mapeados no Tailwind | Baixo | 1 | UX | **Sim** | -- |
| 17 | TD-SYS-008 | Sem pre-commit hooks | Alto | 2 | SYS | **Sim** | -- |
| 18 | TD-SYS-015 | Sem rate limiting auth | Medio | 2 | SYS | **Sim** | -- |
| 19 | TD-SYS-016 | Vercel functions timeout 10s | Medio | 2 | SYS | **Sim** | -- |
| 20 | TD-DB-002 | RLS granular (WITH CHECK) | Media | 2 | DB | -- | -- |
| 21 | TD-SYS-005 | Supabase client recriado por request | Alto | 3 | SYS | -- | -- |
| 22 | TD-SYS-007 | JWT cached em modulo serverless | Alto | 3 | SYS | -- | -- |
| 23 | TD-UX-004 | Button nao utilizado | Medio | 3 | UX | -- | -- |
| 24 | TD-SYS-006 | Sem Pydantic nos endpoints auth | Alto | 4 | SYS | -- | -- |
| 25 | TD-UX-020 | Sem Input/Select reutilizavel | Medio | 4 | UX | -- | -- |
| 26 | TD-SYS-004 | Testes integracao CI placeholder | Alto | 8 | SYS | -- | -- |
| 27 | TD-SYS-009 / TD-UX-014 | Coverage thresholds baixos | Alto / Medio | 16 | SYS+UX | -- | -- |
| 28 | TD-DB-010 | Ativar retention policy | Media | 1.5 | DB | -- | -- |
| 29 | TD-SYS-013 | Sem migration runner | Medio | 6 | SYS | -- | -- |
| 30 | TD-SYS-010 | docker-compose desatualizado | Medio | 2 | SYS | -- | -- |
| 31 | TD-SYS-011 | Sem /health frontend | Medio | 2 | SYS | -- | -- |
| 32 | TD-SYS-012 | API versioning sem deprecacao | Medio | 4 | SYS | -- | -- |
| 33 | TD-SYS-014 | ThreadPoolExecutor sem monitoring | Medio | 3 | SYS | -- | -- |
| 34 | TD-SYS-017 | Sem logging estruturado frontend | Medio | 4 | SYS | -- | -- |
| 35 | TD-UX-005 | Pagina unica sem rota resultados | Medio | 8 | UX | -- | -- |
| 36 | TD-UX-007 | Versao hardcoded v2.0 | Baixo | 0.5 | UX | **Sim** | -- |
| 37 | TD-UX-008 | rounded-modal nao usado | Trivial | 0.5 | UX | **Sim** | -- |
| 38 | TD-UX-019 | SourceBadges inline style | Baixo | 0.5 | UX | **Sim** | -- |
| 39 | TD-SYS-018 | Diretorio com nome invalido | Baixo | 0.5 | SYS | **Sim** | -- |
| 40 | TD-DB-003 | UNIQUE em users.email | Baixa | 0.5 | DB | **Sim** | -- |
| 41 | TD-DB-007 | Indice parcial cleanup | Baixa | 0.5 | DB | **Sim** | -- |
| 42 | TD-DB-008 | Limite em saved_searches.name | Baixa | 0.5 | DB | **Sim** | -- |
| 43 | TD-DB-009 | updated_at em saved_searches | Baixa | 0.5 | DB | **Sim** | -- |
| 44 | TD-DB-011 | Indice em users.email | Baixa | 0.5 | DB | **Sim** | -- |
| 45 | TD-DB-017 | Status cancelled nao propagado ao DB | Baixa | 0.5 | DB | **Sim** | -- |
| 46 | TD-UX-011 | SearchSummary inline styles | Baixo | 0.5 | UX | **Sim** | -- |
| 47 | TD-SYS-022 | Path alias inconsistente | Baixo | 1 | SYS | **Sim** | -- |
| 48 | TD-SYS-023 | Transparencia sem API key | Baixo | 1 | SYS | **Sim** | -- |
| 49 | TD-SYS-019 | Markdown na raiz | Baixo | 1 | SYS | **Sim** | -- |
| 50 | TD-SYS-021 | Fonts sem fallback | Baixo | 1 | SYS | **Sim** | -- |
| 51 | TD-UX-006 | Footer duplicado | Baixo | 1 | UX | **Sim** | -- |
| 52 | TD-UX-009 | Sem loading state pagina inicial | Baixo | 1 | UX | -- | -- |
| 53 | TD-UX-015 | Setores fallback sem indicacao | Baixo | 1 | UX | -- | -- |
| 54 | TD-DB-012 | Limite saved_searches no DB | Baixa | 1 | DB | -- | -- |
| 55 | TD-DB-013 | Metricas falha persistencia | Baixa | 1.5 | DB | -- | -- |
| 56 | TD-DB-006 | Cleanup em batches | Baixa | 1 | DB | -- | -- |
| 57 | TD-UX-009 | Loading state pagina inicial | Baixo | 1 | UX | -- | -- |
| 58 | TD-SYS-024 | Sem CHANGELOG | Baixo | 2 | SYS | -- | -- |
| 59 | TD-UX-017 | carouselData nao auditado | Baixo | 2 | UX | -- | -- |
| 60 | TD-SYS-020 | ESLint minimal | Baixo | 3 | SYS | -- | -- |
| 61 | TD-UX-018 | Sem PWA/Service Worker | Baixo | 8 | UX | -- | -- |
| 62 | TD-UX-016 | SSE nao implementado | Baixo | 12 | UX | -- | -- |
| 63 | TD-UX-012 | Sem i18n | Baixo | 16 | UX | -- | -- |

---

## Plano de Resolucao

### Pre-Demo (BLOQUEANTE) -- ~12h

Itens que **DEVEM** ser corrigidos antes de qualquer demonstracao ou apresentacao. Divididos em duas categorias: visual (constrangimento em demo) e seguranca (risco reputacional).

#### Visual / UX -- 5.5h

| Ordem | ID | Debito | Horas | Justificativa |
|-------|----|--------|-------|---------------|
| 1 | TD-UX-001 | AuthModal: corrigir 6 tokens CSS inexistentes | 2h | Modal de auth visualmente quebrado em todos os temas. Texto invisivel em temas escuros, inputs sem borda, botao submit transparente. **Constrangimento garantido em demo que envolva login.** |
| 2 | TD-UX-002 | AuthModal: migrar feedback erro/sucesso para tokens semanticos | 1h | Dependencia direta do anterior. Completar correcao do AuthModal. `bg-red-100` -> `bg-error-subtle`. |
| 3 | TD-UX-003 | ItemsList: migrar badges e texto de erro para tokens | 2h | Badges inconsistentes com SearchSummary na mesma pagina. Visivel em qualquer demo com resultados. |
| 4 | TD-UX-010 | Acentos nos aria-labels da paginacao | 0.5h | Fix trivial. Melhora acessibilidade. Incluir neste sprint por custo zero. |

#### Seguranca -- 6.5h

| Ordem | ID | Debito | Horas | Justificativa |
|-------|----|--------|-------|---------------|
| 5 | TD-SYS-001 / TD-DB-016 | Remover SQLite legado (arquivo .db + aiosqlite + .gitignore) | 1h | Arquivo pode conter dados de usuarios. Risco reputacional se inspecionarem o repo. Verificar conteudo antes de remover. |
| 6 | TD-DB-014 | Completar unificacao JWT (supabase_auth.py -> PyJWT) | 1.5h | python-jose tem CVEs conhecidos e esta sem manutencao ativa. Duas libs JWT e superficie de ataque desnecessaria. |
| 7 | TD-DB-005 | Habilitar verify_aud=True com audience="authenticated" | 1h | Aceitar tokens de qualquer projeto Supabase e inaceitavel. Depende de TD-DB-014. |
| 8 | TD-DB-015 | Rastrear DEFAULT auth.uid() em migracao SQL | 1h | Schema drift. Recriar DB a partir das migracoes quebraria INSERT de saved_searches. |
| 9 | TD-SYS-015 | Rate limiting nos endpoints auth | 2h | Brute force prevention basico. |

---

### Sprint 1: Quick Wins -- ~15h

Itens de baixo esforco com alto impacto. Nao requerem mudancas arquiteturais.

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-UX-023 | Botao Buscar -> componente Button | 0.5h | Ganha spinner integrado. Quick win imediato. |
| 2 | TD-DB-001 | CHECK constraint em status (incluir cancelled) | 0.5h | Integridade de dados. Migracao SQL trivial. |
| 3 | TD-UX-013 | Extrair dateDiffInDays para utils | 0.5h | Deduplicacao trivial. |
| 4 | TD-UX-021 | Estilizar mark por tema (HighlightedText) | 1h | Contraste WCAG AA em temas escuros. |
| 5 | TD-UX-022 | Mapear tokens restantes no Tailwind config | 1h | Raiz de TD-UX-011 e TD-UX-019. Elimina inline styles. |
| 6 | TD-SYS-016 | Ajustar Vercel timeout | 2h | Evita timeout em buscas grandes. |
| 7 | TD-SYS-018 | Remover diretorio invalido na raiz | 0.5h | Limpeza trivial. |
| 8 | TD-SYS-019 | Organizar markdowns da raiz | 1h | Higiene do repositorio. |
| 9 | TD-UX-007 | Versao dinamica no footer | 0.5h | Contradiz narrativa v3.x. |
| 10 | TD-DB-017 | Status cancelled no DB | 0.5h | Semantica correta. Depende de TD-DB-001. |
| 11 | TD-UX-004 | Adotar Button nos demais botoes | 2.5h | Consistencia visual. (3h total com TD-UX-023 = 3h) |
| 12 | TD-UX-006 | Extrair Footer como componente | 1h | Deduplicacao simples. |
| 13 | TD-DB-008 | CHECK length em saved_searches.name | 0.5h | Defesa contra nomes gigantes. |
| 14 | TD-SYS-022 | Corrigir path alias build/test | 1h | DX. |
| 15 | TD-SYS-023 | Transparencia source API key | 1h | Confiabilidade. |
| -- | | **Subtotal** | **~14.5h** | |

---

### Sprint 2: Fundacao -- ~36h

Itens estruturais que habilitam qualidade e seguranca a longo prazo.

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-SYS-003 | Configurar linter Python (ruff) | 4h | Prerequisito para refatoracao segura. |
| 2 | TD-SYS-008 | Pre-commit hooks (husky + lint-staged + ruff) | 2h | Gate de qualidade antes do commit. Depende de SYS-003. |
| 3 | TD-SYS-005 + TD-SYS-006 | Refatorar auth endpoints (Pydantic + Supabase client DI) | 7h | Cluster de auth. Resolver junto. |
| 4 | TD-DB-002 | RLS granular por operacao (WITH CHECK) | 2h | Boas praticas. Policies explicitas sao auditaveis. |
| 5 | TD-SYS-013 | Migration runner automatizado (supabase db push) | 6h | Habilita todas as migracoes DB futuras. |
| 6 | TD-DB-010 | Ativar retention policy (GitHub Actions schedule) | 1.5h | Dados so acumulam apos meses. |
| 7 | TD-UX-020 | Criar Input/Select reutilizavel | 4h | Completar design system basico. |
| 8 | TD-SYS-007 | Corrigir JWT cache serverless | 3h | Confiabilidade da auth no frontend. |
| 9 | TD-SYS-017 | Logging estruturado frontend | 4h | Observabilidade cross-stack. |
| 10 | TD-SYS-010 | Atualizar docker-compose | 2h | DX local. |
| -- | | **Subtotal** | **~35.5h** | |

---

### Sprint 3: Otimizacao -- ~71h+

Itens de medio/longo prazo que melhoram escalabilidade e experiencia. Pos-POC.

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-SYS-002 | Refatorar main.py | 8h | Depende de linter + hooks. |
| 2 | TD-SYS-004 | Implementar testes integracao CI | 8h | Cobertura de integracao real. |
| 3 | TD-SYS-009 / TD-UX-014 | Subir coverage thresholds | 16h | Prevencao de regressoes. |
| 4 | TD-UX-005 | Rotas de resultado (deep-link) | 8h | Requer design de URL, TTL, UX de expirado. |
| 5 | TD-UX-016 | SSE para progresso em tempo real | 12h | So se houver reclamacoes de latencia. |
| 6 | TD-SYS-012 | Estrategia de deprecacao API | 4h | Governanca. |
| 7 | TD-SYS-020 | Expandir ESLint config | 3h | Qualidade incremental. |
| 8 | TD-UX-018 | PWA / Service Worker | 8h | So se houver demanda offline. |
| 9 | TD-UX-012 | i18n framework | 16h | So se houver plano de internacionalizacao. |
| -- | | **Subtotal** | **~83h** (inclui itens fora de escopo POC) | |

### Fora de Escopo POC

Items que devem ser avaliados apenas se o produto escalar:

| ID | Debito | Horas | Razao |
|----|--------|-------|-------|
| TD-UX-012 | i18n | 16h | App 100% brasileiro. Sem plano de internacionalizacao. |
| TD-UX-018 | PWA / Service Worker | 8h | Licitacoes dependem 100% de APIs online. |
| TD-UX-016 | SSE | 12h | Polling com backoff e adequado para buscas de 30s-5min. |
| TD-SYS-014 | ThreadPool monitoring | 3h | So com metricas de saturacao. |
| TD-SYS-011 | /health frontend | 2h | Depende de politica de monitoramento. |
| TD-SYS-024 | CHANGELOG | 2h | Commits suficientes para equipe pequena. |
| TD-DB-006 | Cleanup em batches | 1h | Volume POC nao justifica. |
| TD-DB-007 | Indice parcial cleanup | 0.5h | So com >50K rows. |
| TD-DB-009 | updated_at em saved_searches | 0.5h | Consistencia cosmetica. |
| TD-DB-011 | Indice em users.email | 0.5h | Nenhuma query usa. |

---

## Grafo de Dependencias (Atualizado)

```
Nivel 0 (sem dependencias -- pode comecar agora):
  TD-SYS-001 / TD-DB-016  (remover SQLite legado)
  TD-UX-001               (AuthModal tokens -- BLOQUEANTE)
  TD-DB-001               (CHECK constraint status)
  TD-DB-015               (schema drift -- MOVIDO para N0 por QA)
  TD-SYS-003              (linter Python)
  TD-SYS-015              (rate limiting auth)
  TD-SYS-016              (Vercel timeout)
  TD-SYS-018/019          (limpeza repo)
  TD-UX-010/013/007       (quick fixes triviais)
  TD-UX-021/022/023       (mark estilo, Tailwind tokens, Botao Buscar)
  TD-DB-003/007/008/011   (schema cosmetico)

Nivel 1 (depende de Nivel 0):
  TD-UX-002               (apos UX-001 -- tokens AuthModal)
  TD-DB-014               (unificacao JWT -- independente mas pre-req de DB-005)
  TD-DB-017               (apos DB-001 -- CHECK constraint)
  TD-SYS-005 + SYS-006    (auth endpoints -- podem comecar em paralelo)

Nivel 2 (depende de Nivel 1):
  TD-UX-003               (apos design token cleanup -- UX-001/002)
  TD-SYS-008              (apos SYS-003 -- pre-commit hooks requerem linter)
  TD-DB-005               (apos DB-014 -- verify_aud requer PyJWT unificado)
  TD-UX-004               (apos UX-023 -- adotar Button nos demais botoes)
  TD-SYS-013              (migration runner -- habilita migracoes DB)
  TD-DB-002               (RLS granular -- pode ser feito independente ou com runner)

Nivel 3 (depende de Nivel 2):
  TD-SYS-002              (refatorar main.py -- apos linter + hooks)
  TD-DB-010               (retention policy -- apos migration runner ou direto via CLI)
  TD-DB-012               (limite saved_searches -- trigger no DB)
  TD-UX-020               (criar Input/Select -- apos Button adotado)

Nivel 4 (longo prazo):
  TD-SYS-004              (testes integracao CI)
  TD-SYS-009 / TD-UX-014  (coverage)
  TD-UX-005               (rotas de resultado)
  TD-UX-016               (SSE)
  TD-UX-012               (i18n)
  TD-UX-018               (PWA)
```

### Dependencias Criticas Validadas por @qa

1. **TD-SYS-003 (linter) -> TD-SYS-008 (hooks) -> TD-SYS-002 (refactor main.py):** Refatorar sem linter e arriscado.
2. **TD-UX-001 (tokens) -> TD-UX-002 (classes):** Primeiro criar tokens, depois migrar classes.
3. **TD-DB-014 (PyJWT) -> TD-DB-005 (verify_aud):** Verificar audience requer lib unificada. **Adicionado por QA.**
4. **TD-DB-015 movido para Nivel 0:** Pode ser feito agora, sem pre-requisitos. **Adicionado por QA.**
5. **TD-SYS-013 (migration runner) -> TD-DB-001 a TD-DB-012:** Migracoes triviais (CHECK constraint) podem ser aplicadas via `supabase db push` sem runner formal.

**Dependencias circulares:** Nenhuma identificada.

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| **AuthModal quebrado impede demonstracao de auth** -- texto invisivel em temas escuros, inputs sem borda, botao submit transparente | **Alta** | **Critico** | Corrigir TD-UX-001 + TD-UX-002 antes de qualquer demo (~3h). **BLOQUEANTE.** |
| **Schema drift causa falha ao recriar DB** -- `DEFAULT auth.uid()` fora das migracoes pode quebrar INSERT de saved_searches se DB for recriado | **Media** | **Alto** | Criar migracao 003 (TD-DB-015, 1h). Auditar schema vivo vs migracoes com `pg_dump --schema-only`. |
| **python-jose com CVEs + unificacao incompleta** -- `supabase_auth.py` ainda usa biblioteca sem manutencao ativa | **Media** | **Alto** | Completar migracao para PyJWT (TD-DB-014, 1.5h). Remover python-jose do requirements. |
| **SQLite legado com possiveis dados de usuarios** -- arquivo `.db` no repositorio pode conter historico de buscas com UFs, setores e termos | **Baixa** | **Alto** | Verificar conteudo, remover do repo, adicionar ao .gitignore (TD-SYS-001/TD-DB-016, 1h). |
| **verify_aud desabilitado aceita tokens de outros projetos** -- tokens JWT de qualquer projeto Supabase seriam aceitos | **Baixa** | **Alto** | Habilitar `verify_aud=True` com `audience="authenticated"` (TD-DB-005, 1h). |
| **main.py monolitico dificulta onboarding** -- 1230 linhas em arquivo unico reduz velocidade de desenvolvimento | **Alta** | **Medio** | Refatorar apos linter configurado (TD-SYS-003 -> TD-SYS-002). |
| **Cleanup nunca executado acumula dados** -- funcao de retencao existe mas nunca e chamada | **Alta** | **Baixo** (POC) | GitHub Actions schedule semanal (TD-DB-010, 1.5h). |
| **Coverage baixa mascara regressoes** -- branches 52.74% permite regressoes ocultas | **Media** | **Medio** | Aumentar gradualmente (TD-SYS-009/TD-UX-014). Nao bloqueante para POC. |

---

## Criterios de Sucesso

### Cobertura de Codigo

| Metrica | Atual | Meta pos-Quick Wins | Meta pos-Sprint 2 |
|---------|-------|---------------------|-------------------|
| Backend coverage (total) | 70%+ | 70%+ (manter) | 75%+ |
| Frontend branches | 52.74% | 55% | 65% |
| Frontend lines | 65%+ | 65%+ (manter) | 72% |

### Seguranca

| Metrica | Atual | Meta |
|---------|-------|------|
| Dependencias com CVE conhecida | 1 (python-jose) | 0 apos TD-DB-014 |
| Endpoints auth sem rate limit | 3 (`/auth/*`) | 0 apos TD-SYS-015 |
| Tokens JWT sem validacao de audience | 1 (supabase_auth.py) | 0 apos TD-DB-005 |
| Arquivos legados com dados potenciais | 1 (descomplicita.db) | 0 apos TD-DB-016 |
| Tokens CSS inexistentes referenciados | 6 (AuthModal) | 0 apos TD-UX-001 |

### Acessibilidade

| Metrica | Atual | Meta |
|---------|-------|------|
| Violacoes WCAG AA criticas (axe-core) | AuthModal: 2 (contraste + focus) | 0 |
| Componentes com cores Tailwind hardcoded | 2 (AuthModal + ItemsList) | 0 |
| mark sem estilizacao tematica | 1 (HighlightedText) | 0 apos TD-UX-021 |

### Design System

| Metrica | Atual | Meta pos-Sprint 2 |
|---------|-------|-------------------|
| Uso do componente Button | 0 instancias | 4-5 instancias |
| Tokens CSS orfaos (definidos, nao usados) | 1 (rounded-modal) | 0 |
| Tokens CSS referenciados, inexistentes | 6 (AuthModal) | 0 |
| Tokens CSS nao mapeados no Tailwind | 3 (ink-warning, badge-*) | 0 apos TD-UX-022 |

### Performance (baseline a medir)

| Metrica | Acao |
|---------|------|
| Tempo de resposta `/auth/login` p95 | Medir, meta < 500ms |
| Tamanho do bundle JS | Monitorar, nao regredir |
| Tempo de criacao Supabase client | Medir antes/depois de TD-SYS-005 |

---

## Debitos Cruzados (Cross-cutting)

### Cluster de Autenticacao

O subsistema de autenticacao concentra a maior quantidade de debitos que atravessam multiplas camadas:

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-SYS-005 | Supabase client recriado por request | Backend (auth endpoints) |
| TD-SYS-006 | Sem Pydantic nos endpoints auth | Backend (API) |
| TD-SYS-007 | JWT cached em modulo serverless | Frontend (BFF) |
| TD-SYS-015 | Sem rate limiting auth | Backend (seguranca) |
| TD-DB-002 | RLS INSERT sem WITH CHECK explicito | Database (seguranca) |
| TD-DB-005 | verify_aud desabilitado | Backend (auth) + Database (seguranca) |
| TD-DB-014 | Unificacao JWT incompleta (python-jose persiste) | Backend (auth) |

**Impacto combinado:** Resolucao coordenada eliminaria 7 debitos (~16h) e fortaleceria significativamente a postura de seguranca.

### Cluster de Qualidade / Cobertura

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-SYS-009 | Coverage thresholds frontend baixos | Frontend (testes) |
| TD-UX-014 | Coverage branches 52.74% | Frontend (testes) |
| TD-SYS-004 | Testes integracao CI placeholder | CI/CD (backend + frontend) |
| TD-SYS-003 | Sem linter Python | Backend (qualidade) |
| TD-SYS-008 | Sem pre-commit hooks | Repo (ambos) |
| TD-SYS-020 | ESLint minimal | Frontend (qualidade) |

**Nota:** TD-SYS-009 e TD-UX-014 sao essencialmente o mesmo debito visto de angulos diferentes. Contabilizar como **1 item** (~16h).

### Cluster de Design Tokens

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-UX-001 | AuthModal tokens inexistentes | Frontend (auth UI) |
| TD-UX-002 | AuthModal classes hardcoded | Frontend (auth UI) |
| TD-UX-003 | ItemsList cores hardcoded | Frontend (resultados) |
| TD-UX-004 | Button nao utilizado | Frontend (design system) |
| TD-UX-020 | Sem Input/Select reutilizavel | Frontend (design system) |
| TD-UX-021 | mark sem estilizacao tematica | Frontend (resultados) |
| TD-UX-022 | Tokens nao mapeados no Tailwind | Frontend (config) |
| TD-UX-023 | Botao Buscar nao usa Button | Frontend (principal) |

**Impacto combinado:** Resolver em sequencia criaria um design system coerente, eliminando 8 debitos (~12h).

### Cluster de Infraestrutura / Operacional

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-SYS-013 | Sem migration runner | Backend + DB |
| TD-DB-010 | Sem retention policy ativa | DB + Operacional |
| TD-DB-015 | Schema drift nao rastreado | DB + Migracoes |
| TD-SYS-010 | docker-compose desatualizado | Dev local |

---

## Testes Requeridos Pos-Resolucao

| Debito | Teste Requerido | Tipo |
|--------|-----------------|------|
| TD-UX-001 + TD-UX-002 | Snapshot tests do AuthModal nos 5 temas; verificar que nenhum `var(--*)` usado e indefinido em globals.css | Unit + Visual |
| TD-UX-003 | Snapshot tests do ItemsList nos 5 temas; comparar badges com SearchSummary | Unit + Visual |
| TD-UX-004 + TD-UX-023 | Verificar que botoes migrados mantem comportamento (click, disabled, loading) | Unit |
| TD-UX-021 | Verificar contraste de `<mark>` nos 5 temas via axe-core | E2E (Accessibility) |
| TD-DB-001 | INSERT com status invalido deve falhar com constraint violation | Integration (SQL) |
| TD-DB-005 | Token JWT com `aud` diferente de `"authenticated"` deve ser rejeitado | Integration |
| TD-DB-014 | Testes existentes de `supabase_auth.py` devem passar apos migracao para PyJWT | Integration |
| TD-DB-015 | Recriar banco a partir das migracoes e testar INSERT em `saved_searches` sem `user_id` | Integration |
| TD-DB-016 / TD-SYS-001 | Verificar que nenhum import referencia `aiosqlite` ou `descomplicita.db` (grep automatizado) | CI script |
| TD-SYS-002 | Testes existentes devem continuar passando; cobertura nao deve cair | Unit + Integration |
| TD-SYS-003 | `ruff check .` deve rodar sem erros no CI | CI |
| TD-SYS-005 | Supabase client nao recriado em cada request (mock + assertion) | Unit |
| TD-SYS-006 | Payload invalido em `/auth/*` deve retornar 422 (Pydantic) | Integration |
| TD-SYS-015 | Burst de 20 requests em `/auth/login` deve retornar 429 | Integration |

---

## Apendice: Sobreposicoes Identificadas

Debitos que aparecem em multiplos relatorios e foram deduplicados na contagem final:

| Debito | Aparece em | ID Unificado | Acao |
|--------|-----------|--------------|------|
| Coverage frontend baixa | TD-SYS-009 + TD-UX-014 | TD-SYS-009 (primario) | Contabilizar 1x (16h) |
| Unificar libs JWT | TD-DB-004 (removido) -> TD-DB-014 | TD-DB-014 (primario) | Contabilizar 1x (1.5h) |
| Sem migration runner | TD-SYS-013 + DB-AUDIT sec. 10 | TD-SYS-013 (primario) | Contabilizar 1x (6h) |
| verify_aud JWT | mencionado em SYS + TD-DB-005 | TD-DB-005 (primario) | Contabilizar 1x (1h) |
| Supabase client recriado | TD-SYS-005 + DB-AUDIT sec. 7 | TD-SYS-005 (primario) | Contabilizar 1x (3h) |
| SQLite legado | TD-SYS-001 + TD-DB-016 | Ambos mantidos (escopos complementares) | SYS-001=limpeza geral, DB-016=.db+aiosqlite |
| Rate limit auth | TD-SYS-015 + DB-AUDIT | TD-SYS-015 (primario) | Contabilizar 1x (2h) |
| Inline styles badges | TD-UX-011 + TD-UX-019 -> TD-UX-022 | TD-UX-022 (raiz) | Resolver raiz elimina ambos |

**Reducao por deduplicacao:** 63 itens brutos -> 56 unidades de trabalho unicas (~152h efetivo).

---

## Apendice: Changelog do Assessment

### DRAFT -> FINAL (2026-03-11)

#### Itens Adicionados

| ID | Debito | Origem | Justificativa |
|----|--------|--------|---------------|
| TD-DB-014 | Unificacao JWT incompleta em supabase_auth.py | @data-engineer | Verificado: `from jose import jwt` persiste. python-jose tem CVEs. |
| TD-DB-015 | Schema drift: DEFAULT auth.uid() fora das migracoes | @data-engineer | Verificado: INSERT em savedSearchesServer.ts nao envia user_id. |
| TD-DB-016 | SQLite fisico + aiosqlite no requirements | @data-engineer | Complementa TD-SYS-001 com detalhes de implementacao. |
| TD-DB-017 | Status cancelled nao propagado ao DB | @data-engineer | Verificado: API retorna "cancelled" mas DB grava "failed". |
| TD-UX-021 | mark sem estilizacao tematica | @ux-design-expert | Risco real de contraste em temas escuros (amarelo default). |
| TD-UX-022 | Tokens CSS nao mapeados no Tailwind | @ux-design-expert | Raiz unica de TD-UX-011 e TD-UX-019. |
| TD-UX-023 | Botao Buscar nao usa componente Button | @ux-design-expert | Verificado: Button component existe mas tem 0 usos. |

#### Itens Removidos

| ID | Acao | Justificativa |
|----|------|---------------|
| TD-DB-004 | Removido (substituido por TD-DB-014) | Unificacao JWT nao estava ausente, estava incompleta. TD-DB-014 captura escopo correto. |

#### Severidades Ajustadas

| ID | Original | Ajustado | Justificativa | Revisado por |
|----|----------|----------|---------------|-------------|
| TD-DB-001 | Media | **Alta** | Status cancelled vs failed e bug de integridade; afeta cleanup futuro | @data-engineer |
| TD-DB-006 | Media | **Baixa** | Volume POC (<3000 rows) nao justifica batching; lock <100ms | @data-engineer |
| TD-UX-008 | Baixo | **Trivial** | Token orfao sem impacto visual; ambos modals usam rounded-xl/rounded-card | @ux-design-expert |
| TD-UX-016 | Medio | **Baixo** | Polling com backoff adequado para buscas 30s-5min; ganho imperceptivel | @ux-design-expert |

#### Estimativas Ajustadas

| ID | Original | Ajustado | Justificativa | Revisado por |
|----|----------|----------|---------------|-------------|
| TD-DB-010 | 2h | 1.5h | GitHub Actions schedule e mais simples que estimativa original | @data-engineer |
| TD-UX-009 | 2h | 1h | Fetch rapido (<500ms); skeleton simples suficiente | @ux-design-expert |
| TD-UX-011 + TD-UX-019 | 1.5h (separados) | 1h (combinados) | Mesma raiz (tokens no Tailwind). Resolver via TD-UX-022 | @ux-design-expert |

#### Condicoes QA Atendidas

| # | Condicao | Status | Como Atendida |
|---|----------|--------|---------------|
| 1 | Incorporar 7 novos debitos (TD-DB-014 a TD-DB-017, TD-UX-021 a TD-UX-023) | **Atendida** | Todos incluidos no inventario e na matriz de priorizacao |
| 2 | Atualizar grafo de dependencias (TD-DB-015 no Nivel 0, TD-DB-014 pre-req de TD-DB-005) | **Atendida** | Grafo atualizado com ambas as mudancas e validacao explicita |
| 3 | Atualizar totais para ~152h | **Atendida** | Total recalculado: ~152h (83h SYS + 16h DB + 48h UX, com ajustes) |
| 4 | Marcar itens pre-demo como BLOQUEANTE | **Atendida** | TD-UX-001/002/003 e TD-SYS-001/TD-DB-016 marcados como BLOQUEANTE na matriz e no plano |
| 5 | Remover TD-DB-004 (substituido por TD-DB-014) | **Atendida** | TD-DB-004 removido do inventario; TD-DB-014 incluido com escopo correto |

---

*Documento consolidado por @architect (Atlas) com base em 8 fases de analise: auditoria arquitetural (Fases 1-3), consolidacao DRAFT (Fase 4), revisao de @data-engineer Forge (Fase 5), revisao de @ux-design-expert Pixel (Fase 6), validacao de @qa Shield (Fase 7), e finalizacao (Fase 8). Todos os caminhos de arquivo, severidades, estimativas e detalhes validados contra o codigo-fonte no commit 2a76827b.*
