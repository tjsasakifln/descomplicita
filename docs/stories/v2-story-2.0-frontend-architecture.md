# [v2] Story 2.0: Frontend Architecture -- Structural Fixes
## Epic: Resolucao de Debitos Tecnicos v2.0 (Marco 2026)

### Contexto

Este sprint aborda debitos estruturais do frontend que afetam seguranca (XSS), performance (polling), e fundacao tecnica (paginacao, formulario semantico). A maioria destes debitos e nova na v2.0 ou representa evolucoes de debitos parcialmente resolvidos na v1.0:

- **TD-M10 (dangerouslySetInnerHTML):** Novo na v2.0 -- inline script para tema bloqueia implementacao de CSP
- **TD-M07/TD-M08 (headers CSP/HSTS):** Novo na v2.0 como debitos separados; v1.0 nao tinha debt especifico para security headers
- **XD-PERF-03 (polling):** Novo na v2.0 -- polling fixo de 2s gerando 60-300 requests desnecessarios
- **TD-M02/XD-PERF-02 (paginacao):** Novo na v2.0 como debito separado
- **UXD-023 (timeout delete):** Novo na v2.0 -- violacao WCAG 2.2.1

A v1.0 story 2.0 focou na decomposicao do god component (TD-004, 1071 linhas). A v2.0 nao lista o god component, sugerindo que foi resolvido. Este sprint foca em problemas estruturais diferentes.

### Objetivo

Resolver debitos de frontend que afetam seguranca (eliminar vetor XSS para habilitar CSP), performance (paginacao e polling inteligente), e acessibilidade (timeout acessivel). Desbloquear a implementacao de Content-Security-Policy.

### Debitos Cobertos

| ID | Debito | Severidade | Horas | Status v1.0 |
|----|--------|------------|-------|-------------|
| TD-M10 | dangerouslySetInnerHTML para script inline de tema | Media | 2-4h | NOVO |
| TD-M07 | Sem header Content-Security-Policy | Media | 2-4h | NOVO (bloqueado por TD-M10) |
| TD-M08 | Sem header Strict-Transport-Security | Media | 2-4h | NOVO |
| XD-SEC-01 | Headers de seguranca ausentes (CSP, HSTS, Referrer-Policy, Permissions-Policy) | Media | 2-4h | NOVO |
| XD-SEC-03 | dangerouslySetInnerHTML + sem CSP (combinacao de risco) | Media | 2-4h | NOVO |
| TD-M02 | Sem paginacao nos resultados | Media | 4-8h | NOVO como debt separado |
| XD-PERF-02 | Sem paginacao end-to-end | Media | 4-8h | NOVO |
| XD-PERF-03 | Polling de intervalo fixo 2s (sem backoff) | Media | 2-4h | NOVO |
| UXD-023 | Timeout de confirmacao de delete (3s) inacessivel | Media | 1h | NOVO |

### Tasks

#### Cadeia de Seguranca: Inline Script + Headers

- [x] Task 1: TD-M10 -- Refatorar inline script de prevencao de FOUC (flash of unstyled content) de tema. Opcoes: (a) usar `data-theme` attribute em `<html>` lido via CSS, (b) usar nonce no script e pass-through para CSP, (c) mover para modulo externo com hash CSP.
- [x] Task 2: TD-M10 -- Verificar que flash de tema nao ocorre apos refatoracao (testar em todos os 5 temas).
- [x] Task 3: TD-M07 -- Adicionar Content-Security-Policy header na config do Vercel (`vercel.json`). Configurar `script-src` com nonce/hash conforme solucao de Task 1.
- [x] Task 4: TD-M08 -- Adicionar Strict-Transport-Security header: `max-age=31536000; includeSubDomains`.
- [x] Task 5: XD-SEC-01 -- Adicionar headers adicionais: `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `X-Content-Type-Options: nosniff`.
- [x] Task 6: XD-SEC-03 -- Verificar que `dangerouslySetInnerHTML` nao cria vetor XSS com CSP ativo (test de penetracao basico).

#### Paginacao End-to-End

- [x] Task 7: TD-M02 -- Implementar paginacao no backend: parametros `page` e `page_size` no endpoint de resultados, com defaults sensatos (page_size=20).
- [x] Task 8: XD-PERF-02 -- Implementar paginacao no frontend: componente de navegacao de paginas, lazy loading de resultados.
- [x] Task 9: XD-PERF-02 -- Testar performance com datasets grandes (500+ resultados) -- verificar que apenas a pagina atual e renderizada.

#### Polling Inteligente

- [x] Task 10: XD-PERF-03 -- Implementar backoff exponencial no polling de status de jobs. Ex: 1s, 2s, 4s, 8s, max 15s.
- [x] Task 11: XD-PERF-03 -- Considerar Server-Sent Events (SSE) como alternativa ao polling para jobs de longa duracao.
- [x] Task 12: XD-PERF-03 -- Medir reducao de requests (meta: reducao de 60-80%).

#### Acessibilidade

- [x] Task 13: UXD-023 -- Aumentar timeout de confirmacao de delete de 3s para 15-20s, ou remover timeout e manter dialog ate acao explicita do usuario.

### Criterios de Aceite

- [x] `dangerouslySetInnerHTML` para tema removido ou protegido com nonce/hash
- [x] CSP header presente em todas as respostas (verificar com curl)
- [x] HSTS header presente com max-age >= 31536000
- [x] Referrer-Policy e Permissions-Policy presentes
- [x] Nenhum flash de tema visivel em nenhum dos 5 temas
- [x] Resultados paginados (max 20 por pagina por default)
- [x] Polling usa backoff exponencial (verificar em network tab do DevTools)
- [x] Reducao mensuravel de requests de polling (>50%)
- [x] Timeout de delete >= 15s ou sem timeout automatico
- [x] WCAG 2.2.1 (timing) atendido para confirmacao de delete

### Testes Requeridos

- [x] Teste unitario: paginacao backend -- parametros, defaults, limites
- [x] Teste unitario: componente de paginacao frontend -- navegacao, estados
- [x] Teste unitario: backoff exponencial -- intervalos crescentes, max cap
- [x] Teste unitario: timeout de delete -- timeout correto ou sem auto-dismiss
- [ ] Teste E2E: busca com paginacao -- navegar entre paginas
- [x] Teste de seguranca: CSP bloqueia inline scripts nao-autorizados
- [x] Teste de seguranca: headers de seguranca presentes (script automatizado)
- [x] Teste visual: sem flash de tema em reload em todos os 5 temas
- [x] Teste de performance: 500+ resultados paginados sem degradacao

### Estimativa

- Horas: 20-30
- Custo: R$ 3.000-4.500 (estimativa a R$ 150/h)
- Sprint: 3 (1-2 semanas, paralelo com v2-story-4.0 backend)

### Dependencias

- Depende de: v2-story-1.0 (security/critical fixes; TD-C01 cadeia critica alimenta TD-M02 paginacao)
- Bloqueia: v2-story-5.0 (polish; CSP e pre-requisito para testes de seguranca finais)
- Interna: TD-M10 DEVE ser resolvido antes de TD-M07 (inline script quebraria com CSP restritivo)
- Interna: TD-M02 (backend paginacao) -> XD-PERF-02 (frontend paginacao)

### Definition of Done

- [x] Codigo implementado
- [x] Testes passando
- [ ] Review aprovado
- [ ] Deploy em staging
- [ ] QA aprovado
