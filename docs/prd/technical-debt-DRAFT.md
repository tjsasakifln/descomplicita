# Technical Debt Assessment - DRAFT

## Descomplicita POC v0.2
## Data: 2026-03-09
## Para Revisao dos Especialistas

> **Status:** RASCUNHO - Consolidacao das Fases 1 e 3 do Brownfield Discovery.
> Fase 2 (Database) foi pulada - arquitetura stateless sem banco de dados.
> Este documento requer validacao dos especialistas antes de ser usado para planejamento.

---

### 1. Debitos de Sistema

Consolidados de `docs/architecture/system-architecture.md` - Secao 9: Technical Debt Inventory.

#### 1.1 Severidade Critica

| ID | Descricao | Impacto | Esforco |
|----|-----------|---------|---------|
| TD-C01 | **Excel bytes armazenados no resultado do job (memoria + Redis).** Jobs completados armazenam bytes Excel brutos tanto no dict Python quanto serializados no Redis como JSON. Um job com 500 licitacoes pode produzir dados multi-MB duplicados entre duas stores. Sem streaming ou armazenamento temporario em arquivo. | Esgotamento de memoria sob carga concorrente, pressao de memoria no Redis | Medio |
| TD-C02 | **Sem autenticacao de usuario.** Chave API unica compartilhada para todos os clientes. Sem identidade de usuario, sem modelo de autorizacao, sem trilha de auditoria. Se API_KEY nao estiver definida, todos os endpoints ficam totalmente abertos. | Exposicao de seguranca, sem accountability | Alto |
| TD-C03 | **3 de 5 fontes de dados desabilitadas.** ComprasGov (API deprecada), Querido Diario (retorna HTML), TCE-RJ (404). A arquitetura multi-source esta subutilizada; efetivamente um sistema dual-source. Codigo morto permanece na codebase. | Cobertura de dados reduzida, carga de manutencao por codigo morto | Alto |

#### 1.2 Severidade Alta

| ID | Descricao | Impacto | Esforco |
|----|-----------|---------|---------|
| TD-H01 | **In-memory job store como primario.** RedisJobStore estende JobStore in-memory em padrao dual-write. Na reinicializacao do processo, estado in-memory e perdido. Redis serve como fallback para leituras, mas o dual-write adiciona complexidade e potencial inconsistencia. | Perda de dados de jobs em restart durante buscas ativas | Medio |
| TD-H02 | **asyncio.create_task para jobs em background.** Jobs rodam como tasks asyncio nao rastreadas no mesmo processo. Sem fila de tarefas (Celery, RQ). Em shutdown/deploy, jobs em execucao sao silenciosamente perdidos. Handler SIGTERM existe mas apenas define um evento que nada aguarda. | Perda de jobs em deploy/restart | Alto |
| TD-H03 | **API OpenAI chamada sincronamente no thread pool.** `gerar_resumo()` usa cliente sincrono OpenAI via `loop.run_in_executor(None, ...)`, bloqueando uma thread do pool padrao. Deveria usar cliente async OpenAI. | Esgotamento do thread pool sob buscas concorrentes | Medio |
| TD-H04 | **Sem banco de dados.** Todo estado e efemero. Sem dados historicos de busca, sem persistencia de analytics, sem preferencias de usuario server-side. Limita evolucao do produto. | Nao e possivel construir features que requerem persistencia | Alto |
| TD-H05 | **CORS allow_headers=\* e excessivamente permissivo.** Aceita qualquer header. Deveria limitar a Content-Type, X-API-Key, X-Request-ID. | Risco menor de seguranca, pratica nao-padrao | Baixo |
| TD-H06 | **Funcoes serverless Vercel tem duracao maxima de 10s.** A rota de download faz buffer do arquivo Excel inteiro (`response.arrayBuffer()`) antes de retornar. Arquivos grandes podem exceder o limite de 10s ou 1024MB de memoria. | Falhas de download para arquivos grandes | Medio |

#### 1.3 Severidade Media

