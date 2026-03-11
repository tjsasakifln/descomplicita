# Story 2.2 -- Fundacao: Consolidacao de Autenticacao

## Contexto

O subsistema de autenticacao e o cluster com maior concentracao de debitos tecnicos cross-cutting: Supabase client recriado a cada request de auth (performance), endpoints sem validacao Pydantic (seguranca e DX), JWT cached em variavel de modulo no frontend serverless (confiabilidade), RLS sem WITH CHECK explicito (auditabilidade), e migration runner ausente para aplicar migracoes de forma segura.

A resolucao coordenada destes itens fortalece significativamente a postura de seguranca e a manutenibilidade do sistema de autenticacao.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Debitos Cruzados: Cluster de Autenticacao" e "Sprint 2: Fundacao"

## Objetivo

Consolidar toda a camada de autenticacao: Pydantic para validacao, Supabase client reutilizavel via DI, JWT corrigido para serverless, RLS granular, migration runner automatizado, e melhorias operacionais de banco.

## Tasks

- [ ] **Task 1** (TD-SYS-005) -- Refatorar criacao de Supabase client: implementar singleton ou dependency injection no FastAPI para reutilizar client entre requests de auth. Verificar thread safety -- 3h
- [ ] **Task 2** (TD-SYS-006) -- Adicionar modelos Pydantic nos endpoints `/auth/login`, `/auth/signup`, `/auth/refresh`, `/auth/token`. Payloads invalidos devem retornar 422 com detalhes de validacao. Documentacao OpenAPI automatica -- 4h
- [ ] **Task 3** (TD-SYS-007) -- Corrigir cache de token JWT em `backendAuth.ts`: nao armazenar em variavel de modulo (serverless pode ter instancias independentes). Buscar token fresco do cookie/session a cada request -- 3h
- [ ] **Task 4** (TD-DB-002) -- Adicionar WITH CHECK explicito nas policies RLS de INSERT em todas as 4 tabelas. Documentar intencao de cada policy. Verificar que policies existentes nao sao alteradas em comportamento -- 2h
- [ ] **Task 5** (TD-SYS-013) -- Configurar migration runner automatizado: integrar `supabase db push` no CI para aplicar migracoes pendentes. Adicionar step no GitHub Action de deploy -- 6h
- [ ] **Task 6** (TD-DB-010) -- Ativar politica de retencao de dados: criar GitHub Actions workflow com schedule semanal para executar funcao de cleanup existente. Alternativa: pg_cron se disponivel no Supabase Pro -- 1.5h
- [ ] **Task 7** (TD-SYS-010) -- Atualizar docker-compose.yml para refletir stack atual (Supabase + Redis). Remover referencias a SQLite. Garantir que `docker compose up` levanta ambiente de desenvolvimento funcional -- 2h

## Criterios de Aceite

- [ ] Supabase client criado uma unica vez e reutilizado entre requests (verificavel via logs ou metricas)
- [ ] Payload invalido em qualquer endpoint `/auth/*` retorna 422 com detalhes Pydantic
- [ ] Documentacao OpenAPI reflete modelos Pydantic nos endpoints de auth
- [ ] `backendAuth.ts` nao armazena token em variavel de modulo; busca fresco a cada request
- [ ] Policies RLS de INSERT incluem WITH CHECK explicito nas 4 tabelas
- [ ] `supabase db push` roda no CI e aplica migracoes pendentes
- [ ] Workflow de retencao executa semanalmente e remove registros conforme politica
- [ ] `docker compose up` levanta ambiente funcional com Supabase + Redis

## Testes Requeridos

- [ ] Teste: Supabase client nao e recriado em cada request (mock + assertion de instancia) (unit)
- [ ] Teste: payload invalido em `/auth/login` retorna 422 (integration)
- [ ] Teste: payload invalido em `/auth/signup` retorna 422 com campo obrigatorio faltante (integration)
- [ ] Teste: `backendAuth.ts` busca token fresco em cada chamada (unit)
- [ ] Teste: INSERT via RLS com user_id diferente do autenticado e rejeitado (integration SQL)
- [ ] Teste: migracoes aplicam em sequencia sem erro (CI)
- [ ] Teste: workflow de retencao executa sem erro (manual/CI dry-run)
- [ ] Teste: `docker compose up` completa sem erro e servicos respondem (manual/CI)

## Estimativa

- **Horas:** 22h (21.5h arredondado)
- **Complexidade:** Complexo (envolve backend, frontend BFF, database, CI/CD e infraestrutura local)

## Dependencias

- **Depende de:** Story 0.2 (PyJWT unificado, verify_aud, migracoes basicas), Story 1.2 (rate limiting ja implementado nos endpoints de auth)
- **Bloqueia:** Story 3.1 (testes de integracao CI precisam de migration runner; coverage precisa de auth consolidado)

## Definition of Done

- [ ] Codigo implementado e revisado
- [ ] Todos os testes passando (existentes + novos)
- [ ] Nenhuma regressao nos 1.349+ testes backend e 576+ testes frontend
- [ ] OpenAPI docs atualizados com modelos Pydantic
- [ ] Migration runner funcional no CI
- [ ] Review aprovado
- [ ] Sem regressoes em nenhum fluxo de autenticacao

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-SYS-005 (Alto), TD-SYS-006 (Alto), TD-SYS-007 (Alto), TD-DB-002 (Media), TD-SYS-013 (Medio), TD-DB-010 (Media), TD-SYS-010 (Medio)*
