# Technical Debt Assessment - FINAL

## Descomplicita POC v0.2
## Data: 2026-03-09
## Status: VALIDADO (QA Approved with Conditions - All Addressed)

> **Versao final** consolidando as fases 1, 3, 4, 6 e 7 do Brownfield Discovery.
> Fase 2 (Database) e Fase 5 (DB Specialist Review) foram puladas -- arquitetura stateless sem banco de dados.
> Este documento e a fonte autoritativa de verdade para planejamento de resolucao de debito tecnico.

---

## Executive Summary

| Metrica | DRAFT (Fase 4) | FINAL (Fase 7) | Delta |
|---------|----------------|-----------------|-------|
| **Total de debitos** | 52 | 55 | +3 (UXD-021, UXD-022, UXD-023 adicionados por @ux-design-expert) |
| **Criticos** | 4 | 3 | -1 (TD-C03 rebaixado para Alto por @qa) |
| **Altos** | 8 | 10 | +2 (TD-C03 promovido de Critico; TD-M04, UXD-015 promovidos de Medio) |
| **Medios** | 24 | 25 | +1 (ajustes de severidade: UXD-018 e UXD-019 promovidos, UXD-006 rebaixada, TD-M09 rebaixado, XD-PERF-03 promovido) |
| **Baixos** | 16 | 17 | +1 (ajustes liquidos) |
| **Esforco total estimado** | 150-225 horas | 155-232 horas | +5-7h (3 novos debitos UX) |

### Mudancas em relacao ao DRAFT

1. **Severidades ajustadas (9 itens):**
   - UXD-006: Media -> Baixa (focus trap funcional, implementacao atende ARIA spec)
   - UXD-015: Media -> Alta (obrigacao legal LBI 13.146/2015, WCAG AA)
   - UXD-018: Baixa -> Media (quebra visual em temas Sepia/Paperwhite)
   - UXD-019: Baixa -> Media (mesma classe de problema que UXD-018)
   - TD-H05: Alta -> Media (inconsistencia corrigida; allow_origins e whitelisted, risco real e moderado)
   - TD-M04: Media -> Alta (cascading failure path com TD-L06 e TD-H03)
   - TD-M09: Media -> Baixa (risco teorico em dados nao-criticos)
   - XD-PERF-03: Baixa -> Media (60-300 requests desnecessarios por busca)
   - TD-C03: Critica -> Alta (codigo morto inerte, POC funcional com 2 fontes)

2. **Novos debitos (3 itens):**
   - UXD-021: Cores amber hardcoded em SourceBadges e carouselData
   - UXD-022: Sem `aria-required` em campos obrigatorios
   - UXD-023: Timeout de confirmacao de delete (3s) inacessivel para screen readers

3. **Dependencias adicionadas (3 arestas):**
   - TD-M10 -> TD-M07 (CSP requer resolucao de inline script)
   - TD-M04 -> TD-L06 -> TD-H03 (cadeia de cascading failure do thread pool)
   - XD-API-02 -> TD-L02/XD-API-03 (contract tests requerem error codes estruturados)

4. **QA Conditions -- todas enderecadas:**
   - TD-H05 severidade corrigida para Media (consistente entre tabela e matriz)
   - TD-M10 -> TD-M07 dependencia adicionada ao grafo
   - Backend test coverage: pendente medicao (documentado como acao imediata requerida)

---

## Methodology

| Fase | Descricao | Responsavel | Status |
|------|-----------|-------------|--------|
| 1 | Analise de arquitetura do sistema | @architect (Atlas) | Completa |
| 2 | Analise de banco de dados | - | **PULADA** (stateless) |
| 3 | Analise de frontend/UX | @ux-design-expert (Vera) | Completa |
| 4 | Consolidacao inicial (DRAFT) | @architect (Atlas) | Completa |
| 5 | Revisao de especialista DB | - | **PULADA** (stateless) |
| 6 | Revisao de especialista UX | @ux-design-expert (Vera) | Completa |
| 7 | Revisao QA | @qa (Quinn) | Aprovado com condicoes |

---

## Inventario Completo de Debitos

### 1. Sistema (validado por @architect, severidades ajustadas por @qa)

#### 1.1 Severidade Critica

| ID | Debito | Impacto | Esforco | Prioridade | Notas |
|----|--------|---------|---------|------------|-------|
| TD-C01 | **Excel bytes armazenados no resultado do job (memoria + Redis).** Jobs completados armazenam bytes Excel brutos no dict Python e serializados no Redis como JSON. Um job com 500 licitacoes pode produzir dados multi-MB duplicados entre duas stores. | Esgotamento de memoria sob carga concorrente, pressao de memoria no Redis | Medio (4-8h) | **P1** | Cadeia critica: TD-C01 -> TD-M02 -> TD-H06 -> XD-PERF-01 |
| TD-C02 | **Sem autenticacao de usuario.** Chave API unica compartilhada para todos os clientes. Sem identidade de usuario, sem modelo de autorizacao, sem trilha de auditoria. Se API_KEY nao estiver definida, endpoints ficam abertos. | Exposicao de seguranca, sem accountability | Alto (8-16h) | **P0** | Bloqueador. JWT stateless possivel como interim sem TD-H04. |

#### 1.2 Severidade Alta

