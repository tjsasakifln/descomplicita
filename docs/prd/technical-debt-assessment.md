# Technical Debt Assessment - FINAL

**Projeto:** Descomplicita
**Data:** 2026-03-09
**Versao:** 1.0
**Status:** Validado por @architect (Atlas), @data-engineer (Delphi), @ux-design-expert (Pixel), @qa (Quartz)
**Source Commit:** 5e56b38d

---

## Executive Summary

| Metrica | Valor |
|---------|-------|
| **Total de debitos unicos** | **60** (24 SYS + 16 DB + 20 FE) |
| **Criticos** | 4 (SYS-001, SYS-002, SYS-003, FE-005) |
| **Altos** | 12 (SYS-004, SYS-005, SYS-006, SYS-007, DB-001, DB-002, DB-003, DB-009, FE-001, FE-007, FE-015, FE-016) |
| **Medios** | 24 |
| **Baixos** | 20 |
| **Esforco total estimado** | **~255 horas** |
| **Esforco critico + alto** | **~100 horas** |

### Contexto

O DescompLicita e uma plataforma de busca de licitacoes publicas brasileiras construida sobre Next.js 16 + FastAPI + SQLite + Redis. A plataforma esta em estagio POC com maturidade arquitetural significativa (404+ testes, 5 temas, ARIA excelente), mas com lacunas criticas em persistencia de dados, identidade de usuario, e qualidade de busca que devem ser resolvidas antes de ir para producao.

### Top 3 Acoes de Maior Impacto

1. **Testar parametro `palavraChave` da API PNCP (2h spike)** -- O parametro nunca e enviado pelo client. Se funcionar, reduz volume de dados 10-20x, eliminando ou reduzindo a urgencia de DB-009, DB-015, timeout alignment, e memory pressure. Potencialmente a acao de maior ROI do inventario inteiro.

2. **Migracao para Supabase PostgreSQL (24-32h)** -- Resolve simultaneamente 7 items: SYS-001, DB-001, DB-002, DB-003, DB-008, DB-010, DB-012. Habilita persistencia real, isolamento multi-user, sistema de migracoes, e backups automaticos.

3. **Corrigir FE-005 error swallowing em ItemsList (2h)** -- Catch vazio na paginacao deixa usuario preso em "Carregando..." sem feedback. Critico porque e pre-requisito para que erros de DB-009 (desserializacao de 85K items) se tornem visiveis ao usuario e ao time de desenvolvimento.

### Nota sobre Sobreposicoes

SYS-001 e DB-002 descrevem o mesmo problema (SQLite efemero). DB-005 e DB-014 sao a mesma vulnerabilidade em dois pontos do codigo. Para planejamento, o inventario contem 60 items unicos mas reduz-se a ~57 unidades de trabalho (3 pares resolvidos juntos).

---

## Areas de Enfase Especial

### Acentuacao e Normalizacao

#### Status Geral: FUNCIONAL

A acentuacao e aspecto fundamental para uma plataforma brasileira. A analise end-to-end, validada por @data-engineer e @ux-design-expert, confirma que o sistema trata acentos corretamente em todas as camadas.

#### Mecanismo: normalize_text() (filter.py linhas 291-334)

A funcao realiza:
1. Lowercase
2. NFD decomposition (decompoe caracteres acentuados em base + combining mark)
3. Remocao de combining marks (categoria Unicode "Mn")
4. Remocao de pontuacao (substituicao por espacos)
5. Normalizacao de whitespace

Resultado: "licitacao" (com cedilha+til) e "licitacao" (sem acentos) produzem resultado normalizado identico.

#### Edge Cases Validados (@data-engineer)

| Caractere | Input | Resultado Apos Normalizacao | Status |
|-----------|-------|-----------------------------|--------|
| Cedilha | "licitacao" (com cedilha) | "licitacao" | OK |
| Til | "sao paulo" (com til) | "sao paulo" | OK |
| Acento agudo | "agua" (com acento) | "agua" | OK |
| Acento circunflexo | "tres" (com circunflexo) | "tres" | OK |
| Trema (historico) | "linguica" (com trema) | "linguica" | OK |
| Hifens | "guarda-po" | "guarda po" (duas palavras) | OK - match funciona via word boundary regex |

NFD decomposition cobre todas as diacriticas do portugues brasileiro. Nao ha edge cases que falhem.

#### Cadeia Completa Input -> Matching -> Display

| Camada | Comportamento | Status |
|--------|---------------|--------|
| Frontend input (SearchForm.tsx) | `.toLowerCase()` preserva acentos | Correto |
| Chips de termos | Exibem texto como digitado (apos lowercase) | Correto |
| Backend matching (match_keywords) | `normalize_text()` aplicado em AMBOS os lados (texto PNCP e keywords) | Correto |
| Display de resultados | Texto original da API PNCP preservado com acentos | Correto |
| Historico de busca | Termos salvos com acentos originais em localStorage | Correto |

#### Problemas Encontrados

