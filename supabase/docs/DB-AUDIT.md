# Auditoria do Banco de Dados - Descomplicita

> **Data:** 2026-03-11 | **Agente:** @data-engineer (Forge)
> **Escopo:** Schema PostgreSQL (Supabase), queries no backend e frontend, RLS, seguranca
> **Nivel:** POC (Proof of Concept)
> **Escala de severidade:** Critica > Alta > Media > Baixa

---

## 1. Resumo Executivo

O schema e enxuto e bem estruturado para um POC: 4 tabelas, RLS habilitada em todas, FKs com CASCADE, triggers de auto-update e criacao automatica de usuario. A arquitetura multi-tenant esta implementada com isolamento por `user_id` tanto no codigo (backend) quanto via RLS (frontend).

**Nota geral: 7/10** -- Solido para POC. Debitos tecnicos identificados sao gerenciaveis e devem ser resolvidos antes de escala em producao.

---

## 2. Qualidade do Schema

### Pontos positivos
- Tipos PostgreSQL nativos adequados: UUID, TIMESTAMPTZ, JSONB, TEXT[], DATE
- Constraints NOT NULL nas colunas obrigatorias
- FKs com ON DELETE CASCADE eliminam registros orfaos
- UNIQUE constraint em `job_id` e `(user_id, key)`
- Trigger SECURITY DEFINER para criacao automatica de perfil
- Funcao de retencao preparada (cleanup_old_searches)

### Pontos negativos
- `status` em `search_history` e TEXT livre sem CHECK constraint
- `setor_id` nao referencia tabela de setores (possivelmente dinamico/externo)
- Sem validacao de formato no array `ufs`
- `search_params` em `saved_searches` e JSONB sem schema validation
- `saved_searches` nao tem coluna `updated_at` (inconsistente com demais tabelas)

---

## 3. Analise de Indices

### Indices existentes (adequados)

| Tabela | Indice | Colunas | Cobre query |
|--------|--------|---------|-------------|
| `search_history` | `idx_search_history_user_created` | `(user_id, created_at DESC)` | `get_recent_searches()` |
| `search_history` | `idx_search_history_setor` | `(setor_id)` | Filtragem por setor |
| `search_history` | `idx_search_history_status` | `(status)` | `cleanup_old_searches()` |
| `search_history` | (implicito UNIQUE) | `(job_id)` | `complete_search()`, `fail_search()` |
| `user_preferences` | `idx_user_preferences_user` | `(user_id)` | Lookup por usuario |
| `user_preferences` | (implicito UNIQUE) | `(user_id, key)` | Upsert de preferencia |
| `saved_searches` | `idx_saved_searches_user` | `(user_id, last_used_at DESC)` | `loadServerSearches()` |

### Indices ausentes (recomendados)

| Tabela | Indice sugerido | Justificativa | Prioridade |
|--------|-----------------|---------------|------------|
| `users` | `idx_users_email` | Script de migracao e possiveis lookups futuros buscam por email | Baixa |
| `search_history` | Indice parcial `(created_at) WHERE status IN ('completed','failed')` | Otimizaria `cleanup_old_searches()` em tabelas grandes | Baixa |

---

## 4. Analise de RLS

### Cobertura

| Tabela | RLS | Policy | Tipo |
|--------|-----|--------|------|
| `users` | Habilitada | `users_own_data` | FOR ALL |
| `search_history` | Habilitada | `search_history_own_data` | FOR ALL |
| `user_preferences` | Habilitada | `user_preferences_own_data` | FOR ALL |
| `saved_searches` | Habilitada | `saved_searches_own_data` | FOR ALL |

### Lacunas identificadas

