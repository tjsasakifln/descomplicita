# [v2] Story 0.0: Quick Wins
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Sprint de quick wins para construir momentum antes dos sprints de maior esforco. Varios destes itens existiam na v1.0 em formas ligeiramente diferentes:

- **UXD-014 (acentos):** Parcialmente coberto por v1.0 TD-044 (hardcoded colors em SourceBadges) mas o problema de acentuacao e novo na v2.0
- **UXD-007/020 (form):** Novo na v2.0 -- sem `<form>` element nao existia na avaliacao v1.0
- **TD-H05 (CORS headers):** v1.0 TD-001 cobria CORS origins wildcard (resolvido); v2.0 TD-H05 foca em `allow_headers=*` que permaneceu
- **TD-M04 (LLM timeout):** Novo na v2.0 -- cadeia de cascading failure identificada pela primeira vez
- **UXD-018/021 (cores hardcoded):** v1.0 TD-044 cobria parcialmente; v2.0 identifica componentes especificos adicionais
- **TD-L04, TD-M11, UXD-009, UXD-022:** Novos na v2.0

### Objetivo

Resolver 10 itens de baixo esforco e alto impacto relativo em 1-2 dias, incluindo correcoes de acessibilidade triviais, higiene de codigo, e prevencao de cascading failure no thread pool.

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| UXD-014 | SourceBadges sem acentos portugues | Baixa | 0.25h | NOVO (v1 TD-044 cobria cores, nao acentos) |
| UXD-020 | Sem `noValidate` no form | Baixa | 0.1h | NOVO |
| UXD-007 | Sem elemento `<form>` envolvendo formulario | Media | 2h | NOVO |
| UXD-022 | Sem `aria-required` em campos obrigatorios | Media | 0.5h | NOVO |
| UXD-009 | Sem confirmacao page unload durante busca | Baixa | 0.5h | NOVO |
| TD-L04 | test_placeholder.py existe | Baixa | 5min | NOVO |
| TD-M11 | Versao hardcoded em multiplos locais | Media | 1h | NOVO |
| TD-H05 | CORS allow_headers=* excessivamente permissivo | Media | 1h | REMANESCENTE (v1 TD-001 resolveu origins; headers permaneceu) |
| UXD-018 | Cores Tailwind hardcoded em SearchSummary | Media | 1h | REMANESCENTE (v1 TD-044 parcialmente cobria) |
| UXD-021 | Cores amber hardcoded em SourceBadges/carouselData | Baixa | 0.5h | NOVO |
| TD-M04 | Sem timeout para chamadas LLM | Alta | 2h | NOVO (cadeia cascading failure identificada na v2.0) |

### Tasks

- [ ] Task 1: UXD-014 -- Corrigir `combinacoes` para `combinacoes` (com acento) em SourceBadges
- [ ] Task 2: UXD-007 -- Envolver formulario de busca em elemento `<form>` com submit handler adequado
- [ ] Task 3: UXD-020 -- Adicionar `noValidate` ao `<form>` para evitar conflito com validacao customizada (depende de Task 2)
- [ ] Task 4: UXD-022 -- Adicionar `aria-required="true"` a todos os campos obrigatorios do formulario
- [ ] Task 5: UXD-009 -- Adicionar `e.preventDefault(); e.returnValue = ""` ao listener `beforeunload` durante busca ativa
- [ ] Task 6: TD-L04 -- Remover `test_placeholder.py` do backend
- [ ] Task 7: TD-M11 -- Criar single source of truth para versao (ex: `__version__` em `__init__.py` ou `pyproject.toml`) e atualizar `main.py`
- [ ] Task 8: TD-H05 -- Restringir `allow_headers` no CORS para `["Content-Type", "X-API-Key", "X-Request-ID"]`
- [ ] Task 9: UXD-018 -- Substituir `bg-blue-100`, `bg-purple-100` em SearchSummary por tokens de tema semanticos
- [ ] Task 10: UXD-021 -- Substituir `text-amber-600 dark:text-amber-400` em SourceBadges/carouselData por tokens de tema
- [ ] Task 11: TD-M04 -- Adicionar timeout explicito ao cliente OpenAI (ex: `timeout=30` no constructor)

### Criterios de Aceite

- [ ] Todos os acentos corretos em SourceBadges (verificar com grep)
- [ ] Formulario de busca usa elemento `<form>` nativo com `noValidate`
- [ ] Campos obrigatorios tem `aria-required="true"`
- [ ] `test_placeholder.py` nao existe mais no repositorio
- [ ] Versao definida em um unico local, sem duplicacao
- [ ] CORS `allow_headers` limitado a headers necessarios
- [ ] Cores de SearchSummary e SourceBadges respondem a temas Sepia/Paperwhite
- [ ] Chamadas LLM tem timeout configurado (verificar com teste unitario)
- [ ] `beforeunload` previne navegacao durante busca ativa

### Testes Requeridos

- [ ] Teste unitario: timeout do cliente OpenAI funciona (mock timeout)
- [ ] Teste unitario: CORS rejeita headers nao-autorizados
- [ ] Teste visual: SearchSummary e SourceBadges renderizam corretamente em todos os 5 temas
- [ ] Teste de regressao: busca end-to-end continua funcionando apos todas as mudancas
- [ ] Verificar com grep: nenhum `bg-blue-100`, `bg-purple-100`, `text-amber-600` hardcoded restante

### Estimativa

- Horas: 8-9
- Custo: R$ 1.200-1.350 (estimativa a R$ 150/h)
- Sprint: 1 (Quick Wins, 1-2 dias)

### Dependencias

- Depende de: Nenhuma (primeiro sprint)
- Bloqueia: v2-story-1.0 (idealmente quick wins sao resolvidos antes de atacar criticos)
- Interna: UXD-020 depende de UXD-007 (precisa do `<form>` antes de adicionar `noValidate`)

### Definition of Done

- [ ] Codigo implementado
- [ ] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado
