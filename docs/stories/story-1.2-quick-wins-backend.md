# Story 1.2 -- Quick Wins: Backend e Infraestrutura

## Contexto

Com a seguranca basica corrigida na Story 0.2, esta story aborda quick wins de backend e infraestrutura: rate limiting nos endpoints de autenticacao (prevencao contra brute force), ajuste de timeout do Vercel para buscas grandes, correcoes de DX (path alias, API key de transparencia), e migracoes SQL de baixo risco para integridade adicional do banco.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Sprint 1: Quick Wins"

## Objetivo

Fortalecer a seguranca operacional do backend com rate limiting, eliminar timeouts em buscas grandes, e resolver quick wins de infraestrutura e DX que melhoram a confiabilidade do sistema.

## Tasks

- [ ] **Task 1** (TD-SYS-015) -- Implementar rate limiting nos endpoints `/auth/login`, `/auth/signup`, `/auth/refresh`. Sugestao: slowapi ou middleware customizado com Redis. Limite: 10 tentativas/minuto por IP -- 2h
- [ ] **Task 2** (TD-SYS-016) -- Ajustar timeout do Vercel para funcoes de longa duracao (buscas grandes, download de Excel). Configurar `maxDuration` no vercel.json ou nas rotas relevantes -- 2h
- [ ] **Task 3** (TD-SYS-022) -- Corrigir inconsistencia de path alias entre build e test. Garantir que `@/` resolve corretamente em jest, tsconfig e next.config -- 1h
- [ ] **Task 4** (TD-SYS-023) -- Adicionar validacao de API key obrigatoria no endpoint de transparencia source. Retornar 401 se ausente em vez de silenciar -- 1h
- [ ] **Task 5** (TD-DB-008) -- Criar migracao com CHECK constraint de comprimento em `saved_searches.name` (ex: `CHECK(length(name) <= 200)`) para prevenir nomes de 10KB -- 0.5h
- [ ] **Task 6** (TD-SYS-021) -- Adicionar fallback system font para Google Fonts (evitar FOUT em conexoes lentas). Ajustar `next/font` config com `fallback` array -- 0.5h

## Criterios de Aceite

- [ ] Burst de 15+ requests em `/auth/login` no intervalo de 1 minuto retorna HTTP 429 (Too Many Requests)
- [ ] Rate limit aplicado por IP, nao globalmente
- [ ] Buscas grandes (>10 UFs, >30 dias) nao sofrem timeout no Vercel
- [ ] Download de Excel com 10.000 itens nao sofre timeout
- [ ] Path alias `@/` funciona identicamente em `next build`, `jest`, e IDE
- [ ] Endpoint de transparencia retorna 401 quando API key ausente
- [ ] INSERT em `saved_searches` com nome > 200 caracteres falha com constraint violation
- [ ] Google Fonts carrega com fallback system font visivel durante load

## Testes Requeridos

- [ ] Teste: burst de 20 requests em `/auth/login` retorna 429 apos limite (integration)
- [ ] Teste: request normal apos cooldown e aceito normalmente (integration)
- [ ] Teste: busca grande completa sem timeout em ambiente Vercel-like (integration)
- [ ] Teste: `saved_searches.name` com 201+ caracteres falha (integration SQL)
- [ ] Testes existentes de auth continuam passando (unit + integration)
- [ ] Build e test suite rodam sem erros de path alias (CI)

## Estimativa

- **Horas:** 7h
- **Complexidade:** Simples a Medio (rate limiting requer escolha de estrategia; Vercel timeout requer teste em deploy preview)

## Dependencias

- **Depende de:** Story 0.2 (seguranca basica -- PyJWT unificado, verify_aud habilitado)
- **Bloqueia:** Story 2.1 (decomposicao main.py depende de infraestrutura estavel)

## Definition of Done

- [ ] Codigo implementado e revisado
- [ ] Todos os testes passando (existentes + novos)
- [ ] Nenhuma regressao nos 1.349+ testes backend e 576+ testes frontend
- [ ] Review aprovado
- [ ] Rate limiting verificado em ambiente de staging/preview

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-SYS-015 (Medio), TD-SYS-016 (Medio), TD-SYS-022 (Baixo), TD-SYS-023 (Baixo), TD-DB-008 (Baixa), TD-SYS-021 (Baixo)*
