# EPIC: Eliminacao de Timeout na Busca — Search Performance & Resilience

**Epic ID:** SP-001
**Titulo:** Search Pipeline Performance — Da Busca Sincrona ao Job Assincrono
**Versao:** 1.0
**Status:** READY TO START
**Data Criada:** March 6, 2026

---

## 1. Objetivo do Epic

Eliminar o erro "A consulta excedeu o tempo limite (5 min)" transformando o pipeline de busca sincrono em arquitetura assincrona com cache, reduzindo latencia percebida de **40-200s** para **< 5s** (com resultados progressivos).

**Resultado Final:** Usuario nunca mais ve timeout. Busca com qualquer combinacao de UFs e periodo funciona com feedback de progresso em tempo real.

---

## 2. Descricao Completa

### Situacao Atual

O pipeline de busca e **100% sincrono**: frontend faz POST para `/api/buscar`, que proxeia para o backend, que busca no PNCP, filtra, gera resumo LLM, gera Excel, e so entao retorna. Um AbortController de 5 minutos no frontend e o unico timeout.

**Cadeia de Latencia Atual:**

| Etapa | Tempo | Multiplicador |
|-------|-------|---------------|
| PNCP Fetch | 30-120s+ | UFs x 5 modalidades x paginas |
| Retry backoff (se falha) | ate 62s | 2+4+8+16+32s exponencial |
| Rate limiting | 1-5s | 100ms entre requests |
| LLM Summary | 5-15s | fixo |
| Excel Generation | 1-3s | fixo |
| **Total real** | **40-200s+** | **explode com 3+ UFs** |

**Por que estoura com 3+ UFs:**

```
3 UFs x 5 modalidades = 15 tasks -> 6 workers -> 3 batches
Cada batch: 15s timeout + possivel retry (62s)
Cenario pessimista: 3 x (15+62) = 231s so de fetch
+ LLM (15s) + Excel (3s) = 249s -> margem de apenas 51s
```

### Causa Raiz Arquitetural

1. **Pipeline sincrono** — frontend espera resposta completa do backend
2. **PNCP API instavel** — latencia variavel, rate limiting frequente
3. **Explosao combinatoria** — UFs x modalidades x paginas x retries
4. **Sem cache** — mesma consulta no mesmo dia refaz todos os requests
5. **Retry agressivo** — 5 retries com backoff exponencial ate 60s

### Situacao Desejada

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Timeout | 5min, estoura com 3+ UFs | Sem timeout (job assincrono) |
| Feedback ao usuario | Nenhum (tela travada) | Barra de progresso por UF |
| Latencia repetida | Igual a primeira | ~0s (cache hit) |
| Resultados parciais | Tudo ou nada | UFs prontas aparecem primeiro |
| Max workers PNCP | 6 | 12 |
| Max retries | 5 (62s backoff) | 3 (14s backoff) |

---

## 3. Escopo

### Incluso

- **Fase 1 (Quick Wins):** Otimizacao de config sem mudanca arquitetural
- **Fase 2 (Cache):** Cache de resultados PNCP com TTL de 4h
- **Fase 3 (Async Jobs):** Arquitetura assincrona com polling e progresso

### Excluso

- Migracao para banco de dados (Supabase/Redis externo)
- Streaming via WebSocket (avaliar em futuro epic se polling nao for suficiente)
- Alteracoes na API do PNCP (externa, sem controle)

---

## 4. Stories

| # | Story | Pontos | Prioridade | Dependencia |
|---|-------|--------|------------|-------------|
| SP-001.1 | Quick Wins — Otimizacao de concorrencia e retry | 3 | P0 | -- |
| SP-001.2 | Cache PNCP — Resultados em memoria com TTL | 5 | P0 | -- |
| SP-001.3 | Job Assincrono — Backend async com polling | 8 | P1 | SP-001.1 |
| SP-001.4 | Progresso no Frontend — Barra de progresso e resultados parciais | 5 | P1 | SP-001.3 |
| SP-001.5 | Testes de Carga e Resiliencia — Validacao end-to-end | 3 | P2 | SP-001.3, SP-001.4 |

**Total:** 24 story points

---

## 5. Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|----------|
| Aumento de workers causa rate limiting PNCP | Alto | Monitorar 429s, fallback para 6 workers |
| Cache stale retorna dados desatualizados | Medio | TTL conservador (4h), invalidacao manual |
| Job assincrono perde resultado (crash) | Alto | Persistir estado em disco, retry do job |
| Complexidade de polling no frontend | Medio | Implementacao simples com setInterval |

---

## 6. Definition of Done (Epic)

- [ ] Todas as 5 stories completas e merged
- [ ] Zero timeouts em teste com 27 UFs + 30 dias de periodo
- [ ] Latencia percebida < 5s para buscas cacheadas
- [ ] Barra de progresso funcional no frontend
- [ ] Testes de carga validados com 10 buscas simultaneas
- [ ] Metricas de latencia documentadas (antes vs depois)