1. **Variantes duplicadas nos keyword sets (~115 entradas redundantes):** Os keyword sets contem versoes com e sem acento de cada termo (ex: "confeccao" e "confeccao" com cedilha). Isso e redundante dado que `normalize_text()` ja normaliza ambos os lados. Impacto em corretude: zero. Impacto em manutencao: medio (risco de atualizar uma variante e esquecer a outra). **Esforco para limpar: 2h.**

2. **FE-018 -- heading "Licitacoes Encontradas" sem acentos:** `ItemsList.tsx` linha 63 usa texto sem cedilha e til, enquanto `page.tsx` usa texto com acentos corretos. Unico bug de acentuacao encontrado no frontend. **Esforco: 0.25h.**

#### Recomendacao UX sobre Acentuacao

Adicionar hint sutil no campo de termos: "Acentos sao opcionais -- 'licitacao' e 'licitacao' (com acentos) retornam os mesmos resultados." Isso reduz incerteza, especialmente para usuarios com teclados internacionais. NAO normalizar visualmente o input -- preservar o que o usuario digitou.

---

### Falsos Positivos e Falsos Negativos

#### Mecanismo de Busca Atual

O sistema usa keyword matching baseado em regex com normalizacao NFD, exclusion check (fail-fast), e tiered scoring opcional:
- Tier A (1.0): termos inequivocos ("uniforme", "fardamento")
- Tier B (0.7): termos fortes ("camiseta", "jaleco")
- Tier C (0.3): termos ambiguos ("camisa", "bota", "meia")
- Threshold: 0.6

#### Fontes de Falsos Positivos

| Fonte | Severidade | Detalhe | Mitigacao Existente |
|-------|-----------|---------|---------------------|
| **Exclusoes desativadas para termos customizados** | **Alta** | main.py linha 543: `exclusions=set()` quando custom_terms. FP rate estimado: 20-40% para termos ambiguos. Ex: busca "confeccao" retorna "confeccao de placas de sinalizacao" | Nenhuma |
| Termos ambiguos (Tier C) sozinhos | Media | "bota" (calcado vs. "bota de concreto") | Exclusion set + Tier C peso 0.3 |
| "EPI" sozinho | Media | EPI de construcao civil (nao vestuario) | `EPI_ONLY_KEYWORDS` check |
| Valor zero/null nao filtrado | Baixa | Items de Registro de Precos com R$ 0.00 | Intencional |

**Achado critico sobre scoring:** O scoring usa `max(score, weight)`, nao soma. Items com multiplos Tier C matches ("bota + meia + avental" = 3 termos, score permanece 0.3) sao sistematicamente rejeitados. Recomendacao do @data-engineer: scoring aditivo com cap `min(1.0, sum_of_weights)`. Esforco: 2h.

#### Fontes de Falsos Negativos

| Fonte | Severidade | Detalhe | Mitigacao Existente |
|-------|-----------|---------|---------------------|
| **Stemming ausente** | **Alta** | "uniformizado" nao casa com "uniforme", "confeccionado" nao casa com "confeccao" | Nenhuma |
| **MAX_PAGES_PER_COMBO = 10** | **Alta** | SP + Pregao Eletronico pode ter 228 paginas; apenas 500 items dos 11,400 sao buscados (95.6% perdidos) | Truncation tracking no SourceBadges (escondido atras de toggle) |
| **palavraChave nao enviado ao PNCP** | **Alta** (indireta) | Toda filtragem e client-side. Volume desnecessariamente alto causa truncamento | Nenhuma |
| Threshold conservador | Baixa | Items com apenas termos Tier C sao rejeitados (0.3 < 0.6) | Intencional |

#### Recomendacoes Priorizadas para Qualidade de Busca

| # | Recomendacao | Esforco | Impacto |
|---|-------------|---------|---------|
| 1 | **Spike: testar PNCP `palavraChave`** -- se funcionar, reduz volume 10-20x e elimina FN por truncamento | 2h teste + 2h integracao | **Muito Alto** |
| 2 | Manter exclusoes do setor ativas para termos customizados (abordagem hibrida com flag bypass) | 3h | Alto -- reduz 20-40% de FP |
| 3 | Implementar stemming PT-BR via RSLP/NLTK | 10h | Alto -- elimina FN de flexoes verbais |
| 4 | Scoring aditivo com cap para Tier C | 2h | Medio -- reduz FN em combinacoes de termos ambiguos |
| 5 | Remover variantes duplicadas de acentos nos keyword sets | 2h | Baixo -- limpeza de manutencao |

#### Golden Test Suite (recomendado por @qa)

Antes e apos qualquer mudanca de qualidade de busca, executar suite com 50 items known-relevant e 50 known-irrelevant contra snapshots reais de dados PNCP. Medir precision e recall. Esforco: 4h para criar suite inicial.

---

### Buscas de Grande Volume (30+ dias, 27 UFs)

Tres analises independentes (@architect, @data-engineer, @ux-design-expert) convergem nas mesmas conclusoes.

#### Parametros de Controle Existentes