| ID | Descricao | Impacto | Esforco |
|----|-----------|---------|---------|
| TD-M01 | **Filtro de deadline desabilitado.** Campo `dataAberturaProposta` foi mal interpretado como prazo de submissao. Filtro comentado com TODO. Sem verificacao alternativa de deadline. | Usuarios veem licitacoes historicas irrelevantes | Medio |
| TD-M02 | **Sem paginacao nos resultados.** Todos os resultados filtrados retornados em uma unica resposta. Conjuntos grandes afetam tempo de resposta e memoria. | Degradacao de performance com muitos resultados | Medio |
| TD-M03 | **Modelo LLM hardcoded.** `gpt-4.1-nano` hardcoded em `llm.py` linha 131. Docker-compose expoe variavel `LLM_MODEL` mas o codigo a ignora. | Nao e possivel trocar modelos sem alterar codigo | Baixo |
| TD-M04 | **Sem timeout para chamadas LLM.** Cliente OpenAI usa timeout padrao. Respostas longas do LLM podem bloquear o worker do thread pool indefinidamente. | Estrangulamento de threads | Baixo |
| TD-M05 | **Estado global mutavel para DI.** `dependencies.py` usa globais a nivel de modulo sem framework de DI. Testes requerem patching cuidadoso. | Complexidade de teste, acoplamento oculto | Medio |
| TD-M06 | **Sem versionamento de API.** Endpoints nao versionados (`/buscar` e nao `/v1/buscar`). Breaking changes afetam todos os clientes simultaneamente. | Evolucao de API dificultada | Medio |
| TD-M07 | **Sem header Content-Security-Policy.** CSP ausente na config do Vercel. | Lacuna na mitigacao de XSS | Baixo |
| TD-M08 | **Sem header Strict-Transport-Security.** HSTS ausente na config do Vercel. | Risco de downgrade de protocolo | Baixo |
| TD-M09 | **MD5 usado para chaves de dedup.** `orchestrator.py` usa MD5 para hashing de chave composta. Embora o risco de colisao seja desprezivel para este caso, e um hash fraco por padroes modernos. | Risco teorico de colisao | Baixo |
| TD-M10 | **dangerouslySetInnerHTML para tema no frontend.** Script inline em `layout.tsx` para prevenir flash de tema. Atualmente seguro (sem input de usuario), mas contorna protecao XSS do React. | Vetor potencial de XSS se modificado | Baixo |
| TD-M11 | **Versao hardcoded em multiplos locais.** "0.3.0" aparece em `main.py` na definicao do app e na resposta do endpoint raiz. Sem single source of truth. | Risco de drift de versao | Baixo |

#### 1.4 Severidade Baixa

| ID | Descricao | Impacto | Esforco |
|----|-----------|---------|---------|
| TD-L01 | **is_healthy() usa httpx sincrono.** `ComprasGovSource.is_healthy()` e `TransparenciaSource.is_healthy()` fazem chamadas HTTP sincronas, bloqueando o event loop se chamadas de contexto async. Atualmente usado apenas em testes. | Chamada bloqueante em contexto async se usado | Baixo |
| TD-L02 | **Sem codigos de erro estruturados.** Respostas de erro usam mensagens em portugues em texto livre. Sem codigos machine-readable para tratamento no cliente. | Tratamento de erros no cliente e fragil | Baixo |
| TD-L03 | **Buscas salvas apenas em localStorage.** Sem persistencia server-side. Perdidas ao limpar browser. Sem sync cross-device. | Perda de dados, sem cross-device | Baixo |
| TD-L04 | **test_placeholder.py existe.** Arquivo de teste vazio commitado como scaffolding. | Higiene de codigo | Baixo |
| TD-L05 | **Conjuntos grandes de keywords/exclusoes.** Setor Vestuario tem ~130 keywords de inclusao e ~100 de exclusao via regex. Custo CPU mitigado por ordenacao fail-fast do filtro. | Preocupacao de performance em escala | Baixo |
| TD-L06 | **filter_batch roda no ThreadPoolExecutor padrao.** Usa `loop.run_in_executor(None, ...)` que compartilha o executor padrao com chamadas LLM. Contencao possivel. | Contencao de recursos sob carga | Baixo |

---

### 2. Debitos de Database

**N/A** - Projeto stateless, sem banco de dados.

O debito TD-H04 (ausencia de banco de dados) esta listado na Secao 1 como debito de sistema, pois impacta a evolucao arquitetural do produto como um todo.

---

### 3. Debitos de Frontend/UX

Consolidados de `docs/frontend/frontend-spec.md` - Secao 11: UX Debt Inventory.

> :warning: **PENDENTE:** Revisao do @ux-design-expert

