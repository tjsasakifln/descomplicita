import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { StageList, STAGES } from '@/app/components/loading-progress/StageList';

describe('StageList', () => {
  it('should render all 5 stages', () => {
    render(
      <StageList
        currentStageIndex={0}
        statusMessage="Iniciando busca..."
        stageConfig={STAGES[0]}
      />
    );
    // Stage labels appear in both the desktop list and mobile detail
    expect(screen.getAllByText('Iniciando busca').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Buscando licitações')).toBeInTheDocument();
    expect(screen.getByText('Filtrando resultados')).toBeInTheDocument();
    expect(screen.getByText('Gerando resumo IA')).toBeInTheDocument();
    expect(screen.getByText('Preparando planilha')).toBeInTheDocument();
  });

  it('should highlight current stage', () => {
    const { container } = render(
      <StageList
        currentStageIndex={2}
        statusMessage="Filtrando resultados..."
        stageConfig={STAGES[2]}
      />
    );
    const circles = container.querySelectorAll('.rounded-full');
    // Circles 0,1 should be past (brand-navy), circle 2 current (brand-blue), 3,4 future (surface-2)
    expect(circles[0].className).toContain('bg-brand-navy');
    expect(circles[1].className).toContain('bg-brand-navy');
    expect(circles[2].className).toContain('bg-brand-blue');
    expect(circles[3].className).toContain('bg-surface-2');
    expect(circles[4].className).toContain('bg-surface-2');
  });

  it('should show mobile stage detail', () => {
    render(
      <StageList
        currentStageIndex={1}
        statusMessage="Buscando em 2/5 estados..."
        stageConfig={STAGES[1]}
      />
    );
    // Mobile detail shows status message
    expect(screen.getByText('Buscando em 2/5 estados...')).toBeInTheDocument();
  });

  it('should export STAGES constant with 5 items', () => {
    expect(STAGES).toHaveLength(5);
    expect(STAGES[0].id).toBe('queued');
    expect(STAGES[4].id).toBe('generating_excel');
  });
});
