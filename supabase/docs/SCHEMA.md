# Schema do Banco de Dados - Descomplicita

> **Atualizado em:** 2026-03-11 | **Agente:** @data-engineer (Forge)
> **Banco:** Supabase (PostgreSQL)
> **Driver:** supabase-py >= 2.13.0 (backend), @supabase/ssr (frontend)
> **Migracoes:** `backend/supabase/migrations/001_initial_schema.sql`, `002_retention_policy.sql`

---

## 1. Extensoes Habilitadas

| Extensao | Objetivo |
|----------|----------|
| `uuid-ossp` | Geracao de UUIDs v4 via `uuid_generate_v4()` |

---

## 2. Tabelas

### 2.1 `public.users`

Perfil de usuario vinculado ao `auth.users` do Supabase Auth. Criado automaticamente via trigger ao cadastrar usuario.

| Coluna | Tipo | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | -- | PK, FK -> `auth.users(id)` ON DELETE CASCADE |
| `email` | TEXT | NOT NULL | -- | -- |
| `display_name` | TEXT | sim | -- | -- |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | -- |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Auto-atualizado via trigger |

**Indices:** Apenas o PK implicito.

**RLS:** Habilitada. Policy `users_own_data` -- `FOR ALL USING (auth.uid() = id)`.

---

### 2.2 `public.search_history`

Historico de buscas realizadas. Cada registro representa um job de busca com seus parametros e resultados.

| Coluna | Tipo | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | BIGSERIAL | NOT NULL | auto-increment | PK |
| `user_id` | UUID | NOT NULL | -- | FK -> `public.users(id)` ON DELETE CASCADE |
| `job_id` | TEXT | NOT NULL | -- | UNIQUE |
| `ufs` | TEXT[] | NOT NULL | -- | Array de siglas UF (ex: `{SP,RJ,MG}`) |
| `data_inicial` | DATE | NOT NULL | -- | -- |
| `data_final` | DATE | NOT NULL | -- | -- |
| `setor_id` | TEXT | NOT NULL | -- | Identificador do setor (ex: `vestuario`) |
| `termos_busca` | TEXT | sim | -- | Termos de busca customizados |
| `total_raw` | INTEGER | sim | `0` | Total de registros antes da filtragem |
| `total_filtrado` | INTEGER | sim | `0` | Total de registros apos filtragem |
| `status` | TEXT | NOT NULL | `'queued'` | Valores esperados: queued, completed, failed |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | -- |
| `completed_at` | TIMESTAMPTZ | sim | -- | -- |
| `elapsed_seconds` | REAL | sim | -- | Tempo de execucao em segundos |

**Indices:**

| Nome | Colunas | Tipo |
|------|---------|------|
| `idx_search_history_user_created` | `(user_id, created_at DESC)` | B-tree |
| `idx_search_history_setor` | `(setor_id)` | B-tree |
| `idx_search_history_status` | `(status)` | B-tree |
| (implicito via UNIQUE) | `(job_id)` | B-tree |

**RLS:** Habilitada. Policy `search_history_own_data` -- `FOR ALL USING (auth.uid() = user_id)`.

---

### 2.3 `public.user_preferences`

Preferencias do usuario no formato key-value com valores JSONB.

| Coluna | Tipo | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | BIGSERIAL | NOT NULL | auto-increment | PK |
| `user_id` | UUID | NOT NULL | -- | FK -> `public.users(id)` ON DELETE CASCADE |
| `key` | TEXT | NOT NULL | -- | UNIQUE(user_id, key) |
| `value` | JSONB | NOT NULL | -- | -- |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Auto-atualizado via trigger |

**Indices:**

| Nome | Colunas | Tipo |
|------|---------|------|
| `idx_user_preferences_user` | `(user_id)` | B-tree |
| (implicito via UNIQUE) | `(user_id, key)` | B-tree |

**RLS:** Habilitada. Policy `user_preferences_own_data` -- `FOR ALL USING (auth.uid() = user_id)`.

