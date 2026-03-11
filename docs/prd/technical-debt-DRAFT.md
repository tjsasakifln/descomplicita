# Technical Debt Assessment - DRAFT

## Para Revisao dos Especialistas

> **Data:** 2026-03-11 | **Autor:** @architect (Atlas)
> **Fase:** POC Brownfield Discovery (Fase 4 - Consolidacao)
> **Fontes:** system-architecture.md (Fase 1), SCHEMA.md + DB-AUDIT.md (Fase 2), frontend-spec.md (Fase 3)
> **Commit base:** 2a76827b (HEAD de main)

---

## 1. Resumo Executivo

| Metrica | Valor |
|---------|-------|
| **Total de debitos identificados** | **57** (24 sistema + 13 database + 20 frontend/UX) |
| **Debitos unicos apos deduplicacao** | **50** (7 sobreposicoes identificadas) |
| **Distribuicao por severidade** | 4 Criticos, 10 Altos, 16 Medios, 20 Baixos |
| **Esforco total estimado** | **~158h** (~83h sistema + ~14.5h DB + ~73.5h UX, com sobreposicoes) |
| **Esforco deduplicado estimado** | **~145h** |
| **Areas mais criticas** | Autenticacao (cross-cutting), tokens CSS do AuthModal, main.py monolitico |

### Distribuicao por Area

| Area | Criticos | Altos | Medios | Baixos | Total | Horas |
|------|----------|-------|--------|--------|-------|-------|
| Sistema (TD-SYS-*) | 3 | 6 | 8 | 7 | 24 | ~83h |
| Database (TD-DB-*) | 0 | 0 | 5 | 8 | 13 | ~14.5h |
| Frontend/UX (TD-UX-*) | 1 | 2 | 5 | 12 | 20 | ~73.5h |

---

## 2. Debitos de Sistema (Fase 1)

Origem: `docs/architecture/system-architecture.md` -- Secao 9

| ID | Debito | Severidade | Horas | Impacto | Area |
|----|--------|------------|-------|---------|------|
| TD-SYS-001 | SQLite legado nao removido (descomplicita.db + aiosqlite) | Critico | 2 | Seguranca, manutencao | Backend |
| TD-SYS-002 | main.py monolitico (~1230 linhas) | Critico | 8 | Manutencao, testabilidade | Backend |
| TD-SYS-003 | Sem linter Python (ruff, flake8, mypy, black) | Critico | 4 | Qualidade | Backend |
| TD-SYS-004 | Testes de integracao CI placeholder | Alto | 8 | Qualidade, confiabilidade | CI/CD |
| TD-SYS-005 | Supabase client criado a cada request de auth | Alto | 3 | Performance | Backend |
| TD-SYS-006 | Sem Pydantic nos endpoints de auth | Alto | 4 | Seguranca, DX | Backend |
| TD-SYS-007 | JWT token cached em variavel de modulo (serverless) | Alto | 3 | Confiabilidade | Frontend |
| TD-SYS-008 | Ausencia de pre-commit hooks | Alto | 2 | Qualidade | DX |
| TD-SYS-009 | Coverage thresholds frontend baixos | Alto | 16 | Qualidade | Frontend |
| TD-SYS-010 | docker-compose.yml desatualizado | Medio | 2 | DX | Infra |
| TD-SYS-011 | Sem /health no frontend | Medio | 2 | Observabilidade | Frontend |
| TD-SYS-012 | API versioning sem deprecacao | Medio | 4 | Manutencao | Backend |
| TD-SYS-013 | Sem migration runner automatizado | Medio | 6 | Operacional | DB/Infra |
| TD-SYS-014 | ThreadPoolExecutor sem monitoring | Medio | 3 | Performance | Backend |
| TD-SYS-015 | Sem rate limiting na autenticacao | Medio | 2 | Seguranca | Backend |
| TD-SYS-016 | Vercel functions timeout 10s | Medio | 2 | Confiabilidade | Frontend |
| TD-SYS-017 | Sem logging estruturado no frontend | Medio | 4 | Observabilidade | Frontend |
| TD-SYS-018 | Diretorio com nome invalido na raiz | Baixo | 0.5 | Limpeza | Repo |
| TD-SYS-019 | Markdown acumulados na raiz | Baixo | 1 | Organizacao | Repo |
| TD-SYS-020 | ESLint config minimal | Baixo | 3 | Qualidade | Frontend |
| TD-SYS-021 | Google Fonts sem fallback system | Baixo | 1 | UX | Frontend |
| TD-SYS-022 | Path alias inconsistente build/test | Baixo | 1 | DX | Frontend |
| TD-SYS-023 | Transparencia source sem API key obrigatoria | Baixo | 1 | Confiabilidade | Backend |
| TD-SYS-024 | Sem CHANGELOG ou release notes | Baixo | 2 | Documentacao | Repo |