| ID | Descricao | Severidade | Esforco |
|----|-----------|------------|---------|
| UXD-001 | **Termos multi-palavras impossiveis.** Espaco dispara criacao de token no input de termos, entao "camisa polo" se torna dois tokens separados. Necessario suporte a aspas ou delimitador alternativo. | **Alta** | Medio (3h) |
| UXD-002 | **Sem estado de carregamento para fetch de setores.** `useSearchForm` busca setores no mount mas nao mostra indicador. Dropdown aparece vazio momentaneamente se backend estiver lento. | Media | Pequeno (1h) |
| UXD-003 | **Sem pagina 404.** Falta `not-found.tsx` para rotas invalidas. | Baixa | Pequeno (1h) |
| UXD-004 | **Sem atalho de teclado para busca.** Enter em campos de data nao submete. Sem Ctrl+Enter ou similar. | Baixa | Pequeno (1h) |
| UXD-005 | **SavedSearchesDropdown usa div como backdrop.** Nao usa `<dialog>` nativo ou padrao ARIA listbox adequado. | Media | Medio (3h) |
| UXD-006 | **SaveSearchDialog usa div, nao `<dialog>` nativo.** Focus trap manual funciona mas elemento nativo e preferido. | Media | Medio (2h) |
| UXD-007 | **Sem elemento `<form>` envolvendo formulario.** Impede submissao nativa e autofill do browser. | Media | Pequeno (2h) |
| UXD-008 | **Mixpanel importado incondicionalmente.** ~40KB mesmo sem token. Deveria usar import dinamico. | Baixa | Pequeno (1h) |
| UXD-009 | **Sem confirmacao antes de page unload durante busca.** Usuario pode navegar para fora durante busca longa sem aviso. | Baixa | Pequeno (1h) |
| UXD-010 | **ThemeProvider aplica 30+ propriedades CSS imperativamente.** Poderia usar data attribute + regras CSS para manutenibilidade. | Baixa | Grande (8h) |
| UXD-011 | **Script FOUC no `<head>` duplica logica do ThemeProvider.** Subset handling pode divergir do ThemeProvider completo. | Media | Medio (3h) |
| UXD-012 | **Sem indicador offline/rede.** Falhas de fetch mostram erros genericos. Sem estado dedicado de conectividade. | Media | Medio (4h) |
| UXD-013 | **Footer sem conteudo significativo.** Linha unica de branding, sem links (privacidade, termos, ajuda). | Baixa | Pequeno (1h) |
| UXD-014 | **Texto de SourceBadges sem acentos portugues.** "combinacoes" deveria ter acentos corretos. | Baixa | Trivial (15min) |
| UXD-015 | **Sem auditoria de contraste de cores para os 5 temas.** Temas Sepia e Paperwhite nao verificados contra WCAG AA. | Media | Medio (4h) |
| UXD-016 | **LoadingProgress tem 450+ linhas.** Gerencia barra de progresso, ETA, estagios, grid UF, carrossel, skeletons, analytics. Deveria decompor. | Media | Grande (6h) |
| UXD-017 | **Setores fallback hardcoded.** 7 setores em `useSearchForm.ts` podem ficar desatualizados se backend mudar. | Baixa | Pequeno (1h) |
| UXD-018 | **Cores Tailwind hardcoded em SearchSummary.** Badges de tipo usam `bg-blue-100`, `bg-purple-100` em vez de design tokens. Quebram nos temas Sepia/Paperwhite. | Baixa | Pequeno (1h) |
| UXD-019 | **carouselData usa cores Tailwind hardcoded por categoria.** `bg-blue-50`, `bg-green-50`, etc. Nao utiliza tokens. | Baixa | Medio (2h) |
| UXD-020 | **Sem atributo `noValidate` no form.** Validacao nativa do browser pode conflitar com validacao customizada. | Baixa | Trivial (5min) |

---

### 4. Debitos Cruzados (Cross-cutting)

Debitos que impactam tanto backend quanto frontend simultaneamente.

#### 4.1 Seguranca Cross-layer

| ID | Descricao | Areas | Severidade |
|----|-----------|-------|------------|
| XD-SEC-01 | **Headers de seguranca ausentes.** Sem CSP (TD-M07), sem HSTS (TD-M08), sem Referrer-Policy, sem Permissions-Policy. Afeta tanto a entrega do frontend (Vercel) quanto o backend (Railway). | Backend + Frontend | Media |
| XD-SEC-02 | **Autenticacao fragil end-to-end.** API key unica compartilhada (TD-C02) combinada com bypass em dev. Frontend depende exclusivamente da BFF layer para seguranca. Sem rate limiting por usuario real. | Backend + Frontend | Critica |
| XD-SEC-03 | **dangerouslySetInnerHTML + sem CSP.** Script inline para tema (TD-M10) combinado com ausencia de CSP (TD-M07) amplia superficie de ataque XSS. | Frontend (com impacto na seguranca geral) | Media |

