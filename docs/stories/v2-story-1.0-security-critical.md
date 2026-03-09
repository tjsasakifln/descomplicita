# [v2] Story 1.0: Security & Critical Fixes
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Este sprint aborda os debitos de severidade critica e alta que bloqueiam a evolucao do produto. Varios destes debitos existiam na v1.0 mas nao foram totalmente resolvidos ou evoluiram:

- **TD-C02/XD-SEC-02 (autenticacao):** v1.0 TD-003 implementou API key auth como Fase 1. A v2.0 identifica que a autenticacao continua fragil -- chave unica compartilhada sem identidade de usuario. A v2.0 propoe JWT stateless como proxima evolucao.
- **TD-C01 (Excel em memoria):** v1.0 TD-007 propunha streaming/signed URL. Se nao totalmente resolvido, permanece como critico na v2.0 com foco em duplicacao memoria+Redis.
- **TD-H02/TD-H01 (jobs duraveis):** v1.0 TD-005/TD-026 propunha Redis job store e cache. A v2.0 reafirma a necessidade de fila duravel (Celery/RQ) em vez de asyncio.create_task.
- **TD-C03 (fontes desabilitadas):** Novo na v2.0 com esta classificacao; v1.0 nao tinha debt especifico para dead code de data sources.
- **UXD-001 (multi-palavras):** Novo na v2.0 -- bloqueador funcional de busca.
- **UXD-015 (contraste):** v1.0 TD-010 abordava contraste de `--ink-muted`; v2.0 UXD-015 expande para auditoria completa dos 5 temas.
- **XD-PERF-01 (download bufferizado):** Relacionado a v1.0 TD-007/TD-023; v2.0 identifica 3 copias em memoria.

### Objetivo

Fechar todos os debitos criticos (P0) e altos (P1) que representam riscos de seguranca, perda de dados em deploy, e bloqueadores funcionais. Implementar JWT stateless, resolver cadeia critica de streaming/memoria, e garantir durabilidade de jobs.

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| TD-C02 | Sem autenticacao de usuario (API key unica compartilhada) | Critica | 8-16h | REMANESCENTE (v1 TD-003 implementou API key Phase 1; JWT pendente) |
| XD-SEC-02 | Autenticacao fragil end-to-end | Critica | Alto | REMANESCENTE (manifestacao cross-cutting de TD-C02) |
| UXD-001 | Termos multi-palavras impossiveis (espaco cria token) | Alta | 3h | NOVO |
| TD-C01 | Excel bytes duplicados em memoria + Redis | Critica | 4-8h | REMANESCENTE (v1 TD-007 propunha streaming; pode nao ter sido totalmente resolvido) |
| XD-PERF-01 | Download bufferizado em cadeia (3 copias em memoria) | Alta | 4-8h | REMANESCENTE (v1 TD-007/TD-023 relacionados) |
| TD-H02 | Jobs asyncio nao duraveis (create_task sem fila) | Alta | 8-16h | REMANESCENTE (v1 TD-005 propunha Redis; v2 propoe fila duravel) |
| TD-H01 | In-memory job store como primario (dual-write) | Alta | 4-8h | REMANESCENTE (v1 TD-005 propunha migracao Redis) |
| TD-C03 | 3 de 5 fontes de dados desabilitadas (codigo morto) | Alta | 8-16h | NOVO (dead code de sources nao catalogado na v1.0) |
| UXD-015 | Sem auditoria de contraste de cores para os 5 temas | Alta | 4h | PARCIALMENTE RESOLVIDO (v1 TD-010 corrigiu ink-muted; auditoria completa pendente) |

### Tasks

#### Seguranca (P0)

- [x] Task 1: TD-C02/XD-SEC-02 -- Implementar autenticacao JWT stateless. Criar `backend/auth/jwt.py` com gerador/validador de tokens. Manter API key como fallback durante transicao.
- [x] Task 2: TD-C02 -- Configurar middleware JWT no FastAPI. Endpoints protegidos retornam 401 sem token valido. Health check permanece aberto.
- [x] Task 3: TD-C02 -- Atualizar frontend para obter e enviar JWT em todas as requests.

#### Bloqueador Funcional (P1)

- [x] Task 4: UXD-001 -- Implementar suporte a termos multi-palavras no input de busca. Solucao: aspas para agrupar + virgula como delimitador. Ex: `"camisa polo", uniforme`.
- [x] Task 5: UXD-001 -- Atualizar parsing de termos no backend para aceitar formato com aspas/virgulas.
- [x] Task 6: UXD-001 -- Testar compatibilidade com saved searches existentes em localStorage.

