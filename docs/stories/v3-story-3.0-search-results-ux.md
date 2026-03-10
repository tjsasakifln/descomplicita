# v3-story-3.0: Search Results UX Enhancement

## Contexto

Os resultados de busca exibem o campo `objeto` como texto puro sem nenhum destaque dos termos que causaram o match. O usuario nao consegue avaliar rapidamente POR QUE um resultado foi retornado, dificultando a identificacao de falsos positivos. Adicionalmente, o campo `tipo` (licitacao/ata) nunca e renderizado nos items individuais, e as saved searches estao apenas em localStorage sem sync cross-device.

O highlight de termos requer uma mudanca no backend: incluir `matched_keywords` na resposta de items (1h backend + 4h frontend).

## Objetivo

Melhorar a experiencia de avaliacao de resultados com highlight de termos, exibicao de tipo, e persistencia server-side de buscas salvas.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| FE-015 | Sem highlight de termos de busca nos resultados | Alta | 5h (1h backend + 4h frontend) |
| SYS-006 | Saved searches apenas em localStorage | Alta | 8h |
| FE-008 | Link /termos quebrado no footer | Media | 2h |
| FE-011 | Teste ausente para SourceBadges | Media | 2h |

Nota: SYS-006 depende de v3-story-2.0 (Supabase + user identity) estar completo.

## Tasks

- [x] Task 1: FE-015 Backend -- Incluir `matched_keywords: string[]` e `relevance_score: float` na resposta de cada item em /api/buscar/items
- [x] Task 2: FE-015 Frontend -- Implementar componente `<HighlightedText>` que recebe texto e array de keywords, renderiza keywords com `<mark>` tag
- [x] Task 3: FE-015 Frontend -- Integrar HighlightedText em ItemsList para o campo `objeto`
- [x] Task 4: FE-015 -- Garantir que highlight funciona com acentos: keyword "licitacao" (sem acento) destaca "licitacao" (com acento) no texto
- [x] Task 5: SYS-006 -- Implementar saved searches server-side via Supabase (tabela saved_searches com user_id, query params, created_at)
- [x] Task 6: SYS-006 -- Migrar dados existentes de localStorage para server-side no primeiro login
- [x] Task 7: SYS-006 -- Manter localStorage como cache local para performance (sync on login)
- [x] Task 8: FE-008 -- Criar pagina /termos com conteudo basico de termos de uso, ou redirecionar para pagina existente
- [x] Task 9: FE-011 -- Escrever testes para SourceBadges (logica condicional complexa: truncation warning, expanded state, badge rendering)

## Criterios de Aceite

- [x] Termos de busca destacados visualmente (cor/background) nos resultados
- [x] Highlight funciona com variantes de acento: busca "confeccao" destaca "confeccao" (com cedilha) no texto
- [x] matched_keywords presente na resposta da API de items
- [x] Saved searches persistem entre sessoes e dispositivos (via Supabase)
- [x] Dados de localStorage migrados automaticamente no primeiro login
- [x] Link /termos funciona e exibe conteudo
- [x] SourceBadges tem cobertura de testes adequada

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| UX3 | Termos de busca destacados nos resultados (apos fix) | Component | P2 |
| EA6 | Term highlight renderiza corretamente com termos acentuados | Component | P2 |
| -- | HighlightedText: keyword sem acento destaca texto com acento | Unit | P2 |
| -- | Saved searches: CRUD server-side via Supabase | Integration | P2 |
| -- | Saved searches: migracao de localStorage funciona | Integration | P3 |
| -- | SourceBadges: truncation warning, expanded toggle, badge rendering | Component | P2 |
| -- | Link /termos retorna 200 e renderiza conteudo | E2E | P3 |

## Estimativa

- Horas: 12h (se SYS-006 incluso; 4h sem SYS-006)
- Complexidade: Media

## Dependencias

- FE-015 backend change (matched_keywords) deve ser feito ANTES do frontend highlight
- SYS-006 (saved searches server-side) REQUER v3-story-2.0 (Supabase + user identity)

## Definition of Done

- [x] Code implemented and reviewed
- [x] Tests written and passing
- [x] Highlight funcional em todos os 5 temas
- [x] No regressions in existing tests
- [x] Acceptance criteria verified