#### 4.2 Contratos de API

| ID | Descricao | Areas | Severidade |
|----|-----------|-------|------------|
| XD-API-01 | **Sem versionamento de API (TD-M06).** Qualquer breaking change no backend quebra o frontend imediatamente. BFF mitiga parcialmente, mas nao elimina o risco. | Backend + Frontend | Media |
| XD-API-02 | **Sem testes de contrato.** Tipos TypeScript no frontend e schemas Pydantic no backend nao sao validados entre si. Drift silencioso e possivel. | Backend + Frontend | Media |
| XD-API-03 | **Codigos de erro nao estruturados (TD-L02).** Frontend faz parsing de mensagens de erro em texto livre do backend. Qualquer mudanca de wording quebra o tratamento de erros. | Backend + Frontend | Baixa |

#### 4.3 Performance End-to-End

| ID | Descricao | Areas | Severidade |
|----|-----------|-------|------------|
| XD-PERF-01 | **Download bufferizado em cadeia.** Backend gera Excel em memoria (TD-C01), envia para BFF, que faz buffer inteiro via `arrayBuffer()` (TD-H06), e entao envia para browser. Tres copias completas do arquivo em memoria simultaneamente. | Backend + Frontend | Alta |
| XD-PERF-02 | **Sem paginacao end-to-end (TD-M02).** Backend retorna todos os resultados de uma vez, frontend renderiza tudo. Sem lazy loading ou virtualizacao. | Backend + Frontend | Media |
| XD-PERF-03 | **Polling de intervalo fixo.** Frontend faz polling a cada 2s independentemente da duracao da busca. Sem backoff exponencial. Gera carga desnecessaria para buscas longas. | Frontend (com carga no Backend) | Baixa |

#### 4.4 Cobertura de Testes Cross-cutting

| ID | Descricao | Areas | Severidade |
|----|-----------|-------|------------|
| XD-TEST-01 | **Sem testes de integracao frontend-backend.** E2E tests dependem de backend live, sem mock server para CI. | Backend + Frontend | Media |
| XD-TEST-02 | **Sem smoke tests pos-deploy.** Health endpoint existe mas sem suite de verificacao automatizada. | Infra + Backend + Frontend | Media |
| XD-TEST-03 | **Sem testes de regressao visual.** Mudancas de tema (5 variantes) e responsividade nao verificadas automaticamente. | Frontend | Baixa |

---

### 5. Matriz Preliminar de Priorizacao

| ID | Debito | Area | Severidade | Impacto | Esforco | Prioridade Preliminar |
|----|--------|------|------------|---------|---------|----------------------|
| TD-C02 | Sem autenticacao de usuario | Sistema | Critica | Critico | Alto | **P0** |
| XD-SEC-02 | Autenticacao fragil end-to-end | Cross-cutting | Critica | Critico | Alto | **P0** |
| TD-C01 | Excel bytes duplicados memoria + Redis | Sistema | Critica | Alto | Medio | **P1** |
| XD-PERF-01 | Download bufferizado em cadeia (3 copias) | Cross-cutting | Alta | Alto | Medio | **P1** |
| TD-H02 | Jobs como tasks asyncio nao duraveis | Sistema | Alta | Alto | Alto | **P1** |
| TD-C03 | 3 de 5 fontes desabilitadas (codigo morto) | Sistema | Critica | Medio | Alto | **P1** |
| UXD-001 | Termos multi-palavras impossiveis | Frontend/UX | Alta | Alto | Medio (3h) | **P1** |
| TD-H01 | In-memory job store como primario | Sistema | Alta | Alto | Medio | **P1** |
| TD-H03 | OpenAI API sincrona no thread pool | Sistema | Alta | Medio | Medio | **P2** |
| TD-H06 | Timeout Vercel 10s em downloads grandes | Sistema | Alta | Medio | Medio | **P2** |
| TD-H04 | Sem banco de dados (limita evolucao) | Sistema | Alta | Alto | Alto | **P2** |
| XD-API-01 | Sem versionamento de API | Cross-cutting | Media | Medio | Medio | **P2** |
| XD-API-02 | Sem testes de contrato | Cross-cutting | Media | Medio | Medio | **P2** |
| TD-M01 | Filtro de deadline desabilitado | Sistema | Media | Medio | Medio | **P2** |
| TD-M02 / XD-PERF-02 | Sem paginacao nos resultados | Sistema + Cross | Media | Medio | Medio | **P2** |
| UXD-015 | Sem auditoria de contraste (5 temas) | Frontend/UX | Media | Medio | Medio (4h) | **P2** |
| UXD-016 | LoadingProgress 450+ linhas | Frontend/UX | Media | Baixo | Grande (6h) | **P2** |
| XD-SEC-01 | Headers de seguranca ausentes | Cross-cutting | Media | Medio | Baixo | **P2** |
| XD-SEC-03 | dangerouslySetInnerHTML + sem CSP | Cross-cutting | Media | Medio | Baixo | **P2** |
| UXD-005 | SavedSearchesDropdown sem ARIA listbox | Frontend/UX | Media | Baixo | Medio (3h) | **P3** |
| UXD-006 | SaveSearchDialog sem `<dialog>` nativo | Frontend/UX | Media | Baixo | Medio (2h) | **P3** |
| UXD-007 | Sem elemento `<form>` | Frontend/UX | Media | Medio | Pequeno (2h) | **P3** |
| UXD-011 | Script FOUC duplica logica do ThemeProvider | Frontend/UX | Media | Baixo | Medio (3h) | **P3** |
| UXD-012 | Sem indicador offline/rede | Frontend/UX | Media | Medio | Medio (4h) | **P3** |
| UXD-002 | Sem loading state para fetch de setores | Frontend/UX | Media | Baixo | Pequeno (1h) | **P3** |
| TD-M05 | Estado global mutavel para DI | Sistema | Media | Medio | Medio | **P3** |
| TD-M06 | Sem versionamento de API | Sistema | Media | Medio | Medio | **P3** |
| XD-TEST-01 | Sem testes integracao frontend-backend | Cross-cutting | Media | Medio | Medio | **P3** |
| XD-TEST-02 | Sem smoke tests pos-deploy | Cross-cutting | Media | Medio | Baixo | **P3** |
| TD-M03 | Modelo LLM hardcoded | Sistema | Media | Baixo | Baixo | **P4** |
| TD-M04 | Sem timeout para chamadas LLM | Sistema | Media | Medio | Baixo | **P4** |
| TD-M07 | Sem CSP header | Sistema | Media | Baixo | Baixo | **P4** |
| TD-M08 | Sem HSTS header | Sistema | Media | Baixo | Baixo | **P4** |
| TD-M09 | MD5 para chaves de dedup | Sistema | Media | Baixo | Baixo | **P4** |
| TD-M10 | dangerouslySetInnerHTML para tema | Sistema | Media | Baixo | Baixo | **P4** |
| TD-M11 | Versao hardcoded em multiplos locais | Sistema | Media | Baixo | Baixo | **P4** |
| TD-H05 | CORS allow_headers=* | Sistema | Alta | Baixo | Baixo | **P4** |
| UXD-003 | Sem pagina 404 | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-004 | Sem atalho teclado para busca | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-008 | Mixpanel importado incondicionalmente | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-009 | Sem confirmacao page unload durante busca | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-010 | ThemeProvider imperativo (30+ props CSS) | Frontend/UX | Baixa | Baixo | Grande (8h) | **P4** |
| UXD-013 | Footer sem conteudo significativo | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-014 | SourceBadges sem acentos | Frontend/UX | Baixa | Trivial | Trivial (15min) | **P4** |
| UXD-017 | Setores fallback hardcoded | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-018 | Cores hardcoded em SearchSummary | Frontend/UX | Baixa | Baixo | Pequeno (1h) | **P4** |
| UXD-019 | carouselData com cores hardcoded | Frontend/UX | Baixa | Baixo | Medio (2h) | **P4** |
| UXD-020 | Sem noValidate no form | Frontend/UX | Baixa | Trivial | Trivial (5min) | **P4** |
| XD-API-03 | Codigos de erro nao estruturados | Cross-cutting | Baixa | Baixo | Baixo | **P4** |
| XD-PERF-03 | Polling intervalo fixo (sem backoff) | Cross-cutting | Baixa | Baixo | Baixo | **P4** |
| XD-TEST-03 | Sem testes regressao visual | Cross-cutting | Baixa | Baixo | Medio | **P4** |
| TD-L01 | is_healthy() usa httpx sincrono | Sistema | Baixa | Baixo | Baixo | **P5** |
| TD-L02 | Sem codigos de erro estruturados | Sistema | Baixa | Baixo | Baixo | **P5** |
| TD-L03 | Buscas salvas apenas em localStorage | Sistema | Baixa | Baixo | Baixo | **P5** |
| TD-L04 | test_placeholder.py existe | Sistema | Baixa | Trivial | Trivial | **P5** |
| TD-L05 | Conjuntos grandes de keywords/exclusoes | Sistema | Baixa | Baixo | Baixo | **P5** |
| TD-L06 | filter_batch no ThreadPoolExecutor padrao | Sistema | Baixa | Baixo | Baixo | **P5** |