---

## 3. Debitos de Database (Fase 2)

Origem: `supabase/docs/DB-AUDIT.md` -- Secao 8

> :warning: **PENDENTE:** Revisao do @data-engineer (Forge)

| ID | Debito | Severidade | Horas | Impacto | Area |
|----|--------|------------|-------|---------|------|
| TD-DB-001 | CHECK constraint em `search_history.status` | Media | 0.5 | Integridade de dados | Schema |
| TD-DB-002 | RLS granular por operacao (WITH CHECK no INSERT) | Media | 2 | Seguranca cross-usuario | RLS |
| TD-DB-003 | UNIQUE em `users.email` | Baixa | 0.5 | Integridade | Schema |
| TD-DB-004 | Unificar bibliotecas JWT (python-jose -> PyJWT) | Baixa | 1 | Superficie de ataque | Auth |
| TD-DB-005 | Habilitar `verify_aud` no Supabase JWT | Media | 1 | Seguranca | Auth |
| TD-DB-006 | Cleanup em batches (evitar locks) | Media | 1 | Estabilidade | Performance |
| TD-DB-007 | Indice parcial para cleanup | Baixa | 0.5 | Performance | Indices |
| TD-DB-008 | Limite em `saved_searches.name` (CHECK length) | Baixa | 0.5 | Integridade | Schema |
| TD-DB-009 | `updated_at` em `saved_searches` | Baixa | 0.5 | Consistencia schema | Schema |
| TD-DB-010 | Ativar pg_cron ou cron externo para retention | Media | 2 | Acumulo de dados | Operacional |
| TD-DB-011 | Indice em `users.email` | Baixa | 0.5 | Performance futura | Indices |
| TD-DB-012 | Limite de saved_searches no DB (trigger/constraint) | Baixa | 1 | Defesa em profundidade | Schema |
| TD-DB-013 | Metricas de falha de persistencia (Database silencioso) | Baixa | 1.5 | Observabilidade | Backend |

---

## 4. Debitos de Frontend/UX (Fase 3)

Origem: `docs/frontend/frontend-spec.md` -- Secao 9

> :warning: **PENDENTE:** Revisao do @ux-expert (Pixel)

