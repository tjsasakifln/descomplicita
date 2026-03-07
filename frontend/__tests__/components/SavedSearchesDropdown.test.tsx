import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SavedSearchesDropdown } from '@/app/components/SavedSearchesDropdown';

// Mock useSavedSearches hook
const mockSearches = [
  {
    id: 'search-1',
    name: 'Uniformes Sul',
    searchParams: {
      searchMode: 'setor' as const,
      setorId: 'uniformes',
      ufs: ['SC', 'PR', 'RS'],
      dataInicial: '2024-01-01',
      dataFinal: '2024-01-31',
    },
    createdAt: new Date().toISOString(),
    lastUsedAt: new Date().toISOString(),
  },
  {
    id: 'search-2',
    name: 'Alimentos Nordeste',
    searchParams: {
      searchMode: 'setor' as const,
      setorId: 'alimentos',
      ufs: ['BA', 'PE'],
      dataInicial: '2024-02-01',
      dataFinal: '2024-02-28',
    },
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    lastUsedAt: new Date(Date.now() - 86400000).toISOString(),
  },
];

const mockDeleteSearch = jest.fn(() => true);
const mockLoadSearch = jest.fn((id: string) => mockSearches.find(s => s.id === id) || null);
const mockClearAll = jest.fn();

// The component uses relative import ../../hooks/useSavedSearches
// which resolves to <rootDir>/hooks/useSavedSearches
jest.mock('../../hooks/useSavedSearches', () => ({
  useSavedSearches: () => ({
    searches: mockSearches,
    loading: false,
    deleteSearch: mockDeleteSearch,
    loadSearch: mockLoadSearch,
    clearAll: mockClearAll,
    isMaxCapacity: false,
  }),
}));

describe('SavedSearchesDropdown', () => {
  const defaultProps = {
    onLoadSearch: jest.fn(),
    onAnalyticsEvent: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should render trigger button with count badge', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    const trigger = screen.getByRole('button', { name: /Buscas salvas/i });
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-haspopup', 'true');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');

    // Count badge
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('should open dropdown on click', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    const trigger = screen.getByRole('button', { name: /Buscas salvas/i });
    fireEvent.click(trigger);

    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Uniformes Sul')).toBeInTheDocument();
    expect(screen.getByText('Alimentos Nordeste')).toBeInTheDocument();
  });

  it('should show header with count', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
    expect(screen.getByText('Buscas Recentes (2/10)')).toBeInTheDocument();
  });

  it('should call loadSearch when a saved search is clicked', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

    // The search name is inside a button - click it
    const searchNameEl = screen.getByText('Uniformes Sul');
    const searchButton = searchNameEl.closest('button');
    fireEvent.click(searchButton!);

    expect(mockLoadSearch).toHaveBeenCalledWith('search-1');
  });

  it('should close on Escape key', async () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    const trigger = screen.getByRole('button', { name: /Buscas salvas/i });
    fireEvent.click(trigger);
    expect(screen.getByText('Uniformes Sul')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByText('Uniformes Sul')).not.toBeInTheDocument();
    });
  });

  describe('Delete Confirmation (double-click pattern)', () => {
    it('should require double-click to delete a search', () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      // Find delete buttons
      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      expect(deleteButtons.length).toBe(2);

      // First click — show confirmation state
      fireEvent.click(deleteButtons[0]);
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();

      // Second click — confirm delete
      fireEvent.click(screen.getByRole('button', { name: /Confirmar exclusão/i }));
      expect(mockDeleteSearch).toHaveBeenCalledWith('search-1');
    });

    it('should auto-reset delete confirmation after 3 seconds', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      fireEvent.click(deleteButtons[0]);
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();

      // Advance time by 3 seconds
      act(() => {
        jest.advanceTimersByTime(3100);
      });

      // Should reset back to normal state
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /Confirmar exclusão/i })).not.toBeInTheDocument();
      });
    });
  });

  describe('Clear All — Custom Confirmation (TD-048)', () => {
    it('should NOT use window.confirm (no native dialogs)', () => {
      const confirmSpy = jest.spyOn(window, 'confirm');
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      fireEvent.click(screen.getByText('Limpar todas'));

      // Should NOT call window.confirm
      expect(confirmSpy).not.toHaveBeenCalled();
      confirmSpy.mockRestore();
    });

    it('should show inline confirmation on first click', () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      fireEvent.click(screen.getByText('Limpar todas'));

      // Should show confirmation text
      expect(screen.getByText('Confirmar exclusão?')).toBeInTheDocument();
    });

    it('should clear all on second click (confirmation)', () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      // First click
      fireEvent.click(screen.getByText('Limpar todas'));
      expect(screen.getByText('Confirmar exclusão?')).toBeInTheDocument();

      // Second click — confirm
      fireEvent.click(screen.getByText('Confirmar exclusão?'));
      expect(mockClearAll).toHaveBeenCalledTimes(1);
    });

    it('should auto-cancel clear confirmation after 3 seconds', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      fireEvent.click(screen.getByText('Limpar todas'));
      expect(screen.getByText('Confirmar exclusão?')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(3100);
      });

      await waitFor(() => {
        expect(screen.getByText('Limpar todas')).toBeInTheDocument();
        expect(screen.queryByText('Confirmar exclusão?')).not.toBeInTheDocument();
      });
    });
  });

  it('should display relative timestamps', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
    // Should show relative time (e.g., "agora" for recent, "ontem" for yesterday)
    expect(screen.getByText('agora')).toBeInTheDocument();
  });
});
