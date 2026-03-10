# Database & Search Specialist Review

**Reviewer:** @data-engineer (Delphi)
**Date:** 2026-03-09
**Scope:** All DB-xxx debt items, search quality (acentuacao, false positives/negatives), large volume scenarios
**Source Commit:** 5e56b38d

---

## Gate Status: VALIDATED

The Technical Debt DRAFT is accurate and well-researched. All DB-xxx items are confirmed with minor severity adjustments and hour refinements. Three new debt items are added based on deep code review. The search quality analysis is particularly thorough -- the architect's findings on accent handling and exclusion bypass are correct.

---

## Debitos Validados

| ID | Debito | Severidade Original | Severidade Revisada | Horas Orig | Horas Rev | Prioridade | Notas |
|----|--------|---------------------|---------------------|------------|-----------|------------|-------|
| DB-001 | Sem isolamento multi-user | Alta | **Alta** (confirmada) | 4h | 4h | P1 | Confirmado: `database.py` `get_recent_searches()` nao tem WHERE user_id. Endpoint `/search-history` retorna tudo. |
| DB-002 | Storage efemero Railway/Vercel | Alta | **Alta** (confirmada) | 16h | 16h | P1 | Confirmado: `database.py` header cita "ephemeral storage is acceptable for POC". Sobrepoe com SYS-001. |
| DB-003 | Sem sistema de migracao | Alta | **Alta** (confirmada) | 8h | 6h | P1 | Schema via `CREATE TABLE IF NOT EXISTS` no startup. Reducao para 6h se usar Supabase CLI (que gera migrations automaticamente). Se usar Alembic, manter 8h. |
| DB-004 | user_preferences nao utilizada | Media | **Media** (confirmada) | 1h | 1h | P3 | Confirmado: 3 metodos (`set_preference`, `get_preference`, `get_all_preferences`) nunca chamados. Decisao: manter tabela para uso futuro com preferences endpoint, ou remover dead code. |
| DB-005 | Timing attack em API key | Media | **Media** (confirmada) | 0.5h | 0.5h | P2 | Confirmado em `middleware/auth.py` linha 71: `if request_key == api_key`. Fix trivial: `hmac.compare_digest(request_key.encode(), api_key.encode())`. Nota: a comparacao em `main.py` linha 317 (`request_key != api_key`) no endpoint `/auth/token` tambem e vulneravel -- sao 2 pontos, nao 1. |
| DB-006 | Redis write amplification | Media | **Media** (confirmada) | 4h | 4h | P3 | Confirmado em `stores/redis_job_store.py`: `update_progress()` chama `self._redis_set(job)` que serializa o job inteiro via `_serialize_job()`. Durante fetching, cada `on_progress` callback dispara uma escrita completa. |
| DB-007 | Sem health check DB | Media | **Media** (confirmada) | 1h | 1h | P3 | Confirmado: `/health` endpoint (main.py linha 270-286) verifica apenas Redis. SQLite nao e verificado. |
| DB-008 | Sem cleanup/retencao SQLite | Media | **Baixa** (rebaixada) | 2h | 2h | P3 | Rebaixamento: o storage e efemero (DB-002), entao dados sao limpos a cada deploy. Torna-se relevante apenas apos migracao para Supabase. |
| DB-009 | Redis items desserializa tudo | Media | **Alta** (elevada) | 4h | 6h | P2 | Confirmado em `redis_job_store.py` linhas 209-233: `get_items_page()` faz `json.loads(raw)` do array completo e depois slice. Para 85K items, estima-se ~50-100MB de alocacao por request de paginacao. Elevado para Alta pela analise de grande volume. Horas aumentadas para 6h porque a migracao para Redis LIST requer mudanca no `store_items()` (RPUSH individual) e no `get_items_page()` (LRANGE + JSON parse individual), alem de garantir atomicidade. |
| DB-010 | Sem backup strategy | Baixa | **Baixa** (confirmada) | 4h | 2h | P4 | Reducao de horas: Supabase gerencia backups. Para POC/SQLite, nao justifica investimento. |
| DB-011 | Degradation esconde falhas | Baixa | **Baixa** (confirmada) | 2h | 2h | P4 | Confirmado: `Database` retorna `[]` silenciosamente (`if not self._db: return []`). `RedisJobStore` faz `logger.warning` mas continua. |
| DB-012 | Supabase env vars nao usadas | Baixa | **Baixa** (confirmada) | 0.5h | 0.5h | P5 | Confirmado: `.env.example` tem vars, nenhum codigo referencia. |
| DB-013 | Sem transaction boundaries | Baixa | **Baixa** (confirmada) | 2h | 2h | P5 | Confirmado: cada metodo faz `await self._db.commit()`. Aceitavel para operacoes single-statement atuais. |

