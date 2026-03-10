# Technical Debt Assessment - DRAFT

## Para Revisao dos Especialistas

**Documento:** DRAFT v2.0
**Data:** 2026-03-09
**Autor:** @architect (Atlas)
**Status:** Consolidado de 3 fases de auditoria -- aguardando revisao
**Fontes:**

1. `docs/architecture/system-architecture.md` (Phase 1 -- 24 itens SYS-xxx)
2. `supabase/docs/SCHEMA.md` + `supabase/docs/DB-AUDIT.md` (Phase 2 -- 13 itens DB-xxx)
3. `docs/frontend/frontend-spec.md` (Phase 3 -- 14 itens FE-xxx)
4. Analise direta do codigo-fonte (backend/filter.py, backend/sectors.py, backend/main.py, backend/clients/async_pncp_client.py, backend/sources/orchestrator.py)

---

## Executive Summary

| Metrica | Valor |
|---------|-------|
| **Total de itens de debito** | **51** (24 SYS + 13 DB + 14 FE) |
| **Criticos** | 3 (SYS-001, SYS-002, SYS-003) |
| **Altos** | 10 (SYS-004..007, DB-001..003, FE-001, FE-005) |
| **Medios** | 21 |
| **Baixos** | 17 |
| **Esforco total estimado** | ~240 horas |
| **Esforco critico+alto** | ~85 horas |

### Contexto

O DescompLicita e uma plataforma de busca de licitacoes publicas brasileiras construida sobre Next.js 16 + FastAPI + SQLite + Redis. A plataforma esta em estagio POC com maturidade arquitetural significativa (404+ testes, 5 temas, ARIA excelente), mas com lacunas criticas em persistencia de dados, identidade de usuario, e qualidade de busca que devem ser resolvidas antes de ir para producao.

---

## ENFASE ESPECIAL: Busca e UX

### Acentuacao e Normalizacao

#### Analise Completa do Stack

A acentuacao e um aspecto **fundamental** para uma plataforma brasileira. A analise revela que o backend implementa normalizacao de acentos, mas ha lacunas significativas no tratamento end-to-end.

##### Backend: `filter.py` - normalize_text()

O backend possui uma funcao `normalize_text()` (linhas 291-334) que realiza:

1. **Lowercase**: `text.lower()`
2. **NFD decomposition**: `unicodedata.normalize("NFD", text)` -- decompoe caracteres acentuados em base + combining mark
3. **Removing combining marks**: Filtra caracteres com categoria Unicode "Mn" (Mark, nonspacing)
4. **Punctuation removal**: Substitui nao-alfanumericos por espacos
5. **Whitespace normalization**: Espacos multiplos viram um so

**Resultado:** `"licitacao"` e `"licitacao"` (sem acento) produzem o mesmo resultado normalizado. `"Jaleco Medico"` se torna `"jaleco medico"`.

##### Keywords no sectors.py: Duplicacao Manual de Variantes

As keyword sets contem **duplicatas manuais** para variantes com e sem acento:

```
"confeccao",       # sem acento
"confeccao",       # com cedilha
"confeccoes",      # sem acento plural
"confeccoes",      # com acento plural
```

Isso e **redundante** dado que `normalize_text()` ja remove acentos antes do matching. As ~130 keywords de inclusao e ~100 de exclusao incluem variantes desnecessarias. Isso nao causa bugs, mas aumenta o tamanho dos sets e a complexidade de manutencao.

##### Lacuna 1: PNCP API nao suporta `palavraChave`

O parametro `palavraChave` da API PNCP e **silenciosamente ignorado** (verificado 2026-03-07, documentado em `pncp_client.py` linha 503). Isso significa que:

- **Toda filtragem e client-side**: o backend busca TODOS os registros para os UFs/datas/modalidades selecionados e depois aplica filtro de keywords localmente
- Nao ha filtragem server-side por termo de busca
- O volume de dados buscados e independente dos termos de busca

##### Lacuna 2: Termos customizados do usuario nao sao normalizados na entrada

Quando o usuario digita termos customizados (`termos_busca`), eles passam por `parse_multi_word_terms()` (main.py linhas 214-246) que faz apenas `term.strip().lower()`. **Nao ha normalizacao de acentos nos termos do usuario.**

Porem, isso nao causa falsos negativos porque `match_keywords()` (filter.py linha 366) aplica `normalize_text()` em **ambos** os lados:
- `objeto_norm = normalize_text(objeto)` -- normaliza o texto do PNCP
- `kw_norm = normalize_text(kw)` -- normaliza cada keyword

**Resultado:** Se o usuario digita `"licitacao"` (sem acento) ou `"licitacao"` (com acento e cedilha), ambos sao normalizados para `"licitacao"` antes do matching. **A busca funciona corretamente com ou sem acentos.**

##### Lacuna 3: Display de resultados preserva acentos originais

