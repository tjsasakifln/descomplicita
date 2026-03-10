# v3-story-1.0: PNCP palavraChave Parameter Investigation Spike

## Contexto

A API PNCP aceita um parametro `palavraChave` que nunca e enviado pelo client Descomplicita. Toda filtragem e feita client-side apos download de dados brutos. Se este parametro funcionar, o volume de dados retornados pela API pode ser reduzido em 10-20x, eliminando ou reduzindo drasticamente a urgencia de DB-009 (desserializacao de 85K items), DB-015 (dual-write de memoria), e o problema de timeout race condition.

Este e potencialmente a acao de maior ROI do inventario inteiro de debitos tecnicos. Todos os revisores (@architect, @data-engineer, @qa) recomendam que seja feito primeiro.

## Objetivo

Determinar se o parametro `palavraChave` da API PNCP filtra resultados server-side, e se funcionar, integra-lo ao client PNCP para reduzir volume de dados.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| -- | PNCP palavraChave nao enviado ao PNCP | Alta (indireta) | 2h spike |
| -- | Integracao do parametro se spike positivo | -- | 2h |

## Tasks

- [ ] Task 1: Fazer chamada manual a API PNCP com parametro `palavraChave` usando termos reais ("uniforme", "confeccao") e comparar volume retornado com e sem o parametro
- [ ] Task 2: Documentar comportamento: o parametro filtra? Quais campos pesquisa (objeto, descricao)? Respeita acentos? Usa AND ou OR para multiplos termos?
- [ ] Task 3: Se funcionar -- integrar parametro no PNCP client (pncp_client.py), enviando os termos de busca como palavraChave
- [ ] Task 4: Medir reducao efetiva de volume com 3 cenarios: (a) 3 UFs x 30 dias, (b) 10 UFs x 30 dias, (c) 27 UFs x 30 dias
- [ ] Task 5: Documentar decisao: se funcionar, atualizar prioridades de DB-009, DB-015, e timeout alignment no epic v3

## Criterios de Aceite

- [ ] Documentacao clara do comportamento do parametro palavraChave com evidencias (requests/responses)
- [ ] Se funcionar: parametro integrado no client PNCP com testes unitarios
- [ ] Se funcionar: medicao de reducao de volume documentada com dados reais
- [ ] Se nao funcionar: documentacao do motivo e confirmacao de que o plano original de sprints 2-3 permanece inalterado
- [ ] Decisao registrada no epic sobre impacto nas prioridades

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| EA3 | PNCP palavraChave teste com endpoint real | Manual | P1 |
| FP8 | PNCP palavraChave parameter: manual API test to determine if it filters results | Manual | P1 |

## Estimativa

- Horas: 4h (2h spike + 2h integracao se positivo)
- Complexidade: Simples

## Dependencias

- Nenhuma. Esta story deve ser executada PRIMEIRO pois seus resultados impactam prioridades de v3-story-2.2.

## Definition of Done

- [ ] Spike executado com resultados documentados
- [ ] Se positivo: codigo implementado e testado
- [ ] Se positivo: epic v3 atualizado com novas prioridades
- [ ] Se negativo: plano original confirmado
- [ ] Resultados compartilhados com time
