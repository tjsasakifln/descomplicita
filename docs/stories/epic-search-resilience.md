# EPIC: Resiliencia do Pipeline de Busca Multi-Source

**Epic ID:** SR-001
**Titulo:** Search Resilience — Correcao de Falhas Sistemicas no Pipeline Multi-Source
**Versao:** 1.0
**Status:** READY TO START
**Data Criada:** March 7, 2026

---

## 1. Objetivo do Epic

Corrigir 5 falhas sistemicas independentes que, combinadas, resultam em 0% de entrega de resultados ao usuario. O PNCP (unica fonte funcional) faz timeout no orchestrator, e as 4 fontes secundarias falham silenciosamente com erros de autenticacao, endpoints deprecados e parsing.

**Resultado Final:** Pipeline multi-source resiliente onde o PNCP completa suas buscas dentro do timeout, fontes secundarias estao operacionais ou desabilitadas com justificativa, e o usuario recebe resultados mesmo quando fontes individuais falham.

---

## 2. Descricao Completa

### Situacao Atual (Incidente 2026-03-07)

Busca por "Saude e Medicamentos" em 7 estados retornou **0 resultados** ao usuario. Logs Railway confirmam:

```
12:37:58 | ERROR | sources.orchestrator | Source PNCP timed out
12:37:58 | ERROR | sources.orchestrator | Source tce_rj timed out
12:37:58 | INFO  | main | Filtering complete: 0/0 bids passed
```

| Fonte | Status | Causa Raiz |
|-------|--------|------------|
| **PNCP** | TIMEOUT | Orchestrator timeout 15s para operacao de 2-5min |
| **Compras.gov.br** | 404 | Endpoint `/licitacoes/v1/licitacoes.json` deprecado |
| **Transparencia** | 401 | API key ausente/expirada no Railway |
| **Querido Diario** | Parse Error | API retornando HTML/vazio em vez de JSON |
| **TCE-RJ** | 404 + Timeout | Endpoint `/api/v1/compras-diretas` retornando 404 |

### Problemas Tecnicos Identificados

1. **Confusao de timeouts:** `SOURCES_CONFIG["pncp"]["timeout"] = 15` (orchestrator) coincide com `RetryConfig.timeout = 15` (HTTP individual) — mesmos 15s para escopos radicalmente diferentes
2. **Resource leak:** `asyncio.wait_for()` cancela o task async mas as threads do `ThreadPoolExecutor` em `pncp_client.py` continuam executando em background (confirmado nos logs)
3. **Fontes secundarias falhando silenciosamente:** sem alertas, sem circuit breaker, sem desabilitacao automatica

### Situacao Desejada

| Aspecto | Antes | Depois |
|---------|-------|--------|
| PNCP orchestrator timeout | 15s (insuficiente) | 120s (comporta 7 UFs x 5 modalidades) |
| Fontes secundarias | Falhando silenciosamente | Operacionais ou desabilitadas com log |
| Transparencia API key | Ausente/expirada | Configurada e validada |
| Compras.gov.br endpoint | 404 | Atualizado ou desabilitado |
| Querido Diario parsing | Crash em corpo vazio | Validacao de content-type |

---

## 3. Escopo

### Incluso

- Correcao de timeouts do orchestrator para todas as fontes
- Restauracao da autenticacao do Portal da Transparencia
- Investigacao e correcao/desabilitacao de endpoints 404 (Compras.gov, TCE-RJ)
- Correcao de parsing defensivo no Querido Diario
- Comentarios no codigo distinguindo os dois tipos de timeout

### Excluso

- Migracao do PNCPClient de `requests` sync para `httpx` async (futuro epic)
- Circuit breaker automatico (futuro epic)
- Alertas/monitoring de falha de fontes (futuro epic)

---

## 4. Stories

| # | Story | Pontos | Prioridade | Dependencia |
|---|-------|--------|------------|-------------|
| SR-001.1 | Corrigir PNCP orchestrator timeout (15s para 120s) | 3 | P0 | -- |
| SR-001.2 | Restaurar Transparencia API key no Railway | 1 | P0 | -- |
| SR-001.3 | Investigar e corrigir endpoint Compras.gov.br 404 | 3 | P1 | -- |
| SR-001.4 | Corrigir Querido Diario JSON parse error | 2 | P1 | -- |
| SR-001.5 | Investigar e corrigir TCE-RJ endpoint 404 | 2 | P1 | -- |

**Total:** 11 story points

### Ordem de Execucao

1. **SR-001.1** (PNCP timeout) — desbloqueia imediatamente os resultados para o usuario
2. **SR-001.2** (Transparencia API key) — fix de config, sem codigo
3. **SR-001.3, SR-001.4, SR-001.5** — podem ser paralelizados

---

## 5. Evidencias

| Arquivo | Linha | Problema |
|---------|-------|----------|
| `backend/config.py` | 75 | `"timeout": 15` — orchestrator timeout = HTTP timeout |
| `backend/sources/orchestrator.py` | 303-305 | `asyncio.wait_for(timeout=timeout)` cancela async mas nao threads |
| `backend/sources/pncp_source.py` | 97-107 | `run_in_executor()` — threads nao cancelaveis via asyncio |
| `backend/pncp_client.py` | 484-492 | `ThreadPoolExecutor(max_workers=12)` — threads orfas |

---

## 6. Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|----------|
| Timeout alto sem circuit breaker | Se PNCP estiver fora do ar, job trava 120s | Futuro epic para circuit breaker |
| Threads orfas (resource leak) | Consumo de CPU/rede em background | Futuro epic para migrar para httpx async |
| Endpoints deprecados permanentemente | Menos fontes disponiveis | Desabilitar fontes mortas, documentar |

---

## 7. Definition of Done (Epic)

- [ ] PNCP orchestrator timeout >= 120s
- [ ] Busca com 7 UFs x 5 modalidades completa sem timeout
- [ ] Transparencia API key configurada e validada no Railway
- [ ] Compras.gov.br endpoint atualizado ou source desabilitada
- [ ] Querido Diario com parsing defensivo (valida content-type)
- [ ] TCE-RJ endpoint atualizado ou source desabilitada
- [ ] Zero erros silenciosos de autenticacao em producao
- [ ] Testes existentes atualizados e passando
- [ ] Comentarios no codigo distinguem timeout HTTP vs timeout orchestrator
