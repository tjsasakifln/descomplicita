import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomePage from '@/app/page';

// Mock fetch globally
global.fetch = jest.fn();

// Mock next/image (used by SearchHeader)
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...props} />;
  },
}));

// Mock child components that aren't relevant to page-level tests
jest.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

jest.mock('@/components/RegionSelector', () => ({
  RegionSelector: () => <div data-testid="region-selector" />,
  REGIONS: {},
}));

jest.mock('@/components/LoadingProgress', () => ({
  LoadingProgress: ({ onCancel, phase }: { onCancel?: () => void; phase?: string }) => (
    <div data-testid="loading-progress">
      <span>Carregando...</span>
      <span data-testid="loading-phase">{phase}</span>
      {onCancel && (
        <button data-testid="cancel-button" onClick={onCancel}>
          Cancelar busca
        </button>
      )}
    </div>
  ),
}));

jest.mock('@/components/EmptyState', () => ({
  EmptyState: ({ sectorName }: { sectorName?: string }) => (
    <div data-testid="empty-state">Nenhuma licitação de {sectorName?.toLowerCase() || 'licitações'} encontrada</div>
  ),
}));

jest.mock('@/components/SourceBadges', () => ({
  SourceBadges: () => <div data-testid="source-badges" />,
  default: () => <div data-testid="source-badges" />,
}));

const mockSuccessResponse = {
  resumo: {
    resumo_executivo: 'Encontradas 15 licitações de uniformes totalizando R$ 450.000,00',
    total_oportunidades: 15,
    valor_total: 450000,
    destaques: [
      'Uniformes escolares - Secretaria de Educação SC - R$ 120.000',
      'Fardamento militar - PM-PR - R$ 85.000',
      'Jalecos - Hospital Municipal RS - R$ 45.000'
    ],
    distribuicao_uf: { SC: 6, PR: 5, RS: 4 },
    alerta_urgencia: 'Licitação com prazo em menos de 7 dias: Prefeitura de Florianópolis'
  },
  download_id: 'uuid-123-456',
  total_raw: 200,
  total_filtrado: 15,
  total_atas: 0,
  total_licitacoes: 15,
  filter_stats: null,
  sources_used: [],
  source_stats: {},
  dedup_removed: 0,
  truncated_combos: 0,
};

/**
 * Mock the full polling flow:
 * 1. /api/setores -> rejected (fallback sectors)
 * 2. POST /api/buscar -> { job_id }
 * 3. GET /api/buscar/status -> { status: "completed", progress: {...} }
 * 4. GET /api/buscar/result -> result data
 */
function mockPollingFlow(resultData: Record<string, unknown>, jobId = "test-job-1234") {
  (global.fetch as jest.Mock)
    .mockRejectedValueOnce(new Error('not found')) // setores
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: jobId }),
    }) // POST /api/buscar
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        job_id: jobId,
        status: "completed",
        progress: { phase: "completed", ufs_completed: 3, ufs_total: 3, items_fetched: 200, items_filtered: 15 },
        elapsed_seconds: 10,
      }),
    }) // GET /api/buscar/status
    .mockResolvedValueOnce({
      ok: true,
      json: async () => resultData,
    }); // GET /api/buscar/result
}

