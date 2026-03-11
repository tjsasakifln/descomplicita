## Database Specialist Review
**Revisor:** @data-engineer (Forge)
**Data:** 2026-03-11
**Commit base:** 2a76827b (HEAD de main)
**Metodo:** Validacao cruzada contra codigo-fonte real (migracoes SQL, database.py, auth/*.py, savedSearchesServer.ts)

---

### Debitos Validados

| ID | Debito | Sev. Original | Sev. Ajustada | Horas | Prioridade | Notas |
|----|--------|---------------|---------------|-------|------------|-------|
| TD-DB-001 | CHECK constraint em `search_history.status` | Media | **Alta** | 0.5 | P1 | **Ajuste para cima.** O cancelamento de jobs (`DELETE /buscar/{job_id}`) chama `job_store.fail()` que grava `status='failed'`, mas a API retorna `{"status": "cancelled"}`. A funcao `cleanup_old_searches()` filtra apenas `completed` e `failed`. Se futuramente o status `cancelled` for gravado no DB (intencao logica clara), registros cancelados nunca seriam limpos. O CHECK deve incluir `cancelled`: `CHECK (status IN ('queued','completed','failed','cancelled'))`. |
| TD-DB-002 | RLS granular por operacao (WITH CHECK no INSERT) | Media | Media | 2 | P2 | Confirmado real. Porem, mitigacao parcial: o frontend (`savedSearchesServer.ts`) nao envia `user_id` no INSERT de `saved_searches` -- depende de um `DEFAULT auth.uid()` que **nao esta nas migracoes** (provavelmente configurado direto no dashboard Supabase). Isso significa que o usuario nao consegue forjar `user_id` de terceiro neste caso especifico. Ainda assim, `search_history` e `user_preferences` sao acessadas pelo backend com service_role (bypassa RLS), entao o risco real e limitado ao acesso direto via anon key. Manter como Media. |
| TD-DB-003 | UNIQUE em `users.email` | Baixa | Baixa | 0.5 | P8 | Confirmado. O trigger `handle_new_user()` insere com o email de `auth.users`, que ja tem UNIQUE interno. O risco e apenas teorico (insercao manual via service_role). Para POC, prioridade baixa. |
| TD-DB-004 | Unificar bibliotecas JWT (python-jose -> PyJWT) | Baixa | **Removido** | -- | -- | **JA RESOLVIDO em v3-story-3.3.** O `auth/jwt.py` ja usa `import jwt as pyjwt` (PyJWT). Porem, `auth/supabase_auth.py` **ainda usa `from jose import jwt`** (python-jose). E `requirements.txt` ainda lista `python-jose[cryptography]==3.3.0`. Portanto, a unificacao esta **incompleta**. Reabrir como debito real -- ver "Debitos Adicionados" (TD-DB-014). |
| TD-DB-005 | Habilitar `verify_aud` no Supabase JWT | Media | Media | 1 | P3 | Confirmado. `supabase_auth.py` linha 52: `options={"verify_aud": False}`. O audience padrao dos tokens Supabase e `"authenticated"` (claim `aud`). Habilitar requer setar `audience="authenticated"` no decode. Estimativa de 1h e adequada. |
| TD-DB-006 | Cleanup em batches (evitar locks) | Media | **Baixa** | 1 | P9 | **Rebaixado.** Para volume de POC (<1000 buscas/mes, retencao 90 dias), o DELETE sem LIMIT em `cleanup_old_searches()` nunca processara mais que ~3000 rows. Lock de milissegundos. So se torna problema com >100K registros. |
| TD-DB-007 | Indice parcial para cleanup | Baixa | Baixa | 0.5 | P10 | Confirmado, mas o indice `idx_search_history_status` ja cobre o filtro `status IN (...)`. O indice parcial so traria beneficio se a tabela tivesse >50K rows com distribuicao desigual de status. Para POC, nice-to-have. |
| TD-DB-008 | Limite em `saved_searches.name` (CHECK length) | Baixa | Baixa | 0.5 | P11 | Confirmado. `saveServerSearch()` faz apenas `name.trim()` sem truncar. Um nome de 10KB passaria. CHECK simples resolve. |
| TD-DB-009 | `updated_at` em `saved_searches` | Baixa | Baixa | 0.5 | P12 | Confirmado. A tabela usa `last_used_at` como proxy, mas semanticamente `updated_at` + trigger seria consistente com as outras 3 tabelas. Baixa prioridade. |
| TD-DB-010 | Ativar pg_cron ou cron externo para retention | Media | Media | 2 | P5 | Confirmado. A funcao existe mas nunca e chamada. Para POC, um GitHub Actions schedule semanal (`SELECT public.cleanup_old_searches(90)`) via `supabase` CLI ou API e suficiente. `pg_cron` requer Supabase Pro. |
| TD-DB-011 | Indice em `users.email` | Baixa | Baixa | 0.5 | P13 | Confirmado mas desnecessario para POC. Nenhuma query no codigo busca por `users.email`. O script de migracao (`migrate_sqlite_to_supabase.py`) e one-time. |
| TD-DB-012 | Limite de saved_searches no DB (trigger/constraint) | Baixa | Baixa | 1 | P7 | Confirmado. `savedSearchesServer.ts` faz `loadServerSearches()` inteira para checar contagem, o que e ineficiente mas funcional. Trigger com `COUNT(*)` seria mais robusto mas para POC o codigo e suficiente. |
| TD-DB-013 | Metricas de falha de persistencia (Database silencioso) | Baixa | Baixa | 1.5 | P6 | Confirmado. Todas as operacoes em `database.py` fazem `except Exception: logger.warning(...)` e retornam silenciosamente. Para POC aceitavel; para producao, precisa de contadores (ex: `statsd`, `prometheus`). |

---

### Debitos Adicionados

| ID | Debito | Severidade | Horas | Impacto | Justificativa |
|----|--------|------------|-------|---------|---------------|
| **TD-DB-014** | **Unificacao JWT incompleta: `supabase_auth.py` ainda usa python-jose** | Media | 1.5 | Superficie de ataque, deps | O DRAFT marcou TD-DB-004 como "unificar JWT libs", e o MEMORY diz que v3-story-3.3 migrou para PyJWT. Mas verificacao do codigo mostra que `auth/supabase_auth.py` linhas 46-54 ainda usa `from jose import jwt`. `requirements.txt` linha 30 ainda lista `python-jose[cryptography]==3.3.0`. A unificacao esta pela metade. Precisa migrar `supabase_auth.py` para PyJWT e remover `python-jose` do requirements. 1.5h (mais que o 1h original porque envolve testar claims do Supabase com PyJWT). |
| **TD-DB-015** | **Schema drift: `DEFAULT auth.uid()` em `saved_searches.user_id` nao rastreado em migracoes** | Alta | 1 | Rastreabilidade, reproducibilidade | O INSERT em `savedSearchesServer.ts` (linhas 73-82) nao envia `user_id`, mas a coluna e `NOT NULL` sem DEFAULT na migracao `001_initial_schema.sql`. O codigo funciona em producao, o que significa que `DEFAULT auth.uid()` foi adicionado diretamente no dashboard do Supabase. Mudancas de schema fora das migracoes sao um risco operacional: se recriar o DB a partir das migracoes, o INSERT de saved_searches falhara. Solucao: adicionar migracao `003_add_default_auth_uid.sql` com `ALTER TABLE saved_searches ALTER COLUMN user_id SET DEFAULT auth.uid()`. |
| **TD-DB-016** | **SQLite legado ainda presente: `descomplicita.db` (arquivo fisico) + `aiosqlite` no requirements.txt** | Alta | 0.5 | Seguranca, limpeza | Relacionado ao TD-SYS-001 do DRAFT, mas complementa: `backend/descomplicita.db` existe fisicamente no repo (verificado). `requirements.txt` linha 26 ainda tem `aiosqlite==0.20.0`. O script de migracao (`scripts/migrate_sqlite_to_supabase.py`) deve ser mantido como referencia mas o `.db` e a dependencia devem ser removidos. Verificar se o `.db` contem dados sensiveis antes de remover (historico de buscas com user_ids). |
| **TD-DB-017** | **Status `cancelled` nao propagado ao banco de dados** | Baixa | 0.5 | Consistencia de dados | O endpoint `DELETE /buscar/{job_id}` (main.py linha 997) chama `job_store.fail(job_id, "Busca cancelada pelo usuario.")` que grava `status='failed'` no Redis e no DB via `database.fail_search()`. A API retorna `{"status": "cancelled"}` mas o DB registra `failed`. Semanticamente incorreto. Solucao: criar metodo `cancel_search()` em `database.py` ou adicionar parametro de status ao `fail_search()`. |

---

### Debitos Removidos/Rebaixados

| ID | Acao | Justificativa |
|----|------|---------------|
| TD-DB-004 | **Removido (substituido por TD-DB-014)** | O debito original dizia "Unificar python-jose -> PyJWT". A unificacao ja comecou em v3-story-3.3 (`auth/jwt.py` usa PyJWT). Mas `auth/supabase_auth.py` ainda usa python-jose. TD-DB-014 captura o trabalho restante com escopo correto. |
| TD-DB-006 | **Rebaixado de Media para Baixa** | Volume de POC (<3000 rows em 90 dias) nao justifica complexidade de DELETE em batches. O lock seria de <100ms. Reavaliar se ultrapassar 50K registros. |

---

### Respostas ao Architect

**1. TD-DB-002 (RLS granular): O `FOR ALL` com `USING` cobre o caso de INSERT?**

No PostgreSQL, quando uma policy e `FOR ALL` com apenas `USING` (sem `WITH CHECK`), a clausula `USING` e usada implicitamente como `WITH CHECK` tambem. Isso significa que:

- **SELECT/UPDATE/DELETE**: filtram por `auth.uid() = user_id` -- correto.
- **INSERT**: a `WITH CHECK` implicita verifica se o registro inserido satisfaz `auth.uid() = user_id` -- ou seja, o usuario **NAO consegue** inserir com `user_id` de terceiro.

**Conclusao: O risco de insercao cross-usuario e MENOR do que reportei no audit original.** O PostgreSQL protege implicitamente. Porem, a recomendacao de separar policies por operacao continua valida por clareza e manutenibilidade -- policies explicitas por operacao documentam a intencao e facilitam auditoria. Manter como Media por boas praticas, nao por vulnerabilidade ativa.

**Dado adicional descoberto:** O `savedSearchesServer.ts` faz INSERT sem enviar `user_id` (linhas 73-82). Isso so funciona se existe `DEFAULT auth.uid()` na coluna, que **nao esta nas migracoes**. Ver TD-DB-015.

**2. TD-DB-005 (verify_aud): Qual e o valor correto do `aud` claim?**

Tokens do Supabase Auth usam `"aud": "authenticated"` para usuarios logados. O valor esta hardcoded no GoTrue (servico de auth do Supabase). Para habilitar:

```python
payload = jwt.decode(
    token, secret, algorithms=["HS256"],
    options={"verify_aud": True},
    audience="authenticated",
)
```

Documentacao: https://supabase.com/docs/guides/auth/jwts -- o claim `aud` e sempre `"authenticated"` para tokens de sessao.

**3. TD-DB-010 (retention policy): O plano atual suporta pg_cron?**

`pg_cron` requer Supabase Pro ou superior. Para o plano Free/POC, as alternativas em ordem de preferencia:

1. **GitHub Actions schedule** (recomendado para POC): workflow `cron: '0 3 * * 0'` (semanal) que executa `SELECT public.cleanup_old_searches(90)` via `supabase` CLI ou HTTP API do PostgREST.
2. **Railway cron job**: se o backend estiver no Railway, usar o cron nativo.
3. **Endpoint protegido**: criar `POST /admin/cleanup` com API key, chamar via cron externo.

Para POC, opcao 1 e zero-cost e suficiente.

**4. TD-DB-006 (cleanup batches): Risco real no POC?**

**Nao.** Com <1000 buscas/mes e retencao de 90 dias, o DELETE processara no maximo ~3000 rows. Em PostgreSQL, isso leva <100ms e o lock e trivial. O batching so se justifica com >50K registros ou se houver queries concorrentes de alta frequencia na mesma tabela. **Rebaixei para Baixa.**

**5. TD-SYS-013 (migration runner): Preferencia?**

Para o estagio atual, recomendo:

1. **`supabase db push`** (CLI oficial) para aplicar migracoes em staging/producao. Simples, integrado, sem dependencias extras.
2. Manter os arquivos `.sql` numerados em `backend/supabase/migrations/` como fonte de verdade.
3. **NAO usar Alembic** -- e overkill para 4 tabelas e adiciona complexidade (ORM mapping) que nao temos.
4. Script SQL customizado como fallback se a CLI nao estiver disponivel no CI.

**Urgencia adicional:** Descobri que existe schema drift (TD-DB-015). Um migration runner e pre-requisito para corrigir isso.

**6. Dados legados no SQLite:**

O arquivo `backend/descomplicita.db` ainda existe no repositorio (confirmado via `ls`). A migracao de dados para Supabase foi completada em v3-story-2.0, mas o arquivo nao foi removido. O script `migrate_sqlite_to_supabase.py` referencia `descomplicita.db` como default path.

**Recomendacao:** Verificar conteudo do `.db` antes de remover (pode conter job_ids, datas de busca, user_ids). Se nao houver dados sensiveis, remover o arquivo e a dependencia `aiosqlite` do `requirements.txt`. Manter o script de migracao como referencia historica mas adicionar `.db` ao `.gitignore`.

---

### Estimativa de Custos Detalhada

| Item | ID | Horas | Complexidade | Dependencias |
|------|----|-------|-------------|--------------|
| CHECK constraint em status (incluir `cancelled`) | TD-DB-001 | 0.5 | Trivial | Nenhuma (migracao SQL simples) |
| Schema drift: rastrear `DEFAULT auth.uid()` | TD-DB-015 | 1 | Baixa | TD-SYS-013 (migration runner) ou aplicar direto via CLI |
| Habilitar `verify_aud` no Supabase JWT | TD-DB-005 | 1 | Baixa | TD-DB-014 (migrar supabase_auth.py para PyJWT primeiro) |
| Completar unificacao JWT (python-jose -> PyJWT) | TD-DB-014 | 1.5 | Media | Testar com tokens Supabase reais |
| RLS granular por operacao | TD-DB-002 | 2 | Media | Nenhuma (pode ser feito independente) |
| Ativar retention policy (GitHub Actions) | TD-DB-010 | 1.5 | Baixa | Acesso ao repo para criar workflow |
| Remover SQLite legado + aiosqlite | TD-DB-016 | 0.5 | Trivial | Verificar conteudo do .db antes |
| Status `cancelled` no DB | TD-DB-017 | 0.5 | Trivial | TD-DB-001 (CHECK constraint) |
| Metricas de falha de persistencia | TD-DB-013 | 1.5 | Media | Framework de metricas (ou logger estruturado) |
| Limite em `saved_searches.name` | TD-DB-008 | 0.5 | Trivial | Nenhuma |
| `updated_at` em `saved_searches` | TD-DB-009 | 0.5 | Trivial | Nenhuma |
| UNIQUE em `users.email` | TD-DB-003 | 0.5 | Trivial | Verificar se ha duplicatas existentes |
| Indice parcial para cleanup | TD-DB-007 | 0.5 | Trivial | Nenhuma |
| Indice em `users.email` | TD-DB-011 | 0.5 | Trivial | Nenhuma |
| Limite de saved_searches no DB (trigger) | TD-DB-012 | 1 | Media | Nenhuma |
| **Total** | | **~12.5h** | | |

**Nota sobre totais:** O total base caiu de ~14.5h para ~12.5h com os ajustes (remocao do TD-DB-004 duplicado, ajuste do TD-DB-010 de 2h para 1.5h). Os novos debitos (TD-DB-014 a TD-DB-017) adicionam ~3.5h. **Total efetivo: ~16h.**

---

### Recomendacoes de Ordem de Resolucao

#### ANTES de producao (obrigatorio) -- ~6.5h

| Ordem | ID | Debito | Horas | Justificativa |
|-------|----|--------|-------|---------------|
| 1 | TD-DB-016 | Remover SQLite legado (`descomplicita.db` + `aiosqlite`) | 0.5 | **Seguranca.** Arquivo pode conter dados de usuarios. Dependencia desnecessaria. Quick win. |
| 2 | TD-DB-015 | Rastrear `DEFAULT auth.uid()` em migracao | 1 | **Reproducibilidade.** Sem isso, reconstruir o DB a partir das migracoes quebra o INSERT de saved_searches. |
| 3 | TD-DB-001 | CHECK constraint em status (incluir `cancelled`) | 0.5 | **Integridade.** Previne valores invalidos e prepara para status `cancelled` futuro. |
| 4 | TD-DB-014 | Completar unificacao JWT (supabase_auth.py -> PyJWT) | 1.5 | **Superficie de ataque.** Duas libs JWT e risco desnecessario. `python-jose` tem CVEs conhecidos. Pre-requisito para TD-DB-005. |
| 5 | TD-DB-005 | Habilitar `verify_aud` em Supabase JWT | 1 | **Seguranca.** Aceitar tokens de qualquer projeto Supabase e inaceitavel em producao. |
| 6 | TD-DB-002 | RLS granular por operacao | 2 | **Boas praticas.** Risco real e baixo (PostgreSQL protege implicitamente), mas policies explicitas sao auditaveis. |

#### PODE esperar (pos-lancamento, primeiro mes) -- ~5.5h

| Ordem | ID | Debito | Horas | Justificativa |
|-------|----|--------|-------|---------------|
| 7 | TD-DB-010 | Ativar retention policy | 1.5 | Dados so acumulam apos meses de uso. |
| 8 | TD-DB-017 | Status `cancelled` no DB | 0.5 | Impacto semantico, nao funcional. |
| 9 | TD-DB-013 | Metricas de falha de persistencia | 1.5 | So importa com volume real de usuarios. |
| 10 | TD-DB-008 | Limite em `saved_searches.name` | 0.5 | Edge case improvavel. |
| 11 | TD-DB-012 | Limite de saved_searches no DB (trigger) | 1 | Codigo ja enforca no frontend. |

#### NICE-TO-HAVE (so se escalar) -- ~3h

| Ordem | ID | Debito | Horas | Justificativa |
|-------|----|--------|-------|---------------|
| 12 | TD-DB-009 | `updated_at` em `saved_searches` | 0.5 | Consistencia cosmetica. |
| 13 | TD-DB-003 | UNIQUE em `users.email` | 0.5 | `auth.users` ja protege. |
| 14 | TD-DB-007 | Indice parcial para cleanup | 0.5 | So com >50K rows. |
| 15 | TD-DB-011 | Indice em `users.email` | 0.5 | Nenhuma query usa. |
| 16 | TD-DB-006 | Cleanup em batches | 1 | So com >50K rows. |

---

### Riscos de Seguranca (DB)

Ordenados por urgencia:

| # | Risco | Severidade | ID | Acao |
|---|-------|-----------|-----|------|
| 1 | **`verify_aud: False`** permite aceitar tokens JWT de qualquer projeto Supabase que compartilhe o mesmo JWT secret (improvavel mas possivel em ambientes multi-tenant) | **Alta** | TD-DB-005 | Habilitar `verify_aud=True` com `audience="authenticated"` |
| 2 | **Arquivo `descomplicita.db` no repositorio** pode conter historico de buscas de usuarios, incluindo UFs, setores e termos buscados | **Alta** | TD-DB-016 | Verificar conteudo, remover do repo, adicionar ao `.gitignore` |
| 3 | **Duas bibliotecas JWT** (`python-jose` + `PyJWT`) aumentam superficie de ataque; `python-jose` tem CVEs conhecidos e esta sem manutencao ativa | **Media** | TD-DB-014 | Migrar `supabase_auth.py` para PyJWT, remover `python-jose` |
| 4 | **Schema drift nao rastreado** (`DEFAULT auth.uid()` fora das migracoes) pode causar falha catastrofica ao recriar o DB | **Media** | TD-DB-015 | Criar migracao `003_add_default_auth_uid.sql` |
| 5 | **RLS sem policies explicitas por operacao** dificulta auditoria de seguranca, embora PostgreSQL proteja implicitamente via `USING` como `WITH CHECK` | **Baixa** | TD-DB-002 | Separar policies por SELECT/INSERT/UPDATE/DELETE |
| 6 | **`handle_new_user()` com SECURITY DEFINER** executa com privilegios elevados; se a funcao for comprometida (SQL injection no email), pode alterar qualquer dado | **Baixa** | -- | O risco e teorico: o email vem de `auth.users` (controlado pelo Supabase). Sem acao imediata. |
| 7 | **Falhas de persistencia silenciosas** em `database.py` (todos os metodos fazem `except: log + return None`) podem mascarar perda de dados | **Baixa** | TD-DB-013 | Adicionar contadores/alertas |

---

### Nota Final

O schema esta solido para um POC. Os debitos identificados sao gerenciaveis e nenhum e bloqueante para um lancamento controlado (beta fechado). Os 6 itens marcados como "antes de producao" totalizam apenas **6.5h** de trabalho e eliminam os riscos de seguranca mais relevantes.

A descoberta mais importante desta revisao e o **schema drift** (TD-DB-015): existe pelo menos uma alteracao de schema (`DEFAULT auth.uid()` em `saved_searches.user_id`) que nao esta rastreada nas migracoes. Isso indica que podem existir outras alteracoes feitas diretamente no dashboard do Supabase. Recomendo um audit completo comparando o schema vivo (`pg_dump --schema-only`) com as migracoes antes de considerar o DB como "production-ready".
