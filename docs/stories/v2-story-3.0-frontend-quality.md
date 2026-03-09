# [v2] Story 3.0: Frontend Quality & Accessibility
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Este sprint aborda debitos de qualidade e acessibilidade do frontend identificados pela avaliacao v2.0. Relacao com v1.0:

- **UXD-005 (ARIA listbox):** Novo na v2.0 -- v1.0 TD-047 cobria ARIA menu pattern em dropdowns; v2.0 identifica SavedSearchesDropdown especificamente sem listbox semantics
- **UXD-011 (FOUC script):** Novo na v2.0 como debt separado -- duplicacao de logica entre script inline e ThemeProvider
- **UXD-012 (offline indicator):** Novo na v2.0
- **UXD-016 (LoadingProgress):** Novo na v2.0 -- componente de 450+ linhas precisa decomposicao
- **UXD-019 (carouselData cores):** Parcialmente coberto por v1.0 TD-044; v2.0 identifica o componente especifico
- **UXD-002 (loading setores):** Novo na v2.0 como debt especifico; v1.0 TD-040 era similar mas no backlog
- **UXD-003/004/006/008/010/013/017 (varios baixos):** Todos novos na v2.0

### Objetivo

Completar compliance WCAG AA, melhorar qualidade de UX com indicadores de rede e loading states, decompor componente LoadingProgress de 450+ linhas, e resolver debitos visuais de baixa prioridade que afetam a percepcao de qualidade do produto.

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| UXD-005 | SavedSearchesDropdown sem ARIA listbox | Media | 3h | NOVO (v1 TD-047 cobria menu pattern, nao listbox) |
| UXD-011 | Script FOUC duplica logica do ThemeProvider | Media | 3h | NOVO |
| UXD-012 | Sem indicador offline/rede | Media | 4h | NOVO |
| UXD-016 | LoadingProgress 450+ linhas | Media | 6h | NOVO |
| UXD-019 | carouselData com cores Tailwind hardcoded | Media | 2h | REMANESCENTE (v1 TD-044 parcialmente cobria) |
| UXD-002 | Sem loading state para fetch de setores | Media | 1h | NOVO (v1 TD-040 similar, era backlog) |
| UXD-003 | Sem pagina 404 | Baixa | 1h | NOVO |
| UXD-004 | Sem atalho de teclado para busca | Baixa | 1h | NOVO |
| UXD-006 | SaveSearchDialog sem `<dialog>` nativo | Baixa | 2h | NOVO (v1 TD-008 focava em focus trap) |
| UXD-008 | Mixpanel importado incondicionalmente (~40KB) | Baixa | 1h | NOVO |
| UXD-010 | ThemeProvider imperativo (30+ props CSS) | Baixa | 8h | NOVO |
| UXD-013 | Footer sem conteudo significativo | Baixa | 1h | NOVO |
| UXD-014 | SourceBadges sem acentos portugues | Baixa | 0.25h | NOVO (coberto em v2-story-0.0) |
| UXD-017 | Setores fallback hardcoded | Baixa | 1h | NOVO |
| UXD-020 | Sem `noValidate` no form | Baixa | 0.1h | NOVO (coberto em v2-story-0.0) |

**Nota:** UXD-014 e UXD-020 ja estao cobertos na v2-story-0.0 (quick wins). Se resolvidos la, remover deste sprint.

### Tasks

#### Acessibilidade Media Prioridade

- [ ] Task 1: UXD-005 -- Refatorar SavedSearchesDropdown para usar semantica `role="listbox"` com `role="option"` nos itens. Adicionar navegacao por setas e selecao com Enter.
- [ ] Task 2: UXD-002 -- Adicionar loading state (spinner ou skeleton) ao dropdown de setores durante fetch. Utilizar FALLBACK_SETORES como placeholder ate dados carregarem.

#### Qualidade Visual e UX

- [ ] Task 3: UXD-011 -- Alinhar script inline de prevencao de FOUC com ThemeProvider. Expandir script para cobrir tokens de surface/border (Sepia/Paperwhite). Nota: pode ser parcialmente resolvido por TD-M10 em v2-story-2.0.
- [ ] Task 4: UXD-012 -- Implementar indicador de status de rede. Detectar `navigator.onLine` + evento `offline`/`online`. Mostrar banner dismissivel quando offline, com mensagem contextual em vez de erro generico.
- [ ] Task 5: UXD-019 -- Substituir cores Tailwind hardcoded em carouselData por tokens de tema semanticos (mesma abordagem de UXD-018 em v2-story-0.0).

