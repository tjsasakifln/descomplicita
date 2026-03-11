-- Migration 003: Add default auth.uid() to saved_searches.user_id
-- Story 0.2, Task 4 (TD-DB-015)
--
-- The saved_searches table requires user_id on every row, but currently
-- the caller must supply it explicitly. By defaulting to auth.uid(),
-- INSERTs issued through Supabase client libraries (which carry the
-- authenticated user's JWT) will automatically populate user_id when
-- the column is omitted. This is especially useful for RLS-protected
-- inserts from the frontend via supabase-js.

ALTER TABLE saved_searches
  ALTER COLUMN user_id SET DEFAULT auth.uid();
