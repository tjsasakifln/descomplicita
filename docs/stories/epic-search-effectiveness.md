# EPIC: Efetividade do Pipeline de Busca — Zero Results Root Cause Fix

**Epic ID:** SE-001
**Titulo:** Search Effectiveness — Correcao da Causa Raiz de Zero Resultados por Setor
**Versao:** 1.0
**Status:** READY TO START
**Data Criada:** March 7, 2026
**Origem:** Veredito unanime do CTO Advisory Board (8/8 clusters)

---

## 1. Objetivo do Epic

Corrigir a causa raiz estrutural que faz buscas setoriais (ex: "Saude e Medicamentos") retornarem consistentemente 0 resultados, mesmo com fontes operacionais. O problema NAO e de resiliencia (corrigido no SR-001), mas de **efetividade**: o pipeline busca TUDO e filtra client-side, resultando em taxa de match proxima a zero para setores especificos em janelas curtas.

**Resultado Final:** Buscas setoriais retornam resultados relevantes para qualquer setor, em qualquer janela de tempo >= 7 dias, com filtragem server-side quando disponivel e faixas de valor adequadas por setor.

---

## 2. Descricao Completa

### Situacao Atual (Diagnostico 2026-03-07)

Busca por "Saude e Medicamentos" em 27 estados / 7 dias retornou **0 resultados**. SR-001 corrigiu timeouts e fontes quebradas, mas o problema persiste porque:

1. **Sem filtro server-side por objeto:** PNCP API suporta `palavraChave` mas o sistema NAO o utiliza. Busca retorna ALL procurement de ALL setores, depois aplica keyword match client-side
2. **Transparencia `codigoUF` possivelmente incompativel:** API pode esperar codigos IBGE numericos (ex: `35` para SP) em vez de siglas (`SP`), retornando silenciosamente 0 resultados
3. **Modalidades incompletas:** `DEFAULT_MODALIDADES = [4,5,6,7,8]` exclui Ata de Registro de Preco (13) e Chamada Publica (15), modalidades comuns para medicamentos
4. **Faixa de valor unica para todos os setores:** `valor_min=10.000`, `valor_max=10.000.000` descarta medicamentos fracionados (<10k) e atas de registro (>10M)

### Cadeia Causal Completa

```
User busca "Saude" (7 dias, 27 UFs)
  -> PNCP: 27 UFs x 5 modalidades = 135 requests (SEM palavraChave)
  -> Retorna ~N mil records de TODOS os setores
  -> filter_batch() aplica 84 keywords de saude no campo objetoCompra
  -> Match rate: ~0.1-2% (saude e fracao pequena do total)
  -> Filtro de valor descarta itens <10k e >10M
  -> Para janela de 7 dias: alta probabilidade de 0 matches
  -> "Nenhuma licitacao encontrada"
```

### Situacao Desejada

```
User busca "Saude" (7 dias, 27 UFs)
  -> PNCP: palavraChave="medicamento" (server-side!)
  -> Retorna apenas records com "medicamento" no objetoCompra
  -> PNCP: palavraChave="hospitalar" (segunda query server-side)
  -> Retorna apenas records com "hospitalar" no objetoCompra
  -> Transparencia: codigoUF validado, retorna dados federais
  -> filter_batch() aplica refinamento com exclusions
  -> Faixa de valor ajustada: 1k-50M para saude
  -> Resultados relevantes retornados ao usuario
```

---

## 3. Escopo

### Incluso

- Implementacao de filtro `palavraChave` server-side no PNCP
- Validacao e correcao do parametro `codigoUF` na Transparencia
- Expansao de modalidades com ata de registro e chamada publica
- Faixa de valor configuravel por setor no SectorConfig
- Testes unitarios e de integracao para cada mudanca

### Excluso

- Adicao de novas fontes de dados (BEC/SP, ComprasNet novo) — futuro epic
- Migracao para httpx async (epic de tech debt)
- Circuit breaker automatico (futuro epic)
- UI para configuracao de faixa de valor pelo usuario

---

## 4. Stories

| # | Story | Pontos | Prioridade | Dependencia |
|---|-------|--------|------------|-------------|
| SE-001.1 | Implementar filtro `palavraChave` server-side no PNCP | 5 | P0 | -- |
| SE-001.2 | Validar e corrigir parametro `codigoUF` na Transparencia | 2 | P0 | -- |
| SE-001.3 | Expandir DEFAULT_MODALIDADES com ata de registro e chamada publica | 1 | P1 | -- |
| SE-001.4 | Implementar faixa de valor configuravel por setor | 3 | P1 | -- |
| SE-001.5 | Adicionar endpoint PNCP `/atas` para Atas de Registro de Preco | 5 | P2 | SE-001.1 |

**Total:** 16 story points

### Ordem de Execucao

1. **SE-001.1** + **SE-001.2** (paralelo) — desbloqueia resultados imediatamente
2. **SE-001.3** — quick win, 15 minutos
3. **SE-001.4** — remove falsos negativos por valor
4. **SE-001.5** — amplia cobertura de atas (medio prazo)

---

## 5. Evidencias (Codebase)

| Arquivo | Linha | Problema |
|---------|-------|----------|
| `backend/pncp_client.py` | 243-252 | `params` NAO inclui `palavraChave` |
| `backend/sources/transparencia_source.py` | 267 | `codigoUF` recebe sigla, pode precisar codigo IBGE |
| `backend/config.py` | 31-36 | `DEFAULT_MODALIDADES = [4,5,6,7,8]` — falta 13, 15 |
| `backend/main.py` | 417 | `valor_min=10_000.0, valor_max=10_000_000.0` — fixo para todos os setores |
| `backend/sectors.py` | 547-618 | SectorConfig de saude sem `valor_min`/`valor_max` |
| `backend/sources/base.py` | 10-16 | SearchQuery sem campo `palavras_chave` |
| `backend/sources/pncp_source.py` | 85-110 | fetch_records NAO passa keywords para PNCPClient |

---

## 6. Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|----------|
| PNCP `palavraChave` pode ter comportamento diferente do esperado | Resultados inesperados | Testar manualmente no Swagger antes de implementar |
| Multiplas queries por setor aumentam tempo total | Busca mais lenta | Limitar a 3-5 keywords prioritarias por setor |
| Transparencia pode nao aceitar codigos IBGE | Sem resultados federais | Testar ambos os formatos (sigla vs numerico) |
| Faixa de valor muito ampla gera ruido | Mais falsos positivos | Keywords + exclusions compensam |

---

## 7. Metricas de Sucesso

| Metrica | Antes | Meta |
|---------|-------|------|
| Taxa de busca com 0 resultados (Saude) | ~90% | < 10% |
| Records retornados por busca (Saude, 7 dias, 27 UFs) | 0 | >= 10 |
| Tempo medio de busca | ~120s | < 60s (menos dados irrelevantes) |
| Cobertura de modalidades | 5 | 7 |

---

## 8. Definition of Done (Epic)

- [ ] PNCP queries incluem `palavraChave` com termos prioritarios do setor
- [ ] Transparencia `codigoUF` validado e funcional em producao
- [ ] `DEFAULT_MODALIDADES` inclui modalidades 13 e 15
- [ ] Cada setor tem `valor_min` e `valor_max` proprios
- [ ] Busca por "Saude e Medicamentos" (7 dias, 5+ UFs) retorna >= 5 resultados
- [ ] Busca por "Alimentos" (7 dias, 5+ UFs) retorna >= 10 resultados
- [ ] Testes unitarios cobrindo novas funcionalidades
- [ ] Zero regressoes nos testes existentes
- [ ] Deploy em producao Railway validado