describe('HomePage - UF Selection and Date Range', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    (global.fetch as jest.Mock).mockRejectedValue(new Error('not found'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('UF Selection', () => {
    it('should render all 27 UF buttons', () => {
      render(<HomePage />);

      const expectedUFs = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
      ];

      expectedUFs.forEach(uf => {
        expect(screen.getByText(uf)).toBeInTheDocument();
      });
    });

    it('should have default UFs selected (SC, PR, RS)', () => {
      render(<HomePage />);

      const scButton = screen.getByText('SC');
      const prButton = screen.getByText('PR');
      const rsButton = screen.getByText('RS');

      expect(scButton).toHaveClass('bg-brand-navy');
      expect(prButton).toHaveClass('bg-brand-navy');
      expect(rsButton).toHaveClass('bg-brand-navy');
    });

    it('should toggle UF selection on click', () => {
      render(<HomePage />);

      const spButton = screen.getByText('SP');
      expect(spButton).not.toHaveClass('bg-brand-navy');

      fireEvent.click(spButton);
      expect(spButton).toHaveClass('bg-brand-navy');

      fireEvent.click(spButton);
      expect(spButton).not.toHaveClass('bg-brand-navy');
    });

    it('should select all UFs when "Selecionar todos" is clicked', () => {
      render(<HomePage />);

      const selectAllButton = screen.getByText('Selecionar todos');
      fireEvent.click(selectAllButton);

      expect(screen.getByText('27 estados selecionados')).toBeInTheDocument();
    });

    it('should clear all UFs when "Limpar" is clicked', () => {
      render(<HomePage />);

      const clearButton = screen.getByText('Limpar');
      fireEvent.click(clearButton);

      expect(screen.getByText('0 estados selecionados')).toBeInTheDocument();
    });

    it('should display count of selected UFs', () => {
      render(<HomePage />);

      expect(screen.getByText('3 estados selecionados')).toBeInTheDocument();

      const spButton = screen.getByText('SP');
      fireEvent.click(spButton);

      expect(screen.getByText('4 estados selecionados')).toBeInTheDocument();
    });

    it('should display singular form for 1 state selected', () => {
      render(<HomePage />);

      const clearButton = screen.getByText('Limpar');
      fireEvent.click(clearButton);

      const scButton = screen.getByText('SC');
      fireEvent.click(scButton);

      expect(screen.getByText('1 estado selecionado')).toBeInTheDocument();
    });
  });

  describe('Date Range', () => {
    it('should have default dates (last 7 days)', () => {
      render(<HomePage />);

      const dataInicialInput = screen.getByLabelText('Data inicial:') as HTMLInputElement;
      const dataFinalInput = screen.getByLabelText('Data final:') as HTMLInputElement;

      const today = new Date().toISOString().split('T')[0];
      expect(dataFinalInput.value).toBe(today);

      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      const expected = sevenDaysAgo.toISOString().split('T')[0];
      expect(dataInicialInput.value).toBe(expected);
    });

    it('should update dates on change', () => {
      render(<HomePage />);

      const dataInicialInput = screen.getByLabelText('Data inicial:') as HTMLInputElement;
      const dataFinalInput = screen.getByLabelText('Data final:') as HTMLInputElement;

      fireEvent.change(dataInicialInput, { target: { value: '2024-01-01' } });
      fireEvent.change(dataFinalInput, { target: { value: '2024-01-15' } });

      expect(dataInicialInput.value).toBe('2024-01-01');
      expect(dataFinalInput.value).toBe('2024-01-15');
    });
  });

  describe('Validation - Min 1 UF', () => {
    it('should show error when no UF is selected', async () => {
      render(<HomePage />);

      const clearButton = screen.getByText('Limpar');
      fireEvent.click(clearButton);

      await waitFor(() => {
        expect(screen.getByText('Selecione pelo menos um estado')).toBeInTheDocument();
      });
    });

    it('should disable submit button when no UF is selected', () => {
      render(<HomePage />);

      const clearButton = screen.getByText('Limpar');
      fireEvent.click(clearButton);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Validation - Date Range Logic', () => {
    it('should show error when data_final < data_inicial', async () => {
      render(<HomePage />);

      const dataInicialInput = screen.getByLabelText('Data inicial:') as HTMLInputElement;
      const dataFinalInput = screen.getByLabelText('Data final:') as HTMLInputElement;

      fireEvent.change(dataInicialInput, { target: { value: '2024-02-01' } });
      fireEvent.change(dataFinalInput, { target: { value: '2024-01-15' } });

      await waitFor(() => {
        expect(screen.getByText('Data final deve ser maior ou igual à data inicial')).toBeInTheDocument();
      });
    });

    it('should disable submit button when date validation fails', async () => {
      render(<HomePage />);

      const dataInicialInput = screen.getByLabelText('Data inicial:') as HTMLInputElement;
      const dataFinalInput = screen.getByLabelText('Data final:') as HTMLInputElement;

      fireEvent.change(dataInicialInput, { target: { value: '2024-02-01' } });
      fireEvent.change(dataFinalInput, { target: { value: '2024-01-15' } });

      const submitButton = screen.getByRole('button', { name: /Buscar/ });

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });
    });
  });

  describe('Inline Error Messages', () => {
    it('should display inline error for UF validation with error styling', async () => {
      render(<HomePage />);

      const clearButton = screen.getByText('Limpar');
      fireEvent.click(clearButton);

      await waitFor(() => {
        const errorMessage = screen.getByText('Selecione pelo menos um estado');
        expect(errorMessage).toHaveClass('text-error');
      });
    });

    it('should display inline error for date range validation with error styling', async () => {
      render(<HomePage />);

      const dataInicialInput = screen.getByLabelText('Data inicial:') as HTMLInputElement;
      const dataFinalInput = screen.getByLabelText('Data final:') as HTMLInputElement;

      fireEvent.change(dataInicialInput, { target: { value: '2024-02-01' } });
      fireEvent.change(dataFinalInput, { target: { value: '2024-01-15' } });

      await waitFor(() => {
        const errorMessage = screen.getByText('Data final deve ser maior ou igual à data inicial');
        expect(errorMessage).toHaveClass('text-error');
      });
    });
  });

  describe('Submit Button State', () => {
    it('should be enabled when form is valid', () => {
      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      expect(submitButton).not.toBeDisabled();
    });

    it('should show loading state during search', async () => {
      mockPollingFlow(mockSuccessResponse);

      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      await act(async () => {
        fireEvent.click(submitButton);
      });

      expect(screen.getByText('Buscando...')).toBeInTheDocument();
      expect(screen.getByTestId('loading-progress')).toBeInTheDocument();
    });
  });

  describe('Header', () => {
    it('should render the DescompLicita logo', () => {
      render(<HomePage />);

      const logo = screen.getByAltText('DescompLicita');
      expect(logo).toBeInTheDocument();
    });

    it('should display "Busca Inteligente de Licitações" text', () => {
      render(<HomePage />);

      expect(screen.getByText('Busca Inteligente de Licitações')).toBeInTheDocument();
    });

    it('should have page title "Busca de Licitações"', () => {
      render(<HomePage />);

      expect(screen.getByRole('heading', { name: 'Busca de Licitações' })).toBeInTheDocument();
    });
  });

  describe('Responsive Layout', () => {
    it('should use grid layout for date inputs', () => {
      render(<HomePage />);

      const dataInicialContainer = screen.getByLabelText('Data inicial:').closest('div')?.parentElement;
      expect(dataInicialContainer).toHaveClass('grid');
    });
  });
});