| ID | Debito | Severidade | Horas | Impacto UX | Area |
|----|--------|------------|-------|------------|------|
| TD-UX-001 | AuthModal usa tokens CSS inexistentes (--card-bg, --text-primary, etc.) | Critico | 2 | Auth quebrado visualmente | Componente |
| TD-UX-002 | AuthModal usa classes Tailwind hardcoded (bg-red-100) | Alto | 1 | Cores incorretas em 3 temas | Componente |
| TD-UX-003 | ItemsList usa cores Tailwind hardcoded | Alto | 2 | Badges inconsistentes com SearchSummary | Componente |
| TD-UX-004 | Button reutilizavel existe mas nao e usado | Medio | 3 | Duplicacao de estilos | Design System |
| TD-UX-005 | Pagina unica (SPA-like), sem rota de resultados | Medio | 8 | Sem deep-linking de resultados | Arquitetura |
| TD-UX-006 | Footer duplicado (page.tsx e termos/page.tsx) | Baixo | 1 | Manutencao duplicada | Componente |
| TD-UX-007 | Versao hardcoded "v2.0" no footer | Baixo | 0.5 | Info desatualizada | Componente |
| TD-UX-008 | rounded-modal definido mas nao usado | Baixo | 0.5 | Inconsistencia radius | Design System |
| TD-UX-009 | Sem loading state para pagina inicial | Baixo | 2 | Flash de conteudo parcial | UX |
| TD-UX-010 | Paginacao sem acentos nos aria-labels | Baixo | 0.5 | Pronuncia incorreta em screen readers | Acessibilidade |
| TD-UX-011 | SearchSummary usa inline style={{}} para badge tokens | Baixo | 1 | Estilos mistos | Componente |
| TD-UX-012 | Sem i18n framework | Baixo | 16 | Internacionalizacao futura custosa | Arquitetura |
| TD-UX-013 | dateDiffInDays duplicada em dois arquivos | Baixo | 0.5 | Risco de divergencia | Codigo |
| TD-UX-014 | Coverage frontend abaixo do ideal (branches 52.74%) | Medio | 8 | Regressoes ocultas | Qualidade |
| TD-UX-015 | Sem indicacao visual de setores fallback | Baixo | 1 | Usuario desinformado | UX |
| TD-UX-016 | SSE nao implementado (polling com backoff) | Medio | 12 | Latencia 1-15s, requests extras | Performance |
| TD-UX-017 | carouselData.ts nao auditado | Baixo | 2 | Conteudo potencialmente incorreto | Conteudo |
| TD-UX-018 | Sem PWA / Service Worker | Baixo | 8 | Sem funcionalidade offline | UX |
| TD-UX-019 | SourceBadges usa style={{}} para --ink-warning | Baixo | 0.5 | Padroes mistos | Componente |
| TD-UX-020 | Sem componente Input/Select reutilizavel | Medio | 4 | ~10 inputs com classes duplicadas | Design System |

---

## 5. Matriz de Priorizacao Preliminar

Ordenado por: Severidade (Critico > Alto > Medio > Baixo), e dentro de cada grupo por esforco (menor = quick win primeiro).