---

### 2.4 `public.saved_searches`

Buscas salvas pelo usuario para reutilizacao rapida. Limite de 10 por usuario (enforced no codigo, nao no DB).

| Coluna | Tipo | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | UUID | NOT NULL | `uuid_generate_v4()` | PK |
| `user_id` | UUID | NOT NULL | -- | FK -> `public.users(id)` ON DELETE CASCADE |
| `name` | TEXT | NOT NULL | -- | Nome dado pelo usuario |
| `search_params` | JSONB | NOT NULL | -- | Parametros da busca (ufs, datas, setor, etc) |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | -- |
| `last_used_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Atualizado ao reutilizar a busca |

**Indices:**

| Nome | Colunas | Tipo |
|------|---------|------|
| `idx_saved_searches_user` | `(user_id, last_used_at DESC)` | B-tree |

**RLS:** Habilitada. Policy `saved_searches_own_data` -- `FOR ALL USING (auth.uid() = user_id)`.

---

## 3. Relacionamentos (Foreign Keys)

```
auth.users (Supabase Auth - tabela interna)
    |
    | 1:1 (id -> id, ON DELETE CASCADE)
    v
public.users
    |
    |-- 1:N --> public.search_history   (id -> user_id, ON DELETE CASCADE)
    |-- 1:N --> public.user_preferences (id -> user_id, ON DELETE CASCADE)
    |-- 1:N --> public.saved_searches   (id -> user_id, ON DELETE CASCADE)
```

Todas as FKs usam `ON DELETE CASCADE` -- excluir o usuario remove automaticamente todos os dados associados.

---

## 4. Diagrama ER

```
+------------------+       +---------------------+
|   auth.users     |       |   public.users      |
|  (Supabase Auth) |<------| id (PK, FK)         |
|  id (PK, UUID)   |  1:1  | email               |
|  email           |       | display_name        |
|  raw_user_meta   |       | created_at          |
+------------------+       | updated_at          |
                           +---------------------+
                                |    |    |
                    +-----------+    |    +----------+
                    |                |               |
                    v                v               v
          +------------------+ +----------------+ +------------------+
          | search_history   | | user_prefs     | | saved_searches   |
          | id (PK, BIGSER.) | | id (PK, BIGSER)| | id (PK, UUID)    |
          | user_id (FK)     | | user_id (FK)   | | user_id (FK)     |
          | job_id (UNIQUE)  | | key            | | name             |
          | ufs (TEXT[])     | | value (JSONB)  | | search_params    |
          | data_inicial     | | updated_at     | |   (JSONB)        |
          | data_final       | | UNIQUE(uid,key)| | created_at       |
          | setor_id         | +----------------+ | last_used_at     |
          | termos_busca     |                     +------------------+
          | total_raw        |
          | total_filtrado   |
          | status           |
          | created_at       |
          | completed_at     |
          | elapsed_seconds  |
          +------------------+