describe('HomePage - Polling Flow & Results', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    (global.fetch as jest.Mock).mockRejectedValue(new Error('not found'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  async function triggerSearchAndComplete(resultData: Record<string, unknown> = mockSuccessResponse) {
    mockPollingFlow(resultData);
    render(<HomePage />);

    const submitButton = screen.getByRole('button', { name: /Buscar/ });
    await act(async () => {
      fireEvent.click(submitButton);
    });

    // Advance timer to trigger polling interval (2s)
    await act(async () => {
      jest.advanceTimersByTime(2100);
    });
  }

  describe('Search Flow', () => {
    it('should show loading progress after clicking search', async () => {
      mockPollingFlow(mockSuccessResponse);
      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      await act(async () => {
        fireEvent.click(submitButton);
      });

      expect(screen.getByTestId('loading-progress')).toBeInTheDocument();
    });

    it('should display cancel button during loading', async () => {
      mockPollingFlow(mockSuccessResponse);
      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      await act(async () => {
        fireEvent.click(submitButton);
      });

      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
    });

    it('should stop loading when cancel is clicked', async () => {
      mockPollingFlow(mockSuccessResponse);
      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      await act(async () => {
        fireEvent.click(submitButton);
      });

      const cancelButton = screen.getByTestId('cancel-button');
      await act(async () => {
        fireEvent.click(cancelButton);
      });

      expect(screen.queryByTestId('loading-progress')).not.toBeInTheDocument();
    });

    it('should display results after polling completes', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        expect(screen.getByText(/Encontradas 15 licitações/i)).toBeInTheDocument();
      });
    });
  });

  describe('Results Display', () => {
    it('should NOT render results section when result is null', () => {
      (global.fetch as jest.Mock).mockReset();
      (global.fetch as jest.Mock).mockRejectedValue(new Error('not found'));

      render(<HomePage />);

      expect(screen.queryByText('Destaques:')).not.toBeInTheDocument();
      expect(screen.queryByText(/Baixar Excel/i)).not.toBeInTheDocument();
      expect(screen.queryByText('valor total')).not.toBeInTheDocument();
    });

    it('should display resumo_executivo text', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        expect(screen.getByText('Encontradas 15 licitações de uniformes totalizando R$ 450.000,00')).toBeInTheDocument();
      });
    });

    it('should display summary in brand-themed card', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        const summaryText = screen.getByText(/Encontradas 15 licitações/i);
        const summaryCard = summaryText.closest('div');
        expect(summaryCard).toHaveClass('bg-brand-blue-subtle', 'border-accent');
      });
    });

    it('should display total_oportunidades as integer', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        const totalElement = screen.getByText('15');
        expect(totalElement).toHaveClass('text-brand-navy');
        expect(screen.getByText('oportunidades')).toBeInTheDocument();
      });
    });

    it('should display valor_total with Brazilian currency formatting', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        const valorTotalLabel = screen.getByText('valor total');
        const valueElement = valorTotalLabel.previousElementSibling;
        expect(valueElement).toHaveTextContent(/R\$ 450\.000/i);
        expect(valueElement).toHaveClass('text-brand-navy');
      });
    });

    it('should display urgency alert when alerta_urgencia is NOT null', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        const alertText = screen.getByText(/Licitação com prazo em menos de 7 dias/i);
        expect(alertText).toBeInTheDocument();

        const alertBox = alertText.closest('div');
        expect(alertBox).toHaveClass('bg-warning-subtle');
        expect(alertBox).toHaveAttribute('role', 'alert');
      });
    });

    it('should NOT display urgency alert when alerta_urgencia is null', async () => {
      await triggerSearchAndComplete({
        ...mockSuccessResponse,
        resumo: { ...mockSuccessResponse.resumo, alerta_urgencia: null },
      });

      await waitFor(() => {
        expect(screen.getByText(/Encontradas 15 licitações/i)).toBeInTheDocument();
      });

      expect(screen.queryByText(/Licitação com prazo/i)).not.toBeInTheDocument();
    });

    it('should display highlights when destaques array has items', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        expect(screen.getByText('Destaques:')).toBeInTheDocument();
        expect(screen.getByText(/Uniformes escolares - Secretaria de Educação SC/i)).toBeInTheDocument();
        expect(screen.getByText(/Fardamento militar - PM-PR/i)).toBeInTheDocument();
      });
    });

    it('should NOT display highlights when destaques is empty', async () => {
      await triggerSearchAndComplete({
        ...mockSuccessResponse,
        resumo: { ...mockSuccessResponse.resumo, destaques: [] },
      });

      await waitFor(() => {
        expect(screen.getByText(/Encontradas 15 licitações/i)).toBeInTheDocument();
      });

      expect(screen.queryByText('Destaques:')).not.toBeInTheDocument();
    });

    it('should render download button', async () => {
      await triggerSearchAndComplete();

      await waitFor(() => {
        const downloadButton = screen.getByRole('button', { name: /Baixar Excel/i });
        expect(downloadButton).toBeInTheDocument();
        expect(downloadButton).toBeEnabled();
        expect(downloadButton).toHaveClass('bg-brand-navy', 'text-white');
      });
    });
  });

  describe('Edge Cases', () => {
    it('should render EmptyState when zero opportunities', async () => {
      await triggerSearchAndComplete({
        resumo: {
          resumo_executivo: 'Nenhuma licitação encontrada',
          total_oportunidades: 0,
          valor_total: 0,
          destaques: [],
          distribuicao_uf: {},
          alerta_urgencia: null,
        },
        download_id: 'empty-id',
        total_raw: 0,
        total_filtrado: 0,
        total_atas: 0,
        total_licitacoes: 0,
        filter_stats: null,
        sources_used: [],
        source_stats: {},
        dedup_removed: 0,
        truncated_combos: 0,
      });

      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      });

      expect(screen.queryByRole('button', { name: /Baixar Excel/i })).not.toBeInTheDocument();
    });

    it('should handle API error gracefully', async () => {
      (global.fetch as jest.Mock)
        .mockRejectedValueOnce(new Error('not found')) // setores
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ message: 'Backend unavailable' }),
        });

      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      await act(async () => {
        fireEvent.click(submitButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Backend unavailable')).toBeInTheDocument();
      });

      expect(screen.queryByText(/Baixar Excel/i)).not.toBeInTheDocument();
    });

    it('should show retry button on error', async () => {
      (global.fetch as jest.Mock)
        .mockRejectedValueOnce(new Error('not found'))
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ message: 'Erro no backend' }),
        });

      render(<HomePage />);

      const submitButton = screen.getByRole('button', { name: /Buscar/ });
      await act(async () => {
        fireEvent.click(submitButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Tentar novamente')).toBeInTheDocument();
      });
    });
  });
});
