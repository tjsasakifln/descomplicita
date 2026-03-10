# v3-story-1.0: PNCP palavraChave Parameter Investigation Spike

**Status: CONCLUIDA (Resultado: NEGATIVO)**
**Data de conclusao: 2026-03-09**

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

- [x] Task 1: Fazer chamada manual a API PNCP com parametro `palavraChave` usando termos reais ("uniforme", "confeccao") e comparar volume retornado com e sem o parametro
- [x] Task 2: Documentar comportamento: o parametro filtra? Quais campos pesquisa (objeto, descricao)? Respeita acentos? Usa AND ou OR para multiplos termos?
- [x] ~~Task 3: Se funcionar -- integrar parametro no PNCP client (pncp_client.py), enviando os termos de busca como palavraChave~~ **N/A -- parametro nao funciona**
- [x] ~~Task 4: Medir reducao efetiva de volume com 3 cenarios~~ **N/A -- parametro nao funciona**
- [x] Task 5: Documentar decisao: se funcionar, atualizar prioridades de DB-009, DB-015, e timeout alignment no epic v3

## Resultado do Spike

### Conclusao: NEGATIVO -- `palavraChave` e silenciosamente ignorado pela API PNCP

O parametro `palavraChave` **NAO filtra resultados** no endpoint `/api/consulta/v1/contratacoes/publicacao`. A API aceita o parametro sem erro mas retorna exatamente os mesmos resultados com ou sem ele.

### Evidencias (2026-03-09)

**Endpoint testado:** `https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao`
**Periodo:** 2026-03-02 a 2026-03-08 (7 dias)
**UF:** SP | **Modalidade:** 6 (Pregao Eletronico)

| Teste | Parametro | totalRegistros | Resultado |
|-------|-----------|---------------|-----------|
| Baseline (sem keyword) | -- | **1532** | Baseline |
| `palavraChave=uniforme` | palavraChave | **1532** | Identico ao baseline |
| `palavraChave=confeccao` | palavraChave | **1532** | Identico ao baseline |
| `palavraChave=xyzzy_nonexistent_term_12345` | palavraChave | **1532** | Identico -- ate nonsense retorna tudo |
| `palavra_chave=uniforme` | palavra_chave | **1532** | Variante snake_case ignorada |
| `q=uniforme` | q | **1532** | Parametro generico ignorado |
| `palavraChave=confeccao` (c/ acento) | palavraChave | **1532** | Versao acentuada tambem ignorada |

**Conclusao definitiva:** Todos os 7 testes retornaram exatamente 1532 registros. O parametro e silenciosamente ignorado pela API -- nao gera erro, nao filtra, nao altera a resposta de forma alguma. Tres variantes de nome de parametro (camelCase, snake_case, "q") foram testadas sem sucesso.

### Respostas as perguntas do spike:

1. **O parametro filtra?** NAO. E silenciosamente ignorado.
2. **Quais campos pesquisa?** N/A -- nao pesquisa nenhum campo.
3. **Respeita acentos?** N/A -- nao processa o parametro de forma alguma.
4. **Usa AND ou OR?** N/A.

### Script e dados

- Script: `backend/scripts/spike_palavrachave.py`
- Resultados: `backend/scripts/spike_palavrachave_results.json`

## Impacto na Prioridade

Com o resultado NEGATIVO:

- **DB-009 (Redis LIST para 85K items):** Prioridade MANTIDA como planejada em v3-story-2.2
- **DB-015 (dual-write de memoria):** Prioridade MANTIDA como planejada em v3-story-2.2
- **Timeout alignment:** Prioridade MANTIDA como planejada em v3-story-1.1
- **Plano original de sprints 2-3:** CONFIRMADO sem alteracoes

A filtragem client-side via `filter_batch()` permanece como unica opcao para reducao de volume. As otimizacoes de memoria e performance planejadas em v3-story-2.2 continuam sendo essenciais.

## Criterios de Aceite

- [x] Documentacao clara do comportamento do parametro palavraChave com evidencias (requests/responses)
- [x] ~~Se funcionar: parametro integrado no client PNCP com testes unitarios~~ **N/A**
- [x] ~~Se funcionar: medicao de reducao de volume documentada com dados reais~~ **N/A**
- [x] Se nao funcionar: documentacao do motivo e confirmacao de que o plano original de sprints 2-3 permanece inalterado
- [x] Decisao registrada no epic sobre impacto nas prioridades

## Testes Requeridos

| ID | Teste | Tipo | Prioridade | Status |
|----|-------|------|-----------|--------|
| EA3 | PNCP palavraChave teste com endpoint real | Manual | P1 | EXECUTADO -- negativo |
| FP8 | PNCP palavraChave parameter: manual API test to determine if it filters results | Manual | P1 | EXECUTADO -- negativo |

## Estimativa

- Horas: 4h (2h spike + 2h integracao se positivo)
- Horas reais: ~2h (apenas spike, sem integracao)
- Complexidade: Simples

## Dependencias

- Nenhuma. Esta story deve ser executada PRIMEIRO pois seus resultados impactam prioridades de v3-story-2.2.

## Definition of Done

- [x] Spike executado com resultados documentados
- [x] ~~Se positivo: codigo implementado e testado~~ **N/A -- resultado negativo**
- [x] ~~Se positivo: epic v3 atualizado com novas prioridades~~ **N/A -- resultado negativo**
- [x] Se negativo: plano original confirmado
- [x] Resultados compartilhados com time