**Legenda de Prioridade:**
- **P0:** Resolver antes de qualquer feature nova (bloqueador)
- **P1:** Resolver na proxima sprint / ciclo
- **P2:** Planejar para o proximo milestone
- **P3:** Backlog priorizado
- **P4:** Backlog geral
- **P5:** Nice-to-have / oportunistico

---

### 6. Estatisticas Resumidas

| Metrica | Valor |
|---------|-------|
| **Total de debitos** | 52 |
| **Criticos** | 4 (TD-C01, TD-C02, TD-C03, XD-SEC-02) |
| **Altos** | 8 (TD-H01..H06, UXD-001, XD-PERF-01) |
| **Medios** | 24 |
| **Baixos** | 16 |
| **Debitos de Sistema** | 20 |
| **Debitos de Frontend/UX** | 20 |
| **Debitos Cross-cutting** | 12 |
| **Debitos de Database** | 0 (stateless) |

#### Estimativa de Esforco

| Area | Esforco Estimado |
|------|-----------------|
| Sistema (Backend) | 80-120 horas |
| Frontend/UX | 40-55 horas |
| Cross-cutting | 30-50 horas |
| **Total** | **150-225 horas** |

> **Nota:** Estimativas de esforco do frontend sao mais precisas (baseadas em horas especificas do frontend-spec.md). Estimativas do backend usam classificacao qualitativa (Baixo/Medio/Alto) do system-architecture.md, convertidas aproximadamente para: Baixo = 2-4h, Medio = 4-8h, Alto = 8-16h.

---

### 7. Perguntas para Especialistas

#### Para @ux-design-expert:

1. **UXD-001 (termos multi-palavras):** Qual a abordagem preferida -- suporte a aspas ("camisa polo"), delimitador diferente (virgula), ou combinacao? Impacto na curva de aprendizado do usuario?
2. **UXD-015 (contraste dos temas):** Existe uma ferramenta/processo preferido para auditoria dos 5 temas? Temas Sepia e Paperwhite devem ser mantidos ou podem ser removidos para reduzir superficie de teste?
3. **UXD-016 (LoadingProgress):** Qual decomposicao e recomendada? ProgressBar + StageList + UfGrid + Carousel como sub-componentes?
4. **Design System:** Prioridade entre: (a) extrair componentes `<TextInput>` e `<Button>`, (b) setup Storybook, (c) documentacao de design system? O que agrega mais valor primeiro?
5. **UXD-005/UXD-006:** Migracao para `<dialog>` nativo e prioritaria dado que focus traps manuais ja estao funcionando?
6. **Acessibilidade geral:** A nota B+ e adequada para o estagio POC, ou existem bloqueadores de acessibilidade que deveriam ser P0?

#### Para @qa:

1. **Cobertura de testes:** O target de 75% de cobertura de statements e adequado para o proximo milestone? Ou deveriam focar em areas especificas (hooks, API routes)?
2. **Testes de contrato (XD-API-02):** Qual abordagem e recomendada -- Pact, schema validation compartilhado, ou outra?
3. **E2E sem backend live (XD-TEST-01):** Mock server (MSW, json-server) ou Docker Compose para CI? Qual tradeoff e aceitavel?
4. **Testes de regressao visual (XD-TEST-03):** Vale o investimento para um POC com 5 temas, ou e prematuro?
5. **Smoke tests pos-deploy (XD-TEST-02):** Escopo minimo recomendado -- health check, busca simples, download?
6. **Quality gates:** Existem metricas de qualidade (alem de cobertura) que deveriam ser enforced no CI?
7. **Componentes sem teste:** ThemeProvider, RegionSelector, AnalyticsProvider, carouselData -- qual e a prioridade de cobertura?

