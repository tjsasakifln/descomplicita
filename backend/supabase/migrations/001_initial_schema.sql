-- v3-story-2.0: Initial Supabase schema migration
-- Replaces SQLite ephemeral storage with persistent PostgreSQL
-- Addresses: SYS-001, SYS-002, DB-001, DB-002, DB-003

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Users table (SYS-002: User identity model)
-- ============================================================================
-- Links to Supabase Auth (auth.users) via id
-- Stores app-specific profile data beyond what auth.users provides

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Search history (migrated from SQLite)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.search_history (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL UNIQUE,
    ufs TEXT[] NOT NULL,
    data_inicial DATE NOT NULL,
    data_final DATE NOT NULL,
    setor_id TEXT NOT NULL,
    termos_busca TEXT,
    total_raw INTEGER DEFAULT 0,
    total_filtrado INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    elapsed_seconds REAL
);

CREATE INDEX IF NOT EXISTS idx_search_history_user_created
    ON public.search_history(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_history_setor
    ON public.search_history(setor_id);

CREATE INDEX IF NOT EXISTS idx_search_history_status
    ON public.search_history(status);

-- ============================================================================
-- User preferences (migrated from SQLite key-value store)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_preferences (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, key)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user
    ON public.user_preferences(user_id);

-- ============================================================================
-- Saved searches (future: v3-story-3.0, but schema prepared now)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    search_params JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_user
    ON public.saved_searches(user_id, last_used_at DESC);

-- ============================================================================
-- Row Level Security (DB-001: Multi-user isolation)
-- ============================================================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_searches ENABLE ROW LEVEL SECURITY;

-- Users can only see/modify their own data
CREATE POLICY users_own_data ON public.users
    FOR ALL USING (auth.uid() = id);

CREATE POLICY search_history_own_data ON public.search_history
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY user_preferences_own_data ON public.user_preferences
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY saved_searches_own_data ON public.saved_searches
    FOR ALL USING (auth.uid() = user_id);

-- ============================================================================
-- Auto-update timestamps trigger
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER tr_user_preferences_updated_at
    BEFORE UPDATE ON public.user_preferences
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================================
-- Auto-create user profile on Supabase Auth signup
-- ============================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