| Rank | ID | Debito | Sev. | Horas | Quick Win? | Cross-cutting? |
|------|-----|--------|------|-------|------------|----------------|
| **1** | TD-UX-001 | AuthModal: tokens CSS inexistentes | Critico | 2 | **Sim** | -- |
| **2** | TD-SYS-001 | SQLite legado nao removido | Critico | 2 | **Sim** | -- |
| **3** | TD-SYS-003 | Sem linter Python | Critico | 4 | -- | -- |
| **4** | TD-SYS-002 | main.py monolitico | Critico | 8 | -- | -- |
| **5** | TD-UX-002 | AuthModal: classes hardcoded | Alto | 1 | **Sim** | -- |
| **6** | TD-SYS-008 | Sem pre-commit hooks | Alto | 2 | **Sim** | -- |
| **7** | TD-UX-003 | ItemsList: cores hardcoded | Alto | 2 | **Sim** | -- |
| **8** | TD-SYS-005 | Supabase client recriado por request | Alto | 3 | -- | **Sim** (auth) |
| **9** | TD-SYS-007 | JWT token cached em modulo serverless | Alto | 3 | -- | **Sim** (auth) |
| **10** | TD-SYS-006 | Sem Pydantic nos endpoints auth | Alto | 4 | -- | **Sim** (auth) |
| **11** | TD-SYS-004 | Testes integracao CI placeholder | Alto | 8 | -- | -- |
| **12** | TD-SYS-009 | Coverage thresholds baixos | Alto | 16 | -- | **Sim** (UX-014) |
| **13** | TD-DB-001 | CHECK constraint em status | Medio | 0.5 | **Sim** | -- |
| **14** | TD-DB-005 | verify_aud no Supabase JWT | Medio | 1 | **Sim** | **Sim** (auth) |
| **15** | TD-DB-006 | Cleanup em batches | Medio | 1 | **Sim** | -- |
| **16** | TD-SYS-010 | docker-compose desatualizado | Medio | 2 | -- | -- |
| **17** | TD-SYS-011 | Sem /health frontend | Medio | 2 | -- | -- |
| **18** | TD-SYS-015 | Sem rate limiting auth | Medio | 2 | **Sim** | **Sim** (auth) |
| **19** | TD-SYS-016 | Vercel timeout 10s | Medio | 2 | **Sim** | -- |
| **20** | TD-DB-002 | RLS granular (WITH CHECK) | Medio | 2 | -- | **Sim** (auth) |
| **21** | TD-DB-010 | Ativar retention policy | Medio | 2 | -- | -- |
| **22** | TD-UX-004 | Button nao utilizado | Medio | 3 | -- | -- |
| **23** | TD-SYS-014 | ThreadPoolExecutor sem monitoring | Medio | 3 | -- | -- |
| **24** | TD-SYS-012 | API versioning sem deprecacao | Medio | 4 | -- | -- |
| **25** | TD-SYS-017 | Sem logging estruturado frontend | Medio | 4 | -- | -- |
| **26** | TD-UX-020 | Sem Input/Select reutilizavel | Medio | 4 | -- | -- |
| **27** | TD-SYS-013 | Sem migration runner | Medio | 6 | -- | **Sim** (DB) |
| **28** | TD-UX-014 | Coverage frontend abaixo do ideal | Medio | 8 | -- | **Sim** (SYS-009) |
| **29** | TD-UX-005 | Pagina unica sem rota resultados | Medio | 8 | -- | -- |
| **30** | TD-UX-016 | SSE nao implementado | Medio | 12 | -- | -- |
| **31** | TD-UX-010 | Paginacao sem acentos | Baixo | 0.5 | **Sim** | -- |
| **32** | TD-UX-013 | dateDiffInDays duplicada | Baixo | 0.5 | **Sim** | -- |
| **33** | TD-UX-007 | Versao hardcoded | Baixo | 0.5 | **Sim** | -- |
| **34** | TD-UX-008 | rounded-modal nao usado | Baixo | 0.5 | **Sim** | -- |
| **35** | TD-UX-019 | SourceBadges inline style | Baixo | 0.5 | **Sim** | -- |
| **36** | TD-SYS-018 | Diretorio com nome invalido | Baixo | 0.5 | **Sim** | -- |
| **37** | TD-DB-003 | UNIQUE em users.email | Baixo | 0.5 | **Sim** | -- |
| **38** | TD-DB-007 | Indice parcial cleanup | Baixo | 0.5 | **Sim** | -- |
| **39** | TD-DB-008 | Limite em saved_searches.name | Baixo | 0.5 | **Sim** | -- |
| **40** | TD-DB-009 | updated_at em saved_searches | Baixo | 0.5 | **Sim** | -- |
| **41** | TD-DB-011 | Indice em users.email | Baixo | 0.5 | **Sim** | -- |
| **42** | TD-SYS-022 | Path alias inconsistente | Baixo | 1 | **Sim** | -- |
| **43** | TD-SYS-023 | Transparencia sem API key obrigatoria | Baixo | 1 | **Sim** | -- |
| **44** | TD-SYS-019 | Markdown na raiz | Baixo | 1 | **Sim** | -- |
| **45** | TD-SYS-021 | Fonts sem fallback | Baixo | 1 | **Sim** | -- |
| **46** | TD-UX-006 | Footer duplicado | Baixo | 1 | **Sim** | -- |
| **47** | TD-UX-011 | SearchSummary inline styles | Baixo | 1 | **Sim** | -- |
| **48** | TD-UX-015 | Setores fallback sem indicacao | Baixo | 1 | -- | -- |
| **49** | TD-DB-004 | Unificar JWT libs | Baixo | 1 | -- | **Sim** (auth) |
| **50** | TD-DB-012 | Limite saved_searches no DB | Baixo | 1 | -- | -- |
| **51** | TD-DB-013 | Metricas falha persistencia | Baixo | 1.5 | -- | -- |
| **52** | TD-UX-009 | Sem loading state pagina inicial | Baixo | 2 | -- | -- |
| **53** | TD-SYS-024 | Sem CHANGELOG | Baixo | 2 | -- | -- |
| **54** | TD-UX-017 | carouselData nao auditado | Baixo | 2 | -- | -- |
| **55** | TD-SYS-020 | ESLint minimal | Baixo | 3 | -- | -- |
| **56** | TD-UX-018 | Sem PWA/Service Worker | Baixo | 8 | -- | -- |
| **57** | TD-UX-012 | Sem i18n | Baixo | 16 | -- | -- |