| ID | Debito | Impacto | Esforco | Prioridade | Notas |
|----|--------|---------|---------|------------|-------|
| TD-C03 | **3 de 5 fontes de dados desabilitadas.** ComprasGov (API deprecada), Querido Diario (retorna HTML), TCE-RJ (404). Codigo morto na codebase. | Cobertura de dados reduzida, carga de manutencao | Alto (8-16h) | **P1** | Rebaixado de Critico por @qa: codigo morto inerte, sistema funcional com 2 fontes |
| TD-H01 | **In-memory job store como primario.** RedisJobStore estende JobStore in-memory em dual-write. Na reinicializacao, estado in-memory e perdido. | Perda de dados de jobs em restart | Medio (4-8h) | **P1** | Depende de TD-H02 |
| TD-H02 | **asyncio.create_task para jobs em background.** Jobs rodam como tasks asyncio nao rastreadas. Sem fila de tarefas duravel. Em shutdown/deploy, jobs em execucao sao perdidos. | Perda de jobs em deploy/restart | Alto (8-16h) | **P1** | Resolver com fila duravel elimina TD-H01 |
| TD-H03 | **API OpenAI chamada sincronamente no thread pool.** `gerar_resumo()` usa cliente sincrono via `run_in_executor(None, ...)`, bloqueando thread do pool padrao. | Esgotamento do thread pool sob buscas concorrentes | Medio (4-8h) | **P2** | Cadeia: TD-M04 -> TD-L06 -> TD-H03 |
| TD-H04 | **Sem banco de dados.** Todo estado e efemero. Sem dados historicos, sem analytics persistente, sem preferencias server-side. | Nao e possivel construir features que requerem persistencia | Alto (8-16h) | **P2** | Dependencia condicional de TD-C02 (JWT pode desbloquear) |
| TD-H06 | **Funcoes serverless Vercel tem duracao maxima de 10s.** Rota de download faz buffer do Excel inteiro antes de retornar. Arquivos grandes podem exceder timeout ou memoria. | Falhas de download para arquivos grandes | Medio (4-8h) | **P2** | Parte da cadeia critica de streaming |
| TD-M04 | **Sem timeout para chamadas LLM.** Cliente OpenAI usa timeout padrao. Respostas longas bloqueiam thread pool indefinidamente. Com TD-L06 (executor compartilhado), cria cascading failure. | Estrangulamento de threads, possivel hang total | Baixo (2-4h) | **P2** | Promovido de Media por @qa: cascading failure path |

#### 1.3 Severidade Media

| ID | Debito | Impacto | Esforco | Prioridade | Notas |
|----|--------|---------|---------|------------|-------|
| TD-H05 | **CORS allow_headers=\* excessivamente permissivo.** Aceita qualquer header. Deveria limitar a Content-Type, X-API-Key, X-Request-ID. | Risco menor de seguranca, pratica nao-padrao | Baixo (2-4h) | **P3** | Corrigido: severidade consistente agora (era Alta na tabela, Baixo na matriz do DRAFT). allow_origins e whitelisted corretamente. |
| TD-M01 | **Filtro de deadline desabilitado.** Campo `dataAberturaProposta` mal interpretado. Filtro comentado com TODO. | Usuarios veem licitacoes historicas irrelevantes | Medio (4-8h) | **P2** | |
| TD-M02 | **Sem paginacao nos resultados.** Todos os resultados retornados em resposta unica. | Degradacao de performance com muitos resultados | Medio (4-8h) | **P2** | Cadeia critica com TD-C01 e TD-H06 |
| TD-M03 | **Modelo LLM hardcoded.** `gpt-4.1-nano` hardcoded em `llm.py`. Docker-compose expoe `LLM_MODEL` mas codigo ignora. | Nao e possivel trocar modelos sem alterar codigo | Baixo (2-4h) | **P4** | |
| TD-M05 | **Estado global mutavel para DI.** `dependencies.py` usa globais de modulo sem framework DI. | Complexidade de teste, acoplamento oculto | Medio (4-8h) | **P3** | |
| TD-M06 | **Sem versionamento de API.** Endpoints nao versionados. Breaking changes afetam todos os clientes. | Evolucao de API dificultada | Medio (4-8h) | **P3** | |
| TD-M07 | **Sem header Content-Security-Policy.** CSP ausente na config do Vercel. | Lacuna na mitigacao de XSS | Baixo (2-4h) | **P3** | **BLOQUEADO por TD-M10** (inline script quebraria com CSP) |
| TD-M08 | **Sem header Strict-Transport-Security.** HSTS ausente na config do Vercel. | Risco de downgrade de protocolo | Baixo (2-4h) | **P3** | Resolver com XD-SEC-01 |
| TD-M10 | **dangerouslySetInnerHTML para tema no frontend.** Script inline para prevenir flash de tema. Contorna protecao XSS do React. | Vetor potencial de XSS se modificado; bloqueia CSP | Baixo (2-4h) | **P3** | **Deve ser resolvido antes de TD-M07** |
| TD-M11 | **Versao hardcoded em multiplos locais.** "0.3.0" em `main.py` sem single source of truth. | Risco de drift de versao | Baixo (2-4h) | **P4** | |

#### 1.4 Severidade Baixa

