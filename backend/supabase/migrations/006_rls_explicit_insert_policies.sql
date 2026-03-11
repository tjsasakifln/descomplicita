-- story-2.2 / TD-DB-002: Add explicit INSERT policies with WITH CHECK
--
-- The existing FOR ALL USING policies implicitly cover INSERT, but PostgreSQL
-- uses the USING clause as WITH CHECK when no explicit WITH CHECK is defined.
-- This migration makes the INSERT intent explicit for auditability and clarity.
--
-- Strategy: Drop existing FOR ALL policies and replace with:
--   1. SELECT policy (USING only — read your own rows)
--   2. INSERT policy (WITH CHECK — can only insert rows owned by you)
--   3. UPDATE policy (USING + WITH CHECK — update only your own rows, can't change ownership)
--   4. DELETE policy (USING only — delete only your own rows)
--
-- This does NOT change runtime behavior — it makes the implicit explicit.

-- ============================================================================
-- users table
-- ============================================================================

DROP POLICY IF EXISTS users_own_data ON public.users;

CREATE POLICY users_select_own ON public.users
    FOR SELECT USING (auth.uid() = id);

-- INSERT: Users can only create their own profile (id must match auth.uid())
CREATE POLICY users_insert_own ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY users_update_own ON public.users
    FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

CREATE POLICY users_delete_own ON public.users
    FOR DELETE USING (auth.uid() = id);

-- ============================================================================
-- search_history table
-- ============================================================================

DROP POLICY IF EXISTS search_history_own_data ON public.search_history;

CREATE POLICY search_history_select_own ON public.search_history
    FOR SELECT USING (auth.uid() = user_id);

-- INSERT: Can only insert search history for your own user_id
CREATE POLICY search_history_insert_own ON public.search_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY search_history_update_own ON public.search_history
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY search_history_delete_own ON public.search_history
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- user_preferences table
-- ============================================================================

DROP POLICY IF EXISTS user_preferences_own_data ON public.user_preferences;

CREATE POLICY user_preferences_select_own ON public.user_preferences
    FOR SELECT USING (auth.uid() = user_id);

-- INSERT: Can only insert preferences for your own user_id
CREATE POLICY user_preferences_insert_own ON public.user_preferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_update_own ON public.user_preferences
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_delete_own ON public.user_preferences
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- saved_searches table
-- ============================================================================

DROP POLICY IF EXISTS saved_searches_own_data ON public.saved_searches;

CREATE POLICY saved_searches_select_own ON public.saved_searches
    FOR SELECT USING (auth.uid() = user_id);

-- INSERT: Can only insert saved searches for your own user_id
CREATE POLICY saved_searches_insert_own ON public.saved_searches
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY saved_searches_update_own ON public.saved_searches
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY saved_searches_delete_own ON public.saved_searches
    FOR DELETE USING (auth.uid() = user_id);