| # | Lacuna | Risco | Severidade |
|---|--------|-------|------------|
| 1 | Policies usam `FOR ALL` sem separacao por operacao (SELECT, INSERT, UPDATE, DELETE) | Nao ha controle granular -- nao valida que `user_id = auth.uid()` em INSERTs | Media |
| 2 | Sem policy WITH CHECK para INSERT | Via anon key, usuario autenticado poderia inserir `user_id` de outro usuario em `search_history`, `user_preferences` e `saved_searches` | Media |
| 3 | Backend bypassa RLS via service_role key | Correto por design, mas nao documentado explicitamente no schema | Baixa |

**Nota:** A lacuna #2 e parcialmente mitigada pelo fato de o frontend so acessar diretamente `saved_searches`, e o backend sempre passa `user_id` do token autenticado.

---

## 5. Integridade de Dados

| # | Item | Tabela | Severidade |
|---|------|--------|------------|
| 1 | `status` sem CHECK constraint | `search_history` | Media |
| 2 | `ufs` aceita qualquer string no array | `search_history` | Baixa |
| 3 | `setor_id` sem FK para tabela de referencia | `search_history` | Baixa |
| 4 | `email` sem UNIQUE em `public.users` | `users` | Baixa |
| 5 | `name` sem limite de tamanho | `saved_searches` | Baixa |
| 6 | Limite de 10 buscas salvas enforced apenas no codigo | `saved_searches` | Baixa |
| 7 | `search_params` sem schema validation | `saved_searches` | Baixa |

---

## 6. Performance

| # | Preocupacao | Impacto | Severidade |
|---|-------------|---------|------------|
| 1 | `cleanup_old_searches()` faz DELETE sem LIMIT | Lock prolongado em tabelas com muitos registros | Media |
| 2 | `saveServerSearch()` faz `loadServerSearches()` inteiro para checar contagem | Query extra; `COUNT(*)` seria mais eficiente | Baixa |
| 3 | `get_or_create_user()` faz SELECT + INSERT condicional | Race condition possivel em concorrencia alta | Baixa |
| 4 | Sem particionamento em `search_history` | Tabela cresce indefinidamente (mitigado pela funcao de cleanup) | Baixa |
| 5 | `loadServerSearches()` nao filtra por `user_id` explicitamente | Depende da RLS para filtrar; funcional, mas semanticamente fragil | Baixa |

---

## 7. Seguranca

| # | Item | Descricao | Severidade |
|---|------|-----------|------------|
| 1 | Service role key no backend | Se vazar, acesso total ao banco sem RLS | Critica (operacional) |
| 2 | `verify_aud: False` na validacao do Supabase JWT | Aceita tokens de qualquer projeto Supabase com o mesmo secret | Media |
| 3 | `handle_new_user()` e SECURITY DEFINER | Executa com privilegios elevados; se comprometida, pode alterar qualquer dado | Media |
| 4 | RLS INSERT sem WITH CHECK | Ver lacuna #2 na secao RLS | Media |
| 5 | Duas bibliotecas JWT (`python-jose` + `PyJWT`) | Superficie de ataque duplicada e inconsistencia | Baixa |
| 6 | Degradacao silenciosa no `Database` | Falhas de persistencia retornam `None`/`[]` sem alertas | Baixa |

---

## 8. Divida Tecnica

