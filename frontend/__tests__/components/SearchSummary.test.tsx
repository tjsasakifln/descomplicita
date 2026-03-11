import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchSummary } from '@/app/components/SearchSummary';
import type { BuscaResult } from '@/app/types';

jest.mock('@/app/components/SourceBadges', () => ({
  SourceBadges: () => <div data-testid="source-badges" />,
  default: () => <div data-testid="source-badges" />,
}));

const mockResult: BuscaResult = {
  resumo: {
    resumo_executivo: 'Encontradas 15 licitações de uniformes',
    total_oportunidades: 15,
    valor_total: 450000,
    destaques: ['Destaque 1', 'Destaque 2'],
    distribuicao_uf: { SC: 6, PR: 5, RS: 4 },
    alerta_urgencia: 'Urgência: prazo curto',
  },
  download_id: 'dl-1',
  total_raw: 200,
  total_filtrado: 15,
  total_atas: 5,
  total_licitacoes: 10,
  filter_stats: null,
  sources_used: ['pncp'],
  source_stats: { pncp: { total_fetched: 200, after_dedup: 195, elapsed_ms: 500, status: 'success', error_message: null } },
  dedup_removed: 5,
  truncated_combos: 0,
};

describe('SearchSummary', () => {
  it('should display executive summary', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText('Encontradas 15 licitações de uniformes')).toBeInTheDocument();
  });

  it('should display total opportunities count', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('oportunidades')).toBeInTheDocument();
  });

  it('should display total value with currency format', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText(/R\$ 450\.000/)).toBeInTheDocument();
    expect(screen.getByText('valor total')).toBeInTheDocument();
  });

  it('should display licitações badge when total_licitacoes > 0', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText(/10 Licitações/)).toBeInTheDocument();
  });

  it('should display atas badge when total_atas > 0', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText(/5 Atas RP/)).toBeInTheDocument();
  });

  it('should display urgency alert', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText(/Urgência: prazo curto/)).toBeInTheDocument();
    const alertDiv = screen.getByText(/Urgência: prazo curto/).closest('div');
    expect(alertDiv).toHaveClass('bg-warning-subtle');
  });

  it('should not display urgency alert when null', () => {
    const noAlert = { ...mockResult, resumo: { ...mockResult.resumo, alerta_urgencia: null } };
    render(<SearchSummary result={noAlert} />);
    expect(screen.queryByText('Atenção:')).not.toBeInTheDocument();
  });

  it('should display highlights', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByText('Destaques:')).toBeInTheDocument();
    expect(screen.getByText('Destaque 1')).toBeInTheDocument();
    expect(screen.getByText('Destaque 2')).toBeInTheDocument();
  });

  it('should not display highlights when empty', () => {
    const noHighlights = { ...mockResult, resumo: { ...mockResult.resumo, destaques: [] } };
    render(<SearchSummary result={noHighlights} />);
    expect(screen.queryByText('Destaques:')).not.toBeInTheDocument();
  });

  it('should render SourceBadges when sources available', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.getByTestId('source-badges')).toBeInTheDocument();
  });

  it('should use brand styling', () => {
    render(<SearchSummary result={mockResult} />);
    const card = screen.getByText('Encontradas 15 licitações de uniformes').closest('div');
    expect(card).toHaveClass('bg-brand-blue-subtle', 'border-accent');
  });

  it('should display freshness timestamp when completedAt is provided', () => {
    const completedAt = new Date('2026-03-10T14:30:00');
    render(<SearchSummary result={mockResult} completedAt={completedAt} />);
    const expected = completedAt.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
    expect(screen.getByText(new RegExp(`Dados consultados em ${expected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`))).toBeInTheDocument();
  });

  it('should not display freshness timestamp when completedAt is not provided', () => {
    render(<SearchSummary result={mockResult} />);
    expect(screen.queryByText(/Dados consultados em/)).not.toBeInTheDocument();
  });
});
