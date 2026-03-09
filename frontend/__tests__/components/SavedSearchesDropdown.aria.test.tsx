import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SavedSearchesDropdown } from '@/app/components/SavedSearchesDropdown';

// Mock useSavedSearches
const mockSearches = [
  {
    id: 'search-1', name: 'Uniformes Sul', createdAt: new Date().toISOString(),
    lastUsedAt: new Date().toISOString(),
    searchParams: { ufs: ['SC', 'PR'], dataInicial: '2026-01-01', dataFinal: '2026-01-07', searchMode: 'setor' as const, setorId: 'vestuario' },
  },
  {
    id: 'search-2', name: 'Alimentos Nordeste', createdAt: new Date().toISOString(),
    lastUsedAt: new Date(Date.now() - 86400000).toISOString(),
    searchParams: { ufs: ['BA', 'PE'], dataInicial: '2026-01-01', dataFinal: '2026-01-07', searchMode: 'setor' as const, setorId: 'alimentos' },
  },
  {
    id: 'search-3', name: 'TI Sudeste', createdAt: new Date().toISOString(),
    lastUsedAt: new Date(Date.now() - 172800000).toISOString(),
    searchParams: { ufs: ['SP', 'RJ'], dataInicial: '2026-01-01', dataFinal: '2026-01-07', searchMode: 'setor' as const, setorId: 'informatica' },
  },
];

const mockLoadSearch = jest.fn((id: string) => mockSearches.find(s => s.id === id) || null);

jest.mock('../../hooks/useSavedSearches', () => ({
  useSavedSearches: () => ({
    searches: mockSearches,
    loading: false,
    deleteSearch: jest.fn(() => true),
    loadSearch: mockLoadSearch,
    clearAll: jest.fn(),
  }),
}));

describe('SavedSearchesDropdown ARIA Listbox (UXD-005)', () => {
  const onLoadSearch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should have role="listbox" on the search list', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('should have role="option" on each search item', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(3);
  });

  it('should set aria-haspopup="listbox" on trigger', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    const trigger = screen.getByRole('button', { name: /Buscas salvas/i });
    expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
  });

  it('should navigate with ArrowDown key', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    const options = screen.getAllByRole('option');
    // First option is active by default
    expect(options[0]).toHaveAttribute('aria-selected', 'true');

    // Arrow down to second
    fireEvent.keyDown(document, { key: 'ArrowDown' });
    expect(options[1]).toHaveAttribute('aria-selected', 'true');
    expect(options[0]).toHaveAttribute('aria-selected', 'false');
  });

  it('should navigate with ArrowUp key', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    // Arrow down then up
    fireEvent.keyDown(document, { key: 'ArrowDown' });
    fireEvent.keyDown(document, { key: 'ArrowUp' });

    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
  });

  it('should wrap around with ArrowDown at end', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    // Go to last item then one more
    fireEvent.keyDown(document, { key: 'ArrowDown' }); // -> 1
    fireEvent.keyDown(document, { key: 'ArrowDown' }); // -> 2
    fireEvent.keyDown(document, { key: 'ArrowDown' }); // -> 0 (wrap)

    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
  });

  it('should select with Enter key', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    // Verify first option is active
    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(document, { key: 'Enter' });
    expect(mockLoadSearch).toHaveBeenCalledWith('search-1');
  });

  it('should jump to first with Home key', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    fireEvent.keyDown(document, { key: 'ArrowDown' });
    fireEvent.keyDown(document, { key: 'ArrowDown' });
    fireEvent.keyDown(document, { key: 'Home' });

    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
  });

  it('should jump to last with End key', () => {
    render(<SavedSearchesDropdown onLoadSearch={onLoadSearch} />);
    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    fireEvent.keyDown(document, { key: 'End' });

    const options = screen.getAllByRole('option');
    expect(options[2]).toHaveAttribute('aria-selected', 'true');
  });
});
