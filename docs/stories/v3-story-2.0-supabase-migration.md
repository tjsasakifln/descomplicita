# v3-story-2.0: Supabase Migration & User Identity

## Contexto

O Descomplicita usa SQLite em filesystem efemero (Railway), o que significa que todos os dados sao perdidos a cada deploy. Nao ha modelo de identidade de usuario, nao ha isolamento multi-tenant (`get_recent_searches()` sem WHERE user_id), nao ha sistema de migracoes (schema via CREATE TABLE IF NOT EXISTS), e nao ha backups.

Esta migracao resolve simultaneamente 7 debt items e e fundacao para saved searches server-side, persistencia real, e multi-tenancy. O @data-engineer recomenda supabase-py para CRUD e Supabase CLI para migracoes.

## Objetivo

Migrar de SQLite efemero para Supabase PostgreSQL, implementar modelo de identidade de usuario, sistema de migracoes, e isolamento multi-tenant. Estabelecer fundacao de persistencia para producao.

## Debt Items Addressed

| ID | Descricao | Severidade | Horas Est. |
|----|-----------|-----------|------------|
| SYS-001 | SQLite em filesystem efemero (Railway) | Critica | 16h (compartilhado com DB-002) |
| SYS-002 | Sem modelo de identidade de usuario | Critica | 8h (design + implementacao basica) |
| DB-001 | Sem isolamento multi-user/multi-tenant | Alta | 4h |
| DB-002 | Storage efemero no Railway/Vercel | Alta | (compartilhado com SYS-001) |
| DB-003 | Sem sistema de migracao | Alta | 6h |
| DB-008 | Sem politica de retencao/cleanup | Baixa | (resolvido por Supabase) |
| DB-010 | Sem estrategia de backup | Baixa | (resolvido por Supabase) |
| DB-012 | Supabase env vars definidas mas nao utilizadas | Baixa | 0.5h |

## Tasks

- [ ] Task 1: Design do modelo de identidade (SYS-002) -- definir schema de users, auth flow com Supabase Auth, mapeamento de localStorage para server-side
- [ ] Task 2: Configurar projeto Supabase -- criar projeto, configurar env vars, setup de desenvolvimento local com Supabase CLI
- [ ] Task 3: Criar migracoes iniciais com Supabase CLI -- tabelas users, searches, search_items, user_preferences com RLS (Row Level Security)
- [ ] Task 4: Implementar camada de acesso a dados com supabase-py -- substituir SQLite CRUD por Supabase client
- [ ] Task 5: Adicionar user_id a todas as queries de busca (DB-001) -- WHERE user_id em get_recent_searches(), saved_searches, etc.
- [ ] Task 6: Configurar Supabase Auth -- signup/login flow basico, JWT validation via Supabase (substitui JWT customizada parcialmente)
- [ ] Task 7: Migrar dados existentes -- script de migracao one-time para dados de localStorage (se aplicavel)
- [ ] Task 8: Conectar env vars Supabase existentes (DB-012) -- SUPABASE_URL, SUPABASE_KEY ja definidas no env
- [ ] Task 9: Configurar backups automaticos (DB-010) -- Supabase gerencia nativamente, validar configuracao
- [ ] Task 10: Configurar politica de retencao (DB-008) -- scheduled cleanup de searches antigas (>90 dias)
- [ ] Task 11: Testes de integracao pos-migracao -- CRUD completo, RLS validation, multi-user isolation

## Criterios de Aceite

- [ ] Dados sobrevivem a deploy no Railway (verificar com deploy + consulta)
- [ ] Cada usuario ve apenas suas proprias buscas (RLS + user_id isolation)
- [ ] Sistema de migracoes funcional via Supabase CLI (`supabase db push`)
- [ ] Backups automaticos configurados (Supabase dashboard)
- [ ] Env vars SUPABASE_URL e SUPABASE_KEY utilizadas pelo backend
- [ ] Auth flow basico funcional: signup, login, token refresh
- [ ] Todas as queries existentes funcionam com PostgreSQL (sem SQL incompativel)
- [ ] Testes de integracao passando para CRUD basico

## Testes Requeridos

| ID | Teste | Tipo | Prioridade |
|----|-------|------|-----------|
| CP4/CP5 | Supabase CRUD basico pos-migracao | Integration | P1 |
| -- | RLS validation: usuario A nao ve dados de usuario B | Integration | P1 |
| -- | Migracao de schema: `supabase db push` sem erros | CI | P2 |
| -- | PostgreSQL compatibility: todas as queries existentes | Integration | P2 |
| -- | Auth flow: signup, login, token refresh, logout | Integration | P2 |

## Estimativa

- Horas: 32h
- Complexidade: Complexa

## Dependencias

- SYS-002 (design de identidade) deve ser feito ANTES da migracao de schema.
- v3-story-2.0 BLOQUEIA: v3-story-3.0 (saved searches server-side depende de persistencia + user_id).

## Definition of Done

- [ ] Code implemented and reviewed
- [ ] Supabase configurado e acessivel em producao
- [ ] Migracoes aplicadas com sucesso
- [ ] Tests written and passing (CRUD, RLS, auth)
- [ ] No regressions in existing tests
- [ ] Deploy realizado com dados persistentes verificados
- [ ] Acceptance criteria verified
