# EPIC: Eliminacao de Falsos Positivos — Qualidade de Filtragem

**Epic ID:** FQ-001
**Titulo:** Aprimoramento da Logica de Filtragem Multi-Setor
**Versao:** 1.0
**Status:** READY TO START
**Data Criada:** March 5, 2026

---

## 1. Objetivo do Epic

Reduzir a taxa de falsos positivos da filtragem de licitacoes de **2.8% global** (101 FPs em 3.593 itens) para **< 1%**, com foco nos 5 setores mais problematicos: Vestuario (22.5%), Informatica (11.9%), Limpeza (8.8%), Engenharia (3.7%) e Alimentos (4.1%).

**Resultado Final:** Sistema de filtragem com precisao >= 99% em todos os 12 setores, validado por auditoria automatizada.

---

## 2. Descricao Completa

### Situacao Atual

Auditoria de 2026-03-05 contra dados reais do PNCP (3.593 itens, SP/MG/RJ, Pregao Eletronico, 7 dias) revelou:

| Setor | Aprovados | FPs | Taxa FP | Causa Raiz |
|-------|-----------|-----|---------|------------|
| Vestuario | 129 | 29 | 22.5% | "EPI" generico sem contexto vestuario |
| Informatica | 201 | 24 | 11.9% | "servidor" = pessoa, "monitor" hospitalar |
| Limpeza | 193 | 17 | 8.8% | "limpeza urbana", "descartavel" hospitalar |
| Engenharia | 430 | 16 | 3.7% | "infraestrutura" TI, "cobertura" seguro |
| Alimentos | 242 | 10 | 4.1% | "oleo" automotivo, "cafe" isolado |
| Veiculos | 367 | 2 | 0.5% | "abastecimento" agua |
| Mobiliario | 106 | 2 | 1.9% | "rack" TI, "banco" financeiro |
| Seguranca | 38 | 1 | 2.6% | "vigilancia" sanitaria |
| Papelaria | 89 | 0 | 0% | OK |
| Saude | 337 | 0 | 0% | OK |
| Hospitalar | 68 | 0 | 0% | OK |
| Servicos Gerais | 61 | 0 | 0% | OK |

### Causa Raiz Arquitetural

O `match_keywords()` em `filter.py` usa match binario: qualquer keyword isolado aprova o item. Keywords ambiguos de alta frequencia ("servidor", "EPI", "limpeza", "infraestrutura", "cobertura") geram FPs quando aparecem sozinhos sem contexto do setor.

### Situacao Desejada

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Taxa FP global | 2.8% (101/3593) | < 1% (< 36/3593) |
| Vestuario FP | 22.5% | < 3% |
| Informatica FP | 11.9% | < 3% |
| Limpeza FP | 8.8% | < 3% |
| Engenharia FP | 3.7% | < 2% |
| Auditoria automatizada | Manual (ad-hoc) | CI gate obrigatorio |

---

## 3. Escopo

### Incluso

- Fase 1: Expansao de exclusoes para eliminacao imediata de 80+ FPs
- Fase 2: Refatoracao de `match_keywords()` com sistema de scoring por tiers
- Fase 3: Auditoria automatizada como quality gate

### Excluso

- Embeddings semanticos / ML (avaliar em futuro epic se scoring nao atingir < 1%)
- Alteracoes de frontend
- Novos setores

---

## 4. Stories

| # | Story | Pontos | Prioridade | Dependencia |
|---|-------|--------|------------|-------------|
| FQ-001.1 | Expansao de exclusoes — Limpeza, Engenharia, Veiculos, Seguranca | 3 | P0 | — |
| FQ-001.2 | Expansao de exclusoes — Vestuario (EPI) | 3 | P0 | — |
| FQ-001.3 | Expansao de exclusoes — Informatica (servidor/monitor) | 3 | P0 | — |
| FQ-001.4 | Expansao de exclusoes — Alimentos e Mobiliario | 2 | P0 | — |
| FQ-001.5 | Refatoracao match_keywords com tier scoring | 8 | P1 | FQ-001.1-4 |
| FQ-001.6 | Auditoria automatizada como CI quality gate | 3 | P2 | FQ-001.5 |

**Total:** 22 story points

---

## 5. Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|----------|
| Exclusoes agressivas geram falsos negativos | Alto | Auditoria bidirecional (FP + FN) |
| Refatoracao de match_keywords quebra setores OK | Alto | Testes de regressao antes de merge |
| PNCP muda formato de dados | Medio | Auditoria periodica detecta drift |
| Cafe e FP ou TP? | Baixo | Cafe isolado e TP (compra de alimento); so bloquear "moinho para cafe" |

---

## 6. Definition of Done (Epic)

- [ ] Todas as 6 stories completas e merged
- [ ] Auditoria automatizada rodando com 0 FPs nos padroes conhecidos
- [ ] Taxa FP < 1% validada contra >= 3000 itens reais do PNCP
- [ ] Zero regressao nos setores que ja tinham 0% FP
- [ ] Documentacao atualizada em sectors.py