Os textos exibidos ao usuario (objeto da licitacao, nome do orgao, municipio) vem diretamente da API PNCP sem transformacao. Isso e **correto** -- o texto original com acentos e preservado para display. Nao ha risco de exibir texto sem acentos.

##### Lacuna 4: Exclusion keywords e accent variants

Os exclusion keywords tambem contem duplicatas de variantes com/sem acento (ex: `"confeccao de placa"` e `"confeccao de placa"` com cedilha). Mesma redundancia mencionada acima -- funcional mas desnecessaria.

#### Avaliacao Geral: Acentuacao

| Aspecto | Status | Risco |
|---------|--------|-------|
| Normalizacao no matching | **Funcional** | Nenhum |
| Termos customizados do usuario | **Funcional** (normalize_text aplicado em ambos os lados) | Nenhum |
| Display de resultados | **Correto** (preserva acentos originais) | Nenhum |
| Keywords duplicadas (com/sem acento) | **Redundante** mas funcional | Baixo (manutencao) |
| Filtragem server-side no PNCP | **Nao disponivel** (palavraChave ignorado) | Medio (volume) |

> **PENDENTE:** Revisao do @data-engineer -- confirmar se ha edge cases com caracteres especiais alem de acentos (ex: cedilha isolada, til em "sao", hifens em "guarda-po").

---

### Falsos Positivos e Falsos Negativos

#### Mecanismo de Busca Atual

O sistema usa um **keyword matching engine baseado em regex** com as seguintes camadas:

1. **Normalizacao** (NFD + lowercase + remove punctuation)
2. **Exclusion check** (fail-fast): se qualquer exclusion keyword faz match, o item e rejeitado
3. **Tier scoring** (quando habilitado por setor):
   - Tier A (1.0): termos inequivocos ("uniforme", "fardamento")
   - Tier B (0.7): termos fortes ("camiseta", "jaleco")
   - Tier C (0.3): termos ambiguos ("camisa", "bota", "meia")
   - Threshold: 0.6 (default)
4. **Binary mode** (fallback): qualquer keyword match aprova

O matching usa `\b` (word boundary) com `re.escape()` para evitar regex injection.

#### Fontes de Falsos Positivos

| Fonte | Severidade | Exemplo | Mitigacao Existente |
|-------|-----------|---------|---------------------|
| Termos ambiguos (Tier C) | Media | "bota" (calcado vs. "bota de concreto") | Exclusion set + Tier C peso 0.3 |
| "EPI" sozinho | Media | EPI de construcao civil (nao vestuario) | `EPI_ONLY_KEYWORDS` check -- rejeita se APENAS EPI fez match |
| "confeccao" generico | Media | "confeccao de placas" | 30+ exclusion entries para "confeccao de X" |
| Termos customizados sem exclusoes | **Alta** | Usuario busca "camisa" e recebe "confeccao de camisa de forca" | **Exclusoes sao DESATIVADAS para termos customizados** (main.py linha 543) |
| Valor zero/null nao filtrado | Media | Items com valor R$ 0.00 passam (Registro de Precos) | Intencional, mas pode incluir items irrelevantes |

**Achado critico:** Quando o usuario usa termos customizados (`termos_busca`), as exclusion keywords do setor sao **completamente ignoradas** (main.py linha 543: `exclusions=sector.exclusions if not custom_terms else set()`). Isso pode gerar falsos positivos significativos para termos ambiguos.

#### Fontes de Falsos Negativos

| Fonte | Severidade | Exemplo | Mitigacao Existente |
|-------|-----------|---------|---------------------|
| Stemming ausente | **Alta** | "uniformizar" nao casa com "uniforme" | Nenhuma -- nao ha stemming/lemmatizacao |
| Sinonimos nao cobertos | Media | Termos regionais ou novos nao listados | Expansao manual dos keyword sets |
| Threshold muito alto | Baixa | Item com apenas 1 keyword Tier C (score 0.3 < 0.6) e rejeitado | Intencional para reduzir ruido |
| MAX_PAGES_PER_COMBO = 10 | **Alta** | Combos com 500+ items (ex: SP + Pregao Eletronico = 228 paginas) sao truncados em 10 paginas (500 items) | Truncation tracking no frontend (SourceBadges) |
| Exclusoes excessivas | Baixa | "colete reflexivo para guarda" pode ser excluido por "colete balistico" proximity | Improvavel -- exclusoes usam frases especificas |

**Achado critico sobre stemming:** O portugues brasileiro tem conjugacoes e derivacoes ricas. Sem stemming:

- "uniformizado" nao casa com "uniforme"
- "vestindo" nao casa com "vestimenta"
- "confeccionado" nao casa com "confeccao"
- "alimentar" nao casa com "alimento"

O keyword set tenta compensar isso listando variantes manualmente (singular/plural, masculino/feminino), mas nao cobre formas verbais ou derivacoes.

#### Busca por Termos Customizados: Qualidade

Quando o usuario usa termos livres:

