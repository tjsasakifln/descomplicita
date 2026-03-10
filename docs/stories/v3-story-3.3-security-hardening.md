# v3-story-3.3: Security Hardening

## Contexto

O backend tem vulnerabilidades de seguranca que devem ser corrigidas antes de producao: implementacao JWT customizada sem PyJWT (sem key rotation, sem audience/issuer, sem JWK), timing attack em 2 pontos de auth (comparacao com `==` ao inves de `hmac.compare_digest`), CORS com `allow_headers=["*"]`, falta de CSP e HSTS headers, e auth bypass silencioso quando API_KEY e JWT_SECRET nao estao definidos.

## Objetivo

Corrigir vulnerabilidades de seguranca criticas e altas: JWT padronizado, timing attack, CORS restritivo, headers de seguranca, e safeguard contra auth bypass.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| SYS-003 | Implementacao JWT customizada (sem PyJWT) | Critica | 4h |
| DB-005 | API key comparison vulneravel a timing attack (middleware) | Media | 0.5h |
| DB-014 | Timing attack no endpoint /auth/token | Media | 0.5h |
| SYS-004 | CORS allow_headers=["*"] | Alta | 1h |
| SYS-005 | Sem CSP ou HSTS headers | Alta | 4h |
| SYS-007 | Auth bypass em dev mode sem safeguard | Alta | 2h |

## Tasks

- [ ] Task 1: SYS-003 -- Substituir JWT customizada por PyJWT: adicionar dependencia, implementar encode/decode com audience, issuer, expiration, e key rotation support
- [ ] Task 2: SYS-003 -- Configurar JWK (JSON Web Key) para key management; rotacao de chaves sem downtime
- [ ] Task 3: DB-005 + DB-014 -- Substituir `==` por `hmac.compare_digest` nos 2 pontos de comparacao de API key: middleware (DB-005) e /auth/token (DB-014, main.py linha 317)
- [ ] Task 4: SYS-004 -- Restringir CORS allow_headers para lista explicita: Content-Type, Authorization, X-API-Key
- [ ] Task 5: SYS-005 -- Adicionar middleware para Content-Security-Policy header com politica restritiva
- [ ] Task 6: SYS-005 -- Adicionar Strict-Transport-Security header (HSTS) com max-age adequado
- [ ] Task 7: SYS-007 -- Adicionar safeguard: quando API_KEY ou JWT_SECRET nao definidos em producao (NODE_ENV=production), falhar com erro explicito ao inves de bypass silencioso
- [ ] Task 8: SYS-007 -- Log warning em dev mode quando auth bypass ativo: "Auth bypass active -- development mode only"

## Criterios de Aceite

- [ ] JWT usa PyJWT com audience, issuer, e expiration validados
- [ ] Key rotation funcional sem downtime
- [ ] `hmac.compare_digest` usado em AMBOS os pontos de auth (validado por teste unitario)
- [ ] CORS rejeita headers nao listados explicitamente
- [ ] Content-Security-Policy header presente em todas as respostas
- [ ] Strict-Transport-Security header presente com max-age >= 31536000 (1 ano)
- [ ] Aplicacao falha ao iniciar em producao se API_KEY ou JWT_SECRET nao definidos
- [ ] Log warning emitido em dev mode quando auth bypass ativo

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| CP4 | hmac.compare_digest usado em ambos os pontos de auth | Unit | P1 |
| -- | JWT encode/decode com PyJWT: audience, issuer, expiration | Unit | P1 |
| -- | JWT rejeita token com audience incorreto | Unit | P1 |
| -- | JWT rejeita token expirado | Unit | P1 |
| -- | CORS rejeita header nao listado (ex: X-Custom-Header) | Integration | P2 |
| -- | CSP header presente na resposta | Integration | P2 |
| -- | HSTS header presente com max-age correto | Integration | P2 |
| -- | App falha ao iniciar sem API_KEY em producao | Integration | P2 |
| -- | App inicia normalmente sem API_KEY em dev mode (com warning) | Integration | P2 |

## Estimativa

- Horas: 8h (nota: SYS-003 4h pode ser parcialmente coberto por Supabase Auth em v3-story-2.0; ajustar se necessario)
- Complexidade: Media

## Dependencias

- Nenhuma bloqueante direta.
- Se v3-story-2.0 (Supabase Auth) estiver completo, SYS-003 pode ser simplificado (Supabase gerencia JWT nativamente). Coordenar com time.
- DB-005 + DB-014 sao independentes e podem rodar em paralelo com qualquer outra story.

## Definition of Done

- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Security headers validados em ambiente de staging
- [ ] No regressions in existing tests
- [ ] Acceptance criteria verified