---

## 6. Debitos Cruzados (Cross-cutting)

### 6.1 Cluster de Autenticacao

O subsistema de autenticacao concentra a maior quantidade de debitos que atravessam multiplas camadas:

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-SYS-005 | Supabase client recriado por request | Backend (auth endpoints) |
| TD-SYS-006 | Sem Pydantic nos endpoints auth | Backend (API) |
| TD-SYS-007 | JWT cached em modulo serverless | Frontend (BFF) |
| TD-SYS-015 | Sem rate limiting auth | Backend (seguranca) |
| TD-DB-002 | RLS INSERT sem WITH CHECK | Database (seguranca) |
| TD-DB-004 | Duas libs JWT (python-jose + PyJWT) | Backend (auth) |
| TD-DB-005 | verify_aud desabilitado | Backend (auth) + Database (seguranca) |

**Impacto combinado:** A resolucao coordenada desse cluster eliminaria 7 debitos (~17h) e fortaleceria significativamente a postura de seguranca do sistema.

### 6.2 Cluster de Qualidade / Cobertura

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-SYS-009 | Coverage thresholds frontend baixos | Frontend (testes) |
| TD-UX-014 | Coverage branches 52.74% | Frontend (testes) |
| TD-SYS-004 | Testes integracao CI placeholder | CI/CD (backend + frontend) |
| TD-SYS-003 | Sem linter Python | Backend (qualidade) |
| TD-SYS-008 | Sem pre-commit hooks | Repo (ambos) |
| TD-SYS-020 | ESLint minimal | Frontend (qualidade) |

**Nota:** TD-SYS-009 e TD-UX-014 sao essencialmente o mesmo debito visto de angulos diferentes. Contabilizar como **1 item** (~16h).

### 6.3 Cluster de Design Tokens

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-UX-001 | AuthModal tokens inexistentes | Frontend (auth UI) |
| TD-UX-002 | AuthModal classes hardcoded | Frontend (auth UI) |
| TD-UX-003 | ItemsList cores hardcoded | Frontend (resultados) |
| TD-UX-004 | Button nao utilizado | Frontend (design system) |
| TD-UX-020 | Sem Input/Select reutilizavel | Frontend (design system) |

**Impacto combinado:** Resolver em sequencia criaria um design system coerente, eliminando 5 debitos (~10h).

### 6.4 Cluster de Infraestrutura / Operacional

| ID | Debito | Camadas afetadas |
|----|--------|------------------|
| TD-SYS-013 | Sem migration runner | Backend + DB |
| TD-DB-010 | Sem retention policy ativa | DB + Operacional |
| TD-SYS-010 | docker-compose desatualizado | Dev local (backend + frontend) |

---

## 7. Dependencias entre Debitos

