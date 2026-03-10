# v3-story-2.1: Search Quality -- Stemming & Relevance

## Contexto

O sistema de busca perde resultados relevantes porque nao realiza stemming: "uniformizado" nao casa com "uniforme", "confeccionado" nao casa com "confeccao". Esta e uma das maiores fontes de falsos negativos identificadas. O @data-engineer recomenda implementar stemming PT-BR via RSLP (Removedor de Sufixos da Lingua Portuguesa) disponivel no NLTK.

Adicionalmente, o campo `tipo` (licitacao/ata) e recebido na interface mas nunca renderizado nos items individuais. Usuarios B2B precisam desta informacao para priorizacao.

IMPORTANTE: Esta story requer que o golden test suite (v3-story-1.2) esteja completo como baseline. Stemming pode gerar novos falsos positivos por over-stemming, e sem baseline nao ha como medir o impacto.

## Objetivo

Implementar stemming PT-BR para eliminar falsos negativos de flexoes verbais, exibir campo tipo nos resultados, e validar que a qualidade de busca melhora sem regressao significativa em precision.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| -- | Stemming ausente (FN de flexoes verbais) | Alta | 10h |
| FE-020 | Termos multi-palavra impossiveis via interface | Media | 3h |
| -- | Campo tipo nao renderizado nos items | Media | 2h |
| -- | Golden test suite validacao pos-stemming | -- | 4h |

## Tasks

- [ ] Task 1: Integrar RSLP stemmer do NLTK no backend -- adicionar dependencia, criar funcao `stem_text()` que aplica stemming apos normalize_text()
- [ ] Task 2: Aplicar stemming em AMBOS os lados do matching: keywords do setor/customizados E texto do objeto PNCP
- [ ] Task 3: Manter matching exato como fallback -- se stemming causar over-matching, termos exatos tem prioridade
- [ ] Task 4: Testar com golden test suite (baseline de v3-story-1.2) -- medir precision e recall antes e apos stemming
- [ ] Task 5: Ajustar exclusion keywords para tambem usar stemming -- garantir que exclusoes continuam funcionando
- [ ] Task 6: FE-020 -- Implementar suporte a virgula como delimitador de termos no SearchForm.tsx (alem de espaco)
- [ ] Task 7: FE-020 -- Adicionar hint text no campo: "Separe termos por virgula. Ex: camisa polo, jaleco medico"
- [ ] Task 8: Renderizar campo `tipo` nos items individuais -- badge visual (Licitacao/Ata) ao lado do numero do item
- [ ] Task 9: Validar que termos com acentos continuam funcionando corretamente apos stemming (stemmer recebe texto normalizado)
- [ ] Task 10: Documentar precision/recall apos mudancas e comparar com baseline

## Criterios de Aceite

- [ ] "uniformizado" casa com "uniforme" nos resultados de busca
- [ ] "confeccionado" casa com "confeccao" (com ou sem cedilha) nos resultados
- [ ] Precision nao cai mais de 10% em relacao a baseline (golden test suite)
- [ ] Recall melhora >= 10% em relacao a baseline
- [ ] Termos multi-palavra funcionam com virgula: "camisa polo, jaleco medico" cria 2 tokens
- [ ] Hint text visivel no campo de termos explicando uso de virgulas
- [ ] Campo tipo exibido como badge nos items individuais (Licitacao/Ata)
- [ ] Acentuacao continua funcional: "licitacao" (sem acento) e "licitacao" (com acento) retornam mesmos resultados apos stemming
- [ ] Stemming nao quebra exclusoes: "confeccao de placa de sinalizacao" continua sendo excluida

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| FP10 | Golden test suite: precision/recall pos-stemming | Benchmark | P1 |
| A1 | normalize_text() com todas as diacriticas PT-BR | Unit | P2 |
| A2 | normalize_text() com NFC vs NFD input (identico output) | Unit | P2 |
| A3 | match_keywords() com keyword acentuada vs objeto sem acento | Unit | P2 |
| A4 | match_keywords() com termos hifenizados ("guarda-po") | Unit | P2 |
| -- | stem_text("uniformizado") == stem_text("uniforme") | Unit | P1 |
| -- | stem_text("confeccionado") == stem_text("confeccao") | Unit | P1 |
| -- | Stemming + exclusoes: termos excluidos continuam excluidos | Unit | P2 |
| -- | Multi-palavra: virgula cria tokens separados no frontend | Component | P2 |
| -- | Campo tipo renderizado como badge nos items | Component | P3 |

## Estimativa

- Horas: 19h
- Complexidade: Complexa

## Dependencias

- **REQUER** v3-story-1.2 (golden test suite como baseline para medir impacto)
- Independente de v3-story-2.0 (Supabase) e v3-story-2.2 (grande volume)

## Definition of Done

- [ ] Code implemented and reviewed
- [ ] Stemming RSLP integrado e funcional
- [ ] Tests written and passing
- [ ] Precision/recall documentados com delta vs baseline
- [ ] Merge bloqueado se precision cair >10% ou recall cair >5%
- [ ] No regressions in existing tests
- [ ] Acceptance criteria verified
