import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UfSelector } from '@/app/components/UfSelector';

jest.mock('@/app/components/RegionSelector', () => ({
  RegionSelector: () => <div data-testid="region-selector" />,
  REGIONS: {},
}));

describe('UfSelector', () => {
  const defaultProps = {
    ufsSelecionadas: new Set(['SC', 'PR', 'RS']),
    onToggleUf: jest.fn(),
    onToggleRegion: jest.fn(),
    onSelecionarTodos: jest.fn(),
    onLimparSelecao: jest.fn(),
    validationErrors: {},
  };

  it('should render all 27 UF buttons', () => {
    render(<UfSelector {...defaultProps} />);
    expect(screen.getAllByRole('button', { pressed: true }).length + screen.getAllByRole('button', { pressed: false }).length).toBeGreaterThanOrEqual(27);
  });

  it('should highlight selected UFs', () => {
    render(<UfSelector {...defaultProps} />);
    expect(screen.getByText('SC')).toHaveClass('bg-brand-navy');
    expect(screen.getByText('SP')).not.toHaveClass('bg-brand-navy');
  });

  it('should call onToggleUf when UF button clicked', () => {
    render(<UfSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('SP'));
    expect(defaultProps.onToggleUf).toHaveBeenCalledWith('SP');
  });

  it('should call onSelecionarTodos when "Selecionar todos" clicked', () => {
    render(<UfSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('Selecionar todos'));
    expect(defaultProps.onSelecionarTodos).toHaveBeenCalled();
  });

  it('should call onLimparSelecao when "Limpar" clicked', () => {
    render(<UfSelector {...defaultProps} />);
    fireEvent.click(screen.getByText('Limpar'));
    expect(defaultProps.onLimparSelecao).toHaveBeenCalled();
  });

  it('should display count of selected UFs', () => {
    render(<UfSelector {...defaultProps} />);
    expect(screen.getByText('3 estados selecionados')).toBeInTheDocument();
  });

  it('should display singular form for 1 state', () => {
    render(<UfSelector {...defaultProps} ufsSelecionadas={new Set(['SC'])} />);
    expect(screen.getByText('1 estado selecionado')).toBeInTheDocument();
  });

  it('should display validation error when present', () => {
    render(<UfSelector {...defaultProps} validationErrors={{ ufs: 'Selecione pelo menos um estado' }} />);
    expect(screen.getByText('Selecione pelo menos um estado')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should render RegionSelector', () => {
    render(<UfSelector {...defaultProps} />);
    expect(screen.getByTestId('region-selector')).toBeInTheDocument();
  });

  it('should have aria-pressed on UF buttons', () => {
    render(<UfSelector {...defaultProps} />);
    expect(screen.getByText('SC')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('SP')).toHaveAttribute('aria-pressed', 'false');
  });
});