---

## Debitos Adicionados

### DB-014: Timing Attack no Endpoint /auth/token

- **Severidade:** Media
- **Descricao:** Alem do `middleware/auth.py` linha 71 (DB-005), o endpoint `/auth/token` em `main.py` linha 317 usa `request_key != api_key` (operador `!=`), que e igualmente vulneravel a timing attack. Sao dois pontos distintos de comparacao insegura.
- **Esforco:** 0.5h (corrigir junto com DB-005)
- **Prioridade:** P2
- **Recomendacao:** Corrigir ambos os pontos na mesma PR. Usar `hmac.compare_digest()`.

### DB-015: In-Memory + Redis Dual-Write sem Invalidacao

- **Severidade:** Media
- **Descricao:** `RedisJobStore` armazena items tanto em `self._items` (in-memory, herdado de `JobStore`) via `super().store_items()` quanto em Redis via `SETEX`. O `get_items_page()` tenta in-memory primeiro e so vai ao Redis se `total == 0`. Porem, se o processo reiniciar (deploy), o cache in-memory se perde e o fallback para Redis funciona corretamente. O problema real e que ambas as copias vivem em memoria simultaneamente -- items estao duplicados entre `self._items[job_id]` (Python list) e a copia serializada no Redis. Para 85K items, isso e ~100MB em Python + ~50MB no Redis.
- **Esforco:** 3h
- **Prioridade:** P3
- **Recomendacao:** Quando Redis estiver disponivel, nao manter copia in-memory dos items. O fallback in-memory so faz sentido quando Redis nao esta configurado. Isso reduz memoria do processo Python pela metade para grandes buscas.

### DB-016: PNCP Cache Keys sem Normalizacao de UF

- **Severidade:** Baixa
- **Descricao:** As chaves de cache PNCP usam o padrao `pncp_cache:{uf}:{modalidade}:{date}:{date}`. Se o frontend enviasse "sp" em vez de "SP", seria um cache miss desnecessario. O `BuscaRequest` faz uppercase via Pydantic (`uf.upper()` ou validacao), mas a defesa em profundidade no cache seria prudente.
- **Esforco:** 0.5h
- **Prioridade:** P5
- **Recomendacao:** Aplicar `.upper()` na chave de cache. Risco atual e baixo porque Pydantic valida.

---

## Deep Dive: Acentuacao

### normalize_text() -- Analise Completa

**Localizacao:** `filter.py` linhas 291-334

A funcao realiza NFD decomposition seguida de remocao de caracteres da categoria Unicode "Mn" (Mark, nonspacing). Esta abordagem e **correta e abrangente** para portugues brasileiro.

#### Testes de Edge Cases

| Caractere | Input | NFD Decomposition | Apos Remocao Mn | Resultado |
|-----------|-------|-------------------|-----------------|-----------|
| Cedilha (c) | "licitacao" (com cedilha) | c + combining cedilla | c | "licitacao" |
| Til (a) | "sao paulo" (com til) | a + combining tilde | a | "sao paulo" |
| Acento agudo | "agua" (com acento) | a + combining acute | a | "agua" |
| Acento circunflexo | "tres" (com circunflexo) | e + combining circumflex | e | "tres" |
| Trema (historico) | "linguica" (com trema) | u + combining diaeresis | u | "linguica" |
| Hifens | "guarda-po" | N/A (regex) | "guarda po" | Hifen removido, vira espaco |

**Achado importante sobre hifens:** A funcao `normalize_text()` remove hifens (via `re.sub(r"[^\w\s]", " ", text)`). Isso significa que "guarda-po" se torna "guarda po" (duas palavras). O keyword "guarda-po" no `KEYWORDS_UNIFORMES` tambem se torna "guarda po". Portanto, o match funciona corretamente via word boundary regex (`\bguarda\b.*\bpo\b`... nao, na verdade o regex usa `re.escape(kw_norm)` que produz `\bguarda po\b`).

**Ponto de atencao com `\b`:** O regex gerado e `\bguarda po\b`. O `\b` faz boundary no inicio de "guarda" e no final de "po". O espaco no meio e literal. Isso funciona corretamente para "aquisicao de guarda po para funcionarios" mas **nao** funcionaria se o texto original tivesse "guarda-po" sem espaco apos normalizacao... exceto que a normalizacao ja converte hifen em espaco. Portanto: **funciona corretamente.**

#### PNCP API -- Dados Pre-Normalizados?

Os dados da API PNCP vem com acentos originais do orgao publicador. O campo `objetoCompra` contem texto livre em portugues com acentuacao completa (cedilhas, acentos agudos, tils, etc.). A normalizacao e aplicada client-side em ambos os lados (texto do PNCP e keywords), portanto **nenhuma normalizacao server-side e necessaria**.

#### Variantes Duplicadas nos Keyword Sets

Contagem de variantes redundantes encontradas:

| Set | Exemplos de Duplicatas | Qtd Estimada |
|-----|----------------------|--------------|
| `KEYWORDS_UNIFORMES` | "confeccao"/"confeccao" (com cedilha), "confeccoes"/"confeccoes" | ~12 pares |
| `KEYWORDS_EXCLUSAO` | "confeccao de placa"/"confeccao de placa", "confeccao de grades"/"confeccao de grades" | ~40 pares |
| Setor alimentos keywords | "genero alimenticio"/"genero alimenticio", "refeicao"/"refeicao" | ~25 pares |
| Setor alimentos exclusions | "alimentacao de dados"/"alimentacao de dados" | ~15 pares |
| Setor informatica | "licenca de software"/"licenca de software" | ~8 pares |
| Setor medicamentos | similar pattern | ~15 pares |

**Total estimado:** ~115 entradas redundantes across all sectors.

**Impacto real:** Zero em corretude, baixo em performance (cada keyword redundante gera uma regex adicional em `match_keywords()`), medio em manutencao (risco de atualizar uma variante e esquecer a outra).

**Recomendacao revisada:** 2h (nao 4h como sugerido no DRAFT). Remover variantes com acento de todos os sets (manter apenas a versao sem acento). Documentar que `normalize_text()` garante equivalencia. Script de validacao:
```python
# Validar que nenhuma keyword com acento e necessaria
for kw in all_keywords:
    assert normalize_text(kw) == normalize_text(kw_sem_acento)
```

#### Resposta a Pergunta do Architect (#1)

> A funcao normalize_text() cobre todos os edge cases do portugues brasileiro?

**Sim.** NFD decomposition + remocao de Mn covers todas as diacriticas do portugues brasileiro: cedilha (c), til (a, o), acento agudo (a, e, i, o, u), acento circunflexo (a, e, o), acento grave (a). O unico caractere "especial" nao-diacritico relevante seria "n" espanhol, que tambem e decomposto corretamente por NFD. Nao ha edge cases que falhem.

---

## Deep Dive: Falsos Positivos e Falsos Negativos

### Exclusoes Desativadas para Termos Customizados -- CONFIRMADO

**Localizacao:** `main.py` linha 543:
```python
exclusions=sector.exclusions if not custom_terms else set(),
```

Quando `custom_terms` e truthy (usuario digitou termos de busca), as exclusoes do setor sao substituidas por `set()` (vazio). Isso significa que **nenhuma exclusao e aplicada**.

#### Exemplos Concretos de Impacto

| Termo do Usuario | Resultado Sem Exclusao | Com Exclusao Teria Sido |
|------------------|----------------------|------------------------|
| "confeccao" | Inclui "confeccao de placas de sinalizacao" | Excluido (exclusion: "confeccao de placa") |
| "camisa" | Inclui "amor a camisa" (expressao idiomatica em edital) | Excluido (exclusion: "amor a camisa") |
| "bota" | Inclui "bota de concreto" (construcao civil) | Excluido (exclusion: "bota de concreto") |
| "colete" | Inclui "colete balistico" (seguranca, nao vestuario) | Excluido (exclusion: "colete balistico") |
| "uniforme" | Inclui "uniformizacao de procedimento" (juridico) | Excluido |

**Avaliacao de risco:** ALTO. Para termos ambiguos, a taxa de falsos positivos sem exclusoes pode ser 20-40% do resultado total. Para termos inequivocos como "jaleco", o impacto e minimo.

#### Trade-off da Decisao

A decisao de desativar exclusoes para termos customizados pode ter sido **intencional** para evitar que exclusoes do setor "vestuario" rejeitem resultados legitimos quando o usuario busca em outro contexto. Por exemplo, se o usuario busca "colete balistico" intencionalmente, a exclusao de "colete balistico" do setor vestuario o impediria de encontrar resultados.

**Recomendacao:** Abordagem hibrida em 3h (nao 2h como estimado no DRAFT):
1. Manter exclusoes do setor selecionado ativas por default (2h)
2. Adicionar exclusoes "universais" que sao sempre aplicadas (ex: "uniformizacao de procedimento", "uniformizacao de entendimento") independente de ser busca customizada (0.5h)
3. Adicionar flag `bypass_exclusions=true` no request body para usuarios avancados que querem desativar exclusoes explicitamente (0.5h)

### Tiered Scoring -- Como Funciona na Pratica

O sistema de tiers esta implementado em `match_keywords()` (filter.py linhas 376-398). Analise:

| Cenario | Keywords Matched | Score | Aprovado (threshold=0.6)? |
|---------|-----------------|-------|---------------------------|
| "uniforme escolar" | Tier A: "uniforme escolar" | 1.0 | Sim |
| "camisa polo azul" | Tier B: "camisa polo" | 0.7 | Sim |
| "bota de couro" | Tier C: "bota" | 0.3 | **Nao** |
| "bota e meia" | Tier C: "bota" + "meia" | 0.3 (usa max, nao soma!) | **Nao** |
| "jaleco e luva" | Tier A: "jaleco" | 1.0 | Sim |
| "epi para servicos gerais" | Tier C: "epi" | 0.3 | **Nao** |
| "camiseta e colete" | Tier A: "camiseta" + Tier C: "colete" | 1.0 | Sim |

**Achado critico:** O scoring usa `max(score, weight)`, nao `score + weight`. Isso significa que multiplos matches de Tier C nunca ultrapassam 0.3. O threshold de 0.6 efetivamente requer pelo menos um match de Tier B (0.7) ou Tier A (1.0). Isso e **muito conservador** -- um item com "bota, meia, e avental" (3 keywords Tier C) ainda e rejeitado.

**Impacto em falsos negativos:** Items que mencionam apenas combinacoes de termos ambiguos sao sistematicamente rejeitados. Isso e provavelmente intencional para manter alta precisao, mas gera falsos negativos para licitacoes de EPIs que listam apenas "bota + meia + colete".

