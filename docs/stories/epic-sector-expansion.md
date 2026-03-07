# EPIC: Expansao de Setores de Licitacao

**Epic ID:** SEC-001
**Titulo:** Expansao de Setores de Busca de Licitacoes
**Versao:** 1.0
**Status:** READY TO START
**Data Criada:** March 05, 2026

---

## 1. Objetivo do Epic

Expandir o Descomplicita de **7 setores** para **12 setores** de busca de licitacoes, cobrindo os segmentos de maior volume do mercado de compras publicas brasileiro (R$ 1,18 trilhao/ano).

**Resultado Final:** 5 novos setores com precision >= 80% validada contra editais reais do PNCP.

---

## 2. Descricao Completa

### Situacao Atual

Descomplicita cobre 7 setores:
- Vestuario e Uniformes
- Alimentos e Merenda
- Informatica e Tecnologia
- Produtos de Limpeza
- Mobiliario
- Papelaria e Material de Escritorio
- Engenharia e Construcao

### Situacao Desejada

Descomplicita cobrira 12 setores (+5 novos):
- Saude e Medicamentos (R$ 75 bi/ano)
- Veiculos, Pecas e Combustiveis (R$ 30+ bi/ano)
- Equipamentos e Material Hospitalar (R$ 20+ bi/ano)
- Seguranca e Vigilancia (R$ 15+ bi/ano)
- Servicos Gerais e Manutencao (R$ 10+ bi/ano)

### Decisao Arquitetural

Zero mudanca de arquitetura necessaria. O padrao `SectorConfig` em `backend/sectors.py` ja e extensivel — cada novo setor e apenas uma nova entrada no dict `SECTORS` com keywords e exclusions. Frontend carrega setores dinamicamente via `/setores`.

---

## 3. Escopo

### Incluso

- 5 novos `SectorConfig` entries em `backend/sectors.py`
- Keywords curadas para cada setor (portugues, com e sem acentos)
- Exclusions robustas para evitar falsos positivos
- Validacao de precision com editais reais do PNCP
- Audit script atualizado

### NAO Incluso

- Mudancas no frontend (carrega dinamicamente)
- Mudancas na API (endpoint `/setores` ja lista todos)
- Mudancas no filtro (ja usa `SectorConfig` generico)
- Sub-setores ou filtros avancados

---

## 4. Criterios de Sucesso

- [ ] 5 novos setores adicionados em `backend/sectors.py`
- [ ] Cada setor com precision >= 80% em 20+ editais reais
- [ ] Zero regressao nos 7 setores existentes
- [ ] Frontend exibe todos os 12 setores sem deploy separado
- [ ] Audit report gerado para cada novo setor

---

## 5. Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Saude: nomenclatura tecnica (DCB/DCM) | Alta | Medio | Keywords especificas + termos genericos |
| Veiculos: "pecas" e termo generico | Media | Alto | Exclusions robustas por contexto |
| Seguranca: confusao com seg. trabalho/alimentar | Alta | Alto | Exclusions extensivas por dominio |
| Hospitalar: sobreposicao com Saude | Media | Medio | Separacao clara: equipamentos vs consumiveis |
| Servicos Gerais: sobreposicao com Engenharia | Media | Medio | Exclusions cruzadas com setor engenharia |

---

## 6. Story Breakdown

| Story | Titulo | Setor ID | SP | Prioridade | GitHub |
|-------|--------|----------|----|------------|--------|
| SEC-001-1 | Saude e Medicamentos | `saude` | 5 | P0 | #15 |
| SEC-001-2 | Veiculos, Pecas e Combustiveis | `veiculos` | 5 | P0 | #16 |
| SEC-001-3 | Equipamentos e Material Hospitalar | `hospitalar` | 5 | P1 | #17 |
| SEC-001-4 | Seguranca e Vigilancia | `seguranca` | 5 | P1 | #18 |
| SEC-001-5 | Servicos Gerais e Manutencao | `servicos_gerais` | 5 | P2 | #19 |

**Total: 25 Story Points | 5 Stories**

---

## 7. Dependencias de Story

```
START
  |- SEC-001-1: Saude e Medicamentos (independente)
  |- SEC-001-2: Veiculos, Pecas e Combustiveis (independente)
  |- SEC-001-3: Equipamentos Hospitalares (independente, mas revisar exclusions com SEC-001-1)
  |- SEC-001-4: Seguranca e Vigilancia (independente)
  |- SEC-001-5: Servicos Gerais (independente, mas revisar exclusions com engenharia)
END
```

Todas as stories sao independentes e podem ser implementadas em paralelo.

---

## 8. Definition of Done (Para Cada Story)

- [ ] `SectorConfig` adicionado em `backend/sectors.py`
- [ ] Keywords testadas manualmente contra PNCP
- [ ] Exclusions validadas contra falsos positivos conhecidos
- [ ] Precision >= 80% em 20+ editais reais
- [ ] Audit script executado e resultados salvos
- [ ] Setores existentes sem regressao
- [ ] Code reviewed

---

## 9. Approval e Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| CTO Advisory Board | Conselho | 2026-03-05 | Aprovado |
| Product Manager | TBD | TBD | Pendente |
| Engineering Manager | TBD | TBD | Pendente |

---

**Epic Created:** March 05, 2026
**Version:** 1.0
**Status:** READY TO START
**Expected Duration:** 1-2 semanas
**GitHub Epic Issue:** #14
