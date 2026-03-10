# v3-story-2.2: Large Volume Search Optimization

## Contexto

Buscas de grande volume (27 UFs x 30+ dias) processam ate 85.000 items, consumindo ~460MB de pico de memoria (Railway free tier: 512MB). O principal gargalo e que `get_items_page()` desserializa TODOS os items do Redis para fazer slice em Python, custando ~50-100MB por request de paginacao. Adicionalmente, items sao armazenados tanto em Python (`self._items`) quanto em Redis, duplicando ~120MB desnecessariamente.

A resolucao de DB-009 (Redis LIST com RPUSH/LRANGE) e DB-015 (eliminacao de dual-write) reduz o pico de memoria de ~460MB para ~200MB, tornando buscas de grande volume viaveis no Railway.

IMPORTANTE: Esta story DEPENDE de v3-story-1.1 (FE-005 error handling) estar completa. Sem error handling na paginacao, regressoes de DB-009 seriam silenciosamente engolidas.

## Objetivo

Otimizar armazenamento e paginacao de items para buscas de grande volume, eliminando desserializacao completa e dual-write, reduzindo pico de memoria para < 400MB.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| DB-009 | Redis items desserializa dataset completo (get_items_page carrega TODOS e faz slice) | Alta | 6h |
| DB-015 | In-memory + Redis dual-write sem invalidacao | Media | 3h |
| DB-006 | Redis write amplification em progress updates | Media | 4h |
| -- | Limitar Excel a 10K items; acima, oferecer CSV | Media | 4h |

## Tasks

- [ ] Task 1: DB-009 -- Migrar armazenamento de items de Redis STRING (JSON serializado) para Redis LIST (RPUSH individual por item)
- [ ] Task 2: DB-009 -- Implementar paginacao via LRANGE ao inves de deserialize-all + slice
- [ ] Task 3: DB-009 -- Implementar LLEN para contagem de items sem desserializacao
- [ ] Task 4: DB-015 -- Eliminar `self._items` (lista Python in-memory) quando Redis esta disponivel -- usar Redis como fonte unica de verdade
- [ ] Task 5: DB-015 -- Manter fallback in-memory apenas quando Redis nao disponivel (graceful degradation)
- [ ] Task 6: DB-006 -- Otimizar progress updates: enviar apenas campos alterados (delta) ao inves de serializar job inteiro
- [ ] Task 7: Limitar exportacao Excel a 10.000 items; acima disso, gerar CSV (menor footprint de memoria)
- [ ] Task 8: Adicionar mensagem no frontend quando Excel limitado: "Exportacao limitada a 10.000 items. Download completo em CSV."
- [ ] Task 9: Medir peak RSS durante processamento de 85K items (antes e apos otimizacoes)
- [ ] Task 10: Testar cenario de 27 UFs x 30 dias com mock PNCP: verificar que completa sem OOM

## Criterios de Aceite

- [ ] Paginacao de 85K items responde em < 200ms (vs ~5s atual com desserializacao completa)
- [ ] Peak RSS para busca de 27 UFs x 30 dias < 400MB (vs ~460MB atual)
- [ ] Items armazenados apenas em Redis quando disponivel (sem duplicacao Python)
- [ ] Fallback in-memory funciona quando Redis indisponivel
- [ ] Progress updates nao serializam job inteiro (delta updates)
- [ ] Excel limitado a 10K items com mensagem clara; CSV disponivel para volumes maiores
- [ ] Busca de 27 UFs x 30 dias completa sem OOM no Railway 512MB
- [ ] Duas buscas grandes simultaneas nao causam OOM (< 400MB cada)

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| LV1 | Frontend timeout >= backend timeout para qualquer combinacao UF/dias | Property-based | P1 |
| LV2 | Busca simulada 27 UFs com mock PNCP: completa sem timeout | Integration | P1 |
| LV3 | Medicao de memoria durante processamento de 85K items | Performance | P2 |
| LV4 | Redis LIST paginacao: LRANGE retorna pagina correta para 85K items | Unit | P2 |
| LV7 | Cancel button: backend job realmente cancelado | Integration | P3 |
| LV8 | 2 buscas simultaneas de 27 UFs: sem OOM ou resource starvation | Stress | P3 |
| -- | Fallback in-memory quando Redis indisponivel | Integration | P2 |
| -- | Excel limitado a 10K items; CSV para volumes maiores | Integration | P3 |

## Estimativa

- Horas: 17h
- Complexidade: Complexa

## Dependencias

- **REQUER** v3-story-1.1 (FE-005 error handling na paginacao) -- sem error handling, regressoes seriam silenciosas
- Resultados de v3-story-1.0 (spike palavraChave) podem REDUZIR urgencia se parametro funcionar (volume reduzido 10-20x)

## Definition of Done

- [ ] Code implemented and reviewed
- [ ] Redis LIST implementado com RPUSH/LRANGE
- [ ] Dual-write eliminado (Redis como fonte unica)
- [ ] Tests written and passing (LV1-LV8)
- [ ] Peak RSS medido e documentado (antes e apos)
- [ ] No regressions in existing tests
- [ ] Acceptance criteria verified