#### Decomposicao de Componente

- [ ] Task 6: UXD-016 -- Decompor LoadingProgress (450+ linhas) em sub-componentes: ProgressBar, StageList, UfGrid, Carousel, Skeleton.
- [ ] Task 7: UXD-016 -- Cada sub-componente deve ter teste unitario co-localizado.
- [ ] Task 8: UXD-016 -- LoadingProgress principal deve orquestrar sub-componentes (< 100 linhas).

#### Itens de Baixa Prioridade

- [ ] Task 9: UXD-003 -- Criar `not-found.tsx` para pagina 404 (app tem rota unica, mas necessario para URLs invalidas).
- [ ] Task 10: UXD-004 -- Adicionar atalho de teclado para submeter busca (ex: Ctrl+Enter ou dedicar Enter no input para submissao em vez de criacao de token).
- [ ] Task 11: UXD-006 -- Migrar SaveSearchDialog de `div[role="dialog"]` para elemento `<dialog>` nativo. Manter focus trap existente.
- [ ] Task 12: UXD-008 -- Converter import do Mixpanel para dynamic import (`next/dynamic` ou `import()` lazy). Reducao estimada: ~40KB do bundle inicial.
- [ ] Task 13: UXD-010 -- Refatorar ThemeProvider de abordagem imperativa (30+ CSS custom properties) para sistema baseado em CSS variables com cascata. Nota: esforco alto (8h), pode ser dividido em sub-tasks.
- [ ] Task 14: UXD-013 -- Adicionar links uteis ao footer (ex: termos de uso, contato, versao do sistema).
- [ ] Task 15: UXD-017 -- Mover setores fallback para arquivo de configuracao ou buscar de endpoint mesmo quando offline.

### Criterios de Aceite

- [ ] SavedSearchesDropdown implementa semantica listbox completa (verificar com axe-core)
- [ ] Dropdown de setores mostra loading state durante fetch
- [ ] Script FOUC alinhado com ThemeProvider (sem flash em Sepia/Paperwhite)
- [ ] Indicador offline visivel quando rede cai (testar com DevTools Network offline)
- [ ] carouselData renderiza corretamente em todos os 5 temas
- [ ] LoadingProgress decomposto: nenhum sub-componente > 200 linhas
- [ ] Pagina 404 existe e renderiza para URLs invalidas
- [ ] Mixpanel carregado via dynamic import (verificar bundle analyzer)
- [ ] Cada sub-componente de LoadingProgress tem teste unitario

### Testes Requeridos

- [ ] Teste unitario: SavedSearchesDropdown com ARIA listbox -- navegacao por setas, selecao
- [ ] Teste unitario: loading state do dropdown de setores
- [ ] Teste unitario: cada sub-componente de LoadingProgress
- [ ] Teste unitario: indicador offline -- detecta mudanca de estado de rede
- [ ] Teste E2E: navegacao para URL invalida mostra 404
- [ ] Teste E2E: axe-core -- zero violacoes criticas/serias
- [ ] Teste visual: carouselData em todos os 5 temas
- [ ] Teste de bundle: Mixpanel nao presente no bundle inicial (verificar com `next build --analyze`)

### Estimativa

- Horas: 15-25 (excluindo itens ja cobertos em v2-story-0.0)
- Custo: R$ 2.250-3.750 (estimativa a R$ 150/h)
- Sprint: 3-4 (1-2 semanas, paralelo com v2-story-4.0 e v2-story-2.0)

### Dependencias

- Depende de: v2-story-1.0 (security/critical), parcialmente v2-story-2.0 (TD-M10 pode resolver base de UXD-011)
- Bloqueia: v2-story-5.0 (polish; UXD-010 ThemeProvider -> UXD-011 FOUC)
- Interna: UXD-011 depende de UXD-010 (refatoracao ThemeProvider facilita alinhamento FOUC)
- Interna: UXD-020 depende de UXD-007 (ambos em v2-story-0.0)

### Definition of Done

- [ ] Codigo implementado
- [ ] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado
