/**
 * Server-side saved searches CRUD via Supabase
 *
 * Maps between camelCase (frontend) and snake_case (DB):
 *   DB:       id, user_id, name, search_params, created_at, last_used_at
 *   Frontend: id, name, searchParams, createdAt, lastUsedAt
 */

import type { SupabaseClient } from '@supabase/supabase-js';
import type { SavedSearch } from './savedSearches';

const MAX_SEARCHES = 10;

// DB row shape (raw from Supabase)
interface DbSavedSearch {
  id: string;
  user_id: string;
  name: string;
  search_params: SavedSearch['searchParams'];
  created_at: string;
  last_used_at: string;
}

function dbRowToFrontend(row: DbSavedSearch): SavedSearch {
  return {
    id: row.id,
    name: row.name,
    searchParams: row.search_params,
    createdAt: row.created_at,
    lastUsedAt: row.last_used_at,
  };
}

/**
 * Fetch the current user's saved searches ordered by last_used_at desc, limit 10.
 * RLS on the table ensures only the authenticated user's rows are returned.
 */
export async function loadServerSearches(supabase: SupabaseClient): Promise<SavedSearch[]> {
  const { data, error } = await supabase
    .from('saved_searches')
    .select('id, user_id, name, search_params, created_at, last_used_at')
    .order('last_used_at', { ascending: false })
    .limit(MAX_SEARCHES);

  if (error) {
    throw new Error(`Failed to load saved searches: ${error.message}`);
  }

  return (data as DbSavedSearch[]).map(dbRowToFrontend);
}

/**
 * Insert a new saved search for the current user.
 * RLS populates user_id via auth.uid() — no need to pass it explicitly.
 */
export async function saveServerSearch(
  supabase: SupabaseClient,
  name: string,
  searchParams: SavedSearch['searchParams']
): Promise<SavedSearch> {
  if (!name || name.trim() === '') {
    throw new Error('Nome da busca é obrigatório');
  }

  // Check capacity before inserting
  const existing = await loadServerSearches(supabase);
  if (existing.length >= MAX_SEARCHES) {
    throw new Error('Máximo de 10 buscas salvas atingido');
  }

  const now = new Date().toISOString();

  const { data, error } = await supabase
    .from('saved_searches')
    .insert({
      name: name.trim(),
      search_params: searchParams,
      created_at: now,
      last_used_at: now,
    })
    .select('id, user_id, name, search_params, created_at, last_used_at')
    .single();

  if (error) {
    throw new Error(`Failed to save search: ${error.message}`);
  }

  return dbRowToFrontend(data as DbSavedSearch);
}

/**
 * Delete a saved search by id.
 * RLS ensures the user can only delete their own rows.
 */
export async function deleteServerSearch(supabase: SupabaseClient, id: string): Promise<void> {
  const { error } = await supabase
    .from('saved_searches')
    .delete()
    .eq('id', id);

  if (error) {
    throw new Error(`Failed to delete saved search: ${error.message}`);
  }
}

/**
 * Update name and/or searchParams for a saved search.
 */
export async function updateServerSearch(
  supabase: SupabaseClient,
  id: string,
  updates: Partial<Pick<SavedSearch, 'name' | 'searchParams'>>
): Promise<SavedSearch | null> {
  const dbUpdates: Partial<{ name: string; search_params: SavedSearch['searchParams'] }> = {};

  if (updates.name !== undefined) {
    dbUpdates.name = updates.name;
  }
  if (updates.searchParams !== undefined) {
    dbUpdates.search_params = updates.searchParams;
  }

  if (Object.keys(dbUpdates).length === 0) {
    return null;
  }

  const { data, error } = await supabase
    .from('saved_searches')
    .update(dbUpdates)
    .eq('id', id)
    .select('id, user_id, name, search_params, created_at, last_used_at')
    .single();

  if (error) {
    throw new Error(`Failed to update saved search: ${error.message}`);
  }

  if (!data) return null;

  return dbRowToFrontend(data as DbSavedSearch);
}

/**
 * Update last_used_at to now for a saved search.
 */
export async function markServerSearchAsUsed(supabase: SupabaseClient, id: string): Promise<void> {
  const { error } = await supabase
    .from('saved_searches')
    .update({ last_used_at: new Date().toISOString() })
    .eq('id', id);

  if (error) {
    throw new Error(`Failed to mark search as used: ${error.message}`);
  }
}

/**
 * Delete all saved searches for the current user.
 * RLS restricts deletions to the authenticated user's own rows.
 */
export async function clearAllServerSearches(supabase: SupabaseClient): Promise<void> {
  // Supabase requires a filter for delete; use a truthy condition on the primary key
  const { error } = await supabase
    .from('saved_searches')
    .delete()
    .neq('id', '00000000-0000-0000-0000-000000000000');

  if (error) {
    throw new Error(`Failed to clear saved searches: ${error.message}`);
  }
}