| Parametro | Valor | Efeito |
|-----------|-------|--------|
| MAX_DATE_RANGE_DAYS | 90 dias | Limite maximo de range |
| MAX_PAGES_PER_COMBO | 10 paginas (500 items) | Truncamento por combo UF+modalidade |
| MODALIDADE_REDUCTION_UF_THRESHOLD | 10 UFs | Acima de 10 UFs, reduz de 7 para 3 modalidades |
| Frontend poll timeout | 10 minutos | Hard limit no frontend |
| PNCP timeout scaling | 300s + 15s/UF acima de 5 | Timeout dinamico no backend |
| Semaphore concurrency | 3 fetches simultaneos | Controle de carga |

#### Cenarios Analisados

| Cenario | Tasks | Volume Maximo | Tempo Estimado | Status |
|---------|-------|---------------|----------------|--------|
| 30 dias, 3 UFs (tipico) | 21 combos | 10,500 items | 60-180s | Funcional |
| 60 dias, 10 UFs (grande) | 2 chunks x 70 combos | 56,000 items | 180-400s | Proximo dos limites |
| 30 dias, 27 UFs (extremo) | 81 combos | ~85,000 items | 240-440s (4-7 min) | Funcional mas proximo dos limites |
| **90 dias, 27 UFs (maximo)** | **3 chunks x 81 combos** | **~85,000 items** | **600-1200s (10-20 min)** | **QUEBRA -- excede todos os timeouts** |

#### Problemas Criticos Confirmados

**1. Timeout Race Condition (Critica)**

| Componente | Timeout |
|------------|---------|
| Frontend (useSearchJob.ts) | 600,000ms (10 min) -- FIXO |
| Backend para 27 UFs | 300 + (27-5)*15 = **630s (10.5 min)** |
| Delta | **30 segundos** onde backend pode completar mas frontend ja mostrou erro |

O backend pode retornar com sucesso, mas o frontend ja exibiu "A consulta excedeu o tempo limite" ao usuario. O job continua em background com resultados em Redis que o usuario nao vera.

**2. Memory Pressure (Critica para Railway 512MB)**

| Componente | Memoria Estimada |
|------------|-----------------|
| Items in-memory (self._items) -- DB-015 dual-write | ~120MB |
| Items em Redis | ~51MB |
| Excel generation (pico) | ~200MB |
| Filter batch (regex matching) | ~140MB |
| **Total pico por job de 85K items** | **~460MB** |

Railway free tier: 512MB. Uma unica busca de 27 UFs x 90 dias pode causar OOM. Duas buscas grandes simultaneas: ~920MB.

**3. ETA Impreciso para Grandes Volumes**

ETAs pos-fetching sao hardcoded ("~15s", "~10s", "~5s") independente do volume. Para 85K items, filtering leva 30-60s, nao 15s. Progress bar fica presa em 60% durante filtering. Usuario percebe sistema como travado.

#### Recomendacoes para Grande Volume

| # | Recomendacao | Esforco | Prioridade |
|---|-------------|---------|------------|
| 1 | Alinhar frontend timeout com backend: calcular timeout dinamico, backend envia `X-Expected-Duration` na resposta | 3h | P1 |
| 2 | Advertencia proativa (FE-016): banner inline quando >10 UFs ou >30 dias, com estimativa de tempo | 3h | P1 |
| 3 | Redis LIST para items (DB-009): RPUSH individual, LRANGE para paginacao | 6h | P2 |
| 4 | Eliminar dual-write in-memory (DB-015): quando Redis disponivel, nao manter copia Python | 3h | P3 |
| 5 | Limitar Excel a 10K items; acima disso, oferecer CSV | 4h | P3 |
| 6 | ETA dinamico baseado em volume de items (multiplicar estimativas base por `ceil(itemsFetched / 5000)`) | 2h | P3 |

---

### Qualidade UX

#### Pontos Fortes Existentes (validados por @ux-design-expert)

- **LoadingProgress** -- Uma das melhores implementacoes de loading state para este tipo de aplicacao: UfGrid visual por estado, curiosity carousel contextual, progress bar com ETA, cancel button sempre visivel, tab notifications
- **EmptyState** -- Excelente breakdown de rejeicao com contagens e tips actionaveis
- **SearchSummary** -- Resumo executivo AI forte com badges, alertas de urgencia, e destaques animados
- **Acessibilidade** -- ARIA listbox em SavedSearchesDropdown, dialog nativo em SaveSearchDialog, Ctrl+Enter shortcut, axe-core Playwright tests

#### Problemas Criticos de UX

**FE-005 (CRITICA): Error Swallowing em ItemsList**
- `catch {}` vazio na paginacao (linha 44). Usuario fica preso em "Carregando..." perpetuo ou ve lista vazia sem explicacao
- Sem retry, sem mensagem de erro, sem logging (Sentry)
- Para buscas de grande volume onde paginacao e essencial, isto e inaceitavel
- Design recomendado: inline error com retry button no container da lista

**FE-015 (ALTA): Sem Highlight de Termos nos Resultados**
- Items exibem `objeto` como texto puro sem destaque dos termos que causaram o match
- Usuario nao consegue avaliar rapidamente POR QUE um resultado foi retornado
- Dificulta identificacao de falsos positivos
- Requer mudanca backend: incluir `matched_keywords` na resposta de items