| ID | Debito | Impacto | Esforco | Prioridade | Notas |
|----|--------|---------|---------|------------|-------|
| TD-M09 | **MD5 usado para chaves de dedup.** Hash fraco por padroes modernos, mas risco de colisao desprezivel para este caso. | Risco teorico de colisao | Baixo (2-4h) | **P5** | Rebaixado de Media por @qa: dados nao-criticos |
| TD-L01 | **is_healthy() usa httpx sincrono.** Chamadas HTTP sincronas em sources. Bloqueante em contexto async. | Chamada bloqueante se usado em async | Baixo (2-4h) | **P5** | Atualmente usado apenas em testes |
| TD-L02 | **Sem codigos de erro estruturados.** Respostas usam mensagens em texto livre. | Tratamento de erros no cliente e fragil | Baixo (2-4h) | **P5** | Bloqueia XD-API-02 (contract tests) |
| TD-L03 | **Buscas salvas apenas em localStorage.** Sem persistencia server-side. | Perda de dados, sem cross-device | Baixo (2-4h) | **P5** | |
| TD-L04 | **test_placeholder.py existe.** Arquivo de teste vazio. | Higiene de codigo | Trivial (5min) | **P4** | Quick win |
| TD-L05 | **Conjuntos grandes de keywords/exclusoes.** ~130 keywords inclusao, ~100 exclusao via regex. | Preocupacao de performance em escala | Baixo (2-4h) | **P5** | Mitigado por ordenacao fail-fast |
| TD-L06 | **filter_batch roda no ThreadPoolExecutor padrao.** Compartilha executor com chamadas LLM (TD-H03). | Contencao de recursos sob carga | Baixo (2-4h) | **P5** | Parte da cadeia TD-M04 -> TD-L06 -> TD-H03 |

---

### 2. Frontend/UX (validado por @ux-design-expert)

| ID | Debito | Severidade | Horas | Prioridade | Impacto UX | Notas |
|----|--------|------------|-------|------------|------------|-------|
| UXD-001 | **Termos multi-palavras impossiveis.** Espaco dispara criacao de token. "camisa polo" se torna dois tokens separados. | **Alta** | 3h | **P1** | Critico | Bloqueador funcional. Solucao: aspas + virgula como delimitadores. |
| UXD-015 | **Sem auditoria de contraste de cores para os 5 temas.** Sepia e Paperwhite nao verificados contra WCAG AA. | **Alta** | 4h | **P2** | Alto | Promovido de Media por @ux-design-expert. Obrigacao legal (LBI 13.146/2015). |
| UXD-022 | **Sem `aria-required` em campos obrigatorios.** Screen readers nao anunciam quais campos sao mandatorios. | **Media** | 0.5h | **P2** | Medio | **NOVO.** Quick win de acessibilidade. |
| UXD-023 | **Timeout de confirmacao de delete (3s) inacessivel.** Usuarios de screen reader ou com deficiencias motoras podem nao confirmar em 3s. Viola WCAG 2.2.1. | **Media** | 1h | **P2** | Medio | **NOVO.** Aumentar para 10-20s ou remover timeout. |
| UXD-002 | **Sem loading state para fetch de setores.** Dropdown pode mostrar dados desatualizados momentaneamente. | Media | 1h | P3 | Medio | Impacto menor que previsto devido a FALLBACK_SETORES. |
| UXD-005 | **SavedSearchesDropdown sem ARIA listbox.** Usa `div` sem `role="listbox"` e `role="option"`. | Media | 3h | P3 | Medio | Necessita semantica de listbox, nao migracao para `<dialog>`. |
| UXD-007 | **Sem elemento `<form>` envolvendo formulario.** Impede autofill e submissao nativa. | Media | 2h | P3 | Medio | Afeta mobile UX (teclado nao mostra "Go"/"Enviar"). |
| UXD-011 | **Script FOUC duplica logica do ThemeProvider.** Flash parcial possivel em Sepia/Paperwhite. | Media | 3h | P3 | Medio | Curto prazo: expandir script inline para cobrir surface/border tokens. |
| UXD-012 | **Sem indicador offline/rede.** Erros de rede mostram mensagem generica. | Media | 4h | P3 | Medio | |
| UXD-016 | **LoadingProgress 450+ linhas.** Componente complexo deveria ser decomposto. | Media | 6h | P3 | Baixo | Decomposicao: ProgressBar + StageList + UfGrid + Carousel + Skeleton. |
| UXD-018 | **Cores Tailwind hardcoded em SearchSummary.** `bg-blue-100`, `bg-purple-100` ignoram temas Sepia/Paperwhite. | **Media** | 1h | **P2** | Medio | Promovido de Baixa por @ux-design-expert. Quick win. |
| UXD-019 | **carouselData usa cores Tailwind hardcoded.** Mesma classe de problema que UXD-018. | **Media** | 2h | P3 | Medio | Promovido de Baixa. Impacto menor (carrossel e transiente). |
| UXD-003 | **Sem pagina 404.** Falta `not-found.tsx`. | Baixa | 1h | P4 | Baixo | App tem rota unica. |
| UXD-004 | **Sem atalho de teclado para busca.** Enter em input cria token, nao submete. | Baixa | 1h | P4 | Baixo | |
| UXD-006 | **SaveSearchDialog sem `<dialog>` nativo.** Usa `div` com `role="dialog"`, `aria-modal="true"`, focus trap funcional. | **Baixa** | 2h | P4 | Baixo | Rebaixado de Media por @ux-design-expert. Implementacao atende ARIA spec. |
| UXD-008 | **Mixpanel importado incondicionalmente.** ~40KB de bundle desnecessario. | Baixa | 1h | P4 | Baixo | Dynamic import resolveria. |
| UXD-009 | **Sem confirmacao page unload durante busca.** Listener `beforeunload` existe mas apenas para analytics. | Baixa | 0.5h | P4 | Baixo | Adicionar `e.preventDefault(); e.returnValue = ""`. |
| UXD-010 | **ThemeProvider imperativo (30+ props CSS).** Funcional mas dificil de manter. | Baixa | 8h | P4 | Baixo | DX concern, nao UX. |
| UXD-013 | **Footer sem conteudo significativo.** Apenas branding, sem links uteis. | Baixa | 1h | P4 | Baixo | |
| UXD-014 | **SourceBadges sem acentos portugues.** `combinacoes` sem acentuacao. | Baixa | 0.25h | P4 | Baixo | Quick win trivial. |
| UXD-017 | **Setores fallback hardcoded.** 7 setores em `useSearchForm.ts` podem ficar desatualizados. | Baixa | 1h | P4 | Baixo | |
| UXD-020 | **Sem `noValidate` no form.** Validacao nativa pode conflitar com customizada. | Baixa | 0.1h | P4 | Trivial | Depende de UXD-007 (sem `<form>` atualmente). |
| UXD-021 | **Cores amber hardcoded em SourceBadges e carouselData.** `text-amber-600 dark:text-amber-400` nao responsivo a temas. | **Baixa** | 0.5h | P4 | Baixo | **NOVO.** Quick win junto com UXD-018. |

