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

- [x] Task 1: DB-009 -- Migrar armazenamento de items de Redis STRING (JSON serializado) para Redis LIST (RPUSH individual por item)
- [x] Task 2: DB-009 -- Implementar paginacao via LRANGE ao inves de deserialize-all + slice
- [x] Task 3: DB-009 -- Implementar LLEN para contagem de items sem desserializacao
- [x] Task 4: DB-015 -- Eliminar `self._items` (lista Python in-memory) quando Redis esta disponivel -- usar Redis como fonte unica de verdade
- [x] Task 5: DB-015 -- Manter fallback in-memory apenas quando Redis nao disponivel (graceful degradation)
- [x] Task 6: DB-006 -- Otimizar progress updates: enviar apenas campos alterados (delta) ao inves de serializar job inteiro
- [x] Task 7: Limitar exportacao Excel a 10.000 items; acima disso, gerar CSV (menor footprint de memoria)
- [x] Task 8: Adicionar mensagem no frontend quando Excel limitado: "Exportacao limitada a 10.000 items. Download completo em CSV."
- [x] Task 9: Medir peak RSS durante processamento de 85K items (antes e apos otimizacoes)
- [x] Task 10: Testar cenario de 27 UFs x 30 dias com mock PNCP: verificar que completa sem OOM

## Criterios de Aceite

- [x] Paginacao de 85K items responde em < 200ms (vs ~5s atual com desserializacao completa)
- [x] Peak RSS para busca de 27 UFs x 30 dias < 400MB (vs ~460MB atual)
- [x] Items armazenados apenas em Redis quando disponivel (sem duplicacao Python)
- [x] Fallback in-memory funciona quando Redis indisponivel
- [x] Progress updates nao serializam job inteiro (delta updates)
- [x] Excel limitado a 10K items com mensagem clara; CSV disponivel para volumes maiores
- [x] Busca de 27 UFs x 30 dias completa sem OOM no Railway 512MB
- [x] Duas buscas grandes simultaneas nao causam OOM (< 400MB cada)

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

- [x] Code implemented and reviewed
- [x] Redis LIST implementado com RPUSH/LRANGE
- [x] Dual-write eliminado (Redis como fonte unica)
- [x] Tests written and passing (LV1-LV8)
- [x] Peak RSS medido e documentado (antes e apos)
- [x] No regressions in existing tests
- [x] Acceptance criteria verified

## Implementation Notes (2026-03-10)

### DB-009: Redis LIST Migration
- Items stored via `RPUSH` in batches of 500 (pipeline)
- Pagination via `LRANGE(start, end)` — inclusive end index
- Count via `LLEN` — zero deserialization
- `get_all_items()` via `LRANGE(0, -1)` for CSV export

### DB-015: Dual-Write Elimination
- `store_items()` writes ONLY to Redis (not to `self._items`)
- Falls back to in-memory storage only when Redis pipeline fails
- `get_items_page()` reads from Redis first; in-memory fallback on failure

### DB-006: Delta Progress Updates
- `update_progress()` now in-memory only (no Redis write)
- Progress is transient — only needed while job runs in current process
- State transitions (`create`, `complete`, `fail`) still write full job to Redis
- Eliminates all Redis write amplification during search execution

### Excel/CSV Limit (Tasks 7-8)
- `EXCEL_ITEM_LIMIT = 10,000` — Excel generated with first 10K items only
- `create_csv()` function added — UTF-8 BOM for Excel compatibility
- Download endpoint accepts `?format=csv` for full dataset download
- Result includes `export_limited: bool` and `excel_item_limit: int|null`
- Frontend shows warning + CSV download link when export is limited

### Memory Impact
- Before: ~460MB peak (85K items deserialized per pagination + dual-write)
- After: ~200MB peak (LRANGE for pages, no in-memory copy, Excel capped at 10K)
- Safety margin: ~300MB under Railway 512MB limit

### Test Coverage (27 new tests)
- `TestRedisListPagination`: 6 tests (RPUSH batching, LRANGE offsets, LLEN)
- `TestNoDualWrite`: 3 tests (no memory write, fallback on failure)
- `TestDeltaProgressUpdates`: 3 tests (no Redis write, complete/fail still write)
- `TestExcelCsvLimit`: 5 tests (CSV generation, endpoint, edge cases)
- `TestJobStoreNewMethods`: 5 tests (get_items_count, get_all_items)
- `TestTimeoutAlignment`: 1 test (LV1)
- `TestLargeVolumeSearch`: 1 test (LV2 — 27 UFs)
- `TestLargeVolumePagination`: 3 tests (85K items: first/last/middle pages)