```
TD-SYS-003 (linter Python)
  \--> TD-SYS-008 (pre-commit hooks) -- hooks dependem de ter linters configurados
         \--> TD-SYS-002 (refactor main.py) -- refactor deve passar por linting

TD-SYS-001 (remover SQLite)
  \--> (independente, pode ser feito a qualquer momento)

TD-UX-001 (tokens AuthModal)
  \--> TD-UX-002 (classes AuthModal) -- primeiro fix tokens, depois migrar classes

TD-UX-004 (usar Button existente)
  \--> TD-UX-020 (criar Input/Select) -- mesmo padrao de componentizacao

TD-DB-004 (unificar JWT libs)
  \--> TD-DB-005 (verify_aud) -- pode ser feito junto na mesma refatoracao

TD-SYS-006 (Pydantic auth)
  \--> TD-SYS-005 (Supabase client DI) -- ambos tocam mesmos endpoints

TD-SYS-013 (migration runner)
  \--> TD-DB-001 (CHECK constraint status)
  \--> TD-DB-002 (RLS granular)
  \--> TD-DB-003 (UNIQUE email)
  \--> TD-DB-006 a TD-DB-012 -- todas migracoes de schema dependem de runner

TD-SYS-009 / TD-UX-014 (coverage)
  \--> TD-SYS-004 (testes integracao) -- subir coverage requer mais testes

TD-UX-005 (rotas de resultado)
  \--> TD-UX-016 (SSE) -- reestruturar paginas antes de mudar protocolo
```

### Grafo Simplificado de Dependencias

```
Nivel 0 (sem dependencias - pode comecar agora):
  TD-SYS-001, TD-UX-001, TD-DB-001, TD-SYS-015, TD-SYS-016,
  TD-SYS-018/019, TD-UX-010/013/007/008, TD-DB-003/007/008/009/011

Nivel 1 (depende de Nivel 0):
  TD-UX-002 (apos UX-001)
  TD-SYS-003 (independente, mas habilita Nivel 2)
  TD-DB-004 + TD-DB-005 (juntos)
  TD-SYS-005 + TD-SYS-006 (juntos)

Nivel 2 (depende de Nivel 1):
  TD-SYS-008 (apos SYS-003)
  TD-UX-003, TD-UX-004 (apos design token cleanup)
  TD-SYS-013 (migration runner)

Nivel 3 (depende de Nivel 2):
  TD-SYS-002 (refactor main.py, apos linter + hooks)
  TD-DB-002, TD-DB-006, TD-DB-010, TD-DB-012 (apos migration runner)
  TD-UX-020 (apos Button adotado)

Nivel 4 (longo prazo):
  TD-SYS-004, TD-SYS-009/UX-014 (coverage)
  TD-UX-005 (rotas de resultado)
  TD-UX-016 (SSE)
  TD-UX-012 (i18n), TD-UX-018 (PWA)
```

---

## 8. Perguntas para Especialistas

### Para @data-engineer (Forge):

1. **TD-DB-002 (RLS granular):** O `FOR ALL` com `USING` cobre o caso de INSERT? Em testes, um usuario autenticado via anon key consegue inserir registros com `user_id` de terceiros em `saved_searches`? Ou o Supabase impede implicitamente?

2. **TD-DB-005 (verify_aud):** Qual e o valor correto do `aud` claim para tokens do nosso projeto Supabase? Existe documentacao oficial sobre o formato esperado?

3. **TD-DB-010 (retention policy):** O plano atual do Supabase suporta `pg_cron`? Se nao, qual alternativa recomendada -- cron job no Railway, GitHub Actions schedule, ou Cloud Scheduler externo?

4. **TD-DB-006 (cleanup batches):** Para o volume esperado no POC (<1000 buscas/mes), o DELETE sem LIMIT ja e um risco real ou so se torna problema em escala?

5. **TD-SYS-013 (migration runner):** Preferencia entre `supabase db push` (CLI oficial), Alembic, ou script SQL customizado para o CI?

6. **Dados legados:** Ha dados relevantes no `descomplicita.db` (SQLite) que precisam ser migrados antes de remover o arquivo? Ou a migracao ja foi completada em v3-story-2.0?