1. **Parsing**: Suporta aspas para multi-word (`"camisa polo"`) e virgulas (main.py `parse_multi_word_terms`)
2. **Matching**: Usa `normalize_text()` + word boundary regex (mesmo mecanismo dos setores)
3. **Sem exclusoes**: Exclusion keywords do setor sao ignoradas (risco de falsos positivos)
4. **Sem tiers**: Todos os termos sao tratados como Tier A (binary match, score 1.0)
5. **Sem LLM keyword extraction**: Os termos do usuario sao usados literalmente -- nao ha expansao semantica via LLM

#### Recomendacoes para Qualidade de Busca

| # | Recomendacao | Esforco | Impacto |
|---|-------------|---------|---------|
| 1 | Implementar stemming PT-BR (RSLP ou Snowball) no `normalize_text()` | 8h | Alto -- elimina falsos negativos de flexao |
| 2 | Manter exclusoes parciais para termos customizados (usar exclusoes do setor selecionado) | 2h | Alto -- reduz falsos positivos |
| 3 | Remover variantes duplicadas de acentos nos keyword sets | 4h | Baixo -- limpeza de manutencao |
| 4 | Adicionar fuzzy matching (distancia de Levenshtein) como fallback para typos | 8h | Medio |
| 5 | Considerar full-text search (Elasticsearch/Typesense) para escala | 40h | Alto (longo prazo) |

> **PENDENTE:** Revisao do @data-engineer
> 1. Confirmar se o PNCP API realmente ignora `palavraChave` em todos os endpoints ou apenas no `/contratacoes/publicacao`
> 2. Avaliar viabilidade de stemming RSLP vs. Snowball para portugues
> 3. Definir se exclusoes devem ser aplicadas para termos customizados (trade-off: menos falsos positivos vs. possivelmente excluir items legitimos que o usuario buscou intencionalmente)

---

### Buscas de Grande Volume (30+ dias, 27 UFs)

#### Analise do Pipeline para Cenarios Extremos

O sistema tem protecoes contra buscas de grande volume, mas varios cenarios extremos podem causar degradacao significativa.

##### Parametros de Controle Existentes

| Parametro | Valor | Definido em |
|-----------|-------|-------------|
| `MAX_DATE_RANGE_DAYS` | 90 dias | config.py (env var) |
| `MAX_PAGES_PER_COMBO` | 10 paginas (500 items) | config.py |
| `MODALIDADE_REDUCTION_UF_THRESHOLD` | 10 UFs | config.py |
| `DEFAULT_MODALIDADES` | 7 modalidades | config.py |
| `PRIORITY_MODALIDADES` | 3 modalidades (>10 UFs) | config.py |
| PNCP timeout (base) | 300s | config.py SOURCES_CONFIG |
| PNCP timeout scaling | +15s por UF alem de 5 | orchestrator.py linha 220 |
| Semaphore concurrency | 3 fetches simultaneos | async_pncp_client.py linha 417 |
| Rate limit adaptativo | 0.3s base, ate 2.0s | async_pncp_client.py |
| Circuit breaker | 3 timeouts consecutivos | async_pncp_client.py |
| Frontend poll timeout | 10 minutos | useSearchJob.ts |
| Max concurrent jobs | 10 | job_store.py |

##### Cenario 1: 30 dias, 3 UFs (caso tipico)

- Date chunks: 1 chunk (30 dias <= 30 max)
- Modalidades: 7 (DEFAULT_MODALIDADES)
- Tasks: 3 UFs x 7 modalidades = **21 combos**
- Max pages: `min(10, max(2, 600/21))` = **10 paginas**
- Volume maximo teorico: 21 x 500 = **10,500 items raw**
- Tempo estimado: 60-180s (tipico)
- **Status:** Funcional, dentro dos limites

##### Cenario 2: 60 dias, 10 UFs (grande)

- Date chunks: 2 chunks (60 dias / 30 = 2)
- Modalidades: 7 (10 UFs = threshold exato, usa DEFAULT)
- Tasks por chunk: 10 x 7 = **70 combos**
- Max pages: `min(10, max(2, 600/70))` = **8 paginas**
- Volume maximo teorico: 2 chunks x 70 x 400 = **56,000 items raw**
- Tempo estimado: 180-400s
- Timeout PNCP: 300 + (10-5)*15 = **375s**
- **Status:** Provavelmente funcional, mas proximo dos limites

##### Cenario 3: 90 dias, 27 UFs (extremo)

- Date chunks: 3 chunks (90 dias / 30 = 3)
- Modalidades: 3 (PRIORITY_MODALIDADES -- 27 > 10 threshold)
- Tasks por chunk: 27 x 3 = **81 combos**
- Max pages: `min(10, max(2, 600/81))` = **7 paginas**
- Volume maximo teorico: 3 x 81 x 350 = **85,050 items raw**
- Tempo estimado: 300-600s+ (potencialmente excedendo timeouts)
- Timeout PNCP: 300 + (27-5)*15 = **630s** (10.5 min > frontend timeout de 10 min)
- Semaphore: 3 concurrent com 81 combos = **27 batches sequenciais** por chunk
- **Status:** **CRITICO** -- frontend timeout de 10 min provavelmente insuficiente