**FE-016 (ALTA): Sem Advertencia para Buscas de Grande Volume**
- Nenhum feedback visual quando usuario seleciona 27 UFs + 30+ dias
- Leva a abandono, confusao, e uso desnecessario de recursos
- Formato recomendado: banner inline (nao modal, nao tooltip)

**FE-020 (MEDIA): Termos Multi-Palavra Impossiveis via Interface**
- SearchForm.tsx (linha 126) usa espaco como delimitador de tokens
- Backend suporta termos multi-palavra via aspas (`"camisa polo"`), mas a UI nao oferece affordance
- Hint text nao menciona aspas ou virgulas
- Usuario nao consegue buscar por termos compostos como "camisa polo" ou "jaleco medico"

**Tipo (licitacao/ata) oculto nos items individuais**
- Campo `tipo` recebido na interface `ProcurementItem` (linha 13) mas nunca renderizado
- Badges de tipo aparecem apenas no SearchSummary como contagem agregada
- Usuario B2B precisa dessa informacao para priorizacao

---

## Inventario Completo de Debitos

### Sistema (validado por @architect)

| ID | Debito | Severidade | Horas | Prioridade | Notas |
|----|--------|-----------|-------|------------|-------|
| SYS-001 | SQLite em filesystem efemero (Railway) | Critica | 16 | P1 | Sobrepoe com DB-002. Resolver como migracao unica para Supabase. |
| SYS-002 | Sem modelo de identidade de usuario | Critica | 24 | P1 | Requerido antes de multi-tenant. Projetar concorrentemente com migracao Supabase. |
| SYS-003 | Implementacao JWT customizada (sem PyJWT) | Critica | 4 | P1 | Sem key rotation, sem audience/issuer, sem JWK. |
| SYS-004 | CORS allow_headers=["*"] | Alta | 1 | P2 | Aceita qualquer header. |
| SYS-005 | Sem CSP ou HSTS headers | Alta | 4 | P2 | Falta Content-Security-Policy e Strict-Transport-Security. |
| SYS-006 | Saved searches apenas em localStorage | Alta | 8 | P2 | Sem persistencia server-side, sem sync cross-device. |
| SYS-007 | Auth bypass em dev mode sem safeguard | Alta | 2 | P2 | API_KEY e JWT_SECRET nao definidos = bypass silencioso. |
| SYS-008 | Version string hardcoded | Media | 2 | P3 | |
| SYS-009 | MD5 para dedup keys | Media | 1 | P3 | MD5 ok para hashing nao-seguranca. |
| SYS-010 | Sem timeout em chamadas OpenAI | Media | 2 | P2 | LLM call pode travar indefinidamente. |
| SYS-011 | Vercel serverless limits para download proxy | Media | 4 | P3 | BFF buffering nega streaming. |
| SYS-012 | 3 data sources depreciadas referenciadas | Media | 2 | P3 | |
| SYS-013 | In-memory JobStore como base do RedisJobStore | Media | 8 | P3 | Dual-write, acoplamento conceitual. Relacionado a DB-015. |
| SYS-014 | Filter engine usa regex para keyword matching | Media | 8 | P4 | ~230 patterns por item. |
| SYS-015 | Sem retry nas chamadas BFF proxy | Media | 4 | P3 | Network blips causam falha imediata. |
| SYS-016 | React 18 com Next.js 16 | Baixa | 8 | P4 | Impede React 19 features. |
| SYS-017 | Module alias mismatch Jest vs tsconfig | Media | 2 | P3 | |
| SYS-018 | Transparencia health check sincrono | Baixa | 2 | P4 | |
| SYS-019 | Deadline filter parcialmente desabilitado | Baixa | 4 | P4 | |
| SYS-020 | Sem OpenAPI schema para items response | Baixa | 1 | P4 | |
| SYS-021 | Integration tests sao placeholder | Baixa | 16 | P4 | |
| SYS-022 | Sem Docker Compose profile para frontend dev | Baixa | 2 | P5 | |
| SYS-023 | Mixpanel carregado em todas as paginas | Baixa | 2 | P5 | |
| SYS-024 | Sem logging estruturado no frontend | Baixa | 4 | P5 | |

### Database e Search (validado por @data-engineer)

| ID | Debito | Severidade | Horas | Prioridade | Notas |
|----|--------|-----------|-------|------------|-------|
| DB-001 | Sem isolamento multi-user/multi-tenant | Alta | 4 | P1 | `get_recent_searches()` sem WHERE user_id. |
| DB-002 | Storage efemero no Railway/Vercel | Alta | 16 | P1 | Sobrepoe com SYS-001. Resolver na migracao Supabase. |
| DB-003 | Sem sistema de migracao | Alta | 6 | P1 | Schema via CREATE TABLE IF NOT EXISTS. 6h com Supabase CLI (vs 8h com Alembic). |
| DB-004 | Tabela user_preferences nao utilizada | Media | 1 | P3 | 3 metodos implementados, nunca chamados. |
| DB-005 | API key comparison vulneravel a timing attack | Media | 0.5 | P2 | `==` ao inves de `hmac.compare_digest`. Corrigir junto com DB-014. |
| DB-006 | Redis write amplification em progress updates | Media | 4 | P3 | Cada progress update serializa job inteiro. |
| DB-007 | Sem health check do database | Media | 1 | P3 | /health verifica Redis mas nao SQLite. |
| DB-008 | Sem politica de retencao/cleanup para SQLite | Baixa | 2 | P3 | Rebaixada de Media: storage efemero torna retencao irrelevante ate migracao Supabase. |
| DB-009 | Redis items desserializa dataset completo | **Alta** | 6 | P2 | Elevada de Media. `get_items_page()` carrega TODOS os items e faz slice. Para 85K items: ~50-100MB por request. Migrar para Redis LIST (RPUSH/LRANGE). |
| DB-010 | Sem estrategia de backup | Baixa | 2 | P4 | Reduzida de 4h: Supabase gerencia backups. |
| DB-011 | Graceful degradation esconde falhas silenciosamente | Baixa | 2 | P4 | Retorna resultados vazios sem metricas. |
| DB-012 | Supabase env vars definidas mas nao utilizadas | Baixa | 0.5 | P5 | |
| DB-013 | Sem transaction boundaries para operacoes multi-step | Baixa | 2 | P5 | Aceitavel para operacoes single-statement atuais. |
| DB-014 | Timing attack no endpoint /auth/token **(NOVO)** | Media | 0.5 | P2 | main.py linha 317: `request_key != api_key`. Corrigir junto com DB-005. |
| DB-015 | In-memory + Redis dual-write sem invalidacao **(NOVO)** | Media | 3 | P3 | Items duplicados em self._items (Python) e Redis. Para 85K items: ~120MB desnecessarios em Python. |
| DB-016 | PNCP cache keys sem normalizacao de UF **(NOVO)** | Baixa | 0.5 | P5 | Risco baixo (Pydantic valida), mas defesa em profundidade. |

### Frontend/UX (validado por @ux-design-expert)

| ID | Debito | Severidade | Horas | Prioridade | Notas |
|----|--------|-----------|-------|------------|-------|
| FE-001 | Cores hardcoded nos badges de SearchSummary | Alta | 1 | P2 | `bg-blue-100 text-blue-800` nao responde a temas paperwhite/sepia/dim. |
| FE-002 | Cor hardcoded no SourceBadges warning | Baixa | 0.5 | P4 | `text-amber-600` ao inves de token semantico. |
| FE-003 | Dependencia UUID desnecessaria | Baixa | 0.5 | P4 | Substituir por `crypto.randomUUID()`. |
| FE-004 | Componente Spinner ausente | Media | 1 | P3 | SVG spinner duplicado em 2+ componentes. |
| FE-005 | Error swallowing silencioso no ItemsList | **Critica** | 2 | **P1** | Elevada de Alta. `catch {}` vazio na paginacao. Usuario preso em loading perpetuo. |
| FE-006 | Componente Button ausente | Media | 3 | P3 | Drift ja visivel entre variantes de botao. |
| FE-007 | ink-muted contraste abaixo de WCAG AA | **Alta** | 1 | **P2** | Elevada de Media. `#5a6a7a` contra branco = 4.1:1 (< 4.5:1). Afeta valores monetarios e datas. Fix: alterar para `#4f5f6f` (~4.8:1). |
| FE-008 | Link /termos quebrado no footer | Media | 2 | P3 | Rota inexistente. Visivel em todas as paginas. |
| FE-009 | Sem error fallback para dynamic imports | Baixa | 1 | P4 | EmptyState e ItemsList sem loading/error fallback. |
| FE-010 | Teste ausente para RegionSelector | Baixa | 1.5 | P4 | |
| FE-011 | Teste ausente para SourceBadges | Media | 2 | P3 | Componente com logica condicional complexa. |
| FE-012 | Tema Dim com cobertura incompleta de tokens | Baixa | 2 | P4 | Dim quase identico a Dark (apenas canvas e surface-0 diferem). |
| FE-013 | SavedSearchesDropdown retorna null durante loading | Baixa | 0.5 | P5 | Layout shift breve. |
| FE-014 | page.tsx e monolitico client component | Baixa | 4 | P5 | 209 linhas de "use client". |
| FE-015 | Sem highlight de termos de busca nos resultados **(NOVO)** | Alta | 4 | P2 | Resultados exibem objeto como texto puro. Requer backend: incluir matched_keywords na resposta. Total: 5h (1h backend + 4h frontend). |
| FE-016 | Sem advertencia proativa para buscas de grande volume **(NOVO)** | Alta | 3 | P2 | Nenhum feedback ao selecionar 27 UFs + 30+ dias. Banner inline quando >10 UFs ou >30 dias. |
| FE-017 | Mensagem de timeout generica sem orientacao **(NOVO)** | Media | 2 | P3 | Sem contexto sobre UFs/dias selecionados, sem sugestao especifica de reducao. |
| FE-018 | ItemsList heading com acento faltando **(NOVO)** | Baixa | 0.25 | P4 | "Licitacoes Encontradas" sem cedilha e til. |
| FE-019 | Sem protecao contra race conditions na paginacao **(NOVO)** | Media | 2 | P3 | fetchPage sem AbortController. Navegacao rapida pode exibir dados stale. |
| FE-020 | Termos multi-palavra impossiveis via interface **(NOVO)** | Media | 3 | P3 | Espaco cria novo token. Backend suporta aspas, mas frontend nao tem affordance. |

