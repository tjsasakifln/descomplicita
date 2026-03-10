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

- [ ] Task 1: FE-007 -- Alterar `--ink-muted` de `#5a6a7a` para `#4f5f6f` (~4.8:1 contraste) em globals.css para tema light
- [ ] Task 2: FE-007 -- Validar contraste de `--ink-muted` em TODOS os 5 temas (light, paperwhite, sepia, dim, dark) -- minimo 4.5:1
- [ ] Task 3: FE-001 -- Substituir `bg-blue-100 text-blue-800` hardcoded em SearchSummary badges por tokens semanticos CSS (--badge-bg, --badge-text)
- [ ] Task 4: FE-018 -- Corrigir heading em ItemsList.tsx linha 63: "Licitacoes Encontradas" com cedilha e til corretos
- [ ] Task 5: FE-004 -- Criar componente `<Spinner>` reutilizavel; substituir SVG spinners duplicados
- [ ] Task 6: FE-006 -- Criar componente `<Button>` com variantes (primary, secondary, ghost, danger) usando tokens semanticos
- [ ] Task 7: FE-009 -- Adicionar loading/error fallback para dynamic imports de EmptyState e ItemsList
- [ ] Task 8: FE-002 -- Substituir `text-amber-600` em SourceBadges por token semantico (--ink-warning)
- [ ] Task 9: Implementar componente `<ErrorBoundary>` generico para secoes criticas (resultados, search form) com fallback UI
- [ ] Task 10: Integrar axe-core checks na CI para prevenir regressoes de acessibilidade
- [ ] Task 11: Validar hint de acentuacao no campo de termos: "Acentos sao opcionais -- 'licitacao' e 'licitacao' retornam os mesmos resultados"

## Criterios de Aceite

- [ ] WCAG AA (>= 4.5:1) para --ink-muted em todos os 5 temas
- [ ] SearchSummary badges legiveis em todos os 5 temas (tokens semanticos)
- [ ] Heading "Licitacoes Encontradas" com acentos corretos (cedilha + til)
- [ ] Componente Spinner reutilizavel; zero SVG spinners duplicados
- [ ] Componente Button com 4 variantes; zero inconsistencias de estilo entre botoes
- [ ] Dynamic imports com loading/error fallback
- [ ] SourceBadges warning usa token semantico
- [ ] ErrorBoundary captura erros de render em secoes criticas com fallback UI
- [ ] axe-core integrado na CI (Playwright E2E)
- [ ] Hint de acentuacao visivel no campo de termos

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

- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] axe-core integrado na CI
- [ ] WCAG AA validado em todos os 5 temas
- [ ] No regressions in existing 404+ tests
- [ ] Acceptance criteria verified
