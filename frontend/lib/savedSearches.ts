import { v4 as uuidv4 } from 'uuid';

const STORAGE_KEY = 'descomplicita_saved_searches';
const MAX_SEARCHES = 10;

export interface SavedSearch {
  id: string;
  name: string;
  searchParams: {
    ufs: string[];
    dataInicial: string;
    dataFinal: string;
    searchMode: string;
    setorId?: string;
    customTerms?: string[];
  };
  createdAt: string;
  lastUsedAt: string;
}

export function loadSavedSearches(): SavedSearch[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const searches: SavedSearch[] = JSON.parse(raw);
    return searches.sort(
      (a, b) => new Date(b.lastUsedAt).getTime() - new Date(a.lastUsedAt).getTime()
    );
  } catch {
    return [];
  }
}

export function saveSearch(
  name: string,
  searchParams: SavedSearch['searchParams']
): SavedSearch {
  if (!name || name.trim() === '') {
    throw new Error('Nome da busca é obrigatório');
  }

  const searches = loadSavedSearches();
  if (searches.length >= MAX_SEARCHES) {
    throw new Error('Máximo de 10 buscas salvas atingido');
  }

  const now = new Date().toISOString();
  const newSearch: SavedSearch = {
    id: uuidv4(),
    name,
    searchParams,
    createdAt: now,
    lastUsedAt: now,
  };

  searches.push(newSearch);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  return newSearch;
}

export function deleteSavedSearch(id: string): boolean {
  const searches = loadSavedSearches();
  const filtered = searches.filter((s) => s.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  return filtered.length < searches.length;
}

export function updateSavedSearch(
  id: string,
  updates: Partial<Pick<SavedSearch, 'name' | 'searchParams'>>
): SavedSearch | null {
  const searches = loadSavedSearches();
  const index = searches.findIndex((s) => s.id === id);
  if (index === -1) return null;

  searches[index] = { ...searches[index], ...updates };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  return searches[index];
}

export function markSearchAsUsed(id: string): void {
  const searches = loadSavedSearches();
  const search = searches.find((s) => s.id === id);
  if (search) {
    search.lastUsedAt = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  }
}

export function clearAllSavedSearches(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function isMaxCapacity(): boolean {
  return loadSavedSearches().length >= MAX_SEARCHES;
}

export const isMaxCapacityReached = isMaxCapacity;
