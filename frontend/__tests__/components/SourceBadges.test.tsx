import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SourceBadges } from '@/app/components/SourceBadges';
import type { SourceStats } from '@/app/types';

const makeStats = (overrides?: Partial<SourceStats>): SourceStats => ({
  total_fetched: 10,
  after_dedup: 10,
  elapsed_ms: 120,
  status: 'success',
  error_message: null,
  ...overrides,
});

const defaultStats: Record<string, SourceStats> = {
  pncp: makeStats({ total_fetched: 15, after_dedup: 14, elapsed_ms: 200 }),
  comprasgov: makeStats({ total_fetched: 5, after_dedup: 5, elapsed_ms: 80 }),
};

const defaultSources = ['pncp', 'comprasgov'];

describe('SourceBadges', () => {
  it('renders source badges with correct labels', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
      />
    );
    expect(screen.getByText(/PNCP: 15/)).toBeInTheDocument();
    expect(screen.getByText(/Compras\.gov: 5/)).toBeInTheDocument();
  });

  it('shows correct number of sources in toggle label (plural)', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
      />
    );
    expect(screen.getByText('2 fontes consultadas')).toBeInTheDocument();
  });

  it('shows singular label when there is 1 source', () => {
    render(
      <SourceBadges
        sources={['pncp']}
        stats={{ pncp: makeStats({ total_fetched: 3, after_dedup: 3, elapsed_ms: 50 }) }}
        dedupRemoved={0}
      />
    );
    expect(screen.getByText('1 fonte consultada')).toBeInTheDocument();
  });

  it('applies green status classes for success with items', () => {
    render(
      <SourceBadges
        sources={['pncp']}
        stats={{ pncp: makeStats({ total_fetched: 5, after_dedup: 5, elapsed_ms: 100, status: 'success' }) }}
        dedupRemoved={0}
      />
    );
    const badge = screen.getByText(/PNCP: 5/).closest('span');
    expect(badge).toHaveClass('bg-status-success-bg');
  });

  it('applies warning status classes for success with 0 items', () => {
    render(
      <SourceBadges
        sources={['pncp']}
        stats={{ pncp: makeStats({ total_fetched: 0, after_dedup: 0, elapsed_ms: 50, status: 'success' }) }}
        dedupRemoved={0}
      />
    );
    const badge = screen.getByText(/PNCP: 0/).closest('span');
    expect(badge).toHaveClass('bg-status-warning-bg');
  });

  it('applies error status classes for error status', () => {
    render(
      <SourceBadges
        sources={['pncp']}
        stats={{ pncp: makeStats({ total_fetched: 0, after_dedup: 0, elapsed_ms: 0, status: 'error', error_message: 'timeout' }) }}
        dedupRemoved={0}
      />
    );
    const badge = screen.getByText(/PNCP: 0/).closest('span');
    expect(badge).toHaveClass('bg-status-error-bg');
  });

  it('toggles expanded state when button is clicked (aria-expanded)', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
      />
    );
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows detailed stats panel when expanded', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
      />
    );
    // Detail panel not visible initially
    expect(screen.queryByText('15 encontradas')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('15 encontradas')).toBeInTheDocument();
    expect(screen.getByText('200ms')).toBeInTheDocument();
  });

  it('shows dedup message when dedupRemoved > 0 and expanded', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={3}
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/3 registros duplicados removidos/)).toBeInTheDocument();
  });

  it('shows singular dedup message when dedupRemoved is 1', () => {
    render(
      <SourceBadges
        sources={['pncp']}
        stats={{ pncp: makeStats({ total_fetched: 5, after_dedup: 4, elapsed_ms: 100 }) }}
        dedupRemoved={1}
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/1 registro duplicado removido/)).toBeInTheDocument();
  });

  it('shows truncation warning when truncatedCombos > 0 and expanded', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
        truncatedCombos={4}
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/Resultados parciais/)).toBeInTheDocument();
    expect(screen.getByText(/4 combinac/)).toBeInTheDocument();
  });

  it('does NOT show truncation warning when truncatedCombos is 0', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
        truncatedCombos={0}
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText(/Resultados parciais/)).not.toBeInTheDocument();
  });

  it('does NOT show truncation warning when truncatedCombos is omitted', () => {
    render(
      <SourceBadges
        sources={defaultSources}
        stats={defaultStats}
        dedupRemoved={0}
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText(/Resultados parciais/)).not.toBeInTheDocument();
  });

  it('returns null when sources array is empty', () => {
    const { container } = render(
      <SourceBadges
        sources={[]}
        stats={{}}
        dedupRemoved={0}
      />
    );
    expect(container.firstChild).toBeNull();
  });
});
