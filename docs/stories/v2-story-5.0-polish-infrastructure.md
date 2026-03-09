# [v2] Story 5.0: Polish & Infrastructure
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Sprint final de polish, testes cross-cutting, e resolucao de debitos de baixa prioridade. Relacao com v1.0:

- **TD-M03 (modelo LLM hardcoded):** Novo na v2.0 -- `gpt-4.1-nano` hardcoded ignorando env var
- **XD-TEST-01/02/03 (testes cross-cutting):** Novos na v2.0 -- integracao, smoke tests, regressao visual
- **TD-M09 (MD5):** Novo na v2.0 -- risco teorico rebaixado para P5
- **TD-L03 (localStorage):** Novo na v2.0 -- buscas salvas sem persistencia server-side
- **TD-L05 (keywords grandes):** Novo na v2.0 -- concern de performance em escala
- **XD-TEST-03 (regressao visual):** Novo na v2.0 -- considerado prematuro para POC por @qa

A v1.0 story 5.0 focava em deprecated APIs, branding, observability (Sentry), e graceful shutdown. Varios desses itens podem ja ter sido resolvidos.

### Objetivo

Fechar debitos de baixa prioridade restantes, implementar testes cross-cutting (integracao, smoke tests pos-deploy), configuracoes operacionais (modelo LLM, bundle baseline), e resolver gaps identificados pelo QA. Ao final deste sprint, todos os 55 debitos da v2.0 estarao enderecados.

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| TD-M03 | Modelo LLM hardcoded (gpt-4.1-nano) | Media | 2-4h | NOVO |
| XD-TEST-01 | Sem testes de integracao frontend-backend | Media | 4-8h | NOVO |
| XD-TEST-02 | Sem smoke tests pos-deploy | Media | 2-4h | NOVO |
| XD-TEST-03 | Sem testes de regressao visual | Baixa | 4-8h | NOVO (prematuro para POC per @qa) |
| TD-M09 | MD5 usado para chaves de dedup | Baixa | 2-4h | NOVO |
| TD-L03 | Buscas salvas apenas em localStorage | Baixa | 2-4h | NOVO |
| TD-L05 | Conjuntos grandes de keywords/exclusoes | Baixa | 2-4h | NOVO |

#### Gaps do QA (da secao "Gaps Reconhecidos" da avaliacao)

| Gap | Debito | Horas | Status |
|-----|--------|-------|--------|
| G-01 | Backend test coverage nao quantificada | 1-2h | ACAO IMEDIATA |
| G-04 | Sem scan de vulnerabilidades em dependencias | 2-4h | NOVO |
| G-10 | Bundle size nao baselinado | 2-4h | NOVO |

### Tasks

#### Configuracao Operacional

- [ ] Task 1: TD-M03 -- Refatorar `llm.py` para ler modelo de `LLM_MODEL` env var (ja exposta em docker-compose mas ignorada pelo codigo). Adicionar fallback para valor default.
- [ ] Task 2: TD-M03 -- Testar troca de modelo sem alterar codigo (ex: `LLM_MODEL=gpt-4o-mini`).

#### Testes Cross-Cutting

- [ ] Task 3: XD-TEST-01 -- Implementar testes de integracao frontend-backend usando MSW (Mock Service Worker). Configurar interceptacao de requests no frontend test env.
- [ ] Task 4: XD-TEST-01 -- Cobrir cenarios: busca com sucesso, busca com erro, polling timeout, download Excel.
- [ ] Task 5: XD-TEST-02 -- Implementar smoke tests pos-deploy via GitHub Actions. Escopo minimo: verificar `/health`, `/setores`, `/buscar` (com parametros minimos).
- [ ] Task 6: XD-TEST-02 -- Configurar alertas para falha de smoke test (notificacao Slack ou email).
- [ ] Task 7: XD-TEST-03 -- Avaliar viabilidade de testes de regressao visual para o momento (5 temas + responsividade). Se prematuro, documentar plano para implementacao futura com design system.

#### Gaps do QA

- [ ] Task 8: G-01 -- Rodar `pytest --cov` e documentar resultado de coverage. Validar que threshold de 70% em `pyproject.toml` esta sendo atingido.
- [ ] Task 9: G-04 -- Adicionar `pip audit` e `npm audit --audit-level=high` ao CI como quality gate. Configurar para falhar build em vulnerabilidades criticas/altas.
- [ ] Task 10: G-10 -- Estabelecer baseline de bundle size com bundle analyzer. Configurar budget no CI (ex: max 500KB JS inicial). Considerar Lighthouse CI para proximo milestone.

#### Debitos de Baixa Prioridade

- [ ] Task 11: TD-M09 -- Avaliar substituicao de MD5 por SHA-256 para chaves de dedup. Se risco e desprezivel para dados nao-criticos (confirmado por @qa), documentar decisao e manter.
- [ ] Task 12: TD-L03 -- Avaliar persistencia server-side para buscas salvas. Se TD-H04 (database) foi implementado em v2-story-4.0, migrar de localStorage para DB. Caso contrario, documentar como dependencia futura.
- [ ] Task 13: TD-L05 -- Avaliar performance de ~130 keywords inclusao + ~100 exclusao. Se mitigado por ordenacao fail-fast existente, documentar e manter. Se necessario, implementar trie ou pre-compilacao de regex.

### Criterios de Aceite

- [ ] Modelo LLM configuravel via env var sem alterar codigo
- [ ] Pelo menos 4 cenarios de integracao com MSW passando
- [ ] Smoke tests pos-deploy rodando automaticamente em GitHub Actions
- [ ] Backend test coverage medido e documentado (>= 70%)
- [ ] `pip audit` e `npm audit` no CI, falhando em vulnerabilidades criticas/altas
- [ ] Bundle size baselinado e budget configurado
- [ ] Todos os 55 debitos da v2.0 enderecados (resolvidos ou documentados como decisoes conscientes)

### Testes Requeridos

- [ ] Teste de integracao MSW: busca sucesso, erro, timeout, download
- [ ] Smoke test: endpoints criticos respondem com status 200
- [ ] Coverage: `pytest --cov` reporta >= 70%
- [ ] Audit: `pip audit` sem vulnerabilidades criticas/altas
- [ ] Audit: `npm audit --audit-level=high` sem vulnerabilidades criticas/altas
- [ ] Teste unitario: LLM_MODEL env var e lido corretamente
- [ ] Teste de regressao: todos os testes existentes continuam passando

### Estimativa

- Horas: 30-40
- Custo: R$ 4.500-6.000 (estimativa a R$ 150/h)
- Sprint: 4 (1-2 semanas, apos sprints 2-3)

### Dependencias

- Depende de: v2-story-1.0 (security), v2-story-2.0 (frontend arch), v2-story-4.0 (backend arch)
- Depende de: v2-story-4.0 TD-H04 (database) para TD-L03 (buscas salvas server-side)
- Bloqueia: Nenhuma (sprint final)
- Nota: XD-TEST-03 (regressao visual) pode ser adiado para apos design system per @qa

### Definition of Done

- [ ] Codigo implementado
- [ ] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado
- [ ] Todos os 55 debitos documentados como resolvidos ou conscientemente adiados
- [ ] Metricas de sucesso da avaliacao v2.0 atingidas (coverage, security headers, smoke tests)