##### Problemas Identificados para Grande Volume

| Problema | Severidade | Detalhe |
|----------|-----------|---------|
| **Frontend timeout vs PNCP timeout** | Critica | Frontend desiste em 10 min; PNCP timeout para 27 UFs = 10.5 min. Race condition. |
| **Redis memory para items** | Alta | 85K items serializados como JSON unico em `job:{id}:items`. Estimativa: ~50-100MB por job. |
| **Paginacao carrega tudo** | Alta | `get_items_page()` desserializa TODOS os items e faz slice em Python (DB-009). Para 85K items: ~100MB por request de paginacao. |
| **Excel para 85K items** | Alta | `create_excel()` em ThreadPoolExecutor com 85K rows. Memoria e tempo significativos. |
| **LLM com 50 items max** | Baixa | LLM trunca em 50 items -- nao escala, mas tambem nao quebra. |
| **Dedup com 85K items** | Media | MD5 hashing + dict lookup para 85K items. Funcional mas memoria significativa. |
| **Filter batch CPU** | Media | Regex matching em 85K items. ThreadPoolExecutor(4) limita paralelismo. |
| **Nenhum feedback de progresso granular** | Media | Frontend mostra stages (fetching/filtering/summarizing) mas nao progresso dentro de cada stage para grandes volumes. |

##### Comportamento do Frontend para Resultados Grandes

| Aspecto | Implementacao | Problema para Grande Volume |
|---------|---------------|---------------------------|
| Polling | Exponential backoff (1s -> 15s max) | Adequado |
| Progress display | 5 stages + UF grid + carousel | Adequado |
| Timeout | 10 min hard limit | Insuficiente para 27 UFs |
| Result display | Paginado (20 items/page) | Adequado |
| Items fetch | Client-side fetch por pagina | Cada fetch desserializa tudo no backend (DB-009) |
| Error on timeout | "A consulta excedeu o tempo limite" | Mensagem generica -- sem sugestao de reduzir escopo |
| Cancel button | Presente durante loading | Adequado |
| Tab notifications | Browser notification on complete | Adequado para buscas longas |

##### Recomendacoes para Grande Volume

| # | Recomendacao | Esforco | Prioridade |
|---|-------------|---------|------------|
| 1 | **Alinhar frontend timeout com backend timeout**: calcular timeout dinamico baseado em UFs * dias | 4h | P1 |
| 2 | **Advertencia proativa no frontend**: ao selecionar >15 UFs ou >30 dias, mostrar estimativa de tempo e sugerir reduzir escopo | 4h | P1 |
| 3 | **Redis LIST para items** (DB-009): RPUSH items individuais, LRANGE para paginacao, elimina desserializacao completa | 4h | P2 |
| 4 | **Progresso granular de fetching**: callback de progresso por UF + combo, nao apenas por source | 8h | P3 |
| 5 | **Streaming Excel**: gerar Excel em chunks ou limitar items no Excel | 4h | P3 |
| 6 | **Limitar UFs no frontend**: hard cap de 15 UFs ou aviso forte acima de 10 | 2h | P2 |
| 7 | **Pre-computed data pipeline**: ingestion batch agendada do PNCP, eliminando busca on-demand | 40h | P4 (longo prazo) |

> **PENDENTE:** Revisao do @data-engineer e @ux-expert
> 1. @data-engineer: Qual o volume real observado para buscas de 27 UFs? Ha metricas de tempo de resposta?
> 2. @data-engineer: Redis memory: qual o pico de uso observado? Ha risco de OOM?
> 3. @ux-expert: Como comunicar ao usuario que buscas de grande volume podem demorar? Barra de progresso mais granular? Estimativa de tempo restante (ja existe ETA)?
> 4. @ux-expert: Deve haver um hard cap no frontend para UFs ou date range, ou apenas um aviso?

---

## 1. Debitos de Sistema (SYS-xxx)

*Fonte: `docs/architecture/system-architecture.md` Secao 10*

### Severidade Critica

#### SYS-001: SQLite em Filesystem Efemero (Railway)

- **Impacto:** Persistencia de dados (historico de busca perdido a cada deploy)
- **Esforco:** 16h
- **Prioridade:** P1 -- Migrar para Supabase PostgreSQL

#### SYS-002: Sem Modelo de Identidade de Usuario

- **Impacto:** Seguranca e produto (API key unica compartilhada, sem user scoping)
- **Esforco:** 24h
- **Prioridade:** P1 -- Requerido antes de multi-tenant

#### SYS-003: Implementacao JWT Customizada