### Para @ux-expert (Pixel):

1. **TD-UX-001 (AuthModal tokens):** Confirma que o AuthModal esta renderizando com cores default do browser? Ha screenshots dos 5 temas para documentar o bug visual?

2. **TD-UX-005 (pagina unica):** Qual a prioridade real de deep-linking de resultados para o publico-alvo? Usuarios de licitacoes costumam compartilhar links de busca?

3. **TD-UX-004 + TD-UX-020 (design system):** Faz sentido criar um sprint dedicado a "Design System Completion" (Button adoption + Input/Select + modal radius) antes de novas features? Ou resolver incrementalmente?

4. **TD-UX-016 (SSE vs polling):** O polling com backoff exponencial (1-15s) causa reclamacoes de usuarios? Ou e aceitavel no contexto de buscas que levam 30s-5min?

5. **TD-UX-012 (i18n):** Ha plano de internacionalizacao no roadmap? Se nao, podemos desprioritizar para alem do POC?

6. **TD-UX-009 (loading inicial):** O tempo de carga da pagina inicial (fetch setores) e perceptivel pelos usuarios? Ou o dynamic import mascara adequadamente?

---

## 9. Recomendacoes Preliminares

### Fase 1 -- Quick Wins (1-2 sprints, ~15h)

Items de baixo esforco com alto impacto. Nao requerem mudancas arquiteturais.

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-UX-001 | AuthModal: fix tokens CSS | 2 | Critico. Auth UI quebrada em todos os temas. |
| 2 | TD-SYS-001 | Remover SQLite legado | 2 | Critico. Elimina confusao e risco de vazamento. |
| 3 | TD-UX-002 | AuthModal: migrar para tokens semanticos | 1 | Alto. Dependencia direta do item anterior. |
| 4 | TD-UX-003 | ItemsList: migrar para tokens | 2 | Alto. Inconsistencia visual com SearchSummary. |
| 5 | TD-SYS-015 | Rate limiting nos endpoints auth | 2 | Medio. Brute force prevention (seguranca). |
| 6 | TD-DB-001 | CHECK constraint em status | 0.5 | Medio. Migracao trivial. |
| 7 | TD-DB-005 | Habilitar verify_aud | 1 | Medio. Seguranca com minimo esforco. |
| 8 | TD-SYS-016 | Ajustar Vercel timeout | 2 | Medio. Evita timeout em buscas grandes. |
| 9 | TD-UX-010 | Acentos nos aria-labels | 0.5 | Baixo. Fix trivial de acessibilidade. |
| 10 | TD-UX-013 | Extrair dateDiffInDays | 0.5 | Baixo. Deduplicacao trivial. |
| 11 | TD-SYS-018 | Remover diretorio invalido | 0.5 | Baixo. Limpeza trivial. |
| 12 | TD-SYS-019 | Organizar markdowns da raiz | 1 | Baixo. Higiene do repositorio. |
| -- | | **Subtotal** | **~15h** | |

### Fase 2 -- Fundacao (2-3 sprints, ~36h)

Items estruturais que habilitam qualidade e seguranca a longo prazo.

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-SYS-003 | Configurar linter Python (ruff) | 4 | Critico. Prerequisito para refactoring seguro. |
| 2 | TD-SYS-008 | Pre-commit hooks (husky + lint-staged + ruff) | 2 | Alto. Gate de qualidade antes do commit. |
| 3 | TD-SYS-005 + SYS-006 | Refatorar auth endpoints (Pydantic + DI) | 7 | Alto. Cluster de auth, resolver junto. |
| 4 | TD-DB-004 + DB-005 | Unificar JWT + verify_aud | 2 | Medio. Reduzir deps, fortalecer auth. |
| 5 | TD-DB-002 | RLS granular com WITH CHECK | 2 | Medio. Fechar brecha de insercao. |
| 6 | TD-SYS-013 | Migration runner automatizado | 6 | Medio. Habilita todas as migracoes DB futuras. |
| 7 | TD-DB-006 + DB-010 | Cleanup batches + retention ativa | 3 | Medio. Estabilidade operacional. |
| 8 | TD-UX-004 | Adotar Button em toda a app | 3 | Medio. Consistencia do design system. |
| 9 | TD-SYS-007 | Corrigir JWT cache serverless | 3 | Alto. Confiabilidade da auth no frontend. |
| 10 | TD-SYS-017 | Logging estruturado frontend | 4 | Medio. Observabilidade cross-stack. |
| -- | | **Subtotal** | **~36h** | |