```

---

## 5. Triggers

| Trigger | Tabela | Evento | Funcao |
|---------|--------|--------|--------|
| `tr_users_updated_at` | `public.users` | BEFORE UPDATE | `update_updated_at()` |
| `tr_user_preferences_updated_at` | `public.user_preferences` | BEFORE UPDATE | `update_updated_at()` |
| `on_auth_user_created` | `auth.users` | AFTER INSERT | `handle_new_user()` |

---

## 6. Funcoes Armazenadas

### `public.update_updated_at()`
- **Tipo:** Trigger function
- **Linguagem:** PL/pgSQL
- **Descricao:** Define `NEW.updated_at = NOW()` antes de cada UPDATE

### `public.handle_new_user()`
- **Tipo:** Trigger function
- **Linguagem:** PL/pgSQL
- **Seguranca:** SECURITY DEFINER
- **Descricao:** Ao criar usuario em `auth.users`, insere perfil em `public.users` com `display_name` extraido de `raw_user_meta_data->>'display_name'` ou da parte local do email

### `public.cleanup_old_searches(retention_days INTEGER DEFAULT 90)`
- **Tipo:** Funcao regular (nao trigger)
- **Linguagem:** PL/pgSQL
- **Descricao:** Remove registros de `search_history` com status `completed` ou `failed` mais antigos que `retention_days` dias
- **Retorno:** INTEGER (quantidade de registros deletados)
- **Agendamento:** Preparado para `pg_cron` (comentado na migracao -- requer Supabase Pro)

---

## 7. Politicas RLS (Row Level Security)

Todas as tabelas do schema `public` tem RLS habilitada.

| Tabela | Policy | Operacao | Regra USING |
|--------|--------|----------|-------------|
| `users` | `users_own_data` | ALL | `auth.uid() = id` |
| `search_history` | `search_history_own_data` | ALL | `auth.uid() = user_id` |
| `user_preferences` | `user_preferences_own_data` | ALL | `auth.uid() = user_id` |
| `saved_searches` | `saved_searches_own_data` | ALL | `auth.uid() = user_id` |

**Nota:** O backend usa `SUPABASE_SERVICE_ROLE_KEY` que bypassa RLS. A RLS atua como defesa em profundidade, protegendo acessos via client-side (anon key).

---

## 8. Camadas de Acesso

### Backend (Python/FastAPI)
- **Driver:** `supabase-py` >= 2.13.0
- **Chave:** `SUPABASE_SERVICE_ROLE_KEY` (bypassa RLS)
- **Modulo:** `backend/database.py` (classe `Database`)
- **Operacoes:** CRUD em `users`, `search_history`, `user_preferences`
- **Isolamento:** `user_id` passado explicitamente em todas as queries

### Frontend (Next.js)
- **Driver:** `@supabase/ssr`
- **Chave:** `NEXT_PUBLIC_SUPABASE_ANON_KEY` (sujeita a RLS)
- **Modulos:**
  - `frontend/lib/supabase/client.ts` -- cliente browser (singleton)
  - `frontend/lib/supabase/server.ts` -- cliente server-side (cookie-based)
  - `frontend/lib/supabase/middleware.ts` -- refresh de sessao
  - `frontend/lib/savedSearchesServer.ts` -- CRUD de `saved_searches`
- **Operacoes:** CRUD apenas em `saved_searches` (via RLS do usuario autenticado)

### Autenticacao (3 camadas, em ordem de prioridade)
1. **Supabase JWT** (preferencial) -- validado via `python-jose` em `auth/supabase_auth.py`, extrai `user_id` do claim `sub`
2. **Custom JWT** (legado) -- validado via `PyJWT` em `auth/jwt.py`, sem `user_id` (claims: iss, aud, sub)
3. **API Key** (fallback legado) -- header `X-API-Key`, sem `user_id`, comparacao via `hmac.compare_digest`

---

## 9. Armazenamento Complementar (Redis)

O Redis nao faz parte do schema PostgreSQL, mas complementa como armazenamento volatil:

| Key Pattern | Tipo | TTL | Finalidade |
|-------------|------|-----|------------|
| `job:{uuid}` | JSON string | 24h | Estado e progresso do job |
| `excel:{uuid}` | Bytes brutos | 2h | Arquivo Excel para download |
| `job:{uuid}:items` | Redis LIST | 24h | Itens filtrados para paginacao |
| `job_params:{uuid}` | JSON string | 24h | Parametros para crash recovery |
| `pncp_cache:{uf}:{mod}:{d1}:{d2}` | JSON string | 4h | Cache de respostas da API PNCP |

---

## 10. Historico de Migracoes

| Arquivo | Versao | Descricao |
|---------|--------|-----------|
| `001_initial_schema.sql` | v3-story-2.0 | Schema completo: tabelas, RLS, triggers, funcao handle_new_user |
| `002_retention_policy.sql` | v3-story-2.0 | Funcao cleanup_old_searches (pg_cron comentado) |