- **Impacto:** Seguranca (sem key rotation, sem audience/issuer, sem JWK)
- **Esforco:** 4h
- **Prioridade:** P1 -- Substituir por PyJWT

### Severidade Alta

#### SYS-004: CORS allow_headers=["*"]

- **Impacto:** Seguranca (aceita qualquer header)
- **Esforco:** 1h
- **Prioridade:** P2

#### SYS-005: Sem CSP ou HSTS Headers

- **Impacto:** Seguranca (falta Content-Security-Policy e Strict-Transport-Security)
- **Esforco:** 4h
- **Prioridade:** P2

#### SYS-006: Saved Searches Apenas em localStorage

- **Impacto:** Produto/UX (sem persistencia server-side, sem sync cross-device)
- **Esforco:** 8h
- **Prioridade:** P2

#### SYS-007: Auth Bypass em Dev Mode sem Safeguard

- **Impacto:** Seguranca (API_KEY e JWT_SECRET nao definidos = bypass silencioso)
- **Esforco:** 2h
- **Prioridade:** P2

### Severidade Media

#### SYS-008: Version String Hardcoded

- **Impacto:** Qualidade de codigo
- **Esforco:** 2h
- **Prioridade:** P3

#### SYS-009: MD5 para Dedup Keys

- **Impacto:** Qualidade de codigo (MD5 deprecated para seguranca, ok para hashing)
- **Esforco:** 1h
- **Prioridade:** P3

#### SYS-010: Sem Timeout em Chamadas OpenAI

- **Impacto:** Performance/confiabilidade (LLM call pode travar indefinidamente)
- **Esforco:** 2h
- **Prioridade:** P2

#### SYS-011: Vercel Serverless Limits para Download Proxy

- **Impacto:** Performance (BFF buffering nega streaming do backend)
- **Esforco:** 4h
- **Prioridade:** P3

#### SYS-012: 3 Data Sources Depreciadas Referenciadas

- **Impacto:** Qualidade de codigo
- **Esforco:** 2h
- **Prioridade:** P3

#### SYS-013: In-Memory JobStore como Base do RedisJobStore

- **Impacto:** Arquitetura (dual-write, acoplamento conceitual)
- **Esforco:** 8h
- **Prioridade:** P3

#### SYS-014: Filter Engine Usa Regex para Keyword Matching

- **Impacto:** Performance (~130 inclusion + ~100 exclusion patterns por item)
- **Esforco:** 8h
- **Prioridade:** P4

#### SYS-015: Sem Retry nas Chamadas BFF Proxy

- **Impacto:** Confiabilidade (network blips causam falha imediata)
- **Esforco:** 4h
- **Prioridade:** P3

#### SYS-016: React 18 com Next.js 16

- **Impacto:** Dependencias (impede React 19 features)
- **Esforco:** 8h
- **Prioridade:** P4

#### SYS-017: Module Alias Mismatch Jest vs tsconfig

- **Impacto:** Qualidade de codigo
- **Esforco:** 2h
- **Prioridade:** P3

#### SYS-018: Transparencia Health Check Sincrono

- **Impacto:** Qualidade de codigo (bloquearia event loop se chamado de async)
- **Esforco:** 2h
- **Prioridade:** P4

### Severidade Baixa

#### SYS-019: Deadline Filter Parcialmente Desabilitado

- **Impacto:** Completude de feature
- **Esforco:** 4h
- **Prioridade:** P4

#### SYS-020: Sem OpenAPI Schema para Items Response

- **Impacto:** Documentacao de API
- **Esforco:** 1h
- **Prioridade:** P4

#### SYS-021: Integration Tests Sao Placeholder

- **Impacto:** Cobertura de testes
- **Esforco:** 16h
- **Prioridade:** P4

#### SYS-022: Sem Docker Compose Profile para Frontend Dev

- **Impacto:** Developer experience
- **Esforco:** 2h
- **Prioridade:** P5

#### SYS-023: Mixpanel Carregado em Todas as Paginas

- **Impacto:** Performance
- **Esforco:** 2h
- **Prioridade:** P5

#### SYS-024: Sem Logging Estruturado no Frontend

- **Impacto:** Observabilidade
- **Esforco:** 4h
- **Prioridade:** P5

---

## 2. Debitos de Database (DB-xxx)

*Fonte: `supabase/docs/DB-AUDIT.md`*

> **PENDENTE:** Revisao do @data-engineer

### Severidade Alta

#### DB-001: Sem Isolamento Multi-User/Multi-Tenant

- **Descricao:** Tabelas `search_history` e `user_preferences` sem `user_id`. `/search-history` retorna buscas de todos os usuarios.
- **Esforco:** 4h
- **Prioridade:** P1

#### DB-002: Storage Efemero no Railway/Vercel

- **Descricao:** SQLite perde dados a cada deploy. Relacionado a SYS-001.
- **Esforco:** 16h
- **Prioridade:** P1

#### DB-003: Sem Sistema de Migracao