---

### 8. Dependencias entre Debitos

```
TD-C02 (sem auth) ──────────────> TD-H04 (sem database)
  "Auth requer persistencia           "Database e pre-requisito
   de usuarios"                        para muitas features"

TD-C01 (Excel em memoria) ─────> TD-M02 (sem paginacao)
  "Buffer grande porque                "Resultados grandes
   retorna tudo de uma vez"             geram Excel grandes"

TD-H06 (Vercel timeout) ───────> TD-C01 (Excel em memoria)
  "Timeout causado por                 "Streaming resolveria
   buffer completo"                     ambos os problemas"

TD-M06 (sem API versioning) ───> XD-API-02 (sem contract tests)
  "Versionamento sem contrato          "Contrato sem versao
   e incompleto"                        e fragil"

XD-SEC-01 (headers) ───────────> TD-M07 (sem CSP) + TD-M08 (sem HSTS)
  "Resolver headers de seguranca       "CSP e HSTS sao subset
   resolve ambos"                       do mesmo trabalho"

UXD-010 (ThemeProvider imperativo) ──> UXD-011 (FOUC script duplica logica)
  "Refatorar ThemeProvider              "Resolveria a duplicacao
   para data-attributes"                automaticamente"

UXD-015 (auditoria contraste) ──> UXD-018 + UXD-019 (cores hardcoded)
  "Auditar primeiro, depois            "Cores hardcoded so podem
   migrar para tokens"                  ser corrigidas apos auditoria"

TD-H02 (jobs nao duraveis) ────> TD-H01 (in-memory store)
  "Fila de tarefas duravel             "Eliminaria necessidade
   (Celery/RQ)                          de dual-write store"
```

**Cadeia critica:** TD-C01 -> TD-M02 -> TD-H06 (resolver paginacao + streaming resolve 3 debitos)

**Cadeia de seguranca:** TD-C02 -> TD-H04 (auth requer persistencia, ambos P0-P1)

---

### 9. Quick Wins Identificados

Debitos com baixo esforco e alto impacto relativo -- candidatos para acao imediata.

| ID | Debito | Esforco | Impacto | Justificativa |
|----|--------|---------|---------|---------------|
| UXD-014 | SourceBadges sem acentos | Trivial (15min) | UX | Correcao de 1 linha, melhora percepcao de qualidade |
| UXD-020 | Sem noValidate no form | Trivial (5min) | UX | 1 atributo, previne conflito de validacao |
| TD-L04 | test_placeholder.py | Trivial (5min) | Higiene | Remover arquivo vazio |
| TD-H05 | CORS allow_headers=* | Baixo (1h) | Seguranca | Listar headers explicitamente, reducao de superficie |
| TD-M07 + TD-M08 | Headers CSP + HSTS | Baixo (2h) | Seguranca | Adicionar headers em vercel.json, protecao imediata |
| TD-M11 | Versao hardcoded | Baixo (1h) | Manutencao | Extrair para constante unica |
| UXD-002 | Loading state para setores | Pequeno (1h) | UX | Spinner simples no dropdown |
| UXD-003 | Pagina 404 | Pequeno (1h) | UX | Arquivo `not-found.tsx` simples |
| UXD-008 | Mixpanel import condicional | Pequeno (1h) | Performance | Dynamic import, -40KB quando desabilitado |
| UXD-009 | Confirmacao page unload | Pequeno (1h) | UX | `beforeunload` event handler |
| UXD-013 | Footer com conteudo | Pequeno (1h) | UX | Links basicos de footer |
| UXD-017 | Remover setores fallback hardcoded | Pequeno (1h) | Manutencao | Simplificar logica |
| UXD-018 | Migrar cores SearchSummary para tokens | Pequeno (1h) | UX | Corrigir quebra em temas Sepia/Paperwhite |

**Total estimado para todos os Quick Wins: ~12-14 horas**

Estes 13 itens representam ~25% dos debitos totais com ~7% do esforco total estimado.

---

*Documento gerado: 2026-03-09*
*Fonte: Brownfield Discovery Fase 1 (system-architecture.md v3.0) + Fase 3 (frontend-spec.md v3.0)*
*Fase 2 (Database): Pulada - arquitetura stateless*
*Proximo passo: Revisao por @ux-design-expert e @qa*
