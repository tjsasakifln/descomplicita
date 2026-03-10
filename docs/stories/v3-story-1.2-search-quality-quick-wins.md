# v3-story-1.2: Search Quality Quick Wins

## Contexto

A qualidade de busca tem dois problemas imediatos que podem ser corrigidos rapidamente: (1) exclusoes de setor desativadas para termos customizados (main.py linha 543: `exclusions=set()`), gerando 20-40% de falsos positivos, e (2) ~115 variantes duplicadas de acentos nos keyword sets que sao redundantes dado que `normalize_text()` ja normaliza ambos os lados.

Alem disso, nao existe baseline quantitativa de FP/FN. Sem medicao antes/depois, e impossivel validar que mudancas de busca (stemming, exclusoes, scoring) realmente melhoram resultados. O @qa recomenda criar um golden test suite com 100 items como pre-requisito para qualquer mudanca de qualidade.

## Objetivo

Reduzir falsos positivos em buscas customizadas, limpar keyword sets redundantes, e estabelecer baseline mensuravel de precision/recall para validar mudancas futuras.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| -- | Exclusoes desativadas para termos customizados | Alta | 3h |
| -- | Variantes duplicadas de acentos nos keyword sets (~115 entradas) | Baixa | 2h |
| -- | Golden test suite para FP/FN (50 relevant + 50 irrelevant) | -- | 4h |
| -- | Scoring aditivo para Tier C (max -> sum com cap) | Media | 2h |

## Tasks

- [ ] Task 1: Re-habilitar exclusoes de setor para termos customizados com abordagem hibrida -- aplicar exclusoes do setor mais proximo quando setor selecionado, com flag bypass opcional para usuarios avancados
- [ ] Task 2: Criar golden test suite com 50 items known-relevant (licitacoes reais de vestuario PNCP) e 50 items known-irrelevant (licitacoes de outros setores com termos ambiguos)
- [ ] Task 3: Medir precision e recall ANTES das mudancas com golden test suite (baseline)
- [ ] Task 4: Implementar scoring aditivo com cap para Tier C: `min(1.0, sum_of_weights)` em filter.py (linhas 378-398), substituindo `max(score, weight)`
- [ ] Task 5: Limpar variantes duplicadas de acentos em sectors.py -- manter apenas versao sem acento (normalize_text ja normaliza ambos os lados)
- [ ] Task 6: Criar script de deteccao de redundancia (A7) para CI -- validar que nenhum par de keywords em sectors.py tem outputs diferentes apos normalize_text()
- [ ] Task 7: Medir precision e recall APOS as mudancas com golden test suite e documentar delta

## Criterios de Aceite

- [ ] Busca com termos customizados ("confeccao") aplica exclusoes do setor quando setor selecionado
- [ ] FP rate para termos ambiguos reduz >= 20% (medido via golden test suite)
- [ ] Items com 3 termos Tier C ("bota + meia + avental" = 0.9) sao aceitos com scoring aditivo (antes: rejeitados com 0.3)
- [ ] Nenhum par de keywords em sectors.py tem normalize_text() outputs diferentes (validado por CI script)
- [ ] Golden test suite executavel como pytest: `pytest tests/benchmark/test_golden_suite.py`
- [ ] Testes de acentuacao: "confeccao" (sem cedilha) e "confeccao" (com cedilha) retornam mesmos resultados
- [ ] Baseline de precision/recall documentada com valores numericos

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| FP1 | Custom terms com exclusoes desativadas: medir FP rate para "confeccao", "camisa", "bota", "colete" | Benchmark | P1 |
| FP2 | Custom terms com exclusoes re-habilitadas: medir reducao de FP | Benchmark | P1 |
| FP3 | Tier C scoring: "bota + meia + avental" rejeitado com max() scoring atual | Unit | P2 |
| FP4 | Tier C scoring: mesmo item aceito com scoring aditivo (0.9 >= 0.6) | Unit | P2 |
| FP5 | EPI_ONLY_KEYWORDS: item com apenas "epi" rejeitado, "epi + jaleco" aceito | Unit | P2 |
| FP6 | Exclusion keyword com variante de acento: "confeccao de placa" exclui corretamente | Unit | P2 |
| FP10 | Golden test suite: 50 relevant + 50 irrelevant, precision/recall | Benchmark | P2 |
| CP6 | Busca com termos customizados: exclusoes aplicadas quando setor selecionado | Integration | P1 |
| RT1 | No keyword pair in sectors.py has different normalize_text() outputs | CI Script | P3 |
| A7 | Validate no keyword pair has different normalized outputs (redundancy detection) | Script | P3 |

## Estimativa

- Horas: 11h
- Complexidade: Media

## Dependencias

- Nenhuma bloqueante para iniciar.
- Golden test suite DEVE ser completada antes de v3-story-2.1 (stemming) para servir como baseline.

## Definition of Done

- [ ] Code implemented and reviewed
- [ ] Golden test suite criada e baseline documentada
- [ ] Tests written and passing (FP1-FP6, FP10, CP6, RT1)
- [ ] No regressions in existing tests
- [ ] CI script de redundancia de keywords integrado
- [ ] Acceptance criteria verified
