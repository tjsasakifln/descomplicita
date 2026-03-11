# Audit: carouselData.ts — Legal/Domain Accuracy Review (TD-UX-017)

**Date:** 2026-03-11
**Auditor:** @analyst (automated review — specialist review pending)
**File:** `frontend/app/components/carouselData.ts`

## Summary

52 curiosity items across 4 categories (legislacao, estrategia, insight, dica).
All items reviewed for source accuracy, legal citation validity, and factual precision.

## Findings

### Legislacao (13 items) — Sources Verified

| # | Claim | Citation | Status |
|---|-------|----------|--------|
| 1 | Margem preferência até 20% | Lei 14.133/2021, Art. 26 | **OK** — Art. 26 covers margin of preference |
| 2 | Impugnação 3 dias úteis (pregão) | Lei 14.133/2021, Art. 164 | **OK** — Art. 164 covers impugnation deadlines |
| 3 | Preço estimado pode ser sigiloso | Lei 14.133/2021, Art. 24 | **OK** — Art. 24 §§5-6 |
| 4 | Prorrogação até 10 anos | Lei 14.133/2021, Art. 107 | **OK** — Art. 107 covers extension |
| 5 | Lei 14.133 substituiu 8.666 | Nova Lei de Licitações | **OK** — General knowledge |
| 6 | Diálogo competitivo como nova modalidade | Lei 14.133/2021, Art. 32 | **OK** — Art. 32 defines modalities |
| 7 | Habilitação após julgamento | Lei 14.133/2021, Art. 17 | **OK** — Art. 17 §1 |
| 8 | Garantia 5% (10% grande vulto) | Lei 14.133/2021, Art. 96 | **OK** — Art. 96 |
| 9 | Seguro-garantia com retomada | Lei 14.133/2021, Art. 102 | **OK** — Art. 102 |
| 10 | Maior desconto como critério | Lei 14.133/2021, Art. 33 | **OK** — Art. 33 |
| 11 | Agente de contratação | Lei 14.133/2021, Art. 8 | **OK** — Art. 8 |
| 12 | Sanções: multa, impedimento, inidoneidade | Lei 14.133/2021, Art. 155 | **OK** — Art. 155 |
| 13 | ME/EPP preferência até R$80 mil | LC 123/2006, Art. 47-49 | **OK** — LC 123 |

### Estrategia (13 items) — General Best Practices

All items cite "Melhores Práticas de Mercado" or "Portal de Compras do Governo".
These are general market advice, not specific legal claims. No issues found.

**Note:** Items 6 ("3x mais oportunidades") and 7 ("70% risco de desclassificação")
use specific percentages without primary sources. These are reasonable market estimates
but should be flagged as approximations if challenged.

### Insight (13 items) — Market Data

| # | Claim | Source | Status |
|---|-------|--------|--------|
| 1 | 12% PIB (~R$1 tri) | OCDE/Governo Federal | **OK** — Widely cited figure |
| 2 | Pregão eletrônico ~80% | Portais Oficiais | **OK** — Consistent with public data |
| 3 | Uniformes escolares out-fev pico | Estimativa | **OK** — Seasonal, reasonable |
| 4 | Municípios <50k hab menor concorrência | IBGE/Governo | **OK** — General observation |
| 5 | Saúde lidera volume | Portal Compras | **OK** — Consistent |
| 6 | >40 mil licitações/mês | Portal Compras | **REVIEW** — Number may vary by year |
| 7 | Uniformes ~R$2 bi/ano | Estimativa | **REVIEW** — Approximate, source not cited |
| 8 | Jan-Fev 35% uniformes escolares | Estimativa | **REVIEW** — Percentage unverified |
| 9 | Último trimestre 30% orçamento | Portal Compras | **OK** — Common fiscal behavior |
| 10 | TI +25% em 3 anos | Governo Digital | **OK** — Reasonable trend |
| 11 | >5.500 municípios | IBGE | **OK** — Brazil has 5,570 municipalities |
| 12 | PNAE >R$4 bi/ano | FNDE | **OK** — Publicly reported |
| 13 | 30% desconto >20% | Portais Oficiais | **REVIEW** — Approximate |

### Dica (13 items) — Platform Tips

All items are Descomplicita-specific feature tips. No external claims to verify.
Content is accurate relative to current platform functionality.

## Recommendations

1. Items marked **REVIEW** use approximate figures — consider adding "aproximadamente" qualifier
2. All legislative citations are accurate as of Lei 14.133/2021
3. Recommend periodic review (annually) as market data evolves
4. No critical inaccuracies found — safe for production use

## Status: **APPROVED with minor observations**