---

### 3. Cross-cutting (validado por @qa)

#### 3.1 Seguranca Cross-layer

| ID | Debito | Areas | Severidade | Esforco | Prioridade | Notas |
|----|--------|-------|------------|---------|------------|-------|
| XD-SEC-02 | **Autenticacao fragil end-to-end.** API key unica compartilhada combinada com bypass em dev. | Backend + Frontend | **Critica** | Alto | **P0** | Manifestacao cross-cutting de TD-C02. |
| XD-SEC-01 | **Headers de seguranca ausentes.** Sem CSP, HSTS, Referrer-Policy, Permissions-Policy. | Backend + Frontend | Media | Baixo | **P2** | CSP bloqueado por TD-M10. |
| XD-SEC-03 | **dangerouslySetInnerHTML + sem CSP.** Script inline para tema combinado com ausencia de CSP. | Frontend | Media | Baixo | **P3** | Alinhar com UXD-010/011 ao implementar. |

#### 3.2 Contratos de API

| ID | Debito | Areas | Severidade | Esforco | Prioridade | Notas |
|----|--------|-------|------------|---------|------------|-------|
| XD-API-01 | **Sem versionamento de API.** Breaking changes quebram frontend imediatamente. | Backend + Frontend | Media | Medio | **P2** | BFF mitiga parcialmente. |
| XD-API-02 | **Sem testes de contrato.** Tipos TypeScript e schemas Pydantic nao validados entre si. | Backend + Frontend | Media | Medio | **P2** | Bloqueado parcialmente por TD-L02 (error codes). Abordagem: JSON Schema compartilhado. |
| XD-API-03 | **Codigos de erro nao estruturados.** Frontend parseia mensagens texto livre. | Backend + Frontend | Baixa | Baixo | **P4** | |

#### 3.3 Performance End-to-End

| ID | Debito | Areas | Severidade | Esforco | Prioridade | Notas |
|----|--------|-------|------------|---------|------------|-------|
| XD-PERF-01 | **Download bufferizado em cadeia.** 3 copias do arquivo em memoria simultaneamente. | Backend + Frontend | **Alta** | Medio | **P1** | Parte da cadeia critica de streaming. |
| XD-PERF-02 | **Sem paginacao end-to-end.** Backend retorna tudo, frontend renderiza tudo. | Backend + Frontend | Media | Medio | **P2** | |
| XD-PERF-03 | **Polling de intervalo fixo (2s).** 60-300 requests desnecessarios por busca. Sem backoff exponencial. | Frontend + Backend | **Media** | Baixo | **P3** | Promovido de Baixa por @qa. Easy win operacional. |

#### 3.4 Cobertura de Testes Cross-cutting

| ID | Debito | Areas | Severidade | Esforco | Prioridade | Notas |
|----|--------|-------|------------|---------|------------|-------|
| XD-TEST-01 | **Sem testes de integracao frontend-backend.** E2E requerem backend live. | Backend + Frontend | Media | Medio | **P3** | Abordagem recomendada: MSW (Mock Service Worker). |
| XD-TEST-02 | **Sem smoke tests pos-deploy.** Health endpoint existe sem verificacao automatizada. | Infra + Backend + Frontend | Media | Baixo | **P3** | Escopo minimo: /health, /setores, /buscar. |
| XD-TEST-03 | **Sem testes de regressao visual.** 5 temas e responsividade nao verificados. | Frontend | Baixa | Medio | **P4** | Prematuro para POC per @qa. Revisitar apos design system. |

---

## Matriz de Priorizacao Final

| Rank | ID | Debito | Area | Severidade | Horas | Prioridade | Dependencias |
|------|-----|--------|------|------------|-------|------------|--------------|
| 1 | TD-C02 | Sem autenticacao de usuario | Sistema | Critica | 8-16h | **P0** | -> TD-H04 (condicional; JWT como alternativa) |
| 2 | XD-SEC-02 | Autenticacao fragil end-to-end | Cross-cutting | Critica | Alto | **P0** | Manifestacao de TD-C02 |
| 3 | TD-C01 | Excel bytes duplicados memoria + Redis | Sistema | Critica | 4-8h | **P1** | -> TD-M02, TD-H06, XD-PERF-01 |
| 4 | TD-H02 | Jobs asyncio nao duraveis | Sistema | Alta | 8-16h | **P1** | -> TD-H01 |
| 5 | UXD-001 | Termos multi-palavras impossiveis | Frontend/UX | Alta | 3h | **P1** | Nenhuma |
| 6 | XD-PERF-01 | Download bufferizado em cadeia (3 copias) | Cross-cutting | Alta | 4-8h | **P1** | <- TD-C01 |
| 7 | TD-C03 | 3 de 5 fontes desabilitadas (codigo morto) | Sistema | Alta | 8-16h | **P1** | Nenhuma |
| 8 | TD-H01 | In-memory job store como primario | Sistema | Alta | 4-8h | **P1** | <- TD-H02 |
| 9 | TD-H03 | OpenAI API sincrona no thread pool | Sistema | Alta | 4-8h | **P2** | <- TD-M04, TD-L06 |
| 10 | TD-M04 | Sem timeout para chamadas LLM | Sistema | Alta | 2-4h | **P2** | -> TD-L06 -> TD-H03 |
| 11 | TD-H04 | Sem banco de dados | Sistema | Alta | 8-16h | **P2** | <- TD-C02 (condicional) |
| 12 | TD-H06 | Timeout Vercel 10s em downloads grandes | Sistema | Alta | 4-8h | **P2** | <- TD-C01 |
| 13 | UXD-015 | Sem auditoria de contraste (5 temas) | Frontend/UX | Alta | 4h | **P2** | -> UXD-018, UXD-019, UXD-021 |
| 14 | UXD-018 | Cores hardcoded em SearchSummary | Frontend/UX | Media | 1h | **P2** | <- UXD-015 |
| 15 | UXD-022 | Sem aria-required em campos obrigatorios | Frontend/UX | Media | 0.5h | **P2** | Nenhuma |
| 16 | UXD-023 | Timeout de confirmacao de delete (3s) | Frontend/UX | Media | 1h | **P2** | Nenhuma |
| 17 | XD-SEC-01 | Headers de seguranca ausentes | Cross-cutting | Media | 2-4h | **P2** | -> TD-M07, TD-M08. CSP bloqueado por TD-M10 |
| 18 | XD-API-01 | Sem versionamento de API | Cross-cutting | Media | 4-8h | **P2** | -> XD-API-02 |
| 19 | XD-API-02 | Sem testes de contrato | Cross-cutting | Media | 4-8h | **P2** | <- XD-API-01, TD-L02 |
| 20 | TD-M01 | Filtro de deadline desabilitado | Sistema | Media | 4-8h | **P2** | Nenhuma |
| 21 | TD-M02 | Sem paginacao nos resultados | Sistema | Media | 4-8h | **P2** | <- TD-C01 |
| 22 | XD-PERF-02 | Sem paginacao end-to-end | Cross-cutting | Media | 4-8h | **P2** | <- TD-M02 |
| 23 | TD-H05 | CORS allow_headers=* | Sistema | Media | 2-4h | **P3** | Nenhuma |
| 24 | TD-M05 | Estado global mutavel para DI | Sistema | Media | 4-8h | **P3** | Nenhuma |
| 25 | TD-M06 | Sem versionamento de API | Sistema | Media | 4-8h | **P3** | -> XD-API-01 |
| 26 | TD-M07 | Sem CSP header | Sistema | Media | 2-4h | **P3** | **BLOQUEADO por TD-M10** |
| 27 | TD-M08 | Sem HSTS header | Sistema | Media | 2-4h | **P3** | Resolver com XD-SEC-01 |
| 28 | TD-M10 | dangerouslySetInnerHTML para tema | Sistema | Media | 2-4h | **P3** | **BLOQUEIA TD-M07** |
| 29 | UXD-005 | SavedSearchesDropdown sem ARIA listbox | Frontend/UX | Media | 3h | **P3** | Nenhuma |
| 30 | UXD-007 | Sem elemento `<form>` | Frontend/UX | Media | 2h | **P3** | -> UXD-020 |
| 31 | UXD-011 | Script FOUC duplica logica ThemeProvider | Frontend/UX | Media | 3h | **P3** | <- UXD-010 |
| 32 | UXD-012 | Sem indicador offline/rede | Frontend/UX | Media | 4h | **P3** | Nenhuma |
| 33 | UXD-016 | LoadingProgress 450+ linhas | Frontend/UX | Media | 6h | **P3** | Nenhuma |
| 34 | UXD-019 | carouselData com cores hardcoded | Frontend/UX | Media | 2h | **P3** | <- UXD-015 |
| 35 | UXD-002 | Sem loading state para fetch setores | Frontend/UX | Media | 1h | **P3** | Nenhuma |
| 36 | XD-SEC-03 | dangerouslySetInnerHTML + sem CSP | Cross-cutting | Media | 2-4h | **P3** | Alinhar com UXD-010/011 |
| 37 | XD-PERF-03 | Polling intervalo fixo (sem backoff) | Cross-cutting | Media | 2-4h | **P3** | Nenhuma |
| 38 | XD-TEST-01 | Sem testes integracao frontend-backend | Cross-cutting | Media | 4-8h | **P3** | Abordagem: MSW |
| 39 | XD-TEST-02 | Sem smoke tests pos-deploy | Cross-cutting | Media | 2-4h | **P3** | Nenhuma |
| 40 | TD-M03 | Modelo LLM hardcoded | Sistema | Media | 2-4h | **P4** | Nenhuma |
| 41 | TD-M11 | Versao hardcoded em multiplos locais | Sistema | Media | 2-4h | **P4** | Nenhuma |
| 42 | UXD-003 | Sem pagina 404 | Frontend/UX | Baixa | 1h | **P4** | Nenhuma |
| 43 | UXD-004 | Sem atalho teclado para busca | Frontend/UX | Baixa | 1h | **P4** | Nenhuma |
| 44 | UXD-006 | SaveSearchDialog sem `<dialog>` nativo | Frontend/UX | Baixa | 2h | **P4** | Nenhuma |
| 45 | UXD-008 | Mixpanel importado incondicionalmente | Frontend/UX | Baixa | 1h | **P4** | Nenhuma |
| 46 | UXD-009 | Sem confirmacao page unload | Frontend/UX | Baixa | 0.5h | **P4** | Nenhuma |
| 47 | UXD-010 | ThemeProvider imperativo (30+ props) | Frontend/UX | Baixa | 8h | **P4** | -> UXD-011 |
| 48 | UXD-013 | Footer sem conteudo significativo | Frontend/UX | Baixa | 1h | **P4** | Nenhuma |
| 49 | UXD-014 | SourceBadges sem acentos | Frontend/UX | Baixa | 0.25h | **P4** | Quick win |
| 50 | UXD-017 | Setores fallback hardcoded | Frontend/UX | Baixa | 1h | **P4** | Nenhuma |
| 51 | UXD-020 | Sem noValidate no form | Frontend/UX | Baixa | 0.1h | **P4** | <- UXD-007 |
| 52 | UXD-021 | Cores amber hardcoded | Frontend/UX | Baixa | 0.5h | **P4** | <- UXD-015 |
| 53 | XD-API-03 | Codigos de erro nao estruturados | Cross-cutting | Baixa | 2-4h | **P4** | Nenhuma |
| 54 | XD-TEST-03 | Sem testes regressao visual | Cross-cutting | Baixa | 4-8h | **P4** | Prematuro para POC |
| 55 | TD-L04 | test_placeholder.py existe | Sistema | Baixa | 5min | **P4** | Quick win |
| -- | TD-M09 | MD5 para chaves de dedup | Sistema | Baixa | 2-4h | **P5** | Nenhuma |
| -- | TD-L01 | is_healthy() usa httpx sincrono | Sistema | Baixa | 2-4h | **P5** | Nenhuma |
| -- | TD-L02 | Sem codigos de erro estruturados | Sistema | Baixa | 2-4h | **P5** | Bloqueia XD-API-02 |
| -- | TD-L03 | Buscas salvas apenas em localStorage | Sistema | Baixa | 2-4h | **P5** | Nenhuma |
| -- | TD-L05 | Conjuntos grandes keywords/exclusoes | Sistema | Baixa | 2-4h | **P5** | Nenhuma |
| -- | TD-L06 | filter_batch no ThreadPoolExecutor padrao | Sistema | Baixa | 2-4h | **P5** | Parte da cadeia TD-M04 |