- **Descricao:** Schema via `CREATE TABLE IF NOT EXISTS` no startup. Sem Alembic/Supabase CLI.
- **Esforco:** 8h
- **Prioridade:** P1

### Severidade Media

#### DB-004: Tabela user_preferences Nao Utilizada

- **Descricao:** 3 metodos implementados mas nunca chamados de nenhum endpoint.
- **Esforco:** 1h
- **Prioridade:** P3

#### DB-005: API Key Comparison Vulneravel a Timing Attack

- **Descricao:** Usa `==` ao inves de `hmac.compare_digest`. Relacionado a SYS-003.
- **Esforco:** 0.5h
- **Prioridade:** P2

#### DB-006: Redis Write Amplification em Progress Updates

- **Descricao:** Cada update de progresso serializa e escreve o JSON completo do job no Redis.
- **Esforco:** 4h
- **Prioridade:** P3

#### DB-007: Sem Health Check do Database

- **Descricao:** `/health` verifica Redis mas nao SQLite.
- **Esforco:** 1h
- **Prioridade:** P3

#### DB-008: Sem Politica de Retencao/Cleanup para SQLite

- **Descricao:** `search_history` cresce sem limite (mitigado pelo storage efemero).
- **Esforco:** 2h
- **Prioridade:** P3

#### DB-009: Redis Items Desserializa Dataset Completo

- **Descricao:** `get_items_page()` carrega TODOS os items do Redis e faz slice em Python. Critico para buscas de grande volume.
- **Esforco:** 4h
- **Prioridade:** P2

### Severidade Baixa

#### DB-010: Sem Estrategia de Backup

- **Descricao:** Nenhum mecanismo de backup para SQLite ou Redis.
- **Esforco:** 4h
- **Prioridade:** P4

#### DB-011: Graceful Degradation Esconde Falhas Silenciosamente

- **Descricao:** Retorna resultados vazios quando conexao indisponivel sem metricas.
- **Esforco:** 2h
- **Prioridade:** P4

#### DB-012: Supabase Env Vars Definidas mas Nao Utilizadas

- **Descricao:** `.env.example` tem vars de Supabase sem integracao.
- **Esforco:** 0.5h
- **Prioridade:** P5

#### DB-013: Sem Transaction Boundaries para Operacoes Multi-Step

- **Descricao:** Cada metodo commit imediatamente. Aceitavel para operacoes single-statement atuais.
- **Esforco:** 2h
- **Prioridade:** P5

---

## 3. Debitos de Frontend/UX (FE-xxx)

*Fonte: `docs/frontend/frontend-spec.md` Secao 11*

> **PENDENTE:** Revisao do @ux-expert

### Severidade Alta

#### FE-001: Cores Hardcoded nos Badges de SearchSummary

- **Descricao:** `bg-blue-100`, `text-blue-800`, `bg-purple-100` etc. bypassing o sistema de temas. Ilegivel em temas sepia/paperwhite.
- **Esforco:** 1h
- **Prioridade:** P2

#### FE-005: Error Swallowing Silencioso no ItemsList

- **Descricao:** `catch {}` vazio na paginacao. Usuario ve "Carregando..." perpetuo sem feedback de erro.
- **Esforco:** 2h
- **Prioridade:** P2

### Severidade Media

#### FE-004: Componente Spinner Ausente

- **Descricao:** SVG spinner duplicado em SearchForm e SearchActions.
- **Esforco:** 1h
- **Prioridade:** P3

#### FE-006: Componente Button Ausente

- **Descricao:** Estilos de botao duplicados como inline Tailwind em 7+ componentes.
- **Esforco:** 3h
- **Prioridade:** P3

#### FE-007: ink-muted Contraste Abaixo de WCAG AA

- **Descricao:** `#5a6a7a` contra branco = ~4.1:1 (abaixo de 4.5:1 para texto normal).
- **Esforco:** 1h
- **Prioridade:** P2

#### FE-008: Link /termos Quebrado no Footer

- **Descricao:** Footer linka para `/termos` que nao existe.
- **Esforco:** 2h
- **Prioridade:** P3

#### FE-011: Teste Ausente para SourceBadges

- **Descricao:** Renderizacao condicional complexa sem teste dedicado.
- **Esforco:** 2h
- **Prioridade:** P3

### Severidade Baixa

#### FE-002: Cor Hardcoded no SourceBadges Warning

- **Descricao:** `text-amber-600` ao inves de token semantico `text-warning`.
- **Esforco:** 0.5h
- **Prioridade:** P4

#### FE-003: Dependencia UUID Desnecessaria

- **Descricao:** `uuid` v13 pode ser substituido por `crypto.randomUUID()`.
- **Esforco:** 0.5h
- **Prioridade:** P4

#### FE-009: Sem Error Fallback para Dynamic Imports

- **Descricao:** EmptyState e ItemsList sem loading/error fallback.
- **Esforco:** 1h
- **Prioridade:** P4

