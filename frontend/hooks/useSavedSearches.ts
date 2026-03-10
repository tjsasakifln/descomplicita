/**
 * React hook for managing saved searches
 *
 * When the user is authenticated and Supabase is available:
 *   - Primary storage is Supabase (server-side)
 *   - localStorage is kept as a write-through cache
 *   - On first login, existing localStorage searches are migrated to Supabase
 *
 * When the user is not authenticated (or Supabase is unavailable):
 *   - localStorage only (original behaviour — unchanged)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  loadSavedSearches,
  saveSearch,
  deleteSavedSearch,
  updateSavedSearch,
  markSearchAsUsed,
  clearAllSavedSearches,
  isMaxCapacity,
  type SavedSearch,
} from '../lib/savedSearches';
import {
  loadServerSearches,
  saveServerSearch,
  deleteServerSearch,
  updateServerSearch,
  markServerSearchAsUsed,
  clearAllServerSearches,
} from '../lib/savedSearchesServer';
import { createClient } from '../lib/supabase/client';
import { useAuth } from '../app/contexts/AuthContext';

/** localStorage key that marks whether migration has already run for this browser */
const MIGRATION_FLAG_KEY = 'descomplicita_searches_migrated';

export interface UseSavedSearchesReturn {
  searches: SavedSearch[];
  loading: boolean;
  isMaxCapacity: boolean;
  saveNewSearch: (name: string, params: SavedSearch['searchParams']) => Promise<SavedSearch | null>;
  deleteSearch: (id: string) => Promise<boolean>;
  updateSearch: (id: string, updates: Partial<Pick<SavedSearch, 'name' | 'searchParams'>>) => Promise<SavedSearch | null>;
  loadSearch: (id: string) => Promise<SavedSearch | null>;
  clearAll: () => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Hook for managing saved searches
 *
 * @example
 * const { searches, saveNewSearch, deleteSearch, loadSearch } = useSavedSearches();
 *
 * // Save a search
 * saveNewSearch("Uniformes SC/PR/RS", {
 *   ufs: ["SC", "PR", "RS"],
 *   dataInicial: "2026-01-22",
 *   dataFinal: "2026-01-29",
 *   searchMode: "setor",
 *   setorId: "vestuario"
 * });
 *
 * // Load a search
 * const search = await loadSearch(searchId);
 * if (search) {
 *   // Apply search params to form
 * }
 */
export function useSavedSearches(): UseSavedSearchesReturn {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [maxCapacity, setMaxCapacity] = useState(false);

  const { user } = useAuth();
  const supabase = createClient();

  /** True when we have an authenticated user AND a working Supabase client */
  const isServerMode = !!(user && supabase);

  // Track previous user id so we can detect when the user first logs in
  const prevUserIdRef = useRef<string | null>(null);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /** Sync the local cache (localStorage) from a list of server searches */
  function syncLocalCache(serverSearches: SavedSearch[]): void {
    try {
      localStorage.setItem('descomplicita_saved_searches', JSON.stringify(serverSearches));
    } catch (_e) {
      void _e;
    }
  }

  // ---------------------------------------------------------------------------
  // refresh
  // ---------------------------------------------------------------------------

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      if (isServerMode) {
        const serverSearches = await loadServerSearches(supabase!);
        setSearches(serverSearches);
        setMaxCapacity(serverSearches.length >= 10);
        syncLocalCache(serverSearches);
      } else {
        const local = loadSavedSearches();
        setSearches(local);
        setMaxCapacity(isMaxCapacity());
      }
    } catch (_e) {
      void _e;
      // Fall back to localStorage on error
      const local = loadSavedSearches();
      setSearches(local);
      setMaxCapacity(isMaxCapacity());
    } finally {
      setLoading(false);
    }
  }, [isServerMode, supabase]);

  // ---------------------------------------------------------------------------
  // Migration: run once when the user first authenticates in this browser
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const currentUserId = user?.id ?? null;
    const justLoggedIn = currentUserId !== null && prevUserIdRef.current === null;
    prevUserIdRef.current = currentUserId;

    if (!justLoggedIn || !isServerMode) return;

    // Only migrate once per browser
    const alreadyMigrated = localStorage.getItem(MIGRATION_FLAG_KEY) === 'true';
    if (alreadyMigrated) return;

    void (async () => {
      try {
        const localSearches = loadSavedSearches();
        if (localSearches.length === 0) {
          localStorage.setItem(MIGRATION_FLAG_KEY, 'true');
          return;
        }

        const serverSearches = await loadServerSearches(supabase!);
        const serverNames = new Set(serverSearches.map((s) => s.name));

        // Insert only searches that don't already exist server-side (by name)
        for (const local of localSearches) {
          if (!serverNames.has(local.name)) {
            try {
              await saveServerSearch(supabase!, local.name, local.searchParams);
            } catch (_e) {
              void _e;
              // Skip individual failures — don't block migration
            }
          }
        }

        localStorage.setItem(MIGRATION_FLAG_KEY, 'true');
        await refresh();
      } catch (_e) {
        void _e;
        // Migration failure is non-fatal; user still has local data
      }
    })();
  }, [user, isServerMode, supabase, refresh]);

  // Load on mount and when auth state changes
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // ---------------------------------------------------------------------------
  // saveNewSearch
  // ---------------------------------------------------------------------------

  const saveNewSearch = useCallback(async (
    name: string,
    params: SavedSearch['searchParams']
  ): Promise<SavedSearch | null> => {
    if (isServerMode) {
      // Save to Supabase (throws on error)
      const newSearch = await saveServerSearch(supabase!, name, params);
      // Mirror to localStorage cache
      try {
        saveSearch(name, params);
      } catch (_e) {
        void _e;
        // Cache write failure is non-fatal
      }
      await refresh();
      return newSearch;
    } else {
      const newSearch = saveSearch(name, params);
      await refresh();
      return newSearch;
    }
  }, [isServerMode, supabase, refresh]);

  // ---------------------------------------------------------------------------
  // deleteSearch
  // ---------------------------------------------------------------------------

  const deleteSearch = useCallback(async (id: string): Promise<boolean> => {
    if (isServerMode) {
      try {
        await deleteServerSearch(supabase!, id);
      } catch (_e) {
        void _e;
        return false;
      }
      // Mirror deletion to localStorage cache
      deleteSavedSearch(id);
      await refresh();
      return true;
    } else {
      const success = deleteSavedSearch(id);
      if (success) await refresh();
      return success;
    }
  }, [isServerMode, supabase, refresh]);

  // ---------------------------------------------------------------------------
  // updateSearch
  // ---------------------------------------------------------------------------

  const updateSearch = useCallback(async (
    id: string,
    updates: Partial<Pick<SavedSearch, 'name' | 'searchParams'>>
  ): Promise<SavedSearch | null> => {
    if (isServerMode) {
      let updated: SavedSearch | null = null;
      try {
        updated = await updateServerSearch(supabase!, id, updates);
      } catch (_e) {
        void _e;
        return null;
      }
      // Mirror to localStorage cache
      updateSavedSearch(id, updates);
      await refresh();
      return updated;
    } else {
      const updated = updateSavedSearch(id, updates);
      if (updated) await refresh();
      return updated;
    }
  }, [isServerMode, supabase, refresh]);

  // ---------------------------------------------------------------------------
  // loadSearch — find in state, mark as used, return
  // ---------------------------------------------------------------------------

  const loadSearch = useCallback(async (id: string): Promise<SavedSearch | null> => {
    const search = searches.find((s) => s.id === id);
    if (!search) return null;

    if (isServerMode) {
      try {
        await markServerSearchAsUsed(supabase!, id);
      } catch (_e) {
        void _e;
      }
      // Mirror to localStorage cache
      markSearchAsUsed(id);
    } else {
      markSearchAsUsed(id);
    }

    await refresh();
    return search;
  }, [searches, isServerMode, supabase, refresh]);

  // ---------------------------------------------------------------------------
  // clearAll
  // ---------------------------------------------------------------------------

  const clearAll = useCallback(async () => {
    if (isServerMode) {
      try {
        await clearAllServerSearches(supabase!);
      } catch (_e) {
        void _e;
      }
      clearAllSavedSearches();
    } else {
      clearAllSavedSearches();
    }
    await refresh();
  }, [isServerMode, supabase, refresh]);

  // ---------------------------------------------------------------------------

  return {
    searches,
    loading,
    isMaxCapacity: maxCapacity,
    saveNewSearch,
    deleteSearch,
    updateSearch,
    loadSearch,
    clearAll,
    refresh,
  };
}
