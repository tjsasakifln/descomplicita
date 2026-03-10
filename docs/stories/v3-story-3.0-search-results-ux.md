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

- [ ] Task 1: FE-015 Backend -- Incluir `matched_keywords: string[]` e `relevance_score: float` na resposta de cada item em /api/buscar/items
- [ ] Task 2: FE-015 Frontend -- Implementar componente `<HighlightedText>` que recebe texto e array de keywords, renderiza keywords com `<mark>` tag
- [ ] Task 3: FE-015 Frontend -- Integrar HighlightedText em ItemsList para o campo `objeto`
- [ ] Task 4: FE-015 -- Garantir que highlight funciona com acentos: keyword "licitacao" (sem acento) destaca "licitacao" (com acento) no texto
- [ ] Task 5: SYS-006 -- Implementar saved searches server-side via Supabase (tabela saved_searches com user_id, query params, created_at)
- [ ] Task 6: SYS-006 -- Migrar dados existentes de localStorage para server-side no primeiro login
- [ ] Task 7: SYS-006 -- Manter localStorage como cache local para performance (sync on login)
- [ ] Task 8: FE-008 -- Criar pagina /termos com conteudo basico de termos de uso, ou redirecionar para pagina existente
- [ ] Task 9: FE-011 -- Escrever testes para SourceBadges (logica condicional complexa: truncation warning, expanded state, badge rendering)

## Criterios de Aceite

- [ ] Termos de busca destacados visualmente (cor/background) nos resultados
- [ ] Highlight funciona com variantes de acento: busca "confeccao" destaca "confeccao" (com cedilha) no texto
- [ ] matched_keywords presente na resposta da API de items
- [ ] Saved searches persistem entre sessoes e dispositivos (via Supabase)
- [ ] Dados de localStorage migrados automaticamente no primeiro login
- [ ] Link /termos funciona e exibe conteudo
- [ ] SourceBadges tem cobertura de testes adequada

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

- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Highlight funcional em todos os 5 temas
- [ ] No regressions in existing tests
- [ ] Acceptance criteria verified