---

## Matriz de Priorizacao Final

### Sprint 1: Quick Wins e Fundacao Critica

**Objetivo:** Eliminar riscos criticos e realizar investigacao de maior ROI.

| Ordem | ID(s) | Debito | Esforco | Justificativa |
|-------|-------|--------|---------|---------------|
| 1 | -- | **Spike: testar PNCP `palavraChave`** | 2h | Maior ROI potencial. Se funcionar, reduz volume 10-20x e muda prioridades de DB-009, DB-015, e timeout. |
| 2 | FE-005 | Error swallowing em ItemsList | 2h | Critico. Pre-requisito para que erros se tornem visiveis. |
| 3 | SYS-003 + DB-005 + DB-014 | JWT customizada + timing attack (2 pontos) | 5h | Seguranca. Correcoes rapidas e independentes. |
| 4 | SYS-001 + DB-002 + DB-001 + DB-003 | Migracao Supabase (resolve tambem DB-008, DB-010, DB-012) | 24-32h | Fundacao para persistencia, multi-user, e migracoes. |
| 5 | -- | Frontend timeout alignment com backend | 3h | Race condition confirmada: 10 min frontend vs 10.5 min backend para 27 UFs. |
| 6 | SYS-002 | Modelo de identidade de usuario | 24h | Design concorrente com migracao Supabase. |

**Subtotal Sprint 1: ~60-68h** (inclui design + implementacao Supabase + identidade)

### Sprint 2: Qualidade de Busca e UX Critica

**Objetivo:** Melhorar qualidade de resultados e experiencia de grandes volumes.

| Ordem | ID(s) | Debito | Esforco | Justificativa |
|-------|-------|--------|---------|---------------|
| 7 | DB-009 | Redis LIST para items (paginacao eficiente) | 6h | Elimina ~100MB alocacao por request de paginacao. Depende de FE-005 estar corrigido. |
| 8 | -- | Exclusoes hibridas para termos customizados | 3h | Reduz 20-40% de FP em buscas customizadas. |
| 9 | FE-016 | Advertencia proativa para grande volume | 3h | Previne abandono e uso desnecessario de recursos. |
| 10 | FE-015 | Highlight de termos nos resultados | 5h | 1h backend (matched_keywords) + 4h frontend. Permite avaliacao rapida de relevancia. |
| 11 | FE-001 + FE-007 | Cores hardcoded badges + ink-muted WCAG AA | 2h | Quick wins de acessibilidade e temas. |
| 12 | SYS-004 + SYS-005 + SYS-007 | CORS + CSP/HSTS + auth bypass safeguard | 7h | Hardening de seguranca. |
| 13 | SYS-010 | Timeout em chamadas OpenAI | 2h | Confiabilidade. |
| 14 | SYS-006 | Saved searches server-side | 8h | Depende de Supabase + identidade (Sprint 1). |

**Subtotal Sprint 2: ~36h**

### Sprint 3: Otimizacao e Refinamento

**Objetivo:** Melhorar qualidade de busca e reduzir debito tecnico.

| Ordem | ID(s) | Debito | Esforco | Justificativa |
|-------|-------|--------|---------|---------------|
| 15 | -- | Stemming PT-BR via RSLP/NLTK | 10h | Elimina classe inteira de FN (flexoes verbais). Validar com golden test suite. |
| 16 | DB-015 | Eliminar dual-write in-memory | 3h | Reduz ~120MB de memoria desnecessaria. |
| 17 | FE-019 | AbortController para paginacao | 2h | Previne exibicao de dados stale. |
| 18 | FE-017 | Mensagem de timeout enriquecida | 2h | Orientacao especifica vs generica. |
| 19 | DB-006 | Redis write amplification | 4h | Reduz writes desnecessarios em progress updates. |
| 20 | -- | Remocao de variantes de acento nos keyword sets | 2h | Limpeza de ~115 entradas redundantes. |
| 21 | -- | Scoring aditivo para Tier C | 2h | Reduz FN em items com multiplos termos ambiguos. |
| 22 | FE-006 | Button component | 3h | Previne drift de estilos. |
| 23 | FE-020 | Termos multi-palavra via interface | 3h | Suporte a virgulas + hint text. |
| 24 | FE-004 + FE-008 + FE-011 | Spinner + link /termos + teste SourceBadges | 5h | Quick wins de qualidade. |

**Subtotal Sprint 3: ~36h**

### Backlog (P4/P5)