#### Cadeia Critica: Streaming/Memoria (P1)

- [x] Task 7: TD-C01 -- Eliminar armazenamento de bytes Excel brutos no dict Python do job result. Armazenar referencia ou gerar on-demand.
- [x] Task 8: TD-C01 -- Reduzir duplicacao de dados no Redis (nao serializar bytes Excel como JSON base64).
- [x] Task 9: XD-PERF-01 -- Implementar download streaming (StreamingResponse) eliminando as 3 copias em memoria.
- [x] Task 10: XD-PERF-01 -- Implementar com feature flag para rollback seguro.

#### Durabilidade de Jobs (P1)

- [x] Task 11: TD-H02 -- Substituir `asyncio.create_task` por fila de tarefas duravel (avaliar Celery com Redis broker, ou RQ, ou arq).
- [x] Task 12: TD-H02 -- Jobs em execucao durante shutdown sao salvos com status interrompido (nao perdidos).
- [x] Task 13: TD-H01 -- Eliminar in-memory job store; Redis como unica fonte de verdade (remove necessidade de dual-write).
- [x] Task 14: TD-H01 -- Adicionar TTL para jobs no Redis (24h) para prevenir crescimento ilimitado.

#### Codigo Morto (P1)

- [x] Task 15: TD-C03 -- Escrever testes de integracao do orquestrador de fontes antes de qualquer remocao.
- [x] Task 16: TD-C03 -- Remover codigo de ComprasGov (API deprecada), Querido Diario (retorna HTML), TCE-RJ (404).
- [x] Task 17: TD-C03 -- Atualizar source registry para refletir apenas as 2 fontes ativas.
- [x] Task 18: TD-C03 -- Documentar processo para adicionar novas fontes no futuro.

#### Acessibilidade Legal (P2)

- [x] Task 19: UXD-015 -- Rodar auditoria de contraste com axe DevTools em todos os 5 temas (Default Light, Default Dark, Paperwhite, Sepia, High Contrast).
- [x] Task 20: UXD-015 -- Corrigir violacoes de contraste encontradas, especialmente em temas Sepia e Paperwhite.
- [x] Task 21: UXD-015 -- Integrar @axe-core/playwright nos testes E2E como quality gate.

### Criterios de Aceite

- [x] Endpoints protegidos retornam 401 sem JWT valido
- [x] JWT e stateless (sem consulta a DB para validacao)
- [x] Busca com "camisa polo" retorna resultados corretos (nao split em dois tokens)
- [x] Download de Excel funciona sem acumular 3 copias em memoria (verificar memory profiling)
- [x] Jobs sobrevivem restart do container (criar job, restart, poll -- estado preservado)
- [x] `asyncio.create_task` nao e mais usado para jobs de busca
- [x] Codigo de ComprasGov, Querido Diario, TCE-RJ removido (verificar com grep)
- [x] Source registry lista apenas 2 fontes ativas
- [x] Auditoria axe-core passa sem violacoes criticas/serias em todos os 5 temas
- [x] Feature flag permite rollback do streaming de download

### Testes Requeridos

- [x] Teste unitario: JWT -- geracao, validacao, expiracao, token invalido
- [x] Teste unitario: middleware JWT retorna 401 para requests sem/com token invalido
- [x] Teste unitario: parsing de termos multi-palavras com aspas e virgulas
- [x] Teste de integracao: orquestrador de fontes funciona com 2 fontes ativas
- [x] Teste de integracao: fila duravel -- job criado, processado, resultado disponivel apos restart
- [x] Teste de integracao: download streaming -- resposta valida .xlsx sem acumulacao de memoria
- [x] Teste E2E: fluxo completo de busca com JWT
- [x] Teste E2E: axe-core em todos os 5 temas -- zero violacoes criticas/serias
- [x] Teste de carga: 10 buscas concorrentes com fila duravel (sem corrupcao)

### Estimativa

- Horas: 40-60
- Custo: R$ 6.000-9.000 (estimativa a R$ 150/h)
- Sprint: 2 (1 semana)

### Dependencias

- Depende de: v2-story-0.0 (quick wins idealmente resolvidos primeiro; TD-M04 timeout previne cascading failure durante carga)
- Bloqueia: v2-story-2.0 (frontend arch), v2-story-3.0 (frontend quality), v2-story-4.0 (backend arch), v2-story-5.0 (polish)
- Interna: TD-C01 -> XD-PERF-01 (streaming e downstream de eliminacao de Excel bytes)
- Interna: TD-H02 -> TD-H01 (fila duravel elimina necessidade de in-memory store)

### Definition of Done

- [x] Codigo implementado
- [x] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado
