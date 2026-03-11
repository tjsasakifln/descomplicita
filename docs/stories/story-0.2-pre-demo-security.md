# Story 0.2 -- Pre-Demo: Seguranca e Integridade

## Contexto

O assessment identificou riscos de seguranca e integridade que, embora nao visualmente aparentes, representam risco reputacional significativo caso alguem inspecione o repositorio ou o sistema durante uma demonstracao. O arquivo SQLite legado (`descomplicita.db`) pode conter dados de usuarios. A biblioteca python-jose, com CVEs conhecidos, ainda persiste em `supabase_auth.py`. A validacao de audience esta desabilitada, aceitando tokens de qualquer projeto Supabase. O schema do banco tem drift nao rastreado em migracoes. E o status `cancelled` nao esta no CHECK constraint do banco.

Estes itens sao **BLOQUEANTES** para demonstracao: investidores que inspecionem o repositorio encontrarao dependencias vulneraveis, arquivos de banco legado e codigo com bypass de validacao.

Referencia: `docs/prd/technical-debt-assessment.md` -- Secao "Pre-Demo Seguranca"

## Objetivo

Eliminar todos os riscos de seguranca e integridade de dados que comprometem a credibilidade do POC, garantindo repositorio limpo, dependencias seguras, autenticacao robusta e schema rastreavel.

## Tasks

- [x] **Task 1** (TD-SYS-001 / TD-DB-016) -- Remover SQLite legado: verificar conteudo de `descomplicita.db`, remover arquivo do repo, remover `aiosqlite==0.20.0` do requirements.txt, adicionar `*.db` ao `.gitignore`, verificar que nenhum import referencia aiosqlite ou descomplicita.db -- 1h
- [x] **Task 2** (TD-DB-014) -- Completar unificacao JWT: migrar `auth/supabase_auth.py` de `from jose import jwt` para PyJWT (`import jwt as pyjwt`), atualizar chamadas `jwt.decode()` para sintaxe PyJWT, remover `python-jose[cryptography]==3.3.0` do requirements.txt -- 1.5h
- [x] **Task 3** (TD-DB-005) -- Habilitar `verify_aud=True` com `audience="authenticated"` em `supabase_auth.py` (linha ~52). Depende de Task 2 (PyJWT unificado) -- 1h
- [x] **Task 4** (TD-DB-015) -- Criar migracao `003_add_default_auth_uid.sql` para rastrear `DEFAULT auth.uid()` em `saved_searches.user_id`. Garantir que recriar banco a partir das migracoes nao quebre INSERT de saved_searches -- 1h
- [x] **Task 5** (TD-DB-001 / TD-DB-017) -- Criar migracao com CHECK constraint em `search_history.status` para valores `queued`, `completed`, `failed`, `cancelled`. Corrigir `DELETE /buscar/{job_id}` para propagar status `cancelled` ao banco (em vez de `failed` via `job_store.fail()`) -- 1h
- [x] **Task 6** -- Limpeza do repositorio: corrigir versao no rodape (v2.0 -> dinamico), remover diretorio com nome invalido na raiz (TD-SYS-018), organizar markdowns soltos na raiz (TD-SYS-019) -- 1h

## Criterios de Aceite

- [x] Arquivo `descomplicita.db` removido do repositorio
- [x] `aiosqlite` removido de requirements.txt
- [x] `*.db` presente no `.gitignore`
- [x] Zero imports de `aiosqlite` ou `jose` no codebase (grep automatizado)
- [x] `python-jose` removido de requirements.txt
- [x] `supabase_auth.py` usa exclusivamente PyJWT para decodificacao de tokens
- [x] Tokens JWT com audience diferente de `"authenticated"` sao rejeitados
- [x] Migracao `003_add_default_auth_uid.sql` existe e e aplicavel
- [ ] INSERT em `saved_searches` sem `user_id` explicito funciona apos recriar banco a partir das migracoes
- [x] CHECK constraint em `search_history.status` aceita apenas `queued`, `completed`, `failed`, `cancelled`
- [x] `DELETE /buscar/{job_id}` grava status `cancelled` (nao `failed`) no banco
- [x] Rodape exibe versao correta (nao "v2.0" hardcoded)
- [x] Diretorio invalido removido da raiz
- [x] Markdowns da raiz organizados

## Testes Requeridos

- [x] Testes existentes de `supabase_auth.py` passam apos migracao para PyJWT (integration)
- [x] Teste: token JWT com `aud` diferente de `"authenticated"` retorna 401 (integration)
- [x] Teste: token JWT com `aud="authenticated"` e aceito normalmente (integration)
- [ ] Teste SQL: INSERT com status invalido falha com constraint violation (integration — requer Supabase staging)
- [ ] Teste SQL: INSERT com status `cancelled` e aceito (integration — requer Supabase staging)
- [x] Grep automatizado no CI: zero ocorrencias de `from jose`, `import jose`, `aiosqlite`, `descomplicita.db` (CI script)
- [x] Teste: `DELETE /buscar/{job_id}` retorna `{"status": "cancelled"}` e banco reflete status correto (integration)
- [ ] Recriar banco a partir das migracoes e testar INSERT em `saved_searches` sem `user_id` (integration — requer Supabase staging)

## Estimativa

- **Horas:** 6.5h
- **Complexidade:** Medio (migracao de biblioteca JWT requer cuidado com sintaxe; migracoes SQL requerem teste em ambiente staging)

## Dependencias

- **Depende de:** Nenhuma (Nivel 0 no grafo de dependencias)
- **Bloqueia:** Story 1.2 (Quick Wins Backend -- rate limiting e demais hardening dependem de auth estavel)
- **Dependencia interna:** Task 3 (verify_aud) depende de Task 2 (PyJWT unificado)

## Definition of Done

- [x] Codigo implementado e revisado
- [x] Todos os testes passando (existentes + novos)
- [x] Nenhuma regressao nos 1.349+ testes backend (1356 passed)
- [x] Migracoes SQL aplicaveis em sequencia (001 -> 002 -> 003 -> 004)
- [ ] Review aprovado
- [x] Grep automatizado confirma zero referencias a bibliotecas/arquivos legados

---

*Story criada em 2026-03-11 por @pm (Sage)*
*Debitos: TD-SYS-001 (Critico), TD-DB-016 (Alta), TD-DB-014 (Media), TD-DB-005 (Media), TD-DB-015 (Alta), TD-DB-001 (Alta), TD-DB-017 (Baixa), TD-SYS-018 (Baixo), TD-SYS-019 (Baixo), TD-UX-007 (Baixo)*