| ID(s) | Debito | Esforco | Notas |
|-------|--------|---------|-------|
| SYS-008, SYS-009, SYS-012, SYS-017 | Limpeza de codigo (version, MD5, sources, aliases) | 7h | |
| SYS-011, SYS-013, SYS-015 | Vercel limits, JobStore refactor, BFF retry | 16h | |
| SYS-014, SYS-016, SYS-018 | Regex engine, React 18, health check | 18h | |
| SYS-019..024 | Deadline filter, OpenAPI, integration tests, Docker, Mixpanel, logging | 29h | |
| DB-004, DB-007, DB-008, DB-011 | user_preferences, health check DB, cleanup, degradation | 6h | |
| DB-010, DB-013, DB-016 | Backup, transactions, cache keys | 4.5h | |
| FE-002, FE-003, FE-009, FE-010 | Cor SourceBadges, UUID, dynamic fallback, teste RegionSelector | 3.5h | |
| FE-012, FE-013, FE-014, FE-018 | Tema Dim, SavedSearches null, page.tsx monolitico, heading acento | 6.75h | |
| -- | Pre-computed data pipeline (ingestion batch PNCP) | 40h | Longo prazo. Elimina buscas on-demand. Requer Supabase. |

**Subtotal Backlog: ~131h**

---

## Plano de Resolucao

### Fluxo de Dependencias

```
                       PNCP palavraChave Spike (2h)
                       |
                       v
                  [Se funcionar: re-priorizar DB-009, DB-015, timeout]
                  [Se nao funcionar: manter plano original]

FE-005 (2h) ---------> DB-009 (6h) ---------> DB-015 (3h)
(error handling)        (Redis LIST)            (eliminar dual-write)
                                    \
                                     ---------> Excel limit (4h)

SYS-002 (design) -----> SYS-001 + DB-002 + DB-001 + DB-003 (24-32h)
(identidade)             (migracao Supabase, resolve +3 items)
                         |
                         v
                         SYS-006 (8h) -- saved searches server-side
                         DB-008 (retencao) -- agora relevante

SYS-003 (4h) + DB-005/014 (1h) -- independentes, paralelo com Supabase

FE-016 (3h) + Timeout alignment (3h) -- coordenar para UX consistente

FE-015 (5h) -- backend change + frontend, independente

Stemming (10h) -- validar com golden test suite (4h) antes de merge

Exclusoes hibridas (3h) -- validar com benchmarks FP1/FP2 antes de merge
```

### Ordem de Resolucao Recomendada

1. **Spike PNCP `palavraChave`** (2h) -- FAZER PRIMEIRO. Resultados podem mudar todas as prioridades.
2. **FE-005** (2h) -- Corrigir error swallowing. Pre-requisito para visibilidade de erros.
3. **SYS-003 + DB-005 + DB-014** (5h) -- Seguranca basica. Pode rodar em paralelo.
4. **Design SYS-002** (identidade) + **Migracao Supabase** (SYS-001/DB-001/002/003) -- 24-32h como unidade atomica.
5. **Frontend timeout alignment + FE-016** (6h) -- Coordenar para UX consistente de grande volume.
6. **DB-009** (6h) -- Redis LIST. Depende de FE-005 estar feito.
7. **Exclusoes hibridas para termos customizados** (3h) -- Com benchmarks de FP.
8. **FE-015** (5h) -- Highlight de termos. Backend + frontend.
9. **FE-001 + FE-007** (2h) -- Quick wins de acessibilidade.
10. **Stemming RSLP** (10h) -- Com golden test suite de validacao.

---

## Riscos e Mitigacoes

| Risco | Areas Afetadas | Severidade | Mitigacao |
|-------|---------------|-----------|-----------|
| **Timeout race condition** (frontend 10min vs backend 10.5min para 27 UFs) | Backend, Frontend, UX | **Critica** | Frontend timeout dinamico baseado em UFs. Backend envia `X-Expected-Duration` header. (3h) |
| **Memory pressure de buscas grandes** (85K items = ~460MB, Railway 512MB) | Backend, Redis, Infra | **Critica** | DB-009 (Redis LIST, 6h) + DB-015 (eliminar dual-write, 3h) + Excel limit (4h). Total: 13h |
| **Qualidade de busca degradada para termos customizados** (exclusoes desativadas) | Backend, Frontend, UX | **Alta** | Exclusoes hibridas (3h) + FE-015 highlight (5h). Total: 8h |
| **Truncamento esconde resultados relevantes** (MAX_PAGES 10, 95.6% perdidos para SP) | Backend, Frontend, UX | **Alta** | Spike palavraChave (2h+2h). Se nao funcionar: surface truncation warning mais proeminente. |
| **FE-005 cascata com DB-009** (catch vazio esconde erros de OOM/timeout na paginacao) | Frontend, Backend | **Alta** | Corrigir FE-005 ANTES de DB-009. Ordem importa. |
| **Migracao Supabase afeta 7+ items** (SYS-001, DB-001/002/003/008/010/012) | Database, Backend, Auth | **Alta** | Planejar como unidade atomica (24-32h). SYS-002 (identidade) deve ser desenhado concorrentemente. |
| **ETA impreciso erode confianca do usuario** (hardcoded "~15s" quando faltam 60s) | Frontend, UX | **Media** | ETA dinamico baseado em volume (2h) + interpolacao de progress bar durante filtering (2h). |
| **Sem baseline quantitativo de FP/FN** (mudancas de busca nao mensuraveis) | Backend, QA | **Media** | Golden test suite com 100 items (4h). Executar antes e apos cada mudanca de qualidade. |

---

## Criterios de Sucesso

### Metricas de Validacao

