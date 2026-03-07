# EPIC: Integracao Multi-Source — Maximizacao de Cobertura com Fontes Gratuitas

**Epic ID:** MS-001
**Titulo:** Multi-Source Integration — De PNCP-Only para Cobertura Nacional Multi-Fonte
**Versao:** 1.0
**Status:** READY TO START
**Data Criada:** March 6, 2026

---

## 1. Objetivo do Epic

Expandir o sistema de busca de licitacoes de uma unica fonte (PNCP) para uma arquitetura multi-source com 5+ fontes gratuitas, maximizando cobertura nacional. Inclui rebrand do frontend de "PNCP" para "Fontes oficiais" e expansao do conteudo educativo no carrossel de processamento.

**Resultado Final:** Sistema consulta PNCP + Compras.gov.br + Portal da Transparencia + Querido Diario + TCE-RJ em paralelo, com deduplicacao automatica. Frontend reflete multi-source sem mencionar PNCP. Carrossel de dicas expandido com 50+ itens cobrindo estrategias, insights e dicas praticas.

---

## 2. Descricao Completa

### Situacao Atual

O backend (`pncp_client.py`) esta acoplado diretamente ao PNCP. Toda a busca depende de uma unica fonte:
- Se o PNCP cair, a busca inteira falha
- Licitacoes de municipios que ainda nao publicam no PNCP nao sao capturadas
- Dados historicos pre-2023 nao estao disponiveis
- Frontend menciona "PNCP" em 13 pontos, limitando a percepcao do produto

### Fontes Identificadas (Gratuitas, com API)

| Fonte | API | Auth | Cobertura | Dados Unicos |
|-------|-----|------|-----------|--------------|
| **PNCP** (atual) | REST | Nenhuma | Nacional (Lei 14.133) | Fonte canonica pos-2023 |
| **Compras.gov.br** | REST | Nenhuma | Federal (SIASG) | Historico federal, CATMAT/CATSER |
| **Portal da Transparencia** | REST | API key gratuita | Federal | Listas sancao CEIS/CNEP/CEPIM |
| **Querido Diario** | REST | Nenhuma | 350+ municipios | Diarios oficiais, texto livre |
| **TCE-RJ** | REST | Nenhuma | Todos municipios RJ | Compras diretas, dispensas |

### Situacao Desejada

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Fontes de dados | 1 (PNCP) | 5+ fontes em paralelo |
| Cobertura municipal | Apenas PNCP-aderentes | +350 municipios via Querido Diario |
| Dados historicos | Apenas pos-2023 | Federal desde 2013 (Compras.gov) |
| Risco de indisponibilidade | Single point of failure | Degradacao graciosa |
| Branding frontend | "PNCP" | "Fontes oficiais" |
| Conteudo carrossel | 20 curiosidades | 50+ dicas, insights e estrategias |
| Duplicatas cross-source | N/A | Dedup automatica |

---

## 3. Escopo

### Incluso

- **Fase 1:** Camada de abstracao DataSourceClient + refactor PNCP como adapter
- **Fase 2:** Integracao Compras.gov.br + Portal da Transparencia
- **Fase 3:** Integracao Querido Diario + TCE-RJ
- **Fase 4:** Orquestrador multi-source com deduplicacao
- **Fase 5:** Frontend rebrand + indicadores de fonte
- **Fase 6:** Expansao do carrossel de dicas/insights/estrategias

### Excluso

- Fontes que requerem scraping (ComprasRS, BEC-SP, etc.) — futuro epic
- Integracao BigQuery (Base dos Dados) — requer Google Cloud
- Fontes TCE de outros estados (TCE-SP, TCE-PE) — Tier 2, futuro sprint
- WebSocket para notificacoes real-time

---

## 4. Stories

| # | Story | Pontos | Prioridade | Dependencia |
|---|-------|--------|------------|-------------|
| MS-001.1 | Abstraction Layer — DataSourceClient + NormalizedRecord | 5 | P0 | -- |
| MS-001.2 | Compras.gov.br — Integracao API federal historica | 5 | P0 | MS-001.1 |
| MS-001.3 | Portal da Transparencia — API CGU + listas de sancao | 5 | P1 | MS-001.1 |
| MS-001.4 | Querido Diario — API diarios oficiais municipais | 5 | P1 | MS-001.1 |
| MS-001.5 | TCE-RJ — API Tribunal de Contas do Estado do RJ | 3 | P1 | MS-001.1 |
| MS-001.6 | Multi-Source Orchestrator — Busca paralela + deduplicacao | 8 | P0 | MS-001.1, MS-001.2 |
| MS-001.7 | Frontend Rebrand — PNCP para "Fontes oficiais" + indicadores | 3 | P0 | MS-001.6 |
| MS-001.8 | Carrossel Expandido — 50+ dicas, insights e estrategias | 3 | P1 | -- |

**Total:** 37 story points

---

## 5. Arquitetura Multi-Source

```
SearchRequest
    |
    v
MultiSourceOrchestrator
    |--- PNCPSource         (existente, refatorado)
    |--- ComprasGovSource   (novo)
    |--- TransparenciaSource(novo)
    |--- QueridoDiarioSource(novo)
    |--- TCERJSource        (novo)
    |
    v (paralelo)
[resultados por fonte]
    |
    v
Deduplicator (CNPJ + numero + ano)
    |
    v
NormalizedRecord[]
    |
    v
FilterEngine (existente, sem mudanca)
    |
    v
LLM + Excel (existente, coluna "Fonte" adicionada)
```

---

## 6. Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|----------|
| APIs sem SLA formal | Alto | Circuit breaker + timeout por fonte + fallback |
| Formatos inconsistentes | Medio | Normalizacao rigorosa no adapter de cada fonte |
| Duplicatas cross-source | Medio | Dedup por chave composta (CNPJ + nro + ano) |
| Latencia agregada | Medio | Timeout por fonte + resultado parcial |
| Querido Diario = texto livre | Alto | Regex/NLP para extrair dados estruturados |
| Portal Transparencia requer API key | Baixo | Registro gratuito por email |
| Fontes redundantes com PNCP ao longo do tempo | Baixo | Feature flags para habilitar/desabilitar |

---

## 7. Definition of Done (Epic)

- [ ] Camada DataSourceClient implementada com interface clara
- [ ] PNCPClient refatorado como PNCPSource adapter
- [ ] 4 novas fontes integradas e funcionais (Compras.gov, Transparencia, QD, TCE-RJ)
- [ ] Orquestrador busca em paralelo com timeout por fonte
- [ ] Deduplicacao cross-source com < 1% falsos positivos
- [ ] Zero mencoes a "PNCP" no frontend (substituido por "Fontes oficiais")
- [ ] Carrossel expandido para 50+ itens com 4 categorias
- [ ] Coluna "Fonte" adicionada ao Excel
- [ ] Testes unitarios para cada source adapter
- [ ] Busca com 5 fontes completa em < 60s
