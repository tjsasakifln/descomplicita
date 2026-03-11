# v3-story-3.1: Large Volume UX Feedback

## Contexto

Quando o usuario seleciona 27 UFs + 30+ dias, nao ha nenhum feedback visual proativo. A busca pode levar 4-7 minutos, mas o usuario nao recebe advertencia antes de iniciar. Durante a execucao, ETAs sao hardcoded ("~15s", "~10s", "~5s") independente do volume -- para 85K items, filtering leva 30-60s, nao 15s. A progress bar fica presa em 60% durante filtering, e o usuario percebe o sistema como travado.

Adicionalmente, a mensagem de timeout e generica sem orientacao especifica, e nao ha indicador de frescor de dados ("dados consultados em...").

## Objetivo

Implementar advertencia proativa para buscas de grande volume, ETAs dinamicos baseados em volume real, e feedback enriquecido de timeout com orientacao especifica.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| FE-016 | Sem advertencia proativa para buscas de grande volume | Alta | 3h |
| FE-017 | Mensagem de timeout generica sem orientacao | Media | 2h |
| -- | ETA dinamico baseado em volume de items | Media | 2h |
| -- | Indicador de frescor de dados ("dados consultados em") | Baixa | 1h |
| -- | Progress bar interpolation durante filtering | Baixa | 2h |

## Tasks

- [x] Task 1: FE-016 -- Implementar banner inline (nao modal) quando usuario seleciona >10 UFs OU date range >30 dias
- [x] Task 2: FE-016 -- Banner mostra: estimativa de tempo, numero de combinacoes UF x modalidade, sugestao de reducao ("Considere selecionar menos estados para resultados mais rapidos")
- [x] Task 3: FE-016 -- Banner usa tokens semanticos de cor (nao hardcoded), visivel em todos os 5 temas
- [x] Task 4: FE-017 -- Enriquecer mensagem de timeout: incluir quantos UFs e dias foram selecionados, sugestao especifica ("Tente com menos de 10 estados ou periodo de 30 dias")
- [x] Task 5: ETA dinamico -- Calcular ETAs pos-fetching baseados em volume real: multiplicar estimativas base por `ceil(itemsFetched / 5000)`
- [x] Task 6: Progress bar -- Interpolar movimento da barra entre 60-90% durante fase de filtering (proporcional ao volume)
- [x] Task 7: Indicador de frescor -- Exibir "Dados consultados em {timestamp}" no header dos resultados
- [x] Task 8: Cancel button -- Verificar que cancel realmente para o job no backend (nao apenas o polling frontend)

## Criterios de Aceite

- [x] Banner de advertencia aparece ao selecionar >10 UFs
- [x] Banner de advertencia aparece ao selecionar date range >30 dias
- [x] Banner mostra estimativa de tempo realista (baseada em formula do backend)
- [x] Banner visivel e legivel em todos os 5 temas (light, paperwhite, sepia, dim, dark)
- [x] Mensagem de timeout inclui contexto: "Voce selecionou X estados e Y dias"
- [x] ETAs pos-fetching proporcionais ao volume real (nao hardcoded)
- [x] Progress bar nao fica presa em 60% durante filtering de grandes volumes
- [x] Timestamp "Dados consultados em..." visivel nos resultados
- [x] ETA accuracy < 30% erro absoluto medio para buscas > 1000 items

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| UX4 | Warning banner aparece quando >10 UFs selecionados | Component | P2 |
| UX5 | Warning banner aparece quando date range >30 dias | Component | P2 |
| EA7 | Large volume warning banner triggers at >10 UFs and >30 days | Component | P2 |
| LV5 | ETA accuracy: ETA proporcional ao tempo real para 10K+ items | Component | P3 |
| LV6 | Progress bar moves from 60-75% during filtering, not stuck | Component | P3 |
| LV7 | Cancel button: backend job realmente cancelado | Integration | P3 |
| UX8 | Banner legivel em todos os 5 temas | Visual | P2 |
| -- | Timeout message inclui contexto de UFs e dias | Component | P3 |
| -- | Timestamp de frescor exibido nos resultados | Component | P4 |

## Estimativa

- Horas: 10h
- Complexidade: Media

## Dependencias

- Nenhuma bloqueante direta. Recomenda-se coordenar com v3-story-1.1 (timeout alignment) para UX consistente.

## Definition of Done

- [x] Code implemented and reviewed
- [x] Tests written and passing
- [x] Banner funcional em todos os 5 temas
- [x] No regressions in existing tests
- [x] Acceptance criteria verified