---

## Grafo de Dependencias

```
CADEIA CRITICA - STREAMING/MEMORIA:
TD-C01 (Excel em memoria) -----> TD-M02 (sem paginacao) -----> XD-PERF-02 (paginacao e2e)
  |                                |
  +------> TD-H06 (Vercel 10s)    +------> XD-PERF-01 (download 3 copias)

CADEIA DE SEGURANCA - AUTH:
TD-C02 (sem auth) - - - -> TD-H04 (sem database)
                   condicional: JWT pode desbloquear sem DB

CADEIA DE SEGURANCA - HEADERS:
                              +---> TD-M07 (sem CSP) -----> XD-SEC-01 (headers ausentes)
TD-M10 (inline script) ------+
                              +---> XD-SEC-03 (innerHTML + sem CSP)

CADEIA DE CASCADING FAILURE - THREAD POOL:
TD-M04 (sem LLM timeout) -----> TD-L06 (executor compartilhado) -----> TD-H03 (sync OpenAI)
  "Resolver TD-H03 (async client) resolve toda a cadeia"

CADEIA DE DURABILIDADE - JOBS:
TD-H02 (asyncio tasks) -----> TD-H01 (in-memory store)
  "Fila duravel (Celery/RQ) elimina dual-write"

CADEIA DE CONTRATOS:
TD-M06 (sem versioning) <-----> XD-API-01 (sem versioning e2e)
                                     |
                                     v
TD-L02 (sem error codes) -----> XD-API-02 (sem contract tests)
  |
  +---> XD-API-03 (erros nao estruturados)

CADEIA DE TEMA/VISUAL:
UXD-010 (ThemeProvider imperativo) -----> UXD-011 (FOUC script duplication)

UXD-015 (auditoria contraste) -----> UXD-018 (cores SearchSummary)
                                |---> UXD-019 (cores carouselData)
                                +---> UXD-021 (cores amber hardcoded)

DEPENDENCIA SIMPLES:
UXD-007 (sem <form>) -----> UXD-020 (sem noValidate)
```

**Nenhuma dependencia circular detectada. O grafo e um DAG.**

---

## Plano de Resolucao

### Sprint 1: Quick Wins (1-2 dias, ~8 horas)

Itens de baixo esforco e alto impacto relativo para construir momentum.

| ID | Debito | Horas | Impacto |
|----|--------|-------|---------|
| UXD-014 | SourceBadges sem acentos | 0.25h | Percepcao de qualidade |
| UXD-020 + UXD-007 | Sem `<form>` + noValidate | 2.1h | Mobile UX, autofill |
| UXD-022 | Sem aria-required | 0.5h | Acessibilidade |
| UXD-009 | Sem confirmacao page unload | 0.5h | Prevencao de perda |
| TD-L04 | test_placeholder.py | 5min | Higiene |
| TD-M11 | Versao hardcoded | 1h | Manutencao |
| TD-H05 | CORS allow_headers=* | 1h | Seguranca |
| UXD-018 | Cores hardcoded SearchSummary | 1h | Corrigir quebra em temas |
| UXD-021 | Cores amber hardcoded | 0.5h | Consistencia visual |
| TD-M04 | Timeout para chamadas LLM | 2h | Prevencao de cascading failure |

### Sprint 2: Critical Fixes (1 semana, ~40-60 horas)

Itens de severidade critica e alta que bloqueiam evolucao do produto.

| ID | Debito | Horas | Justificativa |
|----|--------|-------|---------------|
| TD-C02 / XD-SEC-02 | Autenticacao de usuario | 8-16h | P0 bloqueador. Implementar JWT stateless como interim. |
| UXD-001 | Termos multi-palavras | 3h | Bloqueador funcional de busca. |
| TD-C01 + XD-PERF-01 | Excel streaming + download | 8-16h | Cadeia critica: resolve memoria, timeout, download. Implementar com feature flag. |
| TD-H02 + TD-H01 | Fila de tarefas duravel | 12-20h | Resolver perda de jobs em deploy. |
| TD-C03 | Remover fontes desabilitadas | 8-16h | Limpar codigo morto. Escrever testes de orquestrador primeiro. |
| UXD-015 | Auditoria de contraste | 4h | Obrigacao legal. Usar axe DevTools + @axe-core/playwright. |

### Sprint 3: Foundation (1-2 semanas, ~40-50 horas)

Itens de severidade media que fortalecem a fundacao tecnica.

| ID | Debito | Horas | Justificativa |
|----|--------|-------|---------------|
| TD-H03 | Async OpenAI client | 4-8h | Resolve cadeia de cascading failure (com TD-M04 ja resolvido). |
| TD-H06 | Streaming Vercel | 4-8h | Resolve timeout de download (cadeia critica). |
| TD-M02 + XD-PERF-02 | Paginacao e2e | 8-16h | Performance com muitos resultados. |
| TD-M10 + TD-M07 + TD-M08 | Inline script + CSP + HSTS | 4-8h | **TD-M10 primeiro**, depois headers. |
| UXD-023 | Timeout de delete acessivel | 1h | WCAG 2.2.1. |
| XD-PERF-03 | Polling backoff exponencial | 2-4h | Reducao de carga operacional. |
| XD-TEST-02 | Smoke tests pos-deploy | 2-4h | /health, /setores, /buscar. GitHub Actions. |
| TD-M01 | Filtro de deadline | 4-8h | Relevancia dos resultados. |

### Sprint 4: Polish (1-2 semanas, ~30-40 horas)

Itens de menor prioridade que melhoram qualidade geral.

| ID | Debito | Horas | Justificativa |
|----|--------|-------|---------------|
| TD-H04 | Banco de dados | 8-16h | Habilita persistencia para evolucao do produto. |
| XD-API-01 + TD-M06 | Versionamento de API | 4-8h | Protecao contra breaking changes. |
| XD-API-02 | Testes de contrato | 4-8h | JSON Schema compartilhado Pydantic/TypeScript. |
| UXD-005 | ARIA listbox no dropdown | 3h | Semantica correta para screen readers. |
| UXD-011 | Script FOUC alinhado | 3h | Eliminar micro-flash de tema. |
| UXD-012 | Indicador offline/rede | 4h | Feedback de conectividade. |
| UXD-016 | Decomposicao LoadingProgress | 6h | Manutenibilidade e testabilidade. |
| XD-TEST-01 | Testes integracao com MSW | 4-8h | E2E em CI sem backend live. |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Resolver TD-C02 (auth) sem TD-H04 (database) cria half-solution | Alta | Alto | Implementar JWT stateless como interim; planejar ambos na mesma sprint |
| Resolver TD-C01 (Excel streaming) pode quebrar rota de download BFF (TD-H06) | Media | Alto | Implementar com feature flag; testar download flow e2e antes de cutover |
| Remover dead code de 3 fontes (TD-C03) pode quebrar source registry | Media | Medio | Escrever testes de integracao do orquestrador antes da remocao |
| Fixar UXD-001 (multi-word terms) muda contrato de busca | Media | Medio | Verificar se backend suporta termos com aspas/virgulas; testar saved searches |
| Adicionar CSP (TD-M07) quebra inline theme script (TD-M10) | Alta | Medio | Resolver TD-M10 primeiro ou simultaneamente; adicionar nonce/hash ao CSP |
| Rate limiting per-IP pode falhar atras de Railway proxy | Media | Alto | Verificar `X-Forwarded-For` handling na configuracao do slowapi |
| Migrar para async OpenAI (TD-H03) muda error handling patterns | Baixa | Medio | Cobertura de teste LLM ja existe; verificar fallback path |
| Switching de tokenizacao (UXD-001) pode invalidar saved searches em localStorage | Media | Baixo | Migrar saved searches ou adicionar fallback de parsing |

---

## Gaps Reconhecidos

Gaps identificados por @qa na revisao. Status de escopo e acoes planejadas.

| # | Gap | In Scope? | Acao |
|---|-----|-----------|------|
| G-01 | Backend test coverage nao quantificada | **Sim** | **ACAO IMEDIATA:** Rodar `pytest --cov` e documentar resultado. Threshold de 70% em pyproject.toml deve ser validado. |
| G-02 | Sem avaliacao de gestao de secrets/credenciais | Parcial | Reconhecido como risco. Escopo de infraestrutura detalhada e responsabilidade de @devops. Nota: env vars sem rotation policy, sem vault. |
| G-03 | Sem avaliacao de PII em logs (LGPD) | Parcial | Reconhecido como risco de compliance. Auditoria de logs deve ser realizada antes de lancamento publico. Fora do escopo desta avaliacao de debito tecnico. |
| G-04 | Sem scan de vulnerabilidades em dependencias | **Sim** | Adicionar `pip audit` e `npm audit --audit-level=high` ao CI como quality gate. |
| G-05 | Sem avaliacao de information leakage em erros | Parcial | Verificar que stack traces nao sao expostas em production mode. Adicionar teste em test_security.py. |
| G-06 | Debitos de infraestrutura nao cobertos | **Fora de escopo** | Esta avaliacao cobre debitos de codigo (sistema, frontend, cross-cutting). Debitos de infraestrutura (IaC, staging, deployment strategy) sao responsabilidade de @devops e devem ser avaliados separadamente. |
| G-07 | Sem avaliacao de profundidade de validacao de input | Parcial | Input validation basica existe (termos_busca max length). Auditoria de SSRF/injection via UF codes e parametros externos e recomendada mas fora do escopo direto. |
| G-08 | Backup/recovery nao enderecado | **Fora de escopo** | Redis e efemero by design (arquitetura stateless). Graceful degradation sem Redis deve ser avaliada como parte de TD-H01. |
| G-09 | Controle de custos OpenAI nao avaliado | Parcial | Risco operacional reconhecido. Token usage limits devem ser implementados como parte da resolucao de TD-M04 (timeout). |
| G-10 | Bundle size nao baselinado | **Sim** | Estabelecer baseline com bundle analyzer e configurar budget no CI. Adicionar Lighthouse CI no proximo milestone. |

---

## Criterios de Sucesso

| Metrica | Valor Atual | Meta | Prazo |
|---------|------------|------|-------|
| Frontend statement coverage | ~68% | 75% | Proximo sprint |
| Frontend branch coverage | ~53% | 60% | Proximo sprint |
| Backend statement coverage | Desconhecido (threshold: 70%) | 75% | Medir imediatamente, melhorar no proximo sprint |
| E2E test scenarios | 4 (requerem backend live) | 8 (com MSW em CI) | Proximo milestone |
| Security headers presentes | 3/6 | 6/6 (CSP, HSTS, Referrer-Policy) | Proximo sprint |
| Lighthouse Performance score | Nao baselinado | Baseline + no regression | Proximo milestone |
| Bundle size (frontend) | Nao baselinado | Baseline + budget | Proximo milestone |
| Tempo medio para detectar falha de deploy | Sem smoke tests | < 2 minutos via smoke test automatizado | Proximo sprint |
| Vulnerabilidades em dependencias | Nao escaneado | 0 criticas, 0 altas | Ongoing |
| OpenAI API error rate | Nao monitorado | < 5% com fallback activation | Proximo milestone |

---

## QA Conditions - Resolution

As tres condicoes REQUERIDAS pela revisao QA e como foram enderecadas.

### Condicao 1: Backend test coverage deve ser medida e documentada

**Status: PENDENTE -- acao imediata requerida.**

A avaliacao reconhece que o backend test coverage nao foi quantificado. O `pyproject.toml` define `fail_under = 70.0` mas o valor real e desconhecido. A acao e rodar `pytest --cov` e atualizar este documento com o resultado. Este item nao bloqueia o uso da avaliacao para planejamento de sprint, mas deve ser resolvido antes do inicio da execucao.

### Condicao 2: TD-H05 severidade inconsistencia deve ser resolvida

**Status: RESOLVIDO.**

TD-H05 agora e consistentemente classificado como **Media** em todas as secoes (tabela de inventario, matriz de priorizacao, e notas). A justificativa: `allow_origins` e corretamente whitelisted, apenas `allow_headers` e permissivo. Risco real e moderado, nao alto. Prioridade: P3.

### Condicao 3: TD-M10 -> TD-M07 dependencia deve ser adicionada ao grafo

**Status: RESOLVIDO.**

A dependencia TD-M10 (dangerouslySetInnerHTML inline script) -> TD-M07 (CSP header) esta documentada no grafo de dependencias e na matriz de priorizacao. TD-M07 esta marcado como **BLOQUEADO por TD-M10**. A nota explicita que adicionar CSP com restricoes de `script-src` quebrara o inline script de tema, exigindo resolucao de TD-M10 primeiro (via nonce, hash, ou refatoracao para data-attributes).

---

## Estatisticas Finais

| Metrica | Valor |
|---------|-------|
| **Total de debitos** | 55 |
| **Criticos** | 3 (TD-C01, TD-C02, XD-SEC-02) |
| **Altos** | 10 (TD-C03, TD-H01, TD-H02, TD-H03, TD-H04, TD-H06, TD-M04, UXD-001, UXD-015, XD-PERF-01) |
| **Medios** | 25 |
| **Baixos** | 17 |
| **Debitos de Sistema** | 20 |
| **Debitos de Frontend/UX** | 23 (+3 novos) |
| **Debitos Cross-cutting** | 12 |
| **Debitos de Database** | 0 (stateless) |

### Estimativa de Esforco Final

| Area | Esforco Estimado |
|------|-----------------|
| Sistema (Backend) | 78-124 horas |
| Frontend/UX | 43-58 horas |
| Cross-cutting | 34-50 horas |
| **Total** | **155-232 horas** |

---

## Appendix: Review Trail

| Documento | Localizacao | Data | Autor |
|-----------|-------------|------|-------|
| DRAFT (Fase 4) | `docs/prd/technical-debt-DRAFT.md` | 2026-03-09 | @architect (Atlas) |
| UX Specialist Review (Fase 6) | `docs/reviews/ux-specialist-review.md` | 2026-03-09 | @ux-design-expert (Vera) |
| QA Review (Fase 7) | `docs/reviews/qa-review.md` | 2026-03-09 | @qa (Quinn) |
| **FINAL Assessment** | `docs/prd/technical-debt-assessment.md` | 2026-03-09 | @architect (Atlas) |

---

*Documento gerado: 2026-03-09*
*Consolidado por: @architect (Atlas)*
*Fontes: Brownfield Discovery Fases 1, 3, 4, 6, 7*
*Fases 2, 5 (Database): Puladas -- arquitetura stateless*
*Status: VALIDADO para planejamento de sprint*
