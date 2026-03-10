# Epic: Resolucao de Debitos Tecnicos v3 -- Descomplicita

## Objetivo

Resolver os 60 debitos tecnicos identificados no Technical Debt Assessment (2026-03-09), priorizando qualidade de busca (falsos positivos/negativos), buscas de grande volume (27 UFs, 30+ dias), acentuacao, e qualidade UX. O objetivo final e levar a plataforma de estagio POC para producao com persistencia real, seguranca adequada, e qualidade de resultados mensuravel.

## Escopo

### Debitos Cobertos: 60 items (24 SYS + 16 DB + 20 FE)

| Severidade | Qtd | IDs |
|-----------|-----|-----|
| Critica | 4 | SYS-001, SYS-002, SYS-003, FE-005 |
| Alta | 12 | SYS-004..007, DB-001..003, DB-009, FE-001, FE-007, FE-015, FE-016 |
| Media | 24 | SYS-008..015, SYS-017, DB-004..007, DB-014, DB-015, FE-004, FE-006, FE-008, FE-011, FE-017, FE-019, FE-020 |
| Baixa | 20 | Restantes |

### Agrupamento por Sprint

- **Sprint 1 (Quick Wins + Investigacao):** PNCP palavraChave spike, error handling critico, quick wins de qualidade de busca
- **Sprint 2 (Fundacao):** Migracao Supabase, stemming e relevancia, otimizacao de grande volume
- **Sprint 3 (UX e Polish):** UX de resultados, UX de grande volume, acessibilidade, seguranca

## Criterios de Sucesso

| Area | Metrica | Valor Alvo |
|------|---------|------------|
| Persistencia | Dados sobrevivem a deploy | 100% apos migracao Supabase |
| Timeout | Frontend timeout >= backend timeout para todas as combinacoes | Sempre |
| Memoria | Peak RSS para busca de 27 UFs x 30 dias | < 400MB |
| FP rate (termos customizados) | Reducao de falsos positivos | >= 20% |
| FN rate (stemming) | Items adicionais com flexoes verbais | >= 10% mais items relevantes |
| Acessibilidade | WCAG AA contraste para --ink-* em todos os temas | >= 4.5:1 |
| Paginacao | Tempo de resposta para 85K items | < 200ms (vs ~5s atual) |
| Error handling | Zero catch {} vazios no frontend | 0 ocorrencias |
| UX loading | ETA accuracy para buscas > 1000 items | < 30% erro absoluto medio |

## Timeline

| Sprint | Periodo | Horas Est. | Stories |
|--------|---------|-----------|---------|
| Sprint 1 | Semanas 1-2 | ~24h | v3-story-1.0, v3-story-1.1, v3-story-1.2 |
| Sprint 2 | Semanas 3-6 | ~68h | v3-story-2.0, v3-story-2.1, v3-story-2.2 |
| Sprint 3 | Semanas 7-9 | ~40h | v3-story-3.0, v3-story-3.1, v3-story-3.2, v3-story-3.3 |
| **Total** | **~9 semanas** | **~132h** | **10 stories** |

Nota: ~123h de items P4/P5 ficam no Backlog para sprints futuros.

## Stories

| ID | Titulo | Sprint | Horas |
|----|--------|--------|-------|
| v3-story-1.0 | PNCP palavraChave Parameter Investigation Spike | 1 | 4h |
| v3-story-1.1 | Critical Error Handling & Silent Failures | 1 | 9h |
| v3-story-1.2 | Search Quality Quick Wins | 1 | 11h |
| v3-story-2.0 | Supabase Migration & User Identity | 2 | 32h |
| v3-story-2.1 | Search Quality -- Stemming & Relevance | 2 | 19h |
| v3-story-2.2 | Large Volume Search Optimization | 2 | 17h |
| v3-story-3.0 | Search Results UX Enhancement | 3 | 12h |
| v3-story-3.1 | Large Volume UX Feedback | 3 | 10h |
| v3-story-3.2 | Accessibility & Visual Polish | 3 | 10h |
| v3-story-3.3 | Security Hardening | 3 | 8h |

## Budget

| Categoria | Horas | Custo Estimado (R$150/h) |
|-----------|-------|--------------------------|
| Sprint 1 -- Quick Wins | 24h | R$ 3.600 |
| Sprint 2 -- Fundacao | 68h | R$ 10.200 |
| Sprint 3 -- UX e Polish | 40h | R$ 6.000 |
| **Total Sprints 1-3** | **132h** | **R$ 19.800** |
| Backlog (P4/P5) | ~123h | R$ 18.450 |
| **Total Completo** | **~255h** | **R$ 38.250** |

## Riscos

| Risco | Severidade | Mitigacao |
|-------|-----------|-----------|
| **PNCP palavraChave nao funciona** -- volume permanece alto, truncamento mantido | Alta | Manter plano de DB-009 (Redis LIST) + DB-015 (dual-write). Re-priorizar se spike confirmar que parametro funciona. |
| **Timeout race condition** -- frontend 10min vs backend 10.5min para 27 UFs | Critica | v3-story-1.1 alinha timeouts. Frontend timeout dinamico baseado em UFs. |
| **Memory OOM em Railway 512MB** -- busca de 85K items = ~460MB pico | Critica | v3-story-2.2 implementa Redis LIST + elimina dual-write. Reduz pico para ~200MB. |
| **Migracao Supabase afeta 7+ items** -- risco de regressao ampla | Alta | Planejar como unidade atomica em v3-story-2.0. Testes de integracao antes de merge. |
| **Stemming gera novos FP** -- over-stemming de termos PT-BR | Media | Golden test suite (v3-story-2.1) executada antes e apos. Bloquear merge se precision cair >10%. |
| **Sem baseline quantitativo de FP/FN** -- mudancas nao mensuraveis | Media | Golden test suite com 100 items criada em v3-story-1.2. |
| **FE-005 cascata com DB-009** -- catch vazio esconde erros de paginacao | Alta | Corrigir FE-005 em v3-story-1.1 ANTES de DB-009 em v3-story-2.2. |

## Dependencias entre Stories

```
v3-story-1.0 (spike) -----> Informa prioridades de v3-story-2.2
v3-story-1.1 (FE-005) ---> v3-story-2.2 (DB-009 depende de error handling)
v3-story-1.2 (golden suite) -> v3-story-2.1 (stemming precisa de baseline)
v3-story-2.0 (Supabase) ---> v3-story-3.0 (saved searches server-side depende de persistencia)
v3-story-2.1 (stemming) ----> Independente, mas validar com golden suite
v3-story-3.0 (UX) ----------> FE-015 requer backend matched_keywords (pode ser paralelo)
```

---

*Epic criado por @pm (Maxwell) em 2026-03-09. Baseado no Technical Debt Assessment v1.0 validado por @architect, @data-engineer, @ux-design-expert, e @qa.*
