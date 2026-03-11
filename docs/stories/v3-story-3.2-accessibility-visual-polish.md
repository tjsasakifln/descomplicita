# v3-story-3.2: Accessibility & Visual Polish

## Contexto

O frontend tem problemas de acessibilidade e consistencia visual: `--ink-muted` (#5a6a7a) tem contraste 4.1:1 contra branco (abaixo do WCAG AA minimo de 4.5:1), badges de SearchSummary usam cores Tailwind hardcoded que nao respondem aos temas paperwhite/sepia/dim, e o heading "Licitacoes Encontradas" esta sem acentos (cedilha e til).

Adicionalmente, ha componentes reutilizaveis ausentes (Spinner, Button) que causam drift de estilos, e falta uma estrategia de Error Boundary para erros de render.

## Objetivo

Alcancar conformidade WCAG AA em todos os temas, corrigir inconsistencias visuais, criar componentes reutilizaveis, e estabelecer protecao contra erros de render.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| FE-007 | ink-muted contraste abaixo de WCAG AA (4.1:1 < 4.5:1) | Alta | 1h |
| FE-001 | Cores hardcoded nos badges de SearchSummary | Alta | 1h |
| FE-018 | ItemsList heading sem acentos ("Licitacoes" sem cedilha/til) | Baixa | 0.25h |
| FE-004 | Componente Spinner ausente (SVG duplicado em 2+ componentes) | Media | 1h |
| FE-006 | Componente Button ausente (drift entre variantes) | Media | 3h |
| FE-009 | Sem error fallback para dynamic imports | Baixa | 1h |
| FE-002 | Cor hardcoded no SourceBadges warning (text-amber-600) | Baixa | 0.5h |
| -- | Error Boundary para secoes criticas (resultados, search form) | Media | 3h |

## Tasks

- [x] Task 1: FE-007 -- Alterar `--ink-muted` de `#5a6a7a` para `#4f5f6f` (~4.8:1 contraste) em globals.css para tema light
- [x] Task 2: FE-007 -- Validar contraste de `--ink-muted` em TODOS os 5 temas (light, paperwhite, sepia, dim, dark) -- minimo 4.5:1
- [x] Task 3: FE-001 -- Substituir `bg-blue-100 text-blue-800` hardcoded em SearchSummary badges por tokens semanticos CSS (--badge-bg, --badge-text)
- [x] Task 4: FE-018 -- Corrigir heading em ItemsList.tsx linha 63: "Licitacoes Encontradas" com cedilha e til corretos
- [x] Task 5: FE-004 -- Criar componente `<Spinner>` reutilizavel; substituir SVG spinners duplicados
- [x] Task 6: FE-006 -- Criar componente `<Button>` com variantes (primary, secondary, ghost, danger) usando tokens semanticos
- [x] Task 7: FE-009 -- Adicionar loading/error fallback para dynamic imports de EmptyState e ItemsList
- [x] Task 8: FE-002 -- Substituir `text-amber-600` em SourceBadges por token semantico (--ink-warning)
- [x] Task 9: Implementar componente `<ErrorBoundary>` generico para secoes criticas (resultados, search form) com fallback UI
- [x] Task 10: Integrar axe-core checks na CI para prevenir regressoes de acessibilidade
- [x] Task 11: Validar hint de acentuacao no campo de termos: "Acentos sao opcionais -- 'licitacao' e 'licitacao' retornam os mesmos resultados"

## Criterios de Aceite

- [x] WCAG AA (>= 4.5:1) para --ink-muted em todos os 5 temas
- [x] SearchSummary badges legiveis em todos os 5 temas (tokens semanticos)
- [x] Heading "Licitacoes Encontradas" com acentos corretos (cedilha + til)
- [x] Componente Spinner reutilizavel; zero SVG spinners duplicados
- [x] Componente Button com 4 variantes; zero inconsistencias de estilo entre botoes
- [x] Dynamic imports com loading/error fallback
- [x] SourceBadges warning usa token semantico
- [x] ErrorBoundary captura erros de render em secoes criticas com fallback UI
- [x] axe-core integrado na CI (Playwright E2E)
- [x] Hint de acentuacao visivel no campo de termos

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| UX9 | ink-muted contraste: WCAG AA (4.5:1) em tema light apos fix | Accessibility | P2 |
| RT3 | Contrast ratio validation para --ink-muted em todos os temas | Unit | P2 |
| RT4 | SearchSummary badges usam tokens semanticos, nao cores hardcoded | Component | P2 |
| UX7 | Heading usa "Licitacoes" com acentos corretos | Component | P4 |
| UX8 | Badges legiveis em todos os 5 temas | Visual | P2 |
| RT2 | axe-core accessibility check na CI (todos os temas) | E2E | P2 |
| A8 | Frontend: chips exibem texto acentuado corretamente | Component | P4 |
| -- | Spinner component renderiza corretamente | Component | P3 |
| -- | Button component: 4 variantes renderizam corretamente | Component | P3 |
| -- | ErrorBoundary captura erros e exibe fallback | Component | P3 |

## Estimativa

- Horas: 10h
- Complexidade: Media

## Dependencias

- Nenhuma bloqueante. Pode rodar em paralelo com outras stories do Sprint 3.

## Definition of Done

- [x] Code implemented and reviewed
- [x] Tests written and passing
- [x] axe-core integrado na CI
- [x] WCAG AA validado em todos os 5 temas
- [x] No regressions in existing 404+ tests
- [x] Acceptance criteria verified