| ID | Descricao | Severidade | Horas Est. | Impacto |
|----|-----------|------------|------------|---------|
| TD-DB-001 | **CHECK constraint em `status`** -- Adicionar `CHECK (status IN ('queued','completed','failed','cancelled'))` em `search_history.status` | Media | 0.5h | Previne dados invalidos no campo status |
| TD-DB-002 | **RLS granular por operacao** -- Substituir `FOR ALL` por policies separadas (SELECT, INSERT, UPDATE, DELETE) com `WITH CHECK (user_id = auth.uid())` no INSERT | Media | 2h | Fecha brecha de insercao cross-usuario via client-side |
| TD-DB-003 | **UNIQUE em `users.email`** -- Adicionar constraint UNIQUE na coluna `email` da tabela `users` | Baixa | 0.5h | Protege contra duplicatas edge-case |
| TD-DB-004 | **Unificar bibliotecas JWT** -- Migrar `auth/supabase_auth.py` de `python-jose` para `PyJWT` (ja usado em `auth/jwt.py`) | Baixa | 1h | Reduz dependencias e superficie de ataque |
| TD-DB-005 | **Habilitar `verify_aud` no Supabase JWT** -- Configurar audience validation em `supabase_auth.py` para aceitar apenas tokens do projeto | Media | 1h | Evita aceitar tokens de projetos Supabase alheios |
| TD-DB-006 | **Cleanup em batches** -- Alterar `cleanup_old_searches()` para deletar em lotes de 1000 com loop, evitando locks prolongados | Media | 1h | Estabilidade em tabelas grandes |
| TD-DB-007 | **Indice parcial para cleanup** -- `CREATE INDEX idx_sh_cleanup ON search_history(created_at) WHERE status IN ('completed','failed')` | Baixa | 0.5h | Otimiza funcao de retencao |
| TD-DB-008 | **Limite em `saved_searches.name`** -- Adicionar `CHECK (length(name) <= 200)` | Baixa | 0.5h | Previne strings excessivas |
| TD-DB-009 | **`updated_at` em `saved_searches`** -- Adicionar coluna e trigger, consistente com as demais tabelas | Baixa | 0.5h | Consistencia do schema |
| TD-DB-010 | **Ativar `pg_cron` ou cron externo** -- Agendar `cleanup_old_searches(90)` diariamente | Media | 2h | Sem agendamento, dados antigos acumulam indefinidamente |
| TD-DB-011 | **Indice em `users.email`** -- B-tree para lookups por email | Baixa | 0.5h | Performance em buscas futuras por email |
| TD-DB-012 | **Limite de saved_searches no DB** -- Adicionar trigger ou constraint para limitar a 10 por usuario (hoje enforced so no codigo) | Baixa | 1h | Defesa em profundidade |
| TD-DB-013 | **Metricas de falha de persistencia** -- Emitir contadores estruturados quando `Database` falha silenciosamente | Baixa | 1.5h | Observabilidade de falhas |

---

## 9. Priorizacao Recomendada

### Antes de producao (Media/Alta)

| Prioridade | ID | Descricao | Horas |
|------------|-----|-----------|-------|
| 1 | TD-DB-002 | RLS granular com WITH CHECK | 2h |
| 2 | TD-DB-005 | Audience validation no JWT | 1h |
| 3 | TD-DB-001 | CHECK constraint em status | 0.5h |
| 4 | TD-DB-006 | Cleanup em batches | 1h |
| 5 | TD-DB-010 | Ativar retention policy | 2h |

### Melhorias de qualidade (Baixa)

| Prioridade | ID | Descricao | Horas |
|------------|-----|-----------|-------|
| 6 | TD-DB-004 | Unificar JWT libs | 1h |
| 7 | TD-DB-003 | UNIQUE em email | 0.5h |
| 8 | TD-DB-007 | Indice parcial cleanup | 0.5h |
| 9 | TD-DB-008 | Limite em name | 0.5h |
| 10 | TD-DB-009 | updated_at em saved_searches | 0.5h |
| 11 | TD-DB-011 | Indice em email | 0.5h |
| 12 | TD-DB-012 | Limite de saved_searches no DB | 1h |
| 13 | TD-DB-013 | Metricas de falha | 1.5h |

---

## 10. Metricas Consolidadas

| Metrica | Valor |
|---------|-------|
| Tabelas no schema public | 4 |
| Indices explicitos | 5 |
| Indices implicitos (UNIQUE/PK) | 6 |
| Policies RLS | 4 |
| Triggers | 3 |
| Funcoes armazenadas | 3 |
| Itens de divida tecnica | 13 |
| Horas estimadas (total) | ~14.5h |
| Severidade critica (schema) | 0 |
| Severidade critica (operacional) | 1 (service role key) |
| Severidade media | 5 |
| Severidade baixa | 8 |
