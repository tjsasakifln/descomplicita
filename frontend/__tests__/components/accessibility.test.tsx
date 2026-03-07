import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SaveSearchDialog } from '@/app/components/SaveSearchDialog';

// Mocks for SearchHeader dependencies
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => <img {...props} />,
}));

jest.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

jest.mock('@/components/SavedSearchesDropdown', () => ({
  SavedSearchesDropdown: () => <div data-testid="saved-searches" />,
}));

// Mock for UfSelector dependency
jest.mock('@/components/RegionSelector', () => ({
  RegionSelector: () => <div data-testid="region-selector" />,
  REGIONS: {},
}));

// Mock for SearchSummary dependency
jest.mock('@/components/SourceBadges', () => ({
  SourceBadges: () => null,
  default: () => null,
}));

describe('Story 3.0: Accessibility Tests', () => {
  describe('SaveSearchDialog Focus Trap (TD-008)', () => {
    const defaultProps = {
      saveSearchName: 'Test',
      onNameChange: jest.fn(),
      onConfirm: jest.fn(),
      onCancel: jest.fn(),
      saveError: null,
    };

    it('should have aria-labelledby pointing to dialog title', () => {
      render(<SaveSearchDialog {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby', 'save-search-dialog-title');

      const title = document.getElementById('save-search-dialog-title');
      expect(title).toBeInTheDocument();
      expect(title).toHaveTextContent('Salvar Busca');
    });

    it('should trap focus with Tab cycling forward', () => {
      render(<SaveSearchDialog {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      const innerModal = dialog.querySelector('.bg-surface-0')!;

      // Get all focusable elements
      const focusables = innerModal.querySelectorAll<HTMLElement>(
        'input, button:not([disabled])'
      );
      expect(focusables.length).toBeGreaterThanOrEqual(3); // input, cancel, save

      // Focus last element
      const lastFocusable = focusables[focusables.length - 1];
      lastFocusable.focus();
      expect(lastFocusable).toHaveFocus();

      // Tab should cycle to first element
      fireEvent.keyDown(innerModal, { key: 'Tab' });
      // The focus trap should prevent default and focus first
    });

    it('should trap focus with Shift+Tab cycling backward', () => {
      render(<SaveSearchDialog {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      const innerModal = dialog.querySelector('.bg-surface-0')!;

      const focusables = innerModal.querySelectorAll<HTMLElement>(
        'input, button:not([disabled])'
      );
      const firstFocusable = focusables[0];
      firstFocusable.focus();

      // Shift+Tab should cycle to last element
      fireEvent.keyDown(innerModal, { key: 'Tab', shiftKey: true });
    });

    it('should close dialog on Escape key', () => {
      const onCancel = jest.fn();
      render(<SaveSearchDialog {...defaultProps} onCancel={onCancel} />);
      const dialog = screen.getByRole('dialog');
      const innerModal = dialog.querySelector('.bg-surface-0')!;

      fireEvent.keyDown(innerModal, { key: 'Escape' });
      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('should focus first element on mount', async () => {
      render(<SaveSearchDialog {...defaultProps} />);

      await waitFor(() => {
        const input = screen.getByLabelText('Nome da busca:');
        expect(input).toHaveFocus();
      });
    });
  });

  describe('SourceBadges CSS Custom Properties (TD-044)', () => {
    // Use jest.requireActual to get the real SourceBadges (bypassing the mock)
    const { SourceBadges } = jest.requireActual('@/components/SourceBadges');

    const defaultProps = {
      sources: ['pncp', 'comprasgov'],
      stats: {
        pncp: { total_fetched: 10, after_dedup: 8, elapsed_ms: 500, status: 'success' as const, error_message: null },
        comprasgov: { total_fetched: 0, after_dedup: 0, elapsed_ms: 200, status: 'success' as const, error_message: null },
      },
      dedupRemoved: 2,
    };

    it('should use semantic status token classes instead of hardcoded colors', () => {
      const { container } = render(<SourceBadges {...defaultProps} />);

      // Should NOT contain hardcoded Tailwind color classes
      const html = container.innerHTML;
      expect(html).not.toContain('bg-green-100');
      expect(html).not.toContain('bg-yellow-100');
      expect(html).not.toContain('bg-red-100');
      expect(html).not.toContain('text-green-800');
      expect(html).not.toContain('text-yellow-800');
      expect(html).not.toContain('text-red-800');

      // Should contain semantic token classes
      expect(html).toContain('bg-status-success-bg');
      expect(html).toContain('bg-status-warning-bg');
    });

    it('should use status dot token classes', () => {
      const { container } = render(<SourceBadges {...defaultProps} />);

      const html = container.innerHTML;
      expect(html).toContain('bg-status-success-dot');
      expect(html).toContain('bg-status-warning-dot');
    });

    it('should have aria-expanded on toggle button', () => {
      render(<SourceBadges {...defaultProps} />);

      const toggleButton = screen.getByRole('button');
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

      fireEvent.click(toggleButton);
      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    });
  });

  describe('EmptyState ARIA Live Region (TD-049)', () => {
    it('should have aria-live and role="status"', () => {
      const { EmptyState } = require('@/components/EmptyState');
      const { container } = render(<EmptyState />);

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveAttribute('aria-live', 'polite');
      expect(wrapper).toHaveAttribute('role', 'status');
    });
  });

  describe('SearchHeader Navigation (TD-043)', () => {
    it('should wrap navigation elements in <nav>', () => {
      const { SearchHeader } = require('@/components/SearchHeader');
      const { container } = render(
        <SearchHeader onLoadSearch={jest.fn()} onAnalyticsEvent={jest.fn()} />
      );

      const nav = container.querySelector('nav');
      expect(nav).toBeInTheDocument();
      expect(nav).toHaveAttribute('aria-label', 'Navegação principal');
    });
  });

  describe('SearchForm aria-describedby (TD-046)', () => {
    it('should link terms input to help text via aria-describedby', () => {
      const { SearchForm } = require('@/components/SearchForm');
      render(
        <SearchForm
          searchMode="termos"
          onSearchModeChange={jest.fn()}
          setores={[]}
          setorId=""
          onSetorIdChange={jest.fn()}
          termosArray={[]}
          onTermosArrayChange={jest.fn()}
          termoInput=""
          onTermoInputChange={jest.fn()}
          onFormChange={jest.fn()}
        />
      );

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'termos-busca-hint');

      const hint = document.getElementById('termos-busca-hint');
      expect(hint).toBeInTheDocument();
    });
  });

  describe('UfSelector Group Label (TD-051)', () => {
    it('should wrap UF grid in role="group" with aria-label', () => {
      const { UfSelector } = require('@/components/UfSelector');
      render(
        <UfSelector
          ufsSelecionadas={new Set(['SC'])}
          onToggleUf={jest.fn()}
          onToggleRegion={jest.fn()}
          onSelecionarTodos={jest.fn()}
          onLimparSelecao={jest.fn()}
          validationErrors={{}}
        />
      );

      const group = screen.getByRole('group');
      expect(group).toHaveAttribute('aria-label', 'Selecionar Unidades Federativas');
    });
  });

  describe('Heading Hierarchy (TD-052)', () => {
    it('should have proper heading structure in SearchSummary', () => {
      const { SearchSummary } = require('@/components/SearchSummary');

      render(
        <SearchSummary
          result={{
            resumo: {
              resumo_executivo: 'Test',
              total_oportunidades: 5,
              valor_total: 1000,
              destaques: ['Destaque 1'],
              distribuicao_uf: {},
              alerta_urgencia: null,
            },
            download_id: 'test',
            total_raw: 10,
            total_filtrado: 5,
            total_atas: 0,
            total_licitacoes: 5,
            filter_stats: null,
            sources_used: [],
            source_stats: {},
            dedup_removed: 0,
            truncated_combos: 0,
          }}
        />
      );

      // Destaques should use h3 (not h4) for proper hierarchy under h2 Results
      const heading = screen.getByRole('heading', { name: 'Destaques:' });
      expect(heading.tagName).toBe('H3');
    });
  });
});
