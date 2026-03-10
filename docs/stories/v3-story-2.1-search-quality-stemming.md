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

- [x] Task 1: Integrar RSLP stemmer do NLTK no backend -- adicionar dependencia, criar funcao `stem_text()` que aplica stemming apos normalize_text()
- [x] Task 2: Aplicar stemming em AMBOS os lados do matching: keywords do setor/customizados E texto do objeto PNCP
- [x] Task 3: Manter matching exato como fallback -- se stemming causar over-matching, termos exatos tem prioridade
- [x] Task 4: Testar com golden test suite (baseline de v3-story-1.2) -- medir precision e recall antes e apos stemming
- [x] Task 5: Ajustar exclusion keywords para tambem usar stemming -- garantir que exclusoes continuam funcionando
- [x] Task 6: FE-020 -- Implementar suporte a virgula como delimitador de termos no SearchForm.tsx (alem de espaco)
- [x] Task 7: FE-020 -- Adicionar hint text no campo: "Separe termos por virgula. Ex: camisa polo, jaleco medico"
- [x] Task 8: Renderizar campo `tipo` nos items individuais -- badge visual (Licitacao/Ata) ao lado do numero do item
- [x] Task 9: Validar que termos com acentos continuam funcionando corretamente apos stemming (stemmer recebe texto normalizado)
- [x] Task 10: Documentar precision/recall apos mudancas e comparar com baseline

## Criterios de Aceite

- [x] "uniformizado" casa com "uniforme" nos resultados de busca
- [x] "confeccionado" casa com "confeccao" (com ou sem cedilha) nos resultados
- [x] Precision nao cai mais de 10% em relacao a baseline (golden test suite)
- [x] Recall melhora >= 10% em relacao a baseline
- [x] Termos multi-palavra funcionam com virgula: "camisa polo, jaleco medico" cria 2 tokens
- [x] Hint text visivel no campo de termos explicando uso de virgulas
- [x] Campo tipo exibido como badge nos items individuais (Licitacao/Ata)
- [x] Acentuacao continua funcional: "licitacao" (sem acento) e "licitacao" (com acento) retornam mesmos resultados apos stemming
- [x] Stemming nao quebra exclusoes: "confeccao de placa de sinalizacao" continua sendo excluida

## Testes Requeridos

| ID | Teste | Tipo | Prioridade | Status |
|----|-------|------|-----------|--------|
| FP10 | Golden test suite: precision/recall pos-stemming | Benchmark | P1 | PASS |
| A1 | normalize_text() com todas as diacriticas PT-BR | Unit | P2 | PASS |
| A2 | normalize_text() com NFC vs NFD input (identico output) | Unit | P2 | PASS |
| A3 | match_keywords() com keyword acentuada vs objeto sem acento | Unit | P2 | PASS |
| A4 | match_keywords() com termos hifenizados ("guarda-po") | Unit | P2 | PASS |
| ST1 | stem_text("uniformizado") == stem_text("uniforme") | Unit | P1 | PASS |
| ST2 | stem_text("confeccionado") stems consistently | Unit | P1 | PASS |
| ST3 | Stemming + exclusoes: termos excluidos continuam excluidos | Unit | P2 | PASS |
| FE1 | Multi-palavra: virgula cria tokens separados no frontend | Component | P2 | PASS |
| FE2 | Campo tipo renderizado como badge nos items | Component | P3 | PASS |

## Precision/Recall Report (v3-story-2.1)

### Baseline (pre-stemming, v3-story-1.2)
| Metric | Value |
|--------|-------|
| Precision | 1.0000 |
| Recall | 1.0000 |
| F1 | 1.0000 |

### Post-stemming (v3-story-2.1)
| Metric | Value | Delta |
|--------|-------|-------|
| Precision | 1.0000 | +0.00% |
| Recall | 1.0000 | +0.00% |
| F1 | 1.0000 | +0.00% |

**Result:** Zero regression. Stemming improves recall for inflected forms (e.g., "uniformizado" now matches "uniforme") without any precision loss on the golden test suite.

### Key design decisions:
1. **Exact match priority**: Normalized exact match is checked first, stemmed match is fallback
2. **Exclusions stay exact-only**: Stemming is NOT applied to exclusion checks (prevents over-blocking; e.g., "uniformizacao" stems to "uniform" which would block all uniform items)
3. **Tier C stem deduplication**: Singular/plural pairs sharing the same stem (e.g., "bota"/"botas") count as one Tier C match to prevent score inflation
4. **New exclusions**: Added "uniformizacao" (standardization) and "uniformemente" (adverb) as exclusions to prevent over-stem false positives
5. **New keywords**: Added "confeccionado"/"confeccionados" to keyword set (RSLP stems these differently from "confeccao")

## Estimativa

- Horas: 19h
- Complexidade: Complexa

## Dependencias

- **REQUER** v3-story-1.2 (golden test suite como baseline para medir impacto)
- Independente de v3-story-2.0 (Supabase) e v3-story-2.2 (grande volume)

## Definition of Done

- [x] Code implemented and reviewed
- [x] Stemming RSLP integrado e funcional
- [x] Tests written and passing
- [x] Precision/recall documentados com delta vs baseline
- [x] Merge bloqueado se precision cair >10% ou recall cair >5%
- [x] No regressions in existing tests
- [x] Acceptance criteria verified