| Area | Metrica | Valor Alvo |
|------|---------|------------|
| Persistencia | Dados sobrevivem a deploy | 100% apos migracao Supabase |
| Timeout | Frontend timeout >= backend timeout para todas as combinacoes validas | Sempre |
| Memoria | Peak RSS para busca de 27 UFs x 30 dias | < 400MB |
| FP rate (termos customizados) | Reducao de falsos positivos apos re-habilitar exclusoes | >= 20% reducao |
| FN rate (stemming) | Items adicionais encontrados com flexoes verbais | >= 10% mais items relevantes |
| Acessibilidade | WCAG AA contraste para todos os tokens --ink-* em todos os temas | >= 4.5:1 |
| Paginacao | Tempo de resposta para paginar 85K items | < 200ms (vs ~5s atual com desserializacao completa) |
| Error handling | Zero `catch {}` vazios no frontend | 0 ocorrencias |
| UX loading | ETA accuracy para buscas > 1000 items | < 30% erro absoluto medio |

### Golden Test Suite para FP/FN

Criar suite com:
- 50 items known-relevant (licitacoes reais de vestuario do PNCP)
- 50 items known-irrelevant (licitacoes de outros setores que contem termos ambiguos)
- Executar antes e apos cada mudanca de qualidade de busca
- Medir precision e recall
- Bloquear merge se recall cair > 5% ou precision cair > 10%

### Testes Criticos Requeridos

| ID | Teste | Valida | Tipo | Esforco |
|----|-------|--------|------|---------|
| CP1 | Frontend timeout >= backend timeout para todas as combinacoes de UF/dias | Timeout race | Property-based | 2h |
| CP2 | Paginacao exibe retry button apos erro (validacao FE-005) | Error handling | Component | 1h |
| CP3 | `hmac.compare_digest` usado em ambos os pontos de auth | Seguranca | Unit | 0.5h |
| CP4 | Supabase CRUD basico pos-migracao | Persistencia | Integration | 2h |
| CP5 | Busca com termos customizados: exclusoes aplicadas quando setor selecionado | Qualidade de busca | Integration | 1h |
| EA1 | `normalize_text()` com todas as diacriticas PT-BR + NFC/NFD | Acentuacao | Unit | 1h |
| EA2 | Golden test suite: 50 relevant + 50 irrelevant, medir precision/recall | FP/FN | Benchmark | 4h |
| EA3 | PNCP `palavraChave` teste com endpoint real | Reducao de volume | Manual | 2h |
| LV1 | Busca simulada de 27 UFs com mock PNCP: completa dentro do frontend timeout | Grande volume | Integration | 2h |
| LV3 | Medicao de memoria durante processamento de 85K items | Grande volume | Performance | 2h |

---

## Dependencias entre Items

### Bloqueios Diretos

| Item Bloqueador | Item Bloqueado | Razao |
|----------------|---------------|-------|
| FE-005 (error handling) | DB-009 (Redis LIST) | Sem error handling, regressoes em paginacao seriam silenciosamente engolidas |
| SYS-002 (identidade - design) | SYS-001/DB-002 (migracao Supabase) | Schema de usuario precisa estar definido antes da migracao |
| Migracao Supabase | SYS-006 (saved searches server-side) | Requer persistencia real e user_id |
| Migracao Supabase | DB-008 (retencao) | Retencao so e relevante com storage persistente |
| Backend matched_keywords (1h) | FE-015 (highlight de termos) | Frontend precisa saber quais termos fizeram match |
| Golden test suite (4h) | Stemming RSLP (10h) | Stemming pode gerar novos FP; precisa baseline para validar |
| Golden test suite (4h) | Exclusoes hibridas (3h) | Precisa medir antes/depois para validar reducao de FP |

### Resolucoes Conjuntas (mesma PR)

| Items | Razao | Esforco Combinado |
|-------|-------|-------------------|
| SYS-001 + DB-002 + DB-001 + DB-003 (+ DB-008, DB-010, DB-012) | Migracao Supabase resolve todos simultaneamente | 24-32h |
| DB-005 + DB-014 | Mesma vulnerabilidade em 2 pontos de codigo | 1h |
| FE-001 + FE-007 | Ambos sao ajustes de tokens CSS semanticos | 2h |
| FE-016 + timeout alignment | UX consistente de grande volume | 6h |

### Paralelizaveis

Os seguintes grupos podem rodar em paralelo:
- **Grupo A:** SYS-003 + DB-005/014 (seguranca basica)
- **Grupo B:** FE-005 (error handling)
- **Grupo C:** Spike palavraChave
- **Grupo D:** FE-016 + timeout alignment (grande volume UX)
- **Grupo E:** Migracao Supabase (apos design de SYS-002)

---

*Documento consolidado por @architect (Atlas) com base em 4 fases de analise: auditoria arquitetural (Phase 1-3), consolidacao DRAFT (Phase 4), revisao de @data-engineer Delphi (Phase 5), revisao de @ux-design-expert Pixel (Phase 6), e validacao de @qa Quartz (Phase 7). Todos os caminhos de arquivo, numeros de versao, e detalhes arquiteturais verificados contra o codigo-fonte no commit 5e56b38d.*
