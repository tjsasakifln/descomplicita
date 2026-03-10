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

const mockDeleteSearch = jest.fn();
const mockLoadSearch = jest.fn();
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
    // Default async implementations (return Promises to match hook's async API)
    mockDeleteSearch.mockResolvedValue(true);
    mockLoadSearch.mockImplementation((id: string) =>
      Promise.resolve(mockSearches.find((s) => s.id === id) ?? null)
    );
    mockClearAll.mockResolvedValue(undefined);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should render trigger button with count badge', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    const trigger = screen.getByRole('button', { name: /Buscas salvas/i });
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
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

    // The search name is inside a role="option" div - click it
    const searchNameEl = screen.getByText('Uniformes Sul');
    const optionEl = searchNameEl.closest('[role="option"]');
    fireEvent.click(optionEl!);

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

    it('should NOT auto-dismiss delete confirmation (WCAG 2.2.1)', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      fireEvent.click(deleteButtons[0]);
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();

      // Advance time well beyond the old 3-second timeout
      act(() => {
        jest.advanceTimersByTime(10000);
      });

      // Confirmation should still be visible — no auto-dismiss
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();
    });

    it('should show a cancel button alongside the confirm button', () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      fireEvent.click(deleteButtons[0]);

      // Cancel button must be present
      expect(screen.getByRole('button', { name: /Cancelar exclusão/i })).toBeInTheDocument();
    });

    it('should dismiss confirmation when cancel button is clicked', () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      fireEvent.click(deleteButtons[0]);
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /Cancelar exclusão/i }));

      expect(screen.queryByRole('button', { name: /Confirmar exclusão/i })).not.toBeInTheDocument();
      expect(mockDeleteSearch).not.toHaveBeenCalled();
    });

    it('should reset delete confirmation when dropdown closes via Escape', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      fireEvent.click(deleteButtons[0]);
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();

      // Close dropdown via Escape
      fireEvent.keyDown(document, { key: 'Escape' });

      await waitFor(() => {
        expect(screen.queryByText('Uniformes Sul')).not.toBeInTheDocument();
      });

      // Reopen and verify confirmation is gone
      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      expect(screen.queryByRole('button', { name: /Confirmar exclusão/i })).not.toBeInTheDocument();
    });

    it('should reset delete confirmation when dropdown closes via backdrop click', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));

      const deleteButtons = screen.getAllByRole('button', { name: /Excluir busca/i });
      fireEvent.click(deleteButtons[0]);
      expect(screen.getByRole('button', { name: /Confirmar exclusão/i })).toBeInTheDocument();

      // Click the backdrop (fixed overlay behind the dropdown)
      const backdrop = document.querySelector('[aria-hidden="true"]') as HTMLElement;
      fireEvent.click(backdrop);

      await waitFor(() => {
        expect(screen.queryByText('Uniformes Sul')).not.toBeInTheDocument();
      });

      // Reopen and verify confirmation is gone
      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      expect(screen.queryByRole('button', { name: /Confirmar exclusão/i })).not.toBeInTheDocument();
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

    it('should NOT auto-dismiss clear confirmation (WCAG 2.2.1)', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      fireEvent.click(screen.getByText('Limpar todas'));
      expect(screen.getByText('Confirmar exclusão?')).toBeInTheDocument();

      // Advance time well beyond the old 3-second timeout
      act(() => {
        jest.advanceTimersByTime(10000);
      });

      // Confirmation should still be visible — no auto-dismiss
      expect(screen.getByText('Confirmar exclusão?')).toBeInTheDocument();
    });

    it('should reset clear confirmation when dropdown closes via Escape', async () => {
      render(<SavedSearchesDropdown {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      fireEvent.click(screen.getByText('Limpar todas'));
      expect(screen.getByText('Confirmar exclusão?')).toBeInTheDocument();

      // Close dropdown via Escape
      fireEvent.keyDown(document, { key: 'Escape' });

      await waitFor(() => {
        expect(screen.queryByText('Uniformes Sul')).not.toBeInTheDocument();
      });

      // Reopen and verify clear confirmation is gone
      fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
      expect(screen.queryByText('Confirmar exclusão?')).not.toBeInTheDocument();
      expect(screen.getByText('Limpar todas')).toBeInTheDocument();
    });
  });

  it('should display relative timestamps', () => {
    render(<SavedSearchesDropdown {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Buscas salvas/i }));
    // Should show relative time (e.g., "agora" for recent, "ontem" for yesterday)
    expect(screen.getByText('agora')).toBeInTheDocument();
  });
});