#### FE-010: Teste Ausente para RegionSelector

- **Descricao:** Sem teste direto (testado indiretamente via UfSelector).
- **Esforco:** 1.5h
- **Prioridade:** P4

#### FE-012: Tema Dim com Cobertura Incompleta de Tokens

- **Descricao:** Dim quase identico a Dark (apenas canvas e surface-0 diferem).
- **Esforco:** 2h
- **Prioridade:** P4

#### FE-013: SavedSearchesDropdown Retorna null Durante Loading

- **Descricao:** Layout shift breve no header durante loading.
- **Esforco:** 0.5h
- **Prioridade:** P5

#### FE-014: page.tsx e Monolitico Client Component

- **Descricao:** 209 linhas de "use client" gerenciando todo o estado.
- **Esforco:** 4h
- **Prioridade:** P5

---

## 4. Matriz Preliminar de Priorizacao

| ID | Debito | Area | Severidade | Impacto | Esforco (h) | Prioridade |
|----|--------|------|-----------|---------|-------------|------------|
| SYS-002 | Sem modelo de identidade de usuario | Seguranca/Produto | Critica | Muito Alto | 24 | P1 |
| SYS-001 | SQLite em filesystem efemero | Persistencia | Critica | Muito Alto | 16 | P1 |
| DB-002 | Storage efemero Railway/Vercel | Persistencia | Alta | Muito Alto | 16 | P1 |
| DB-001 | Sem isolamento multi-user | Seguranca | Alta | Muito Alto | 4 | P1 |
| DB-003 | Sem sistema de migracao | Engenharia | Alta | Alto | 8 | P1 |
| SYS-003 | JWT customizada sem PyJWT | Seguranca | Critica | Alto | 4 | P1 |
| SYS-007 | Auth bypass sem safeguard | Seguranca | Alta | Alto | 2 | P2 |
| DB-005 | Timing attack em API key | Seguranca | Media | Medio | 0.5 | P2 |
| SYS-004 | CORS allow_headers=["*"] | Seguranca | Alta | Alto | 1 | P2 |
| SYS-005 | Sem CSP/HSTS headers | Seguranca | Alta | Alto | 4 | P2 |
| SYS-010 | Sem timeout OpenAI | Confiabilidade | Media | Alto | 2 | P2 |
| FE-005 | Error swallowing em ItemsList | UX | Alta | Alto | 2 | P2 |
| FE-001 | Cores hardcoded em badges | UX/Temas | Alta | Alto | 1 | P2 |
| FE-007 | ink-muted contraste < WCAG AA | Acessibilidade | Media | Alto | 1 | P2 |
| DB-009 | Redis items desserializa tudo | Performance | Media | Alto (grande volume) | 4 | P2 |
| SYS-006 | Saved searches so localStorage | Produto/UX | Alta | Medio | 8 | P2 |
| SYS-015 | Sem retry nas chamadas BFF | Confiabilidade | Media | Medio | 4 | P3 |
| SYS-008 | Version hardcoded | Codigo | Media | Baixo | 2 | P3 |
| SYS-009 | MD5 para dedup keys | Codigo | Media | Baixo | 1 | P3 |
| SYS-011 | Vercel limits para download | Performance | Media | Medio | 4 | P3 |
| SYS-012 | Sources depreciadas referenciadas | Codigo | Media | Baixo | 2 | P3 |
| SYS-013 | In-memory JobStore base class | Arquitetura | Media | Medio | 8 | P3 |
| SYS-017 | Module alias mismatch | Codigo | Media | Baixo | 2 | P3 |
| DB-004 | user_preferences nao utilizada | Codigo | Media | Baixo | 1 | P3 |
| DB-006 | Redis write amplification | Performance | Media | Medio | 4 | P3 |
| DB-007 | Sem health check DB | Observabilidade | Media | Medio | 1 | P3 |
| DB-008 | Sem cleanup/retencao SQLite | Operacoes | Media | Baixo | 2 | P3 |
| FE-004 | Spinner component ausente | Codigo/UX | Media | Baixo | 1 | P3 |
| FE-006 | Button component ausente | Codigo/UX | Media | Medio | 3 | P3 |
| FE-008 | Link /termos quebrado | UX | Media | Medio | 2 | P3 |
| FE-011 | Teste SourceBadges ausente | Testes | Media | Medio | 2 | P3 |
| SYS-014 | Filter engine usa regex | Performance | Media | Medio (grande volume) | 8 | P4 |
| SYS-016 | React 18 com Next.js 16 | Dependencias | Media | Medio | 8 | P4 |
| SYS-018 | Transparencia health check sync | Codigo | Media | Baixo | 2 | P4 |
| SYS-019 | Deadline filter parcial | Feature | Baixa | Baixo | 4 | P4 |
| SYS-020 | Sem OpenAPI para items | Documentacao | Baixa | Baixo | 1 | P4 |
| SYS-021 | Integration tests placeholder | Testes | Baixa | Medio | 16 | P4 |
| DB-010 | Sem backup strategy | Operacoes | Baixa | Medio | 4 | P4 |
| DB-011 | Degradation esconde falhas | Observabilidade | Baixa | Baixo | 2 | P4 |
| FE-002 | Cor hardcoded SourceBadges | UX/Temas | Baixa | Baixo | 0.5 | P4 |
| FE-003 | UUID dependency desnecessaria | Bundle | Baixa | Baixo | 0.5 | P4 |
| FE-009 | Sem fallback dynamic imports | UX | Baixa | Baixo | 1 | P4 |
| FE-010 | Teste RegionSelector ausente | Testes | Baixa | Baixo | 1.5 | P4 |
| FE-012 | Tema Dim incompleto | UX/Temas | Baixa | Baixo | 2 | P4 |
| SYS-022 | Sem Docker profile frontend dev | DX | Baixa | Baixo | 2 | P5 |
| SYS-023 | Mixpanel em todas as paginas | Performance | Baixa | Baixo | 2 | P5 |
| SYS-024 | Sem logging estruturado frontend | Observabilidade | Baixa | Baixo | 4 | P5 |
| DB-012 | Supabase env vars nao usadas | Codigo | Baixa | Baixo | 0.5 | P5 |
| DB-013 | Sem transaction boundaries | Engenharia | Baixa | Baixo | 2 | P5 |
| FE-013 | SavedSearches null durante load | UX | Baixa | Baixo | 0.5 | P5 |
| FE-014 | page.tsx monolitico | Arquitetura | Baixa | Baixo | 4 | P5 |