### Fase 3 -- Otimizacao (3-5 sprints, ~71h)

Items de medio/longo prazo que melhoram escalabilidade e experiencia.

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | TD-SYS-002 | Refatorar main.py | 8 | Critico (mas depende de linter). |
| 2 | TD-SYS-004 | Implementar testes integracao CI | 8 | Alto. Cobertura de integracao real. |
| 3 | TD-SYS-009 / UX-014 | Subir coverage thresholds | 16 | Alto. Prevencao de regressoes. |
| 4 | TD-UX-020 | Criar Input/Select reutilizavel | 4 | Medio. Completar design system. |
| 5 | TD-UX-005 | Rotas de resultado (deep-link) | 8 | Medio. Depende de validacao UX. |
| 6 | TD-UX-016 | SSE para progresso em tempo real | 12 | Medio. Melhoria de performance. |
| 7 | TD-SYS-012 | Estrategia de deprecacao API | 4 | Medio. Governanca de API. |
| 8 | TD-SYS-020 | Expandir ESLint config | 3 | Baixo. Qualidade incremental. |
| 9 | TD-UX-018 | PWA / Service Worker | 8 | Baixo. Depende de demanda. |
| -- | | **Subtotal** | **~71h** | |

### Fora de Escopo POC

Items que devem ser avaliados apenas se o produto escalar:

- **TD-UX-012** (i18n, 16h) -- So se houver plano de internacionalizacao
- **TD-SYS-014** (ThreadPool monitoring, 3h) -- So com metricas de saturacao
- **TD-SYS-011** (/health frontend, 2h) -- Depende de politica de monitoramento

---

## Apendice: Sobreposicoes Identificadas

Debitos que aparecem em multiplos relatorios e foram deduplicados na contagem final:

| Debito | Aparece em | ID Unificado | Acao |
|--------|-----------|--------------|------|
| Coverage frontend baixa | TD-SYS-009 + TD-UX-014 | TD-SYS-009 (primario) | Contabilizar 1x (16h) |
| Unificar libs JWT | TD-SYS (mencionado sec. 3.4) + TD-DB-004 | TD-DB-004 (primario) | Contabilizar 1x (1h) |
| Sem migration runner | TD-SYS-013 + DB-AUDIT sec. 10 | TD-SYS-013 (primario) | Contabilizar 1x (6h) |
| verify_aud JWT | TD-SYS (mencionado sec. 3.4) + TD-DB-005 | TD-DB-005 (primario) | Contabilizar 1x (1h) |
| Supabase client recriado | TD-SYS-005 + DB-AUDIT sec. 7 | TD-SYS-005 (primario) | Contabilizar 1x (3h) |
| Metricas de falha DB | TD-SYS-017 (parcial) + TD-DB-013 | Ambos mantidos | Escopos diferentes |
| Rate limit auth | TD-SYS-015 + DB-AUDIT sec. 7 (mencionado) | TD-SYS-015 (primario) | Contabilizar 1x (2h) |

**Reducao por deduplicacao:** ~13h (de ~171h bruto para ~158h, e com sobreposicoes parciais para ~145h efetivo).

---

> **Proximo passo:** Revisao pelos especialistas (@data-engineer e @ux-expert) para validar severidades, estimativas e prioridades. Apos revisao, promover para `technical-debt-assessment.md` (versao final).
