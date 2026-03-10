# v3-story-1.1: Critical Error Handling & Silent Failures

## Contexto

O frontend tem um `catch {}` vazio na paginacao de ItemsList.tsx (linha 44) que engole erros silenciosamente, deixando o usuario preso em "Carregando..." perpetuo sem feedback, retry, ou logging. Este e o debito critico de maior impacto no frontend -- e tambem pre-requisito para que erros de DB-009 (desserializacao de 85K items) se tornem visiveis.

Adicionalmente, ha uma race condition confirmada de timeout: o frontend tem timeout fixo de 10 minutos enquanto o backend calcula timeout dinamico de ate 10.5 minutos para 27 UFs, criando uma janela de 30 segundos onde o backend pode completar com sucesso mas o frontend ja exibiu erro ao usuario.

## Objetivo

Eliminar silent failures criticos no frontend: error swallowing na paginacao, race condition de paginacao (AbortController), e timeout race condition entre frontend e backend.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| FE-005 | Error swallowing silencioso no ItemsList (catch {} vazio) | Critica | 2h |
| FE-019 | Sem AbortController na paginacao (race condition) | Media | 2h |
| -- | Frontend timeout alignment com backend | Alta | 3h |
| SYS-010 | Sem timeout em chamadas OpenAI | Media | 2h |

## Tasks

- [x] Task 1: FE-005 -- Substituir `catch {}` vazio em ItemsList.tsx por error state com mensagem e retry button inline
- [x] Task 2: FE-005 -- Adicionar error boundary para erros de rede vs erros de parsing, com mensagens diferenciadas
- [x] Task 3: FE-019 -- Implementar AbortController em fetchPage para cancelar requests anteriores ao navegar rapidamente entre paginas
- [x] Task 4: Timeout alignment -- Backend: enviar header `X-Expected-Duration` na resposta de /api/buscar
- [x] Task 5: Timeout alignment -- Frontend: useSearchJob.ts calcular POLL_TIMEOUT dinamicamente baseado em UFs selecionadas (formula: 300 + max(0, ufs-5)*15 + 60 segundos de margem)
- [x] Task 6: SYS-010 -- Adicionar timeout de 30s nas chamadas OpenAI (summary generation) com fallback graceful
- [x] Task 7: Adicionar lint rule (eslint no-empty no-catch) para prevenir reintroducao de catch {} vazios

## Criterios de Aceite

- [x] ItemsList exibe mensagem de erro clara quando fetch falha, com botao "Tentar novamente"
- [x] Erro de paginacao diferencia timeout de rede vs erro de servidor
- [x] Navegacao rapida entre paginas nao exibe dados stale (AbortController cancela requests anteriores)
- [x] Frontend timeout >= backend timeout para TODAS as combinacoes validas de UFs (1-27) e dias (1-90)
- [x] Chamadas OpenAI tem timeout de 30s; se expirar, summary mostra fallback sem travar a busca
- [x] Zero `catch {}` vazios restantes no frontend (validado por lint)
- [x] Testes de timeout verificam formula para cenarios: 1 UF, 5 UFs, 10 UFs, 27 UFs

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| CP1 | Frontend timeout >= backend timeout para todas as combinacoes UF/dias | Property-based | P1 |
| CP2 | Paginacao exibe retry button apos erro | Component | P1 |
| UX1 | FE-005: verify error state is displayed when fetch fails | Component | P1 |
| UX2 | FE-005: verify retry button re-fetches the page | Component | P1 |
| CP3 | AbortController cancels stale requests on page change | Component | P1 |
| UX6 | FE-019: verify AbortController cancels previous fetch | Component | P3 |
| RT5 | No empty catch blocks in frontend (lint rule) | Lint | P2 |

## Estimativa

- Horas: 9h
- Complexidade: Media

## Dependencias

- Nenhuma bloqueante. Esta story DEVE ser completada antes de v3-story-2.2 (DB-009 Redis LIST) pois sem error handling, regressoes na paginacao seriam silenciosamente engolidas.

## Definition of Done

- [x] Code implemented and reviewed
- [x] Tests written and passing (CP1, CP2, CP3, UX1, UX2, UX6, RT5)
- [x] No regressions in existing 455+ tests (39 suites, 0 failures)
- [x] Lint rule ativa para catch vazios (eslint.config.mjs + no-empty rule)
- [x] Acceptance criteria verified