**Nota sobre sobreposicao:** SYS-001 e DB-002 descrevem o mesmo problema (SQLite efemero). Uma migracao para Supabase (estimada em 24-32h pela auditoria DB) resolveria simultaneamente: SYS-001, DB-001, DB-002, DB-003, DB-008, DB-010, DB-012.

---

## 5. Perguntas para Especialistas

### Para @data-engineer

1. **Acentuacao:** A funcao `normalize_text()` cobre todos os edge cases do portugues brasileiro? Ha caracteres especificos (cedilha isolada, til em "ao", hifens em "guarda-po") que podem falhar no NFD decomposition?

2. **Search quality -- stemming:** Qual a viabilidade de implementar stemming RSLP (Removedor de Sufixos da Lingua Portuguesa) ou Snowball no `normalize_text()`? Qual o impacto no tempo de filtragem para 85K items?

3. **Search quality -- exclusoes para termos customizados:** Atualmente exclusoes sao desativadas para termos customizados. Isso e intencional? Deve haver ao menos um subset de exclusoes universais (ex: "uniformizacao de procedimento")?

4. **PNCP API palavraChave:** O parametro e realmente ignorado em todos os endpoints? Ha algum endpoint alternativo que suporte filtragem server-side?

5. **Grande volume -- Redis:** Qual o pico de memoria Redis observado em producao? Buscas de 27 UFs x 90 dias estao causando problemas?

6. **Grande volume -- DB-009:** A migracao para Redis LIST (RPUSH/LRANGE) e viavel? Qual seria o impacto na serializacao/desserializacao de items individuais?

7. **Supabase migration:** Qual o plano de migracao preferido? Supabase Python client vs asyncpg direto? Alembic vs Supabase CLI para migracoes?

### Para @ux-expert

1. **Grande volume -- feedback:** O LoadingProgress atual (5 stages, UF grid, carousel) e suficiente para buscas de 5+ minutos? O ETA estimado e preciso para grandes volumes?

2. **Grande volume -- limites proativos:** Devemos avisar o usuario ao selecionar >10 UFs ou >30 dias? Qual a melhor abordagem UX (banner, tooltip, confirmacao modal)?

3. **Search quality -- display de resultados:** Os badges de tipo (licitacao/ata) sao confusos para usuarios? O EmptyState com filter breakdown e compreensivel?

4. **FE-005 -- erro silencioso na paginacao:** Qual o design preferido para erro de paginacao? Inline retry? Toast notification? Banner?

5. **FE-007 -- ink-muted contraste:** O valor atual de `#5a6a7a` (4.1:1) e aceitavel para metadados que nao sao conteudo primario? Ou devemos atender WCAG AA estritamente (4.5:1)?

6. **Acentuacao -- input do usuario:** O campo de busca deve normalizar acentos visualmente (ex: mostrar preview do termo normalizado)? Ou isso confundiria o usuario?

7. **FE-012 -- Tema Dim:** O tema Dim deveria ter identidade visual distinta do Dark? Ou a diferenca sutil (apenas canvas/surface) e aceitavel?

---

*Documento gerado por @architect (Atlas) com base em analise abrangente do codebase. Todos os caminhos de arquivo, numeros de versao, e detalhes arquiteturais verificados contra o codigo-fonte no commit 5e56b38d.*