**Recomendacao:** Considerar scoring aditivo com cap: `score = min(1.0, sum_of_weights)`. Com 3 items Tier C (0.3+0.3+0.3=0.9), ultrapassaria o threshold. Esforco: 2h. Impacto: medio (reduz falsos negativos sem aumentar muito os falsos positivos, porque a combinacao de multiplos termos ambiguos geralmente indica relevancia).

### Stemming -- Analise de Viabilidade

**Resposta a Pergunta do Architect (#2):**

| Biblioteca | Algoritmo | Qualidade PT-BR | Performance | Dependencia |
|------------|-----------|-----------------|-------------|-------------|
| NLTK RSLPStemmer | RSLP (Removedor de Sufixos) | **Boa** -- projetado especificamente para PT | ~0.5ms/termo | nltk (~14MB) |
| Snowball (PyStemmer) | Snowball Portuguese | **Razoavel** -- generico, menos preciso que RSLP | ~0.1ms/termo | PyStemmer (~1MB) |
| spaCy pt_core_news_sm | Lematizacao (nao stemming) | **Excelente** -- verdadeira lematizacao | ~2ms/termo | spacy + modelo (~15MB) |

**Recomendacao:** RSLP via NLTK. Razoes:
1. Projetado especificamente para portugues
2. Leve o suficiente para nao impactar performance significativamente
3. Resolveria os exemplos citados: "uniformizado" -> "uniform-", "confeccionado" -> "confeccion-"

**Impacto em performance para 85K items:**
- Normalizacao atual (normalize_text): ~0.05ms/item -> ~4.25s total
- Com RSLP adicional: ~0.15ms/item -> ~12.75s total
- Delta: ~8.5s adicionais para 85K items
- Aceitavel dado que o fetch de 85K items leva 300-600s

**Esforco revisado:** 10h (nao 8h). Inclui:
- Integracao do RSLP no `normalize_text()` (2h)
- Stemming das keyword sets (pre-computado no startup) (2h)
- Testes unitarios com corpus de licitacoes reais (3h)
- Validacao de que o stemming nao gera novos falsos positivos (3h)

**Risco:** Stemming pode gerar novos falsos positivos. Exemplo: RSLP pode reduzir "material" e "materiais" ao mesmo stem, mas "material de construcao" ja tem exclusao. O risco e gerenciavel com testes.

### Outras Fontes de Falsos Positivos/Negativos

| Fonte | Tipo | Severidade | Detalhe |
|-------|------|-----------|---------|
| MAX_PAGES_PER_COMBO = 10 | FN | Alta | Combos com 500+ items sao truncados. SP + Pregao Eletronico pode ter 228 paginas (11,400 items), das quais apenas 500 sao buscados. Items relevantes apos a pagina 10 sao perdidos. |
| Valor zero/null passa | FP | Baixa | Items de "Registro de Precos" com valor R$ 0.00 passam o filtro de valor. Intencional. |
| Deadline filter parcial | FP | Baixa | `dataFimReceberPropostas` nem sempre esta presente. Quando ausente, items com deadline passada ainda aparecem (SYS-019). |
| EPI_ONLY_KEYWORDS check | FN | Baixa | Items com APENAS "epi" ou "epis" sao rejeitados. Se um EPI e genuinamente de vestuario (luva termica, avental), pode ser falso negativo. Porem: essa regra so se aplica quando NENHUM outro keyword fez match, entao o risco e baixo. |

---

## Deep Dive: Buscas de Grande Volume

### Timeout Race Condition -- CONFIRMADA

| Componente | Timeout | Fonte |
|------------|---------|-------|
| Frontend (useSearchJob.ts) | 600,000ms (10 min) | `POLL_TIMEOUT = 10 * 60 * 1000` (linha 154) |
| PNCP source timeout (base) | 300s (5 min) | `config.py` SOURCES_CONFIG |
| PNCP timeout scaling | +15s por UF alem de 5 | `orchestrator.py` linha 220 |
| PNCP timeout para 27 UFs | 300 + (27-5)*15 = **630s (10.5 min)** | Calculado |
| Transparencia timeout | 90s | `config.py` SOURCES_CONFIG |

**Cenario de falha:** Com 27 UFs, o timeout PNCP e 630s. O frontend desiste em 600s. Ha uma janela de 30 segundos onde o backend pode completar a busca com sucesso, mas o frontend ja exibiu erro de timeout ao usuario. O job continua em background e seus resultados ficam em Redis sem que o usuario saiba.

**Agravante:** O timeout do orchestrator (`asyncio.wait_for`) roda ANTES do timeout PNCP do fetch individual. O PNCP client tem adaptive rate limiting que pode aumentar o intervalo entre requests para ate 2.0s. Com 81 combos por chunk e semaforo de 3, sao 27 batches x 2.0s = 54s apenas de rate limiting, mais o tempo de fetch real.

### Redis Memory para Items -- Analise

**Calculo para cenario extremo (85K items):**

Cada item PNCP normalizado contem ~20 campos. Estimativa de tamanho JSON:
- Item medio: ~600 bytes em JSON
- 85,000 items: ~51MB em JSON string no Redis
- Python list de dicts em memoria: ~120MB (overhead de objetos Python)

**Pontos de pressao de memoria:**
1. `store_items()`: serializa 85K items para JSON (~51MB string) e armazena no Redis
2. `store_items()` tambem armazena em `self._items` in-memory (~120MB Python objects) -- DB-015
3. Cada `get_items_page()` que faz fallback para Redis: desserializa 51MB JSON para Python, faz slice, descarta o resto -- DB-009
4. `create_excel()` em ThreadPoolExecutor: itera 85K items, gera openpyxl Workbook (~200MB pico)
5. Job result JSON (sem items, sem excel): ~5KB -- OK

**Pico de memoria estimado por job de 85K items:**
- Items in-memory (self._items): ~120MB
- Excel generation: ~200MB (pico)
- Filter batch (regex matching): ~120MB (items raw) + ~20MB (regex compiled)
- **Total pico por job: ~460MB**

Com max_concurrent_jobs = 10 e mesmo 2 buscas grandes simultaneas: **~920MB** so em items e Excel.

### O que Acontece com 27 UFs x 30+ Dias na Pratica

**Cenario: 27 UFs x 30 dias**

1. Date chunks: 1 chunk (30 dias <= 30 max)
2. Modalidades: 3 (PRIORITY_MODALIDADES -- 27 > 10 threshold)
3. Tasks: 27 x 3 = 81 combos
4. Max pages: min(10, max(2, 600/81)) = 7 paginas
5. Semaphore: 3 concurrent -> 27 batches sequenciais
6. Rate limiting: 0.3s base x 81 requests minimo = 24.3s apenas de rate limiting
7. Fetch time estimado: 200-400s (dependendo do PNCP)
8. Filter time: 85K items x 230 keywords = ~5s
9. LLM: truncado em 50 items, ~5s
10. Excel: 85K items, ~30s
11. **Total estimado: 240-440s (4-7 minutos)**

**Cenario: 27 UFs x 90 dias**

1. Date chunks: 3 chunks de 30 dias
2. Tasks por chunk: 81 combos
3. Fetch time estimado: 3 x 200-400s = 600-1200s (10-20 minutos!)
4. **EXCEDE todos os timeouts.**

### Rate Limiting da API PNCP

O PNCP nao documenta rate limits oficiais, mas o client tem protecoes:
- Adaptive rate limiting: 0.3s base, dobra ate 2.0s quando respostas sao lentas
- Circuit breaker: 3 timeouts consecutivos -> pausa de 15-60s
- HTTP 429 detection: incrementa contador de rate limits

**Observacao:** Nao ha metricas persistidas sobre frequencia de rate limiting ou circuit breaker activations. Seria valioso loggar essas metricas para entender o comportamento do PNCP em producao.

### Recomendacoes Revisadas para Grande Volume

| # | Recomendacao | Esforco | Prioridade | Notas |
|---|-------------|---------|------------|-------|
| 1 | Alinhar frontend timeout com backend | 3h | P1 | Calcular timeout dinamico: `base_timeout + (num_ufs - 5) * 15s + date_chunks * 120s`. Enviar como header `X-Expected-Duration` na resposta do POST /buscar. Frontend usa esse valor como deadline. |
| 2 | Advertencia proativa no frontend | 3h | P1 | Ao selecionar >15 UFs ou >60 dias, mostrar banner com estimativa de tempo. Ao selecionar 27 UFs + >30 dias, mostrar modal de confirmacao. |
| 3 | Redis LIST para items (DB-009) | 6h | P2 | RPUSH items individuais (cada um como JSON string), LRANGE para paginacao, LLEN para contagem. Elimina desserializacao completa. |
| 4 | Eliminar dual-write in-memory (DB-015) | 3h | P3 | Quando Redis disponivel, nao chamar `super().store_items()`. Apenas Redis. |
| 5 | Streaming Excel / Excel limit | 4h | P3 | Limitar Excel a 10K items (cobrem 99% dos casos de uso). Para >10K, oferecer CSV (muito mais leve). |
| 6 | Scoring aditivo para Tier C | 2h | P3 | `score = min(1.0, sum_of_weights)` em vez de `max`. |
| 7 | Pre-computed data pipeline | 40h | P4 | Ingestion batch agendada do PNCP. Elimina buscas on-demand. Requer Supabase. |

---

## Respostas ao Architect

### Pergunta 1: normalize_text() edge cases

Respondida no Deep Dive de Acentuacao. **Nao ha edge cases que falhem.** NFD decomposition cobre todas as diacriticas do portugues brasileiro. Cedilha, til, hifens em "guarda-po" -- todos funcionam corretamente.

### Pergunta 2: Stemming RSLP vs Snowball

Respondida no Deep Dive de Falsos Positivos. **Recomendo RSLP via NLTK.** Snowball e inferior para portugues. spaCy e desnecessariamente pesado para este caso. Esforco: 10h (nao 8h). Performance: +8.5s para 85K items (aceitavel).

### Pergunta 3: Exclusoes para termos customizados

Respondida no Deep Dive de Falsos Positivos. **Recomendo abordagem hibrida:** manter exclusoes do setor ativas por default + exclusoes universais + flag `bypass_exclusions`. Esforco: 3h.

### Pergunta 4: PNCP API palavraChave

O parametro `palavraChave` **nao e passado pelo client** (verificado em `async_pncp_client.py` linhas 119-129 -- o `fetch_page()` nao inclui `palavraChave` nos params). O `SectorConfig` tem um campo `search_keywords` (e.g., `["uniforme", "fardamento", ...]`), mas este campo nao e usado em nenhum lugar do pipeline de busca. Ele aparenta ser um placeholder para uso futuro.

**Nota:** A afirmacao no DRAFT de que `palavraChave` e "silenciosamente ignorado" pela API PNCP nao pode ser confirmada por codigo -- o parametro simplesmente nunca e enviado. Seria necessario um teste manual para verificar se a API PNCP realmente ignora o parametro ou se ele filtra resultados. Se funcionar, poderia reduzir drasticamente o volume de dados buscados.

**Recomendacao:** Testar manualmente a API PNCP com `palavraChave=uniforme` vs sem o parametro. Se filtrar resultados, integrar no `fetch_page()`. Esforco: 2h para teste + 2h para integracao = 4h. Impacto potencial: MUITO ALTO (reduziria volume de 85K para potencialmente <5K items).

### Pergunta 5: Redis memory pico em producao

Nao ha metricas de producao disponiveis para responder com dados reais. A analise teorica (ver Deep Dive de Grande Volume) estima pico de ~460MB por job de 85K items. Para o tier gratuito do Railway (512MB), uma unica busca de 27 UFs x 90 dias pode causar OOM.

**Recomendacao:** Adicionar metricas de memoria (psutil) ao endpoint `/health` e ao log de cada job. Esforco: 2h.

### Pergunta 6: Redis LIST viabilidade

**Sim, e viavel.** A migracao de STRING (JSON array) para LIST (RPUSH items individuais) e direta:
- `store_items()`: Pipeline RPUSH de items individuais (cada item como JSON string individual)
- `get_items_page()`: LRANGE start end -> retorna apenas os items da pagina
- Total count: LLEN key
- TTL: EXPIRE apos o pipeline

**Vantagem:** Cada request de paginacao busca apenas 20 items (~12KB) em vez de desserializar 85K items (~51MB).

**Desvantagem:** RPUSH de 85K items individuais requer pipeline Redis. Sem pipeline, seriam 85K roundtrips. Com pipeline, e um unico roundtrip. Esforco: 6h (incluindo pipeline, testes, e fallback).

### Pergunta 7: Supabase migration path

**Recomendacao:** supabase-py (o client oficial) para operacoes CRUD simples. asyncpg direto para queries complexas ou performance-critical. Supabase CLI para migrations (nao Alembic -- Supabase CLI e mais integrado com o ecossistema Supabase e RLS).

| Aspecto | supabase-py | asyncpg |
|---------|-------------|---------|
| Facilidade | Alta | Media |
| Performance | Media | Alta |
| RLS integration | Nativa | Manual |
| Type safety | Limitada | Forte (com models) |
| Async | Sim (via httpx) | Nativo |

Para o caso de uso atual (search_history + user_preferences), supabase-py e suficiente. Se o volume crescer para >100K queries/dia, considerar asyncpg.

---

## Recomendacoes -- Ordem de Resolucao Priorizada

### Sprint 1 (Critico -- antes de producao)

| Ordem | Item | Esforco | Justificativa |
|-------|------|---------|---------------|
| 1 | DB-002 + SYS-001 (Supabase migration) | 24-32h | Resolve simultaneamente DB-001, DB-002, DB-003, DB-008, DB-010, DB-012 |
| 2 | DB-005 + DB-014 (timing attack) | 1h | Fix trivial, dois pontos de vulnerabilidade |
| 3 | Frontend timeout alignment | 3h | Previne race condition em buscas grandes |

### Sprint 2 (Alto impacto)

| Ordem | Item | Esforco | Justificativa |
|-------|------|---------|---------------|
| 4 | DB-009 (Redis LIST para items) | 6h | Elimina ~100MB de alocacao por request de paginacao |
| 5 | Exclusoes para termos customizados | 3h | Reduz 20-40% de falsos positivos em buscas customizadas |
| 6 | Remocao de variantes de acento | 2h | Cleanup de ~115 entradas redundantes |

### Sprint 3 (Melhoria de qualidade)

| Ordem | Item | Esforco | Justificativa |
|-------|------|---------|---------------|
| 7 | Stemming RSLP | 10h | Elimina classe inteira de falsos negativos (flexoes verbais) |
| 8 | DB-015 (eliminar dual-write) | 3h | Reduz memoria do processo |
| 9 | DB-006 (Redis write amplification) | 4h | Reduz writes desnecessarios |
| 10 | Teste da API PNCP palavraChave | 4h | Potencialmente o item de maior impacto (reduz volume 10-20x) |

### Backlog

| Item | Esforco | Justificativa |
|------|---------|---------------|
| Scoring aditivo Tier C | 2h | Reduz falsos negativos em items com multiplos termos ambiguos |
| DB-004 (user_preferences) | 1h | Dead code cleanup |
| DB-007 (health check DB) | 1h | Observabilidade |
| DB-011 (degradation metricas) | 2h | Observabilidade |
| DB-016 (cache key normalizacao) | 0.5h | Defesa em profundidade |
| Pre-computed pipeline | 40h | Longo prazo -- elimina buscas on-demand |
